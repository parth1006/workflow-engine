"""
FastAPI routes for the workflow engine.

Exposes endpoints for creating graphs, running workflows, and checking status.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging

from app.core.models import (
    CreateGraphRequest, CreateGraphResponse,
    RunGraphRequest, RunGraphResponse,
    GetStateResponse, GraphDefinition, RunStatus
)
from app.core.graph_engine import GraphEngine
from app.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/graph", tags=["workflows"])

# Initialize storage (will be properly initialized in main.py)
storage: SQLiteStorage = None
engine = GraphEngine()


def set_storage(storage_instance: SQLiteStorage):
    """Set the storage instance (called from main.py on startup)."""
    global storage
    storage = storage_instance


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/create",
    response_model=CreateGraphResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workflow graph",
    description="Define a workflow graph with nodes and edges. Returns a unique graph_id."
)
async def create_graph(request: CreateGraphRequest) -> CreateGraphResponse:
    """
    Create a new workflow graph.
    
    The graph definition includes:
    - **nodes**: List of node definitions (name, type, tool)
    - **edges**: List of edges connecting nodes
    - **entry_point**: Starting node name
    
    Returns:
        Graph ID and success message
    """
    try:
        # Validate entry point exists
        node_names = {node.name for node in request.nodes}
        if request.entry_point not in node_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Entry point '{request.entry_point}' not found in nodes"
            )
        
        # Validate edges reference valid nodes
        for edge in request.edges:
            if edge.from_node not in node_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Edge from_node '{edge.from_node}' not found in nodes"
                )
            if edge.to_node not in node_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Edge to_node '{edge.to_node}' not found in nodes"
                )
        
        # Create graph definition
        graph = GraphDefinition(
            name=request.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
            entry_point=request.entry_point
        )
        
        # Save to storage
        graph_id = await storage.save_graph(graph)
        
        logger.info(f"Created graph '{graph.name}' with ID: {graph_id}")
        
        return CreateGraphResponse(
            graph_id=graph_id,
            message=f"Graph '{graph.name}' created successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create graph: {str(e)}"
        )


@router.post(
    "/run",
    status_code=status.HTTP_200_OK,
    summary="Execute a workflow graph",
    description="Run a workflow graph with initial state. Returns final state and execution logs."
)
async def run_graph(request: RunGraphRequest):
    """
    Execute a workflow graph.
    
    Runs the graph from start to finish with the provided initial state.
    
    Args:
        request: Contains graph_id and initial_state
        
    Returns:
        Run results including final state, logs, and execution statistics
    """
    try:
        # Retrieve graph
        graph = await storage.get_graph(request.graph_id)
        if not graph:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Graph with ID '{request.graph_id}' not found"
            )
        
        logger.info(f"Starting execution of graph '{graph.name}' ({request.graph_id})")
        
        # Execute graph
        run = await engine.execute(
            graph=graph,
            initial_state=request.initial_state,
            max_iterations=10  # Default safety limit
        )
        
        # DEBUG: Check what we have
        logger.info(f"Run status: {run.status}")
        logger.info(f"Execution logs count: {len(run.execution_logs)}")
        
        # Save run to storage
        logger.info("Saving run to storage...")
        await storage.save_run(run)
        logger.info("Run saved successfully")
        
        # Calculate total execution time
        total_time = sum(log.execution_time_ms for log in run.execution_logs)
        
        logger.info(
            f"Execution completed. Status: {run.status}, "
            f"Nodes executed: {len(run.execution_logs)}, "
            f"Total time: {total_time:.2f}ms"
        )
        
        # DEBUG: Try to serialize each log individually
        serialized_logs = []
        for i, log in enumerate(run.execution_logs):
            try:
                log_dict = log.model_dump(mode='json')
                logger.info(f"Log {i} serialized successfully")
                serialized_logs.append(log_dict)
            except Exception as e:
                logger.error(f"Failed to serialize log {i}: {e}")
                logger.error(f"Log timestamp type: {type(log.timestamp)}")
                raise
        
        # Use Pydantic's model_dump with mode='json' for proper serialization
        return {
            "run_id": run.run_id,
            "status": run.status.value if hasattr(run.status, 'value') else run.status,
            "final_state": run.current_state.data,
            "execution_logs": serialized_logs,
            "total_execution_time_ms": total_time,
            "iterations_completed": run.iteration_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Failed to execute graph: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute graph: {str(e)}"
        )


@router.get(
    "/state/{run_id}",
    status_code=status.HTTP_200_OK,
    summary="Get workflow run state",
    description="Retrieve the current state and status of a workflow run."
)
async def get_run_state(run_id: str):
    """
    Get the current state of a workflow run.
    
    Useful for checking the status of long-running workflows
    or retrieving results of completed runs.
    
    Args:
        run_id: Unique identifier of the run
        
    Returns:
        Current run state, status, and metadata
    """
    try:
        # Retrieve run from storage
        run = await storage.get_run(run_id)
        
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Run with ID '{run_id}' not found"
            )
        
        return {
            "run_id": run.run_id,
            "status": run.status.value if hasattr(run.status, 'value') else run.status,
            "current_node": run.current_node,
            "current_state": run.current_state.data,
            "iterations_completed": run.iteration_count,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve run state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve run state: {str(e)}"
        )


@router.get(
    "/list",
    status_code=status.HTTP_200_OK,
    summary="List all graphs",
    description="Retrieve a list of all workflow graphs."
)
async def list_graphs():
    """
    List all available workflow graphs.
    
    Returns:
        List of graph definitions with metadata
    """
    try:
        graphs = await storage.list_graphs()
        
        return {
            "count": len(graphs),
            "graphs": [
                {
                    "graph_id": g.graph_id,
                    "name": g.name,
                    "description": g.description,
                    "node_count": len(g.nodes),
                    "edge_count": len(g.edges),
                    "entry_point": g.entry_point,
                    "created_at": g.created_at.isoformat()
                }
                for g in graphs
            ]
        }
    
    except Exception as e:
        logger.error(f"Failed to list graphs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list graphs: {str(e)}"
        )


@router.get(
    "/runs/{graph_id}",
    status_code=status.HTTP_200_OK,
    summary="List runs for a graph",
    description="Retrieve execution history for a specific graph."
)
async def list_runs(graph_id: str, limit: int = 10):
    """
    List all runs for a specific graph.
    
    Args:
        graph_id: Graph identifier
        limit: Maximum number of runs to return (default: 10)
        
    Returns:
        List of run summaries
    """
    try:
        # Verify graph exists
        graph = await storage.get_graph(graph_id)
        if not graph:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Graph with ID '{graph_id}' not found"
            )
        
        runs = await storage.list_runs(graph_id=graph_id, limit=limit)
        
        return {
            "graph_id": graph_id,
            "graph_name": graph.name,
            "count": len(runs),
            "runs": [
                {
                    "run_id": r.run_id,
                    "status": r.status.value if hasattr(r.status, 'value') else r.status,
                    "iterations": r.iteration_count,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "error": r.error
                }
                for r in runs
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list runs: {str(e)}"
        )