"""
Pattern Analysis Method - Analyze patterns in log data using LLM.
"""

import logging
from typing import Dict
from .base_method import BaseMethod

logger = logging.getLogger(__name__)


class PatternAnalysisMethod(BaseMethod):
    """Analyze patterns in log data using LLM."""
    
    def __init__(self, llm_client):
        super().__init__("pattern_analysis")
        self.llm_client = llm_client
    
    def execute(self, params: Dict, context) -> Dict:
        """
        Analyze patterns in logs.
        
        Args:
            params: Optionally contains specific logs to analyze
            context: AnalysisContext with all_logs
            
        Returns:
            Dict with patterns and anomalies found
        """
        # Use provided logs or last 100 from context
        logs = params.get("logs", context.all_logs[-100:] if context.all_logs else [])
        
        if not logs:
            logger.warning("No logs available for pattern analysis")
            return {"patterns": [], "anomalies": []}
        
        logger.info(f"Analyzing patterns in {len(logs)} logs")
        
        # Build prompt for LLM
        prompt = f"""Perform DETAILED pattern analysis on these logs:

TOTAL LOGS: {len(logs)}

LOGS TO ANALYZE:
{self._format_logs_for_llm(logs, limit=50)}

Your task: Provide a COMPREHENSIVE analysis of patterns, behaviors, and anomalies.

ANALYSIS REQUIREMENTS:

1. **Message/Event Patterns:**
   - What types of messages/events appear? (e.g., "ProcEvAddCpe", "ConfigChange")
   - How frequently does each occur?
   - Are there any sequences (A always followed by B)?
   - Group similar events and count occurrences

2. **Timing Patterns:**
   - Regular intervals vs bursts vs continuous activity
   - Time gaps between events (delays, timeouts?)
   - Event rate (events per second/minute)
   - Any timing anomalies (too fast, too slow, stuck)

3. **Entity Behavior:**
   - Which entities are active? (CM MACs, CPE MACs, MDIDs, etc.)
   - What's the relationship between entities? (1 CM → multiple CPEs?)
   - Entity state changes (registration, config, offline)
   - Entity frequency (which entities appear most?)

4. **State Transitions:**
   - Lifecycle events (registration → active → offline)
   - Configuration changes
   - Error recovery sequences

5. **Anomalies & Issues:**
   - Repeated errors (same error multiple times)
   - Missing expected events (e.g., no response after request)
   - Unusual entity combinations
   - Suspicious timing (rapid retries, stuck loops)
   - Severity spikes (sudden ERROR after all INFO)

6. **Statistical Summary:**
   - Message type distribution (count each message type)
   - Severity distribution (INFO, DEBUG, ERROR counts)
   - Entity counts (how many unique CMs, CPEs, etc.)
   - Time span coverage

Return JSON with DETAILED findings:
{{
  "patterns": [
    {{
      "type": "message_frequency|timing|state_transition|entity_relationship|sequence",
      "description": "DETAILED description with specifics (not vague)",
      "details": "Additional context, examples, or evidence",
      "frequency": "Exact count or rate (e.g., '18 occurrences', 'every 5 seconds')",
      "entities_involved": ["cm_mac:20:f1:9e:ff:bc:76"],
      "confidence": 0.9,
      "significance": "Why this pattern matters"
    }}
  ],
  "anomalies": [
    {{
      "description": "SPECIFIC description of what's unusual",
      "evidence": "What in the logs proves this is anomalous",
      "severity": "low|medium|high",
      "affected_entities": ["entity1", "entity2"],
      "recommendation": "What should be investigated or fixed"
    }}
  ],
  "statistics": {{
    "message_types": {{"ProcEvAddCpe": 18, "ConfigChange": 6}},
    "severity_distribution": {{"DEBUG": 20, "INFO": 3, "ERROR": 1}},
    "entity_counts": {{"cm_mac": 1, "cpe_mac": 3, "md_id": 1}},
    "time_span": "15:30:00 to 15:32:00",
    "event_rate": "12 events per minute"
  }},
  "behavior_summary": "2-3 sentences describing the overall behavior observed in these logs",
  "health_assessment": "healthy|warning|error - based on patterns detected"
}}
"""
        
        try:
            response = self.llm_client.generate_json(prompt)
            
            patterns = response.get("patterns", [])
            anomalies = response.get("anomalies", [])
            statistics = response.get("statistics", {})
            
            logger.info(f"Found {len(patterns)} patterns, {len(anomalies)} anomalies")
            
            return {
                "patterns": patterns,
                "anomalies": anomalies,
                "statistics": statistics,
                "behavior_summary": response.get("behavior_summary", ""),
                "health_assessment": response.get("health_assessment", "unknown")
            }
        
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return {"patterns": [], "anomalies": [], "error": str(e)}

