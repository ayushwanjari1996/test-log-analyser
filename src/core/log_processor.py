"""Log processing engine for reading, filtering, and extracting log data."""

import csv
import re
from typing import List, Dict, Any, Optional, Iterator, Tuple
from pathlib import Path
from datetime import datetime
import pandas as pd

from ..utils.logger import setup_logger
from ..utils.exceptions import LogFileError
from ..utils.config import config

logger = setup_logger()


class LogProcessor:
    """
    Handles log file reading, filtering, and entity extraction.
    
    Features:
    - Streaming CSV reading for large files
    - Entity-based filtering
    - Time-range filtering
    - Pattern-based entity extraction
    """
    
    def __init__(self, log_file_path: str, schema_name: str = "default"):
        """
        Initialize log processor with file path and schema.
        
        Args:
            log_file_path: Path to the CSV log file
            schema_name: Schema name from log_schema.yaml
        """
        self.log_file_path = Path(log_file_path)
        self.schema_name = schema_name
        
        if not self.log_file_path.exists():
            raise LogFileError(f"Log file not found: {log_file_path}")
        
        if not self.log_file_path.suffix.lower() == '.csv':
            raise LogFileError(f"Only CSV files are supported: {log_file_path}")
        
        # Load schema configuration
        self.columns = config.get_log_columns(schema_name)
        logger.info(f"Initialized LogProcessor for {log_file_path} with schema '{schema_name}'")
    
    def read_csv_stream(self, chunk_size: int = 1000) -> Iterator[pd.DataFrame]:
        """
        Stream CSV file in chunks for memory-efficient processing.
        
        Args:
            chunk_size: Number of rows per chunk
            
        Yields:
            DataFrame chunks
        """
        try:
            logger.debug(f"Reading CSV in chunks of {chunk_size} rows")
            
            for chunk in pd.read_csv(
                self.log_file_path,
                chunksize=chunk_size,
                encoding='utf-8',
                on_bad_lines='skip'  # Skip malformed lines
            ):
                yield chunk
                
        except Exception as e:
            raise LogFileError(f"Error reading CSV file: {e}")
    
    def read_all_logs(self) -> pd.DataFrame:
        """
        Read entire log file into memory.
        Use this for smaller files or when you need all data at once.
        
        Returns:
            DataFrame with all log entries
        """
        try:
            logger.debug(f"Reading entire log file: {self.log_file_path}")
            df = pd.read_csv(
                self.log_file_path,
                encoding='utf-8',
                on_bad_lines='skip'
            )
            logger.info(f"Loaded {len(df)} log entries")
            return df
            
        except Exception as e:
            raise LogFileError(f"Error reading log file: {e}")
    
    def filter_by_entity(
        self, 
        logs: pd.DataFrame, 
        entity_column: str, 
        entity_value: str,
        exact_match: bool = False
    ) -> pd.DataFrame:
        """
        Filter logs by entity value.
        
        Args:
            logs: DataFrame of log entries
            entity_column: Column name to filter on
            entity_value: Value to search for
            exact_match: If True, only exact matches; if False, substring matches
            
        Returns:
            Filtered DataFrame
        """
        if entity_column not in logs.columns:
            logger.warning(f"Column '{entity_column}' not found in logs")
            return pd.DataFrame()
        
        try:
            if exact_match:
                filtered = logs[logs[entity_column] == entity_value]
            else:
                # Case-insensitive substring match
                filtered = logs[
                    logs[entity_column].astype(str).str.contains(
                        entity_value, 
                        case=False, 
                        na=False,
                        regex=False
                    )
                ]
            
            logger.debug(f"Filtered to {len(filtered)} entries matching '{entity_value}'")
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering by entity: {e}")
            return pd.DataFrame()
    
    def filter_by_timerange(
        self,
        logs: pd.DataFrame,
        timestamp_column: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        time_format: str = "%Y-%m-%d %H:%M:%S"
    ) -> pd.DataFrame:
        """
        Filter logs by time range.
        
        Args:
            logs: DataFrame of log entries
            timestamp_column: Column containing timestamps
            start_time: Start time (inclusive)
            end_time: End time (inclusive)
            time_format: Timestamp format string
            
        Returns:
            Filtered DataFrame
        """
        if timestamp_column not in logs.columns:
            logger.warning(f"Timestamp column '{timestamp_column}' not found")
            return logs
        
        try:
            # Convert timestamp column to datetime
            logs[timestamp_column] = pd.to_datetime(
                logs[timestamp_column], 
                format=time_format,
                errors='coerce'
            )
            
            # Apply filters
            if start_time:
                start_dt = pd.to_datetime(start_time, format=time_format)
                logs = logs[logs[timestamp_column] >= start_dt]
            
            if end_time:
                end_dt = pd.to_datetime(end_time, format=time_format)
                logs = logs[logs[timestamp_column] <= end_dt]
            
            logger.debug(f"Filtered to {len(logs)} entries in time range")
            return logs
            
        except Exception as e:
            logger.error(f"Error filtering by time range: {e}")
            return logs
    
    def extract_entities(
        self,
        logs: pd.DataFrame,
        entity_type: str,
        search_columns: Optional[List[str]] = None
    ) -> Dict[str, List[int]]:
        """
        Extract entities from logs using regex patterns.
        
        Args:
            logs: DataFrame of log entries
            entity_type: Type of entity (e.g., 'cm', 'md_id')
            search_columns: Columns to search in (default: all text columns)
            
        Returns:
            Dictionary mapping entity values to list of row indices
        """
        patterns = config.get_entity_pattern(entity_type)
        
        if not patterns:
            logger.warning(f"No patterns defined for entity type '{entity_type}'")
            return {}
        
        # Determine columns to search
        if search_columns is None:
            search_columns = logs.select_dtypes(include=['object']).columns.tolist()
        
        entities_found: Dict[str, List[int]] = {}
        
        try:
            for pattern in patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                
                for col in search_columns:
                    if col not in logs.columns:
                        continue
                    
                    for idx, value in logs[col].items():
                        if pd.isna(value):
                            continue
                        
                        matches = regex.findall(str(value))
                        for match in matches:
                            entity_value = match if isinstance(match, str) else match[0]
                            
                            if entity_value not in entities_found:
                                entities_found[entity_value] = []
                            
                            if idx not in entities_found[entity_value]:
                                entities_found[entity_value].append(idx)
            
            logger.info(f"Extracted {len(entities_found)} unique '{entity_type}' entities")
            return entities_found
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return {}
    
    def get_context_around_line(
        self,
        logs: pd.DataFrame,
        line_index: int,
        before_lines: int = 10,
        after_lines: int = 10
    ) -> pd.DataFrame:
        """
        Get context lines around a specific log entry.
        
        Args:
            logs: DataFrame of log entries
            line_index: Index of the target line
            before_lines: Number of lines before
            after_lines: Number of lines after
            
        Returns:
            DataFrame with context lines
        """
        start_idx = max(0, line_index - before_lines)
        end_idx = min(len(logs), line_index + after_lines + 1)
        
        context = logs.iloc[start_idx:end_idx]
        logger.debug(f"Retrieved {len(context)} context lines around index {line_index}")
        
        return context
    
    def search_text(
        self,
        logs: pd.DataFrame,
        search_term: str,
        search_columns: Optional[List[str]] = None,
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """
        Search for text across log entries.
        
        Args:
            logs: DataFrame of log entries
            search_term: Text to search for
            search_columns: Columns to search in (default: all text columns)
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            Filtered DataFrame with matching entries
        """
        if search_columns is None:
            search_columns = logs.select_dtypes(include=['object']).columns.tolist()
        
        try:
            # Create mask for matching rows
            mask = pd.Series([False] * len(logs), index=logs.index)
            
            for col in search_columns:
                if col not in logs.columns:
                    continue
                
                mask |= logs[col].astype(str).str.contains(
                    search_term,
                    case=case_sensitive,
                    na=False,
                    regex=False
                )
            
            result = logs[mask]
            logger.debug(f"Found {len(result)} entries matching '{search_term}'")
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching text: {e}")
            return pd.DataFrame()
    
    def filter_by_severity(
        self,
        logs: pd.DataFrame,
        severity_column: str = "severity",
        min_severity: str = "INFO"
    ) -> pd.DataFrame:
        """
        Filter logs by minimum severity level.
        
        Args:
            logs: DataFrame of log entries
            severity_column: Column containing severity levels
            min_severity: Minimum severity level (DEBUG, INFO, WARN, ERROR, CRITICAL)
            
        Returns:
            Filtered DataFrame
        """
        severity_order = {
            "DEBUG": 0,
            "INFO": 1,
            "WARN": 2,
            "WARNING": 2,
            "ERROR": 3,
            "CRITICAL": 4,
            "FATAL": 4
        }
        
        if severity_column not in logs.columns:
            logger.warning(f"Severity column '{severity_column}' not found")
            return logs
        
        try:
            min_level = severity_order.get(min_severity.upper(), 0)
            
            def severity_filter(severity_value):
                if pd.isna(severity_value):
                    return False
                severity_str = str(severity_value).upper()
                return severity_order.get(severity_str, 0) >= min_level
            
            filtered = logs[logs[severity_column].apply(severity_filter)]
            logger.debug(f"Filtered to {len(filtered)} entries at {min_severity}+ level")
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering by severity: {e}")
            return logs
    
    def get_statistics(self, logs: pd.DataFrame) -> Dict[str, Any]:
        """
        Get basic statistics about the log data.
        
        Args:
            logs: DataFrame of log entries
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_entries": len(logs),
            "columns": list(logs.columns),
            "memory_usage_mb": logs.memory_usage(deep=True).sum() / (1024 * 1024),
        }
        
        # Count by severity if column exists
        if "severity" in logs.columns:
            stats["severity_counts"] = logs["severity"].value_counts().to_dict()
        
        # Time range if timestamp column exists
        timestamp_cols = [col for col in logs.columns if "time" in col.lower()]
        if timestamp_cols:
            ts_col = timestamp_cols[0]
            try:
                logs[ts_col] = pd.to_datetime(logs[ts_col], errors='coerce')
                stats["time_range"] = {
                    "earliest": str(logs[ts_col].min()),
                    "latest": str(logs[ts_col].max())
                }
            except:
                pass
        
        return stats

