"""
Grep-based tools for fast, memory-efficient log analysis.

These tools use streaming search instead of loading entire CSV into memory.
"""

import json
import logging
from typing import List, Optional, Dict, Any
import pandas as pd

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from ..stream_searcher import StreamSearcher

logger = logging.getLogger(__name__)


class GrepLogsTool(Tool):
    """
    Grep logs for matching patterns.
    
    Fast, memory-efficient search that only returns matching lines.
    Replaces SearchLogsTool which loaded ALL logs.
    """
    
    def __init__(self, log_file: str):
        super().__init__(
            name="grep_logs",
            description="Search logs for matching pattern (fast, memory-efficient)",
            parameters=[
                ToolParameter(
                    name="pattern",
                    param_type=ParameterType.STRING,
                    description="Search pattern (text, MAC address, IP, etc.)",
                    required=True
                ),
                ToolParameter(
                    name="case_sensitive",
                    param_type=ParameterType.BOOLEAN,
                    description="Case-sensitive matching (default: false)",
                    required=False
                ),
                ToolParameter(
                    name="max_results",
                    param_type=ParameterType.INTEGER,
                    description="Maximum results to return (default: no limit)",
                    required=False
                )
            ]
        )
        self.log_file = log_file
        self.searcher = StreamSearcher(log_file)
        self.requires_logs = False  # Doesn't need pre-loaded logs!
    
    def execute(self, **kwargs) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        case_sensitive = kwargs.get("case_sensitive", False)
        max_results = kwargs.get("max_results")
        
        if not pattern:
            return ToolResult(
                success=False,
                data=None,
                error="No search pattern provided"
            )
        
        try:
            # Use stream searcher for fast grep
            results = self.searcher.search(
                search_term=pattern,
                case_sensitive=case_sensitive,
                max_results=max_results
            )
            
            count = len(results)
            
            if count == 0:
                return ToolResult(
                    success=True,
                    data=pd.DataFrame(),
                    message=f"No logs found matching '{pattern}'",
                    metadata={"count": 0, "pattern": pattern}
                )
            
            limit_msg = f" (limited to {max_results})" if max_results and count >= max_results else ""
            
            return ToolResult(
                success=True,
                data=results,
                message=f"Found {count} logs matching '{pattern}'{limit_msg}",
                metadata={"count": count, "pattern": pattern}
            )
            
        except Exception as e:
            logger.error(f"Grep failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Grep failed: {str(e)}"
            )


class ParseJsonFieldTool(Tool):
    """
    Extract field values from JSON log column.
    
    Parses _source.log JSON and extracts specific fields.
    """
    
    def __init__(self):
        super().__init__(
            name="parse_json_field",
            description="Extract field value from JSON logs",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="Logs DataFrame to parse",
                    required=True
                ),
                ToolParameter(
                    name="field_name",
                    param_type=ParameterType.STRING,
                    description="JSON field to extract (e.g., 'MdId', 'CmMacAddress')",
                    required=True
                )
            ]
        )
        self.requires_logs = True
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        field_name = kwargs.get("field_name", "")
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data=[],
                message="No logs to parse",
                metadata={"field": field_name, "count": 0}
            )
        
        if not field_name:
            return ToolResult(
                success=False,
                data=None,
                error="No field name provided"
            )
        
        try:
            values = []
            
            # Parse JSON from _source.log column
            if '_source.log' in logs.columns:
                for log_entry in logs['_source.log']:
                    try:
                        log_json = json.loads(log_entry)
                        if field_name in log_json:
                            value = log_json[field_name]
                            if value:  # Skip empty values
                                values.append(value)
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            if not values:
                return ToolResult(
                    success=True,
                    data=[],
                    message=f"Field '{field_name}' not found in logs",
                    metadata={"field": field_name, "count": 0}
                )
            
            return ToolResult(
                success=True,
                data=values,
                message=f"Extracted {len(values)} values for '{field_name}'",
                metadata={"field": field_name, "count": len(values), "values": values[:5]}
            )
            
        except Exception as e:
            logger.error(f"Parse failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Parse failed: {str(e)}"
            )


class ExtractUniqueValuesTool(Tool):
    """
    Get unique values from a list or parsed field results.
    """
    
    def __init__(self):
        super().__init__(
            name="extract_unique",
            description="Get unique values from a list",
            parameters=[
                ToolParameter(
                    name="values",
                    param_type=ParameterType.LIST,
                    description="List of values to deduplicate",
                    required=True
                )
            ]
        )
        self.requires_logs = False
    
    def execute(self, **kwargs) -> ToolResult:
        values = kwargs.get("values", [])
        
        if not values:
            return ToolResult(
                success=True,
                data=[],
                message="No values provided",
                metadata={"unique_count": 0}
            )
        
        try:
            # Get unique values
            unique_vals = list(set(values))
            unique_count = len(unique_vals)
            
            return ToolResult(
                success=True,
                data=unique_vals,
                message=f"Found {unique_count} unique values (from {len(values)} total)",
                metadata={
                    "unique_count": unique_count,
                    "total_count": len(values),
                    "sample": unique_vals[:5]
                }
            )
            
        except Exception as e:
            logger.error(f"Extract unique failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Extract unique failed: {str(e)}"
            )


class CountValuesTool(Tool):
    """
    Count occurrences of values.
    """
    
    def __init__(self):
        super().__init__(
            name="count_values",
            description="Count unique values in a list",
            parameters=[
                ToolParameter(
                    name="values",
                    param_type=ParameterType.LIST,
                    description="List of values to count",
                    required=True
                )
            ]
        )
        self.requires_logs = False
    
    def execute(self, **kwargs) -> ToolResult:
        values = kwargs.get("values", [])
        
        if not values:
            return ToolResult(
                success=True,
                data=0,
                message="No values to count",
                metadata={"count": 0}
            )
        
        try:
            unique_count = len(set(values))
            total_count = len(values)
            
            return ToolResult(
                success=True,
                data=unique_count,
                message=f"{unique_count} unique values (from {total_count} total)",
                metadata={
                    "unique_count": unique_count,
                    "total_count": total_count
                }
            )
            
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Count failed: {str(e)}"
            )


class GrepAndParseTool(Tool):
    """
    Combined grep + parse operation (common pattern).
    
    Grep for pattern, then extract JSON field from results.
    """
    
    def __init__(self, log_file: str):
        super().__init__(
            name="grep_and_parse",
            description="Search logs and extract JSON field in one step",
            parameters=[
                ToolParameter(
                    name="pattern",
                    param_type=ParameterType.STRING,
                    description="Search pattern",
                    required=True
                ),
                ToolParameter(
                    name="field_name",
                    param_type=ParameterType.STRING,
                    description="JSON field to extract",
                    required=True
                ),
                ToolParameter(
                    name="unique_only",
                    param_type=ParameterType.BOOLEAN,
                    description="Return only unique values (default: true)",
                    required=False
                )
            ]
        )
        self.log_file = log_file
        self.searcher = StreamSearcher(log_file)
        self.requires_logs = False
    
    def execute(self, **kwargs) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        field_name = kwargs.get("field_name", "")
        unique_only = kwargs.get("unique_only", True)
        
        if not pattern or not field_name:
            return ToolResult(
                success=False,
                data=None,
                error="Both pattern and field_name required"
            )
        
        try:
            # Step 1: Grep
            results = self.searcher.search(pattern)
            
            if results.empty:
                return ToolResult(
                    success=True,
                    data=[],
                    message=f"No logs found for pattern '{pattern}'",
                    metadata={"pattern": pattern, "field": field_name, "count": 0}
                )
            
            # Step 2: Parse
            values = []
            if '_source.log' in results.columns:
                for log_entry in results['_source.log']:
                    try:
                        log_json = json.loads(log_entry)
                        if field_name in log_json:
                            value = log_json[field_name]
                            if value:
                                values.append(value)
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            # Step 3: Unique (if requested)
            if unique_only and values:
                values = list(set(values))
            
            if not values:
                return ToolResult(
                    success=True,
                    data=[],
                    message=f"Field '{field_name}' not found in logs matching '{pattern}'",
                    metadata={"pattern": pattern, "field": field_name, "count": 0}
                )
            
            return ToolResult(
                success=True,
                data=values,
                message=f"Found {len(values)} values for '{field_name}' in logs matching '{pattern}'",
                metadata={
                    "pattern": pattern,
                    "field": field_name,
                    "count": len(values),
                    "sample": values[:5]
                }
            )
            
        except Exception as e:
            logger.error(f"Grep and parse failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Grep and parse failed: {str(e)}"
            )

