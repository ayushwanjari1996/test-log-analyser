"""
Dummy tool for testing Phase 1.

This tool will be replaced with real tools in Phase 2.
"""

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType


class EchoTool(Tool):
    """Simple echo tool that returns what you give it"""
    
    def __init__(self):
        super().__init__(
            name="echo",
            description="Returns the input message as-is. Useful for testing.",
            parameters=[
                ToolParameter(
                    name="message",
                    param_type=ParameterType.STRING,
                    description="Message to echo back",
                    required=True,
                    example="Hello, world!"
                )
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message", "")
        
        return ToolResult(
            success=True,
            data={"echoed": message},
            message=f"Echoed: {message}"
        )


class CountTool(Tool):
    """Tool that counts from 1 to N"""
    
    def __init__(self):
        super().__init__(
            name="count",
            description="Counts from 1 to N and returns the list",
            parameters=[
                ToolParameter(
                    name="n",
                    param_type=ParameterType.INTEGER,
                    description="Number to count to",
                    required=True,
                    example=5
                )
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        n = kwargs.get("n", 0)
        
        if n < 0:
            return ToolResult(
                success=False,
                data=None,
                error="N must be positive"
            )
        
        if n > 100:
            return ToolResult(
                success=False,
                data=None,
                error="N too large (max 100)"
            )
        
        numbers = list(range(1, n + 1))
        
        return ToolResult(
            success=True,
            data=numbers,
            message=f"Counted from 1 to {n}",
            metadata={"count": n}
        )

