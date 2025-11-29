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
        prompt = f"""Analyze these logs and identify patterns:

{self._format_logs_for_llm(logs, limit=50)}

Your task:
1. Identify repeated event sequences
2. Detect timing patterns (regular intervals, bursts, gaps)
3. Find state transitions (e.g., online→offline, active→idle)
4. Discover common entity combinations (which entities appear together)
5. Spot anomalies or unusual behavior

Return JSON:
{{
  "patterns": [
    {{
      "type": "repeated_sequence|timing|state_transition|entity_combination",
      "description": "Human readable description",
      "frequency": "how often this occurs",
      "confidence": 0.0-1.0
    }}
  ],
  "anomalies": [
    {{
      "description": "What's unusual",
      "severity": "low|medium|high",
      "affected_entities": ["entity1", "entity2"]
    }}
  ],
  "summary": "Brief overall summary of patterns found"
}}
"""
        
        try:
            response = self.llm_client.generate_json(prompt)
            
            patterns = response.get("patterns", [])
            anomalies = response.get("anomalies", [])
            
            logger.info(f"Found {len(patterns)} patterns, {len(anomalies)} anomalies")
            
            return {
                "patterns": patterns,
                "anomalies": anomalies,
                "summary": response.get("summary", "")
            }
        
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return {"patterns": [], "anomalies": [], "error": str(e)}

