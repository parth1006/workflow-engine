"""
Abstract storage interface for the workflow engine.

This defines the contract that all storage implementations must follow.
Makes it easy to swap storage backends (SQLite, PostgreSQL, etc.).
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from app.core.models import GraphDefinition, Run


class StorageInterface(ABC):
    """
    Abstract base class for storage backends.
    
    All storage implementations must implement these methods.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the storage backend.
        Create necessary tables, indices, etc.
        """
        pass
    
    @abstractmethod
    async def save_graph(self, graph: GraphDefinition) -> str:
        """
        Save a graph definition.
        
        Args:
            graph: The graph to save
            
        Returns:
            The graph_id
        """
        pass
    
    @abstractmethod
    async def get_graph(self, graph_id: str) -> Optional[GraphDefinition]:
        """
        Retrieve a graph by ID.
        
        Args:
            graph_id: The graph identifier
            
        Returns:
            The graph definition, or None if not found
        """
        pass
    
    @abstractmethod
    async def list_graphs(self) -> List[GraphDefinition]:
        """
        List all graphs.
        
        Returns:
            List of all graph definitions
        """
        pass
    
    @abstractmethod
    async def delete_graph(self, graph_id: str) -> bool:
        """
        Delete a graph.
        
        Args:
            graph_id: The graph identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def save_run(self, run: Run) -> str:
        """
        Save a new run.
        
        Args:
            run: The run to save
            
        Returns:
            The run_id
        """
        pass
    
    @abstractmethod
    async def get_run(self, run_id: str) -> Optional[Run]:
        """
        Retrieve a run by ID.
        
        Args:
            run_id: The run identifier
            
        Returns:
            The run, or None if not found
        """
        pass
    
    @abstractmethod
    async def update_run(self, run: Run) -> None:
        """
        Update an existing run.
        
        Args:
            run: The run with updated data
        """
        pass
    
    @abstractmethod
    async def list_runs(
        self,
        graph_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Run]:
        """
        List runs, optionally filtered by graph_id.
        
        Args:
            graph_id: Optional filter by graph
            limit: Maximum number of runs to return
            
        Returns:
            List of runs
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Close the storage connection.
        Clean up resources.
        """
        pass