"""
Meta-tools that help the ReAct loop itself function.

These tools operate at a higher level than domain-specific tools,
helping the LLM communicate its decisions and reasoning.
"""

import json
import re
from typing import Dict, Any, Optional, List
from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from ...utils.logger import setup_logger

logger = setup_logger()


class ParseDecisionTool(Tool):
    """
    Parses LLM's natural language reasoning into structured decision.
    
    This tool acts as a bridge between LLM's natural reasoning and
    the structured format needed by the orchestrator.
    """
    
    def __init__(self, tool_registry):
        super().__init__(
            name="parse_decision",
            description="INTERNAL: Parses your natural language reasoning into structured action",
            parameters=[
                ToolParameter(
                    name="reasoning",
                    param_type=ParameterType.STRING,
                    description="Your step-by-step thinking about what to do next",
                    required=True
                ),
                ToolParameter(
                    name="next_action",
                    param_type=ParameterType.STRING,
                    description="What you want to do: 'call_tool' or 'finalize'",
                    required=True
                ),
                ToolParameter(
                    name="tool_name",
                    param_type=ParameterType.STRING,
                    description="If calling a tool, which tool",
                    required=False
                ),
                ToolParameter(
                    name="tool_params",
                    param_type=ParameterType.DICT,
                    description="If calling a tool, its parameters",
                    required=False
                ),
                ToolParameter(
                    name="answer",
                    param_type=ParameterType.STRING,
                    description="If finalizing, the complete answer",
                    required=False
                ),
                ToolParameter(
                    name="confidence",
                    param_type=ParameterType.FLOAT,
                    description="Your confidence in this decision (0.0-1.0)",
                    required=False
                )
            ]
        )
        self.tool_registry = tool_registry
    
    def execute(self, **kwargs) -> ToolResult:
        """Parse and validate the decision"""
        reasoning = kwargs.get("reasoning", "")
        next_action = kwargs.get("next_action", "").lower()
        
        if next_action == "call_tool":
            tool_name = kwargs.get("tool_name")
            tool_params = kwargs.get("tool_params", {})
            
            if not tool_name:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Must specify tool_name when next_action is 'call_tool'"
                )
            
            # Validate tool exists
            tool = self.tool_registry.get_tool(tool_name)
            if not tool:
                available = ", ".join(self.tool_registry.get_all_tool_names())
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Unknown tool '{tool_name}'. Available: {available}"
                )
            
            # Validate parameters
            is_valid, error = tool.validate_parameters(tool_params)
            if not is_valid:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Invalid parameters for {tool_name}: {error}"
                )
            
            return ToolResult(
                success=True,
                data={
                    "action": "call_tool",
                    "tool": tool_name,
                    "parameters": tool_params,
                    "reasoning": reasoning
                },
                message=f"Decision parsed: calling {tool_name}"
            )
        
        elif next_action == "finalize":
            answer = kwargs.get("answer")
            confidence = kwargs.get("confidence", 0.8)
            
            if not answer:
                return ToolResult(
                    success=False,
                    data=None,
                    error="Must provide 'answer' when next_action is 'finalize'"
                )
            
            return ToolResult(
                success=True,
                data={
                    "action": "finalize",
                    "answer": answer,
                    "confidence": confidence,
                    "reasoning": reasoning
                },
                message=f"Decision parsed: finalizing with answer"
            )
        
        else:
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid next_action '{next_action}'. Must be 'call_tool' or 'finalize'"
            )


class FinalizeAnswerTool(Tool):
    """
    Simple finalization tool - direct way to end analysis.
    
    Alternative to parse_decision for when LLM wants to be explicit.
    """
    
    def __init__(self):
        super().__init__(
            name="finalize_answer",
            description="Call this when you have the complete answer to the user's query",
            parameters=[
                ToolParameter(
                    name="answer",
                    param_type=ParameterType.STRING,
                    description="The complete answer with all details and actual values",
                    required=True,
                    example="Found 2 CMs connected to RPD MAWED07T01: 1c:93:7c:2a:72:c3, 28:7a:ee:c9:66:4a"
                ),
                ToolParameter(
                    name="confidence",
                    param_type=ParameterType.FLOAT,
                    description="How confident you are (0.0-1.0)",
                    required=False
                )
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        """Mark analysis as complete"""
        answer = kwargs.get("answer")
        confidence = kwargs.get("confidence", 0.9)
        
        return ToolResult(
            success=True,
            data={
                "action": "finalize",
                "answer": answer,
                "confidence": confidence
            },
            message="Analysis finalized"
        )

