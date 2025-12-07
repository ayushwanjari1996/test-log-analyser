"""
Tools module for ReAct orchestrator.

Provides primitive atomic operations that the LLM can compose.
"""

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from .grep_tools import (
    GrepLogsTool,
    ParseJsonFieldTool,
    ExtractUniqueValuesTool,
    CountValuesTool,
    GrepAndParseTool
)
from .relationship_tools import (
    FindRelationshipChainTool
)
from .time_tools import (
    SortByTimeTool,
    ExtractTimeRangeTool
)
from .analysis_tools import (
    SummarizeLogsTool,
    AggregateByFieldTool,
    AnalyzeLogsTool
)
from .aggregation_tools import (
    CountUniquePerGroupTool,
    CountViaRelationshipTool
)
from .meta_tools import (
    FinalizeAnswerTool
)
from .output_tools import (
    ReturnLogsTool
)

__all__ = [
    # Base classes
    'Tool', 'ToolResult', 'ToolParameter', 'ParameterType',
    # Grep tools (fast, memory-efficient)
    'GrepLogsTool', 'ParseJsonFieldTool', 'ExtractUniqueValuesTool',
    'CountValuesTool', 'GrepAndParseTool',
    # Advanced tools
    'FindRelationshipChainTool',  # Relationship discovery
    'CountUniquePerGroupTool', 'CountViaRelationshipTool',  # Aggregation
    'SortByTimeTool', 'ExtractTimeRangeTool',  # Time-based
    'SummarizeLogsTool', 'AggregateByFieldTool', 'AnalyzeLogsTool',  # Analysis
    # Meta tools
    'FinalizeAnswerTool',
    # Output tools
    'ReturnLogsTool',
]


def create_all_tools(log_file_path: str, config_dir: str = "config"):
    """
    Factory function to create all tools.
    
    Args:
        log_file_path: Path to CSV log file
        config_dir: Path to configuration directory
        
    Returns:
        List of all instantiated tools
    """
    tools = []
    
    # NEW: Grep-based tools (memory-efficient)
    tools.append(GrepLogsTool(log_file_path))
    tools.append(ParseJsonFieldTool())
    tools.append(ExtractUniqueValuesTool())
    tools.append(CountValuesTool())
    tools.append(GrepAndParseTool(log_file_path))
    
    # NEW: Advanced tools (Phase 1-3)
    tools.append(FindRelationshipChainTool(log_file_path, config_dir))  # Relationship discovery
    tools.append(CountUniquePerGroupTool())  # Aggregation: count distinct per group
    tools.append(CountViaRelationshipTool(log_file_path, config_dir))  # Aggregation: via chains
    tools.append(SortByTimeTool())  # Time-based
    tools.append(ExtractTimeRangeTool())
    tools.append(SummarizeLogsTool())  # Analysis
    tools.append(AggregateByFieldTool())
    tools.append(AnalyzeLogsTool())  # LLM-based deep analysis
    
    # Output tools
    tools.append(ReturnLogsTool())
    
    # Meta tools
    tools.append(FinalizeAnswerTool())
    
    return tools
