"""
Core graph execution engine for the workflow system.

Handles node traversal, state management, branching, and looping.
"""
import asyncio
import copy
import time
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone

from app.core.models import (
    GraphDefinition, NodeDefinition, EdgeDefinition, Run,
    RunStatus, WorkflowState, ExecutionLog, NodeType
)
from app.core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class GraphEngine:
    """
    Executes workflow graphs by traversing nodes and managing state.
    
    Supports:
    - Sequential execution
    - Conditional branching
    - Loops with max iteration safety
    """
    
    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """
        Initialize the graph engine.
        
        Args:
            tool_registry: Optional custom tool registry. Uses global if None.
        """
        self.tool_registry = tool_registry or ToolRegistry()
    
    async def execute(
        self,
        graph: GraphDefinition,
        initial_state: Dict[str, Any],
        max_iterations: int = 10
    ) -> Run:
        """
        Execute a workflow graph from start to finish.
        
        Args:
            graph: The graph definition to execute
            initial_state: Starting state data
            max_iterations: Maximum loop iterations (safety limit)
            
        Returns:
            Completed Run object with final state and execution logs
        """
        # Initialize run
        run = Run(
            graph_id=graph.graph_id,
            status=RunStatus.RUNNING,
            current_node=graph.entry_point,
            current_state=WorkflowState(
                data=initial_state,
                metadata={"graph_name": graph.name}
            ),
            started_at=datetime.now(timezone.utc),
            max_iterations=max_iterations
        )
        
        logger.info(f"Starting execution of graph '{graph.name}' (run_id: {run.run_id})")
        
        try:
            # Build adjacency map for efficient traversal
            adjacency_map = self._build_adjacency_map(graph.edges)
            node_map = {node.name: node for node in graph.nodes}
            
            # Start execution from entry point
            current_node_name = graph.entry_point
            visited_nodes: Set[str] = set()
            
            while current_node_name:
                # Safety check: prevent infinite loops
                if run.iteration_count >= max_iterations:
                    raise RuntimeError(
                        f"Maximum iterations ({max_iterations}) exceeded. "
                        f"Possible infinite loop detected."
                    )
                
                # Check if node exists
                if current_node_name not in node_map:
                    raise ValueError(f"Node '{current_node_name}' not found in graph")
                
                current_node = node_map[current_node_name]
                run.current_node = current_node_name
                
                logger.info(f"Executing node: {current_node_name}")
                
                # Execute the node
                execution_log = await self._execute_node(
                    node=current_node,
                    state=run.current_state,
                    iteration=run.iteration_count
                )
                
                # Add log to run
                run.execution_logs.append(execution_log)
                
                # Check if execution failed
                if not execution_log.success:
                    run.status = RunStatus.FAILED
                    run.error = execution_log.error
                    run.completed_at = datetime.now(timezone.utc)
                    logger.error(f"Node execution failed: {execution_log.error}")
                    break
                
                # Update state from execution
                run.current_state = WorkflowState(
                    data=execution_log.output_state,
                    metadata=run.current_state.metadata
                )
                
                # Track visited nodes for loop detection
                visited_nodes.add(current_node_name)
                
                # Determine next node
                next_node = await self._get_next_node(
                    current_node_name=current_node_name,
                    adjacency_map=adjacency_map,
                    state=run.current_state.data
                )
                
                # Check if we're looping back to a visited node
                if next_node and next_node in visited_nodes:
                    run.iteration_count += 1
                    logger.info(f"Loop detected. Iteration: {run.iteration_count}")
                
                # Move to next node
                current_node_name = next_node
                
                # If no next node, we've reached the end
                if not current_node_name:
                    logger.info("Reached terminal node. Execution complete.")
                    break
            
            # Mark as completed
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                f"Execution completed successfully. "
                f"Total nodes executed: {len(run.execution_logs)}, "
                f"Iterations: {run.iteration_count}"
            )
            
        except Exception as e:
            # Handle any unexpected errors
            run.status = RunStatus.FAILED
            run.error = str(e)
            run.completed_at = datetime.now(timezone.utc)
            logger.exception(f"Graph execution failed: {e}")
        
        return run
    
    async def _execute_node(
        self,
        node: NodeDefinition,
        state: WorkflowState,
        iteration: int
    ) -> ExecutionLog:
        """
        Execute a single node.
        
        Args:
            node: The node to execute
            state: Current workflow state
            iteration: Current iteration count
            
        Returns:
            Execution log with results
        """
        start_time = time.time()
        input_state = copy.deepcopy(state.data)
        
        try:
            # Handle different node types
            if node.node_type == NodeType.FUNCTION:
                # Execute function node (calls a tool)
                output_state = await self._execute_function_node(node, state.data)
            
            elif node.node_type == NodeType.CONDITIONAL:
                # Conditional nodes don't modify state, just used for routing
                output_state = state.data
            
            elif node.node_type in [NodeType.START, NodeType.END]:
                # Special nodes that don't execute anything
                output_state = state.data
            
            else:
                raise ValueError(f"Unknown node type: {node.node_type}")
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return ExecutionLog(
                node_name=node.name,
                timestamp=datetime.now(timezone.utc),
                input_state=input_state,
                output_state=output_state,
                execution_time_ms=execution_time,
                success=True
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Node '{node.name}' execution failed: {e}")
            
            return ExecutionLog(
                node_name=node.name,
                timestamp=datetime.now(timezone.utc),
                input_state=input_state,
                output_state=input_state,  # Return unchanged state on error
                execution_time_ms=execution_time,
                success=False,
                error=str(e)
            )
    
    async def _execute_function_node(
        self,
        node: NodeDefinition,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a function node by calling its associated tool.
        
        Args:
            node: The function node
            state: Current state
            
        Returns:
            Modified state after tool execution
        """
        if not node.tool_name:
            raise ValueError(f"Function node '{node.name}' has no tool_name")
        
        # Get the tool from registry
        try:
            tool = self.tool_registry.get(node.tool_name)
        except KeyError:
            raise ValueError(
                f"Tool '{node.tool_name}' not found in registry. "
                f"Available tools: {self.tool_registry.list_tools()}"
            )
        
        # Execute the tool
        # Tools can be sync or async, handle both
        if asyncio.iscoroutinefunction(tool):
            result = await tool(state)
        else:
            # Run sync functions in thread pool to avoid blocking
            result = await asyncio.to_thread(tool, state)
        
        return result
    
    async def _get_next_node(
        self,
        current_node_name: str,
        adjacency_map: Dict[str, List[EdgeDefinition]],
        state: Dict[str, Any]
    ) -> Optional[str]:
        """
        Determine the next node to execute based on edges and conditions.
        
        Args:
            current_node_name: Current node
            adjacency_map: Map of node -> outgoing edges
            state: Current state for condition evaluation
            
        Returns:
            Name of next node, or None if terminal
        """
        # Get outgoing edges from current node
        outgoing_edges = adjacency_map.get(current_node_name, [])
        
        if not outgoing_edges:
            # No outgoing edges - terminal node
            return None
        
        # Check edges with conditions first (for branching)
        conditional_edges = [e for e in outgoing_edges if e.condition]
        unconditional_edges = [e for e in outgoing_edges if not e.condition]
        
        # Evaluate conditional edges
        for edge in conditional_edges:
            if self._evaluate_condition(edge.condition, state):
                logger.info(
                    f"Condition '{edge.condition}' evaluated to True. "
                    f"Taking edge to '{edge.to_node}'"
                )
                return edge.to_node
        
        # If no conditional edge matched, take first unconditional edge
        if unconditional_edges:
            return unconditional_edges[0].to_node
        
        # If we have only conditional edges and none matched
        if conditional_edges and not unconditional_edges:
            logger.warning(
                f"No conditional edge from '{current_node_name}' was satisfied. "
                f"Terminating execution."
            )
            return None
        
        return None
    
    def _evaluate_condition(
        self,
        condition: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition expression safely.
        
        Args:
            condition: Python expression as string (e.g., "state['score'] >= 8")
            state: Current state data
            
        Returns:
            Boolean result of evaluation
        """
        try:
            # Create a restricted namespace for eval
            # Only expose 'state' and safe built-ins
            namespace = {
                'state': state,
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'True': True,
                    'False': False,
                    'None': None,
                }
            }
            
            result = eval(condition, namespace)
            return bool(result)
        
        except Exception as e:
            logger.error(f"Condition evaluation failed: {condition}. Error: {e}")
            # On error, return False (don't take the edge)
            return False
    
    def _build_adjacency_map(
        self,
        edges: List[EdgeDefinition]
    ) -> Dict[str, List[EdgeDefinition]]:
        """
        Build an adjacency map for efficient graph traversal.
        
        Args:
            edges: List of edge definitions
            
        Returns:
            Dict mapping node_name -> list of outgoing edges
        """
        adjacency_map: Dict[str, List[EdgeDefinition]] = {}
        
        for edge in edges:
            if edge.from_node not in adjacency_map:
                adjacency_map[edge.from_node] = []
            adjacency_map[edge.from_node].append(edge)
        
        return adjacency_map
