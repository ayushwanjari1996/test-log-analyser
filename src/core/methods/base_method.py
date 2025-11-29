"""
Base Method - Abstract interface for all analysis methods.
"""

from abc import ABC, abstractmethod
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BaseMethod(ABC):
    """
    Abstract base class for all analysis methods.
    
    Each method must implement execute() which takes params and context
    and returns a result dictionary.
    """
    
    def __init__(self, name: str):
        self.name = name
        logger.debug(f"Method initialized: {name}")
    
    @abstractmethod
    def execute(self, params: Dict, context) -> Dict:
        """
        Execute the analysis method.
        
        Args:
            params: Parameters for this specific execution
            context: AnalysisContext with current state
            
        Returns:
            Dictionary with results:
                - logs: List of log entries found (if any)
                - entities: Dict of entity_type -> values found (if any)
                - errors: List of error logs (if any)
                - patterns: List of patterns detected (if any)
                - answer: Answer string (if found)
                - confidence: Confidence score 0.0-1.0 (if applicable)
                - ... method-specific fields
        """
        pass
    
    def _format_logs_for_llm(self, logs: list, limit: int = 50) -> str:
        """
        Format logs for LLM consumption.
        
        Args:
            logs: List of log dictionaries
            limit: Max number of logs to include
            
        Returns:
            Formatted string with logs
        """
        if not logs:
            return "No logs available"
        
        formatted = []
        for i, log in enumerate(logs[:limit], 1):
            timestamp = log.get("timestamp", "??:??:??")
            severity = log.get("severity", "INFO")
            message = log.get("message", "")
            
            formatted.append(f"{i}. [{timestamp}] {severity}: {message}")
        
        if len(logs) > limit:
            formatted.append(f"\n... and {len(logs) - limit} more logs")
        
        return "\n".join(formatted)

