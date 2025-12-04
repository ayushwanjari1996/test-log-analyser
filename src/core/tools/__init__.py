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
from .meta_tools import (
    FinalizeAnswerTool
)
from .output_tools import (
    ReturnLogsTool
)

# Old tools (DEPRECATED - will be removed)
from .search_tools import (
    SearchLogsTool,
    FilterByTimeTool,
    FilterBySeverityTool,
    FilterByFieldTool,
    GetLogCountTool
)
from .entity_tools import (
    ExtractEntitiesTool,
    CountEntitiesTool,
    AggregateEntitiesTool,
    FindEntityRelationshipsTool
)
from .smart_search_tools import (
    NormalizeTermTool,
    FuzzySearchTool
)

__all__ = [
    # Base classes
    'Tool', 'ToolResult', 'ToolParameter', 'ParameterType',
    # NEW: Grep tools (fast, memory-efficient)
    'GrepLogsTool', 'ParseJsonFieldTool', 'ExtractUniqueValuesTool',
    'CountValuesTool', 'GrepAndParseTool',
    # NEW: Advanced tools (Phase 1-3)
    'FindRelationshipChainTool',  # Relationship discovery
    'SortByTimeTool', 'ExtractTimeRangeTool',  # Time-based
    'SummarizeLogsTool', 'AggregateByFieldTool', 'AnalyzeLogsTool',  # Analysis
    # Meta tools
    'FinalizeAnswerTool',
    # Output tools
    'ReturnLogsTool',
    # OLD (deprecated)
    'SearchLogsTool', 'FilterByTimeTool', 'FilterBySeverityTool', 
    'FilterByFieldTool', 'GetLogCountTool',
    'ExtractEntitiesTool', 'CountEntitiesTool', 'AggregateEntitiesTool',
    'FindEntityRelationshipsTool',
    'NormalizeTermTool', 'FuzzySearchTool',
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


def create_all_tools_legacy(log_file_path: str, config_dir: str = "config"):
    """
    OLD: Factory function with legacy load-all tools.
    
    DEPRECATED: Use create_all_tools() instead.
    This loads entire CSV into memory (slow, memory-heavy).
    """
    from ..log_processor import LogProcessor
    from ..entity_manager import EntityManager
    
    # Initialize components
    processor = LogProcessor(log_file_path)
    entity_manager = EntityManager()
    
    # Create tools
    tools = []
    
    # Search tools (OLD)
    tools.append(SearchLogsTool(processor))
    tools.append(FilterByTimeTool(processor))
    tools.append(FilterBySeverityTool(processor))
    tools.append(FilterByFieldTool(processor))
    tools.append(GetLogCountTool(processor))
    
    # Entity tools (OLD)
    tools.append(ExtractEntitiesTool(entity_manager))
    tools.append(CountEntitiesTool(entity_manager))
    tools.append(AggregateEntitiesTool(entity_manager))
    tools.append(FindEntityRelationshipsTool(entity_manager))
    
    # Smart search tools (OLD)
    normalize_tool = NormalizeTermTool(config_dir)
    tools.append(normalize_tool)
    tools.append(FuzzySearchTool(normalize_tool, config_dir))
    
    # Output tools
    tools.append(ReturnLogsTool())
    
    # Meta tools
    tools.append(FinalizeAnswerTool())
    
    return tools
