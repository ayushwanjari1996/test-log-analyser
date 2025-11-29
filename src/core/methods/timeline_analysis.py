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
        prompt = f"""Build a DETAILED chronological timeline of events from these logs:

TOTAL LOGS: {len(sorted_logs)}

LOGS (chronologically sorted):
{self._format_logs_for_llm(sorted_logs, limit=50)}

Your task: Create a COMPREHENSIVE timeline that tells the complete story of what happened.

REQUIREMENTS:
1. Include ALL significant events (don't skip important details)
2. For each event, provide:
   - Exact timestamp (HH:MM:SS.mmm format if available)
   - Clear description of what happened (be specific, not vague)
   - Which entities were involved (CM MAC, CPE MAC, MDID, etc.)
   - Event type (normal/warning/error/critical)
   - WHY this event matters in the overall flow
   - Any state changes or transitions

3. Group similar repetitive events (e.g., "5 CPE registration events between 15:30-15:32")
4. Identify patterns in timing (bursts, delays, gaps)
5. Note any anomalies or unexpected sequences
6. Provide context for technical events (e.g., what "ProcEvAddCpe" means)

DETAILED ANALYSIS:
- What was the entity doing throughout this period?
- Were there any errors or issues?
- What was the flow/sequence of operations?
- Any interesting patterns or anomalies?
- What's the current state at the end?

Return JSON:
{{
  "timeline": [
    {{
      "timestamp": "HH:MM:SS.mmm",
      "event": "DETAILED description of what happened (be specific!)",
      "entities": ["cm_mac:20:f1:9e:ff:bc:76", "cpe_mac:fc:ae:34:f2:3f:0d"],
      "type": "normal|warning|error|critical",
      "significance": "Why this event matters and how it fits in the overall flow",
      "technical_details": "Any relevant technical context"
    }}
  ],
  "flow_summary": "2-3 sentences describing the overall flow/story from start to end",
  "key_observations": [
    "Detailed observation about patterns, timing, or behavior",
    "Another important observation with specifics"
  ],
  "anomalies": [
    "Any unexpected behavior or issues detected"
  ],
  "event_summary": {{
    "total_events": 10,
    "errors": 2,
    "warnings": 1,
    "normal": 7
  }},
  "current_state": "What's the final state/status of the entity at the end of the timeline?"
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
                "flow_summary": response.get("flow_summary", ""),
                "key_observations": response.get("key_observations", []),
                "anomalies": response.get("anomalies", []),
                "event_summary": response.get("event_summary", {}),
                "current_state": response.get("current_state", "Unknown")
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

