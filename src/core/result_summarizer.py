"""
Result Summarizer for Iterative ReAct.

Creates compact summaries of tool results for state tracking
and context building.
"""

import logging
from typing import Any, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ResultSummarizer:
    """
    Creates compact summaries of tool execution results.
    
    Converts tool results (DataFrames, dicts, etc.) into
    human-readable summaries for LLM context.
    """
    
    def __init__(self, max_text_length: int = 100):
        """
        Initialize summarizer.
        
        Args:
            max_text_length: Maximum length for text summaries
        """
        self.max_text_length = max_text_length
        logger.info(f"ResultSummarizer initialized (max_length={max_text_length})")
    
    def summarize(self, result: Any) -> str:
        """
        Create compact summary of a tool result.
        
        Args:
            result: Tool result (ToolResult object or raw data)
            
        Returns:
            Human-readable summary string
        """
        # Handle None
        if result is None:
            return "No result"
        
        # If it's a ToolResult object, extract the data
        if hasattr(result, 'success'):
            if not result.success:
                error = getattr(result, 'error', 'Unknown error')
                return f"Error: {error}"
            
            # Use the message if available
            if hasattr(result, 'message') and result.message:
                return result.message
            
            # Otherwise summarize the data
            if hasattr(result, 'data'):
                return self._summarize_data(result.data)
        
        # Raw data
        return self._summarize_data(result)
    
    def _summarize_data(self, data: Any) -> str:
        """
        Summarize raw data.
        
        Args:
            data: Raw data to summarize
            
        Returns:
            Summary string
        """
        if data is None:
            return "No data"
        
        # DataFrame
        if isinstance(data, pd.DataFrame):
            return self._summarize_dataframe(data)
        
        # Dictionary
        elif isinstance(data, dict):
            return self._summarize_dict(data)
        
        # List
        elif isinstance(data, list):
            return self._summarize_list(data)
        
        # Scalar types
        elif isinstance(data, (int, float)):
            return str(data)
        
        # String
        elif isinstance(data, str):
            if len(data) > self.max_text_length:
                return data[:self.max_text_length] + "..."
            return data
        
        # Default
        else:
            text = str(data)
            if len(text) > self.max_text_length:
                return text[:self.max_text_length] + "..."
            return text
    
    def _summarize_dataframe(self, df: pd.DataFrame) -> str:
        """
        Summarize a DataFrame.
        
        Args:
            df: DataFrame to summarize
            
        Returns:
            Summary string
        """
        if len(df) == 0:
            return "Empty DataFrame (0 rows)"
        
        summary = f"DataFrame: {len(df)} rows"
        
        # Add column info if helpful
        if len(df.columns) <= 5:
            cols = ", ".join(df.columns)
            summary += f" ({cols})"
        else:
            summary += f" ({len(df.columns)} columns)"
        
        return summary
    
    def _summarize_dict(self, data: Dict) -> str:
        """
        Summarize a dictionary.
        
        Args:
            data: Dictionary to summarize
            
        Returns:
            Summary string
        """
        if not data:
            return "Empty dict"
        
        # Check if it's an entity dict (all values are lists)
        if all(isinstance(v, list) for v in data.values()):
            return self._summarize_entity_dict(data)
        
        # Regular dict
        parts = []
        for k, v in list(data.items())[:3]:  # First 3 keys
            if isinstance(v, (list, dict)):
                parts.append(f"{k}: {type(v).__name__}")
            else:
                parts.append(f"{k}: {v}")
        
        summary = "{" + ", ".join(parts)
        if len(data) > 3:
            summary += f", ... ({len(data)} keys total)"
        summary += "}"
        
        return summary
    
    def _summarize_entity_dict(self, data: Dict[str, list]) -> str:
        """
        Summarize an entity dictionary.
        
        Args:
            data: Entity dictionary (entity_type -> list of values)
            
        Returns:
            Summary string
        """
        parts = []
        for entity_type, values in data.items():
            count = len(values)
            if count > 0:
                # Show sample values
                sample = ", ".join(str(v) for v in values[:3])
                if count > 3:
                    sample += f" (and {count-3} more)"
                parts.append(f"{entity_type}: {count} [{sample}]")
            else:
                parts.append(f"{entity_type}: 0")
        
        return "Entities: " + "; ".join(parts)
    
    def _summarize_list(self, data: list) -> str:
        """
        Summarize a list.
        
        Args:
            data: List to summarize
            
        Returns:
            Summary string
        """
        if not data:
            return "Empty list"
        
        count = len(data)
        
        # Show first few items
        if count <= 3:
            items = ", ".join(str(x) for x in data)
            return f"[{items}]"
        else:
            items = ", ".join(str(x) for x in data[:3])
            return f"[{items}, ... ({count} items total)]"

