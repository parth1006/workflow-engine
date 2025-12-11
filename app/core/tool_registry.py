"""
Tool Registry for managing callable tools in the workflow engine.

Tools are Python functions that nodes can invoke during execution.
The registry provides a centralized place to register and retrieve tools.
"""
from typing import Callable, Dict, Any, Optional
from functools import wraps
import inspect
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Singleton registry for workflow tools.
    
    Tools are Python functions that can be called by workflow nodes.
    Each tool has a unique name and can accept/return arbitrary data.
    """
    
    _instance: Optional['ToolRegistry'] = None
    _tools: Dict[str, Callable] = {}
    
    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
        return cls._instance
    
    def register(
        self,
        name: str,
        func: Callable,
        override: bool = False
    ) -> None:
        """
        Register a tool function.
        
        Args:
            name: Unique identifier for the tool
            func: Callable function
            override: If True, allows overwriting existing tools
            
        Raises:
            ValueError: If tool name already exists and override=False
        """
        if name in self._tools and not override:
            raise ValueError(
                f"Tool '{name}' already registered. "
                f"Use override=True to replace it."
            )
        
        # Validate that it's callable
        if not callable(func):
            raise ValueError(f"Tool '{name}' must be callable")
        
        self._tools[name] = func
        logger.info(f"Registered tool: {name}")
    
    def get(self, name: str) -> Callable:
        """
        Retrieve a tool by name.
        
        Args:
            name: Tool identifier
            
        Returns:
            The registered callable
            
        Raises:
            KeyError: If tool doesn't exist
        """
        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' not found. "
                f"Available tools: {list(self._tools.keys())}"
            )
        return self._tools[name]
    
    def exists(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def list_tools(self) -> list[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
    
    def unregister(self, name: str) -> None:
        """
        Remove a tool from the registry.
        
        Args:
            name: Tool identifier
            
        Raises:
            KeyError: If tool doesn't exist
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        del self._tools[name]
        logger.info(f"Unregistered tool: {name}")
    
    def clear(self) -> None:
        """Remove all tools from registry. Useful for testing."""
        self._tools.clear()
        logger.info("Cleared all tools from registry")
    
    def get_tool_info(self, name: str) -> Dict[str, Any]:
        """
        Get information about a tool.
        
        Returns:
            Dict with tool name, signature, and docstring
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        
        func = self._tools[name]
        sig = inspect.signature(func)
        
        return {
            "name": name,
            "signature": str(sig),
            "docstring": inspect.getdoc(func) or "No documentation available",
            "parameters": [
                {
                    "name": param_name,
                    "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "default": str(param.default) if param.default != inspect.Parameter.empty else None
                }
                for param_name, param in sig.parameters.items()
            ]
        }


# ============================================================================
# DECORATOR FOR EASY TOOL REGISTRATION
# ============================================================================

def tool(name: Optional[str] = None):
    """
    Decorator to register a function as a tool.
    
    Usage:
        @tool(name="my_tool")
        def my_function(state: dict) -> dict:
            # Do something
            return state
    
    Args:
        name: Optional custom name. If not provided, uses function name.
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        registry = ToolRegistry()
        registry.register(tool_name, func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# GLOBAL REGISTRY INSTANCE
# ============================================================================

# Create global registry instance for easy access
registry = ToolRegistry()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def register_tool(name: str, func: Callable) -> None:
    """
    Convenience function to register a tool.
    
    Usage:
        def my_tool(state):
            return state
        
        register_tool("my_tool", my_tool)
    """
    registry.register(name, func)


def get_tool(name: str) -> Callable:
    """Convenience function to get a tool."""
    return registry.get(name)


def list_tools() -> list[str]:
    """Convenience function to list all tools."""
    return registry.list_tools()