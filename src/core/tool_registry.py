"""
Tool Registry for managing and discovering tools.

The registry maintains a catalog of all available tools
and provides formatted descriptions for the LLM.
"""

import logging
from typing import Dict, List, Optional
from .tools.base_tool import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry of all available tools.
    
    Provides:
    - Tool registration and lookup
    - Formatted tool descriptions for LLM
    - Tool discovery
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        logger.info("ToolRegistry initialized")
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool instance to register
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def register_multiple(self, tools: List[Tool]) -> None:
        """Register multiple tools at once"""
        for tool in tools:
            self.register(tool)
    
    def get(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """Get list of all registered tool names"""
        return list(self._tools.keys())
    
    def get_tools_description(self, format: str = "text") -> str:
        """
        Get formatted descriptions of all tools for LLM.
        
        Args:
            format: Output format ("text" or "json")
            
        Returns:
            Formatted string with all tool descriptions
        """
        if format == "text":
            return self._get_text_description()
        elif format == "json":
            return self._get_json_description()
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _get_text_description(self) -> str:
        """Get text-formatted tool descriptions"""
        if not self._tools:
            return "No tools available."
        
        desc = f"AVAILABLE TOOLS ({len(self._tools)} tools):\n\n"
        
        for i, tool in enumerate(self._tools.values(), 1):
            desc += f"{i}. {tool.to_description()}\n"
        
        return desc
    
    def _get_json_description(self) -> str:
        """Get JSON-formatted tool descriptions"""
        import json
        tools_dict = {
            name: tool.to_dict() 
            for name, tool in self._tools.items()
        }
        return json.dumps(tools_dict, indent=2)
    
    def get_tool_names_summary(self) -> str:
        """Get quick summary of tool names"""
        if not self._tools:
            return "No tools available"
        
        return ", ".join(self._tools.keys())
    
    def clear(self) -> None:
        """Clear all registered tools (useful for testing)"""
        self._tools.clear()
        logger.info("Tool registry cleared")
    
    def __len__(self) -> int:
        """Number of registered tools"""
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        """Check if tool is registered"""
        return name in self._tools

