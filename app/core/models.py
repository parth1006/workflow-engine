"""
Core data models for the workflow engine.
Uses Pydantic for validation and type safety.
"""
from typing import Dict, List, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime,timezone
from enum import Enum
import uuid


class NodeType(str, Enum):
    """Types of nodes in the workflow graph."""
    FUNCTION = "function"  # Regular function node
    CONDITIONAL = "conditional"  # Branching node
    START = "start"  # Entry point
    END = "end"  # Terminal node


class RunStatus(str, Enum):
    """Status of a workflow run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# STATE MODELS
# ============================================================================

class WorkflowState(BaseModel):
    """
    The shared state that flows through the workflow.
    This is a flexible dict that nodes can read from and write to.
    """
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        # Allow arbitrary types for flexibility
        arbitrary_types_allowed = True


# ============================================================================
# NODE & EDGE DEFINITIONS
# ============================================================================

class NodeDefinition(BaseModel):
    """
    Defines a single node in the workflow graph.
    
    Attributes:
        name: Unique identifier for the node
        node_type: Type of node (function, conditional, etc.)
        tool_name: Name of the tool to execute (for function nodes)
        config: Additional configuration (e.g., max_iterations for loops)
    """
    name: str
    node_type: NodeType
    tool_name: Optional[str] = None  # Required for FUNCTION nodes
    config: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class EdgeDefinition(BaseModel):
    """
    Defines a directed edge between two nodes.
    
    Attributes:
        from_node: Source node name
        to_node: Target node name
        condition: Optional Python expression to evaluate for conditional routing
                  Example: "state['quality_score'] >= 8"
        label: Optional human-readable label for the edge
    """
    from_node: str
    to_node: str
    condition: Optional[str] = None  # Python expression string
    label: Optional[str] = None  # For documentation/visualization


class GraphDefinition(BaseModel):
    """
    Complete definition of a workflow graph.
    
    Attributes:
        graph_id: Unique identifier (auto-generated)
        name: Human-readable name
        description: What this workflow does
        nodes: List of all nodes
        edges: List of all edges
        entry_point: Name of the starting node
        created_at: Timestamp of creation
    """
    graph_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    nodes: List[NodeDefinition]
    edges: List[EdgeDefinition]
    entry_point: str  # Must match a node name
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# EXECUTION MODELS
# ============================================================================

class ExecutionLog(BaseModel):
    """
    Log entry for a single node execution.
    
    Tracks what happened when a node was executed.
    """
    node_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_state: Dict[str, Any]  # State before execution
    output_state: Dict[str, Any]  # State after execution
    execution_time_ms: float  # How long it took
    success: bool = True
    error: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        # Add this line to enable json_mode serialization
        from_attributes = True

class Run(BaseModel):
    """
    Represents a single execution of a workflow graph.
    
    Tracks the complete state of a workflow run from start to finish.
    """
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    graph_id: str
    status: RunStatus = RunStatus.PENDING
    current_node: Optional[str] = None
    current_state: WorkflowState = Field(default_factory=WorkflowState)
    execution_logs: List[ExecutionLog] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Loop tracking
    iteration_count: int = 0
    max_iterations: int = 10  # Safety limit
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class CreateGraphRequest(BaseModel):
    """Request model for POST /graph/create"""
    name: str
    description: Optional[str] = None
    nodes: List[NodeDefinition]
    edges: List[EdgeDefinition]
    entry_point: str


class CreateGraphResponse(BaseModel):
    """Response model for POST /graph/create"""
    graph_id: str
    message: str = "Graph created successfully"


class RunGraphRequest(BaseModel):
    """Request model for POST /graph/run"""
    graph_id: str
    initial_state: Dict[str, Any] = Field(default_factory=dict)


class RunGraphResponse(BaseModel):
    """Response model for POST /graph/run"""
    run_id: str
    status: str
    final_state: Dict[str, Any]
    execution_logs: List[ExecutionLog]
    total_execution_time_ms: float
    iterations_completed: int


class GetStateResponse(BaseModel):
    """Response model for GET /graph/state/{run_id}"""
    run_id: str
    status: str
    current_node: Optional[str]
    current_state: Dict[str, Any]
    iterations_completed: int
    started_at: Optional[str]
    completed_at: Optional[str]