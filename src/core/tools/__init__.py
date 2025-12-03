"""
Tools module for ReAct orchestrator.

Provides primitive atomic operations that the LLM can compose.
"""

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
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
from .meta_tools import (
    FinalizeAnswerTool
)
from .output_tools import (
    ReturnLogsTool
)

__all__ = [
    # Base classes
    'Tool', 'ToolResult', 'ToolParameter', 'ParameterType',
    # Search tools
    'SearchLogsTool', 'FilterByTimeTool', 'FilterBySeverityTool', 
    'FilterByFieldTool', 'GetLogCountTool',
    # Entity tools
    'ExtractEntitiesTool', 'CountEntitiesTool', 'AggregateEntitiesTool',
    'FindEntityRelationshipsTool',
    # Smart search
    'NormalizeTermTool', 'FuzzySearchTool',
    # Output tools
    'ReturnLogsTool',
    # Meta tools
    'FinalizeAnswerTool'
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
    from ..log_processor import LogProcessor
    from ..entity_manager import EntityManager
    
    # Initialize components
    processor = LogProcessor(log_file_path)
    entity_manager = EntityManager()
    
    # Create tools
    tools = []
    
    # Search tools
    tools.append(SearchLogsTool(processor))
    tools.append(FilterByTimeTool(processor))
    tools.append(FilterBySeverityTool(processor))
    tools.append(FilterByFieldTool(processor))
    tools.append(GetLogCountTool(processor))
    
    # Entity tools
    tools.append(ExtractEntitiesTool(entity_manager))
    tools.append(CountEntitiesTool(entity_manager))
    tools.append(AggregateEntitiesTool(entity_manager))
    tools.append(FindEntityRelationshipsTool(entity_manager))
    
    # Smart search tools
    normalize_tool = NormalizeTermTool(config_dir)
    tools.append(normalize_tool)
    tools.append(FuzzySearchTool(normalize_tool, config_dir))
    
    # Output tools
    tools.append(ReturnLogsTool())
    
    # Meta tools
    tools.append(FinalizeAnswerTool())
    
    return tools
