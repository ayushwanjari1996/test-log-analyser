"""
Timeline Analysis Method - Build chronological timeline of events.
"""

import logging
from typing import Dict
from datetime import datetime
from .base_method import BaseMethod

logger = logging.getLogger(__name__)


class TimelineAnalysisMethod(BaseMethod):
    """Build chronological timeline of events."""
    
    def __init__(self, llm_client):
        super().__init__("timeline_analysis")
        self.llm_client = llm_client
    
    def execute(self, params: Dict, context) -> Dict:
        """
        Build timeline of events from logs.
        
        Args:
            params: Optionally contains specific logs
            context: AnalysisContext with all_logs
            
        Returns:
            Dict with timeline, duration, event distribution
        """
        logs = params.get("logs", context.all_logs if context.all_logs else [])
        
        if not logs:
            logger.warning("No logs available for timeline analysis")
            return {"timeline": [], "duration": "N/A", "event_distribution": {}}
        
        logger.info(f"Building timeline from {len(logs)} logs")
        
        # Sort logs by timestamp
        sorted_logs = sorted(logs, key=lambda x: x.get("timestamp", ""))
        
        # Build prompt for LLM
        prompt = f"""Build a chronological timeline of key events from these logs:

{self._format_logs_for_llm(sorted_logs, limit=50)}

Create a timeline showing:
1. Timestamp of each significant event
2. Event description (what happened)
3. Entities involved
4. Event type (normal/warning/error/critical)
5. Impact or significance

Focus on important state changes, errors, and significant activities.
Group similar events if many repetitions.

Return JSON:
{{
  "timeline": [
    {{
      "timestamp": "HH:MM:SS",
      "event": "Description of what happened",
      "entities": ["entity1", "entity2"],
      "type": "normal|warning|error|critical",
      "significance": "Why this event matters"
    }}
  ],
  "key_observations": [
    "Overall observation about the timeline"
  ],
  "event_summary": {{
    "total_events": 10,
    "errors": 2,
    "warnings": 1,
    "normal": 7
  }}
}}
"""
        
        try:
            response = self.llm_client.generate_json(prompt)
            
            timeline = response.get("timeline", [])
            
            # Calculate duration
            duration = self._calculate_duration(sorted_logs)
            
            # Analyze distribution
            distribution = self._analyze_distribution(sorted_logs)
            
            logger.info(f"Timeline created: {len(timeline)} key events over {duration}")
            
            return {
                "timeline": timeline,
                "duration": duration,
                "event_distribution": distribution,
                "key_observations": response.get("key_observations", []),
                "event_summary": response.get("event_summary", {})
            }
        
        except Exception as e:
            logger.error(f"Timeline analysis failed: {e}")
            return {"timeline": [], "duration": "N/A", "event_distribution": {}, "error": str(e)}
    
    def _calculate_duration(self, logs: list) -> str:
        """Calculate time span of logs."""
        if not logs:
            return "N/A"
        
        try:
            timestamps = [log.get("timestamp", "") for log in logs if log.get("timestamp")]
            if not timestamps:
                return "N/A"
            
            first = timestamps[0]
            last = timestamps[-1]
            
            return f"{first} to {last}"
        except:
            return "N/A"
    
    def _analyze_distribution(self, logs: list) -> Dict:
        """Analyze severity distribution."""
        distribution = {
            "INFO": 0,
            "DEBUG": 0,
            "WARNING": 0,
            "ERROR": 0,
            "CRITICAL": 0
        }
        
        for log in logs:
            severity = log.get("severity", "INFO")
            if severity in distribution:
                distribution[severity] += 1
        
        return distribution

