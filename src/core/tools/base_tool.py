"""
Base classes for tools in the ReAct system.

Tools are atomic operations that the LLM can use to accomplish tasks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class ParameterType(Enum):
    """Parameter types for tool validation"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    DATAFRAME = "dataframe"


@dataclass
class ToolParameter:
    """
    Definition of a tool parameter.
    
    Used to generate tool descriptions for LLM and validate inputs.
    """
    name: str
    param_type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    example: Any = None


@dataclass
class ToolResult:
    """
    Result from tool execution.
    
    Contains both the actual data and metadata about the execution.
    """
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM consumption"""
        result = {
            "success": self.success,
            "message": self.message,
        }
        
        if self.success:
            # Format data for LLM
            if hasattr(self.data, 'to_dict'):
                result["data"] = self.data.to_dict()
            elif hasattr(self.data, '__len__'):
                result["data"] = self.data
                result["count"] = len(self.data)
            else:
                result["data"] = self.data
            
            result["metadata"] = self.metadata
        else:
            result["error"] = self.error
        
        return result


class Tool(ABC):
    """
    Abstract base class for all tools.
    
    Tools are atomic operations that the LLM can use.
    Each tool should do ONE thing well and be composable.
    """
    
    def __init__(self, name: str, description: str, parameters: List[ToolParameter]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success status and data/error
        """
        pass
    
    def validate_parameters(self, kwargs: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate that provided parameters match tool specification.
        Provides helpful error messages to guide LLM self-correction.
        
        Returns:
            (is_valid, error_message)
        """
        valid_param_names = {p.name for p in self.parameters}
        
        # Check for unknown parameters (LLM hallucination)
        for provided_param in kwargs.keys():
            if provided_param not in valid_param_names:
                available = ", ".join([p.name for p in self.parameters])
                return False, f"Unknown parameter '{provided_param}'. Valid parameters for {self.name}: {available}"
        
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                available = ", ".join([p.name for p in self.parameters])
                return False, f"Missing required parameter '{param.name}'. Valid parameters: {available}"
        
        # Check parameter types (basic validation)
        for param in self.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]
                
                # Type checking
                if param.param_type == ParameterType.STRING and not isinstance(value, str):
                    return False, f"Parameter '{param.name}' must be string, got {type(value).__name__}"
                elif param.param_type == ParameterType.INTEGER and not isinstance(value, int):
                    return False, f"Parameter '{param.name}' must be integer, got {type(value).__name__}"
                elif param.param_type == ParameterType.BOOLEAN and not isinstance(value, bool):
                    return False, f"Parameter '{param.name}' must be boolean, got {type(value).__name__}"
                elif param.param_type == ParameterType.LIST and not isinstance(value, list):
                    # Allow empty string for optional list parameters (convert to empty list or None)
                    if isinstance(value, str) and value.strip() == "" and not param.required:
                        kwargs[param.name] = None
                    else:
                        return False, f"Parameter '{param.name}' must be list, got {type(value).__name__}"
                elif param.param_type == ParameterType.DICT and not isinstance(value, dict):
                    return False, f"Parameter '{param.name}' must be dict, got {type(value).__name__}"
        
        return True, None
    
    def to_description(self) -> str:
        """
        Format tool description for LLM.
        
        Returns human-readable description with parameter details.
        """
        desc = f"**{self.name}**\n"
        desc += f"{self.description}\n"
        
        if self.parameters:
            desc += "Parameters:\n"
            for param in self.parameters:
                # Type string with emphasis
                type_str = param.param_type.value.upper()
                required_str = "[REQUIRED]" if param.required else "[OPTIONAL]"
                
                # Build parameter line
                desc += f"  • {param.name} {required_str} - Type: {type_str}\n"
                desc += f"    {param.description}\n"
                
                if param.example is not None:
                    # Format example based on type
                    if param.param_type == ParameterType.STRING:
                        example_str = f'"{param.example}"'
                    elif param.param_type == ParameterType.LIST:
                        example_str = str(param.example) if isinstance(param.example, list) else f'["{param.example}"]'
                    else:
                        example_str = str(param.example)
                    desc += f"    Usage: {{\"{param.name}\": {example_str}}}\n"
        
        return desc
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool definition to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.param_type.value,
                    "description": p.description,
                    "required": p.required,
                    "example": p.example
                }
                for p in self.parameters
            ]
        }

