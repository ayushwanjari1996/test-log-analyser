"""
Output and formatting tools for presenting results to users.
"""

import pandas as pd
from datetime import datetime
from typing import Optional

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType


class ReturnLogsTool(Tool):
    """
    Formats and returns a human-readable summary of logs.
    Use this when the user explicitly asks to "see logs", "show logs", "get logs", etc.
    """
    
    def __init__(self):
        super().__init__(
            name="return_logs",
            description=(
                "Formats cached logs into a human-readable summary. "
                "Use this when user wants to SEE the actual logs, not just entities extracted from them. "
                "Returns: log count, time range, severity distribution, and sample log entries."
            ),
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="The logs to format (auto-injected from cache)",
                    required=False  # Auto-injected by orchestrator
                ),
                ToolParameter(
                    name="max_samples",
                    param_type=ParameterType.INTEGER,
                    description="Maximum number of sample log entries to include in summary (default: 5)",
                    required=False,
                    example=5
                )
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        max_samples = kwargs.get("max_samples", 5)
        
        if logs is None or (isinstance(logs, pd.DataFrame) and logs.empty):
            return ToolResult(
                success=True,
                data={"formatted": "No logs found"},
                message="No logs to format",
                metadata={"count": 0}
            )
        
        # Validate DataFrame
        if not isinstance(logs, pd.DataFrame):
            return ToolResult(
                success=False,
                data={},
                message="Expected logs to be a DataFrame",
                error="Invalid logs type"
            )
        
        count = len(logs)
        
        # Build summary
        summary_parts = []
        summary_parts.append(f"Found {count} log{'s' if count != 1 else ''}")
        
        # Time range
        time_field = self._find_time_field(logs)
        if time_field:
            try:
                times = pd.to_datetime(logs[time_field], errors='coerce')
                valid_times = times.dropna()
                if len(valid_times) > 0:
                    time_range = f"Time range: {valid_times.min()} to {valid_times.max()}"
                    summary_parts.append(time_range)
            except:
                pass
        
        # Severity distribution
        severity_field = self._find_severity_field(logs)
        if severity_field:
            try:
                severity_counts = logs[severity_field].value_counts().to_dict()
                severity_str = ", ".join([f"{count} {sev}" for sev, count in severity_counts.items()])
                summary_parts.append(f"Severity: {severity_str}")
            except:
                pass
        
        # Sample log entries
        sample_count = min(max_samples, count)
        summary_parts.append(f"\nShowing {sample_count} sample log entries:")
        
        for idx, (_, row) in enumerate(logs.head(sample_count).iterrows(), 1):
            log_content = self._extract_log_content(row)
            summary_parts.append(f"\n  [{idx}] {log_content}")
        
        if count > sample_count:
            summary_parts.append(f"\n... and {count - sample_count} more log entries")
        
        formatted_output = "\n".join(summary_parts)
        
        return ToolResult(
            success=True,
            data={"formatted": formatted_output, "count": count},
            message=f"Formatted {count} logs for display",
            metadata={
                "count": count,
                "samples_shown": sample_count
            }
        )
    
    def _find_time_field(self, logs: pd.DataFrame) -> Optional[str]:
        """Find timestamp field in logs"""
        time_candidates = ['@timestamp', 'timestamp', 'time', '_source.@timestamp']
        for field in time_candidates:
            if field in logs.columns:
                return field
        return None
    
    def _find_severity_field(self, logs: pd.DataFrame) -> Optional[str]:
        """Find severity/level field in logs"""
        severity_candidates = ['_source.log.severity', 'severity', 'level', 'log.severity']
        for field in severity_candidates:
            if field in logs.columns:
                return field
        return None
    
    def _extract_log_content(self, row: pd.Series) -> str:
        """Extract the main log content from a row"""
        # Try different possible log content fields
        content_candidates = ['_source.log', 'log', 'message', 'msg']
        
        for field in content_candidates:
            if field in row.index and pd.notna(row[field]):
                content = str(row[field])
                # Truncate if too long
                if len(content) > 200:
                    content = content[:200] + "..."
                return content
        
        # Fallback: return first non-null field value
        for field, value in row.items():
            if pd.notna(value) and field not in ['_id', 'index']:
                content = str(value)
                if len(content) > 200:
                    content = content[:200] + "..."
                return content
        
        return "[empty log entry]"

