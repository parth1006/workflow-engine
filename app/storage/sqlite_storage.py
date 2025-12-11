"""
SQLite storage implementation for the workflow engine.

Uses aiosqlite for async database operations.
Stores graphs and runs with JSON serialization for complex fields.
"""
import aiosqlite
import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from app.core.models import GraphDefinition, Run, NodeDefinition, EdgeDefinition, WorkflowState, ExecutionLog
from app.storage.base import StorageInterface

logger = logging.getLogger(__name__)


class SQLiteStorage(StorageInterface):
    """
    SQLite-based storage implementation.
    
    Schema:
        - graphs: Stores graph definitions
        - runs: Stores workflow runs
    """
    
    def __init__(self, db_path: str = "data/workflow.db"):
        """
        Initialize SQLite storage.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> None:
        """
        Initialize database connection and create tables.
        """
        self.db = await aiosqlite.connect(self.db_path)
        self.db.row_factory = aiosqlite.Row  # Access columns by name
        
        # Create tables
        await self._create_tables()
        logger.info(f"Initialized SQLite storage at {self.db_path}")
    
    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        
        # Graphs table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS graphs (
                graph_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                nodes TEXT NOT NULL,
                edges TEXT NOT NULL,
                entry_point TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Runs table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                status TEXT NOT NULL,
                current_node TEXT,
                current_state TEXT NOT NULL,
                execution_logs TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error TEXT,
                iteration_count INTEGER DEFAULT 0,
                max_iterations INTEGER DEFAULT 10,
                FOREIGN KEY (graph_id) REFERENCES graphs(graph_id)
            )
        """)
        
        # Create indices for better query performance
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_graph_id 
            ON runs(graph_id)
        """)
        
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_status 
            ON runs(status)
        """)
        
        await self.db.commit()
    
    # ========================================================================
    # GRAPH OPERATIONS
    # ========================================================================
    
    async def save_graph(self, graph: GraphDefinition) -> str:
        """Save a graph definition."""
        
        # Serialize complex fields to JSON
        nodes_json = json.dumps([node.model_dump() for node in graph.nodes])
        edges_json = json.dumps([edge.model_dump() for edge in graph.edges])
        
        await self.db.execute("""
            INSERT INTO graphs (
                graph_id, name, description, nodes, edges, entry_point, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            graph.graph_id,
            graph.name,
            graph.description,
            nodes_json,
            edges_json,
            graph.entry_point,
            graph.created_at.isoformat()
        ))
        
        await self.db.commit()
        logger.info(f"Saved graph: {graph.graph_id}")
        return graph.graph_id
    
    async def get_graph(self, graph_id: str) -> Optional[GraphDefinition]:
        """Retrieve a graph by ID."""
        
        async with self.db.execute(
            "SELECT * FROM graphs WHERE graph_id = ?",
            (graph_id,)
        ) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        # Deserialize JSON fields
        nodes = [NodeDefinition(**node) for node in json.loads(row['nodes'])]
        edges = [EdgeDefinition(**edge) for edge in json.loads(row['edges'])]
        
        return GraphDefinition(
            graph_id=row['graph_id'],
            name=row['name'],
            description=row['description'],
            nodes=nodes,
            edges=edges,
            entry_point=row['entry_point'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    async def list_graphs(self) -> List[GraphDefinition]:
        """List all graphs."""
        
        async with self.db.execute(
            "SELECT * FROM graphs ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
        
        graphs = []
        for row in rows:
            nodes = [NodeDefinition(**node) for node in json.loads(row['nodes'])]
            edges = [EdgeDefinition(**edge) for edge in json.loads(row['edges'])]
            
            graphs.append(GraphDefinition(
                graph_id=row['graph_id'],
                name=row['name'],
                description=row['description'],
                nodes=nodes,
                edges=edges,
                entry_point=row['entry_point'],
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        
        return graphs
    
    async def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph."""
        
        cursor = await self.db.execute(
            "DELETE FROM graphs WHERE graph_id = ?",
            (graph_id,)
        )
        await self.db.commit()
        
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted graph: {graph_id}")
        return deleted
    
    # ========================================================================
    # RUN OPERATIONS
    # ========================================================================
    
    async def save_run(self, run: Run) -> str:
        """Save a new run."""
        
        # Serialize complex fields - FIX: Convert datetime to string first
        current_state_json = json.dumps(run.current_state.model_dump())
        
        # FIX: Manually serialize execution logs with datetime conversion
        execution_logs_data = []
        for log in run.execution_logs:
            log_dict = {
                "node_name": log.node_name,
                "timestamp": log.timestamp.isoformat() if hasattr(log.timestamp, 'isoformat') else str(log.timestamp),
                "input_state": log.input_state,
                "output_state": log.output_state,
                "execution_time_ms": log.execution_time_ms,
                "success": log.success,
                "error": log.error
            }
            execution_logs_data.append(log_dict)
        
        execution_logs_json = json.dumps(execution_logs_data)
        
        # Handle status - could be enum or string
        status_value = run.status.value if hasattr(run.status, 'value') else run.status
        
        await self.db.execute("""
            INSERT INTO runs (
                run_id, graph_id, status, current_node, current_state,
                execution_logs, started_at, completed_at, error,
                iteration_count, max_iterations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.run_id,
            run.graph_id,
            status_value,
            run.current_node,
            current_state_json,
            execution_logs_json,
            run.started_at.isoformat() if run.started_at else None,
            run.completed_at.isoformat() if run.completed_at else None,
            run.error,
            run.iteration_count,
            run.max_iterations
        ))
        
        await self.db.commit()
        logger.info(f"Saved run: {run.run_id}")
        return run.run_id
    
    async def get_run(self, run_id: str) -> Optional[Run]:
        """Retrieve a run by ID."""
        
        async with self.db.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
        
        if not row:
            return None
        
        # Deserialize JSON fields
        current_state_data = json.loads(row['current_state'])
        current_state = WorkflowState(**current_state_data)
        
        execution_logs_data = json.loads(row['execution_logs'])
        execution_logs = [ExecutionLog(**log) for log in execution_logs_data]
        
        return Run(
            run_id=row['run_id'],
            graph_id=row['graph_id'],
            status=row['status'],
            current_node=row['current_node'],
            current_state=current_state,
            execution_logs=execution_logs,
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            error=row['error'],
            iteration_count=row['iteration_count'],
            max_iterations=row['max_iterations']
        )
    
    async def update_run(self, run: Run) -> None:
        """Update an existing run."""
        
        # Serialize complex fields - FIX: Convert datetime to string first
        current_state_json = json.dumps(run.current_state.model_dump())
        
        # FIX: Manually serialize execution logs with datetime conversion
        execution_logs_data = []
        for log in run.execution_logs:
            log_dict = {
                "node_name": log.node_name,
                "timestamp": log.timestamp.isoformat() if hasattr(log.timestamp, 'isoformat') else str(log.timestamp),
                "input_state": log.input_state,
                "output_state": log.output_state,
                "execution_time_ms": log.execution_time_ms,
                "success": log.success,
                "error": log.error
            }
            execution_logs_data.append(log_dict)
        
        execution_logs_json = json.dumps(execution_logs_data)
        
        # Handle status - could be enum or string
        status_value = run.status.value if hasattr(run.status, 'value') else run.status
        
        await self.db.execute("""
            UPDATE runs SET
                status = ?,
                current_node = ?,
                current_state = ?,
                execution_logs = ?,
                started_at = ?,
                completed_at = ?,
                error = ?,
                iteration_count = ?,
                max_iterations = ?
            WHERE run_id = ?
        """, (
            status_value,
            run.current_node,
            current_state_json,
            execution_logs_json,
            run.started_at.isoformat() if run.started_at else None,
            run.completed_at.isoformat() if run.completed_at else None,
            run.error,
            run.iteration_count,
            run.max_iterations,
            run.run_id
        ))
        
        await self.db.commit()
        logger.debug(f"Updated run: {run.run_id}")
    
    async def list_runs(
        self,
        graph_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Run]:
        """List runs, optionally filtered by graph_id."""
        
        if graph_id:
            query = """
                SELECT * FROM runs 
                WHERE graph_id = ? 
                ORDER BY started_at DESC 
                LIMIT ?
            """
            params = (graph_id, limit)
        else:
            query = """
                SELECT * FROM runs 
                ORDER BY started_at DESC 
                LIMIT ?
            """
            params = (limit,)
        
        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
        
        runs = []
        for row in rows:
            current_state_data = json.loads(row['current_state'])
            current_state = WorkflowState(**current_state_data)
            
            execution_logs_data = json.loads(row['execution_logs'])
            execution_logs = [ExecutionLog(**log) for log in execution_logs_data]
            
            runs.append(Run(
                run_id=row['run_id'],
                graph_id=row['graph_id'],
                status=row['status'],
                current_node=row['current_node'],
                current_state=current_state,
                execution_logs=execution_logs,
                started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                error=row['error'],
                iteration_count=row['iteration_count'],
                max_iterations=row['max_iterations']
            ))
        
        return runs
    
    async def close(self) -> None:
        """Close the database connection."""
        if self.db:
            await self.db.close()
            logger.info("Closed SQLite storage connection")