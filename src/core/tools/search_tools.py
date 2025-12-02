"""
Log search and filter tools.

Provides primitive operations for searching and filtering logs.
These tools wrap LogProcessor functionality with ReAct-compatible interface.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from ..log_processor import LogProcessor


class SearchLogsTool(Tool):
    """Search for logs containing a specific value"""
    
    def __init__(self, processor: LogProcessor):
        super().__init__(
            name="search_logs",
            description="Search for logs containing a specific text value in any column",
            parameters=[
                ToolParameter(
                    name="value",
                    param_type=ParameterType.STRING,
                    description="Text to search for (entity value, keyword, etc.)",
                    required=True,
                    example="MAWED07T01"
                ),
                ToolParameter(
                    name="columns",
                    param_type=ParameterType.LIST,
                    description="Specific columns to search (default: all columns)",
                    required=False,
                    example=["_source.log"]
                )
            ]
        )
        self.processor = processor
        self._logs_cache = None
    
    def execute(self, **kwargs) -> ToolResult:
        value = kwargs.get("value")
        columns = kwargs.get("columns")
        
        # Load logs if not cached
        if self._logs_cache is None:
            self._logs_cache = self.processor.read_all_logs()
        
        # Search
        if columns:
            # Search specific columns only
            result_df = self.processor.search_text(self._logs_cache, value, search_columns=columns)
        else:
            # Search all columns
            result_df = self.processor.search_text(self._logs_cache, value)
        
        count = len(result_df)
        
        if count == 0:
            return ToolResult(
                success=True,
                data=result_df,
                message=f"No logs found containing '{value}'",
                metadata={"count": 0, "search_term": value}
            )
        
        return ToolResult(
            success=True,
            data=result_df,
            message=f"Found {count} logs containing '{value}'",
            metadata={"count": count, "search_term": value}
        )


class FilterByTimeTool(Tool):
    """Filter logs by time range"""
    
    def __init__(self, processor: LogProcessor):
        super().__init__(
            name="filter_by_time",
            description="Filter logs within a specific time range",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs to filter",
                    required=True
                ),
                ToolParameter(
                    name="start_time",
                    param_type=ParameterType.STRING,
                    description="Start time (ISO format or relative like '1 hour ago')",
                    required=False,
                    example="2024-01-01T00:00:00"
                ),
                ToolParameter(
                    name="end_time",
                    param_type=ParameterType.STRING,
                    description="End time (ISO format or relative like 'now')",
                    required=False,
                    example="2024-01-01T23:59:59"
                )
            ]
        )
        self.processor = processor
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data=pd.DataFrame(),
                message="No logs to filter",
                metadata={"count": 0}
            )
        
        # Check if logs have timestamp column
        timestamp_col = None
        for col in ['timestamp', '@timestamp', 'time', '_source.@timestamp']:
            if col in logs.columns:
                timestamp_col = col
                break
        
        if not timestamp_col:
            return ToolResult(
                success=False,
                data=None,
                error="No timestamp column found in logs"
            )
        
        # For now, return all logs (time filtering can be added later)
        # This is a placeholder implementation
        return ToolResult(
            success=True,
            data=logs,
            message=f"Time filtering not yet implemented, returning all {len(logs)} logs",
            metadata={"count": len(logs)}
        )


class FilterBySeverityTool(Tool):
    """Filter logs by severity level"""
    
    def __init__(self, processor: LogProcessor):
        super().__init__(
            name="filter_by_severity",
            description="Filter logs by severity level (ERROR, WARNING, INFO, etc.)",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs to filter",
                    required=True
                ),
                ToolParameter(
                    name="severities",
                    param_type=ParameterType.LIST,
                    description="List of severity levels to include",
                    required=True,
                    example=["ERROR", "CRITICAL"]
                )
            ]
        )
        self.processor = processor
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        severities = kwargs.get("severities", [])
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data=pd.DataFrame(),
                message="No logs to filter",
                metadata={"count": 0}
            )
        
        # Check if severity column exists
        severity_col = None
        for col in ['severity', 'Severity', 'level', 'Level']:
            if col in logs.columns:
                severity_col = col
                break
        
        if not severity_col:
            # No severity column, try to extract from log content
            # For now, return empty result
            return ToolResult(
                success=True,
                data=pd.DataFrame(),
                message=f"No severity column found in logs",
                metadata={"count": 0}
            )
        
        # Filter by matching any of the specified severities
        mask = logs[severity_col].astype(str).str.upper().isin([s.upper() for s in severities])
        filtered = logs[mask]
        count = len(filtered)
        
        if count == 0:
            return ToolResult(
                success=True,
                data=filtered,
                message=f"No logs found with severity in {severities}",
                metadata={"count": 0, "severities": severities}
            )
        
        return ToolResult(
            success=True,
            data=filtered,
            message=f"Found {count} logs with severity in {severities}",
            metadata={"count": count, "severities": severities}
        )


class FilterByFieldTool(Tool):
    """Filter logs by field value"""
    
    def __init__(self, processor: LogProcessor):
        super().__init__(
            name="filter_by_field",
            description="Filter logs where a specific field contains a value",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs to filter",
                    required=True
                ),
                ToolParameter(
                    name="field",
                    param_type=ParameterType.STRING,
                    description="Field name to search in",
                    required=True,
                    example="_source.log"
                ),
                ToolParameter(
                    name="value",
                    param_type=ParameterType.STRING,
                    description="Value to search for",
                    required=True,
                    example="registration"
                )
            ]
        )
        self.processor = processor
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        field = kwargs.get("field")
        value = kwargs.get("value")
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data=pd.DataFrame(),
                message="No logs to filter",
                metadata={"count": 0}
            )
        
        # Check if field exists
        if field not in logs.columns:
            return ToolResult(
                success=False,
                data=None,
                error=f"Field '{field}' not found in logs"
            )
        
        # Filter logs where field contains value
        mask = logs[field].astype(str).str.contains(value, case=False, na=False)
        filtered = logs[mask]
        count = len(filtered)
        
        if count == 0:
            return ToolResult(
                success=True,
                data=filtered,
                message=f"No logs found where {field} contains '{value}'",
                metadata={"count": 0, "field": field, "value": value}
            )
        
        return ToolResult(
            success=True,
            data=filtered,
            message=f"Found {count} logs where {field} contains '{value}'",
            metadata={"count": count, "field": field, "value": value}
        )


class GetLogCountTool(Tool):
    """Count number of logs"""
    
    def __init__(self, processor: LogProcessor):
        super().__init__(
            name="get_log_count",
            description="Get the count of logs in a dataset",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs to count",
                    required=True
                )
            ]
        )
        self.processor = processor
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        
        if logs is None:
            count = 0
        else:
            count = len(logs)
        
        return ToolResult(
            success=True,
            data={"count": count},
            message=f"Log count: {count}",
            metadata={"count": count}
        )

