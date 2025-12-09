"""
Time-based tools for temporal analysis.

Sorting, filtering, and analyzing logs by timestamp.
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import re

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType

logger = logging.getLogger(__name__)


class SortByTimeTool(Tool):
    """
    Sort logs by timestamp in chronological order.
    Essential for flow and timeline analysis.
    """
    
    def __init__(self):
        super().__init__(
            name="sort_by_time",
            description="Sort logs chronologically by timestamp",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="Logs to sort (auto-injected)",
                    required=True
                ),
                ToolParameter(
                    name="order",
                    param_type=ParameterType.STRING,
                    description="Sort order: 'asc' (oldest first) or 'desc' (newest first)",
                    required=False
                )
            ]
        )
        self.requires_logs = True
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        order = kwargs.get("order", "asc").lower()
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data=pd.DataFrame(),
                message="No logs to sort"
            )
        
        try:
            # Find timestamp column
            time_col = self._find_time_column(logs)
            
            if not time_col:
                return ToolResult(
                    success=False,
                    data=None,
                    error="No timestamp column found in logs"
                )
            
            # Parse timestamps
            logs_copy = logs.copy()
            logs_copy['_parsed_time'] = self._parse_timestamps(logs_copy[time_col])
            
            # Sort
            ascending = (order == "asc")
            sorted_logs = logs_copy.sort_values('_parsed_time', ascending=ascending)
            
            # Drop temporary column
            sorted_logs = sorted_logs.drop(columns=['_parsed_time'])
            
            direction = "oldest→newest" if ascending else "newest→oldest"
            
            return ToolResult(
                success=True,
                data=sorted_logs,
                message=f"[RAW DATA] Sorted {len(sorted_logs)} log entries {direction}",
                metadata={"count": len(sorted_logs), "order": order, "data_type": "raw_logs"}
            )
            
        except Exception as e:
            logger.error(f"Sort failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Sort failed: {str(e)}"
            )
    
    def _find_time_column(self, logs: pd.DataFrame) -> Optional[str]:
        """Find timestamp column in DataFrame."""
        candidates = [
            '_source.@timestamp',
            '_source.date',
            '@timestamp',
            'timestamp',
            'date',
            'time'
        ]
        
        for col in candidates:
            if col in logs.columns:
                return col
        
        return None
    
    def _parse_timestamps(self, time_series: pd.Series) -> pd.Series:
        """Parse timestamp strings to datetime objects."""
        try:
            # Try custom format: "Nov 5, 2025 @ 15:30:51.495"
            parsed = pd.to_datetime(time_series, format="%b %d, %Y @ %H:%M:%S.%f", errors='coerce')
            # If many failed, try auto-detection
            if parsed.isna().sum() > len(parsed) * 0.5:
                parsed = pd.to_datetime(time_series, errors='coerce')
            return parsed
        except:
            # Fallback: return as-is (will sort lexicographically)
            return time_series


class ExtractTimeRangeTool(Tool):
    """
    Extract logs within a specific time window.
    Supports absolute and relative times.
    """
    
    def __init__(self):
        super().__init__(
            name="extract_time_range",
            description="Filter logs to specific time window",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="Logs to filter (auto-injected)",
                    required=True
                ),
                ToolParameter(
                    name="start_time",
                    param_type=ParameterType.STRING,
                    description="Start time (ISO or relative like 'now-1h')",
                    required=True
                ),
                ToolParameter(
                    name="end_time",
                    param_type=ParameterType.STRING,
                    description="End time (ISO or 'now')",
                    required=True
                )
            ]
        )
        self.requires_logs = True
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        start_time = kwargs.get("start_time", "")
        end_time = kwargs.get("end_time", "")
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data=pd.DataFrame(),
                message="No logs to filter"
            )
        
        if not start_time or not end_time:
            return ToolResult(
                success=False,
                data=None,
                error="Both start_time and end_time required"
            )
        
        try:
            # Find timestamp column
            time_col = self._find_time_column(logs)
            
            if not time_col:
                return ToolResult(
                    success=False,
                    data=None,
                    error="No timestamp column found"
                )
            
            # Parse start and end times
            start_dt = self._parse_time(start_time)
            end_dt = self._parse_time(end_time)
            
            # Parse log timestamps
            logs_copy = logs.copy()
            # Try custom format first
            parsed_times = pd.to_datetime(logs_copy[time_col], format="%b %d, %Y @ %H:%M:%S.%f", errors='coerce')
            # Fallback to auto if many failed
            if parsed_times.isna().sum() > len(parsed_times) * 0.5:
                parsed_times = pd.to_datetime(logs_copy[time_col], errors='coerce')
            logs_copy['_parsed_time'] = parsed_times
            
            # Filter
            mask = (logs_copy['_parsed_time'] >= start_dt) & (logs_copy['_parsed_time'] <= end_dt)
            filtered = logs_copy[mask].drop(columns=['_parsed_time'])
            
            return ToolResult(
                success=True,
                data=filtered,
                message=f"[RAW DATA] Extracted {len(filtered)} log entries between {start_time} and {end_time}",
                metadata={
                    "count": len(filtered),
                    "start": str(start_dt),
                    "end": str(end_dt),
                    "data_type": "raw_logs"
                }
            )
            
        except Exception as e:
            logger.error(f"Time range extraction failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Time range extraction failed: {str(e)}"
            )
    
    def _find_time_column(self, logs: pd.DataFrame) -> Optional[str]:
        """Find timestamp column."""
        candidates = [
            '_source.@timestamp',
            '_source.date',
            '@timestamp',
            'timestamp',
            'date',
            'time'
        ]
        
        for col in candidates:
            if col in logs.columns:
                return col
        
        return None
    
    def _parse_time(self, time_str: str) -> datetime:
        """
        Parse time string to datetime.
        Supports absolute and relative times.
        """
        time_str = time_str.strip()
        
        # Handle 'now'
        if time_str.lower() == 'now':
            return datetime.now()
        
        # Handle relative times: now-1h, now-30m, now-1d
        relative_pattern = r'now-(\d+)([hmd])'
        match = re.match(relative_pattern, time_str.lower())
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'h':
                delta = timedelta(hours=amount)
            elif unit == 'm':
                delta = timedelta(minutes=amount)
            elif unit == 'd':
                delta = timedelta(days=amount)
            else:
                delta = timedelta(hours=1)
            
            return datetime.now() - delta
        
        # Try parsing as ISO or standard formats
        try:
            return pd.to_datetime(time_str)
        except:
            # Fallback: assume it's a time string like "15:30:00"
            # Use today's date
            try:
                time_part = datetime.strptime(time_str, "%H:%M:%S").time()
                return datetime.combine(datetime.now().date(), time_part)
            except:
                # Last resort: return now
                logger.warning(f"Could not parse time '{time_str}', using now")
                return datetime.now()

