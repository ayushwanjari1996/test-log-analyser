"""
Root Cause Analysis Method - Find root cause of errors/issues.
"""

import logging
from typing import Dict
from .base_method import BaseMethod

logger = logging.getLogger(__name__)


class RootCauseAnalysisMethod(BaseMethod):
    """Find root cause of errors/issues."""
    
    def __init__(self, llm_client):
        super().__init__("root_cause_analysis")
        self.llm_client = llm_client
    
    def execute(self, params: Dict, context) -> Dict:
        """
        Analyze errors and find root cause.
        
        Args:
            params: May contain 'error_logs' to analyze
            context: AnalysisContext with errors_found and all_logs
            
        Returns:
            Dict with root_cause, causal_chain, confidence, evidence
        """
        error_logs = params.get("error_logs", context.errors_found if context.errors_found else [])
        all_logs = context.all_logs
        
        if not error_logs:
            logger.warning("No errors to analyze for root cause")
            return {
                "root_cause": None,
                "causal_chain": [],
                "confidence": 0.0,
                "evidence": []
            }
        
        logger.info(f"Analyzing root cause for {len(error_logs)} errors")
        
        # Get context logs (logs around the errors)
        context_logs = all_logs[-50:] if len(all_logs) > 50 else all_logs
        
        # Build prompt
        prompt = f"""You are analyzing logs to find the root cause of errors.

ERROR LOGS:
{self._format_logs_for_llm(error_logs, limit=20)}

CONTEXT (logs before/around the errors):
{self._format_logs_for_llm(context_logs, limit=30)}

ENTITY RELATIONSHIPS DISCOVERED:
{self._format_relationships(context.relationships)}

Your task:
1. Identify what failed or caused the errors
2. Determine when the problem started
3. Analyze what was happening before the failure
4. Identify which entity or component caused the issue
5. Build a causal chain showing how the problem developed

Return JSON:
{{
  "root_cause": "Clear description of the root cause",
  "causal_chain": [
    {{
      "step": 1,
      "timestamp": "HH:MM:SS",
      "entity": "entity_type:value",
      "event": "What happened",
      "impact": "How it affected the system"
    }}
  ],
  "confidence": 0.0-1.0,
  "supporting_evidence": [
    "Log excerpt or observation supporting this conclusion"
  ],
  "affected_entities": ["entity1", "entity2"],
  "recommendations": [
    "What to check or fix"
  ]
}}
"""
        
        try:
            response = self.llm_client.generate_json(prompt)
            
            root_cause = response.get("root_cause", "Unable to determine root cause")
            causal_chain = response.get("causal_chain", [])
            confidence = response.get("confidence", 0.5)
            evidence = response.get("supporting_evidence", [])
            
            logger.info(f"Root cause analysis complete (confidence: {confidence:.2f})")
            logger.info(f"Root cause: {root_cause}")
            
            return {
                "root_cause": root_cause,
                "causal_chain": causal_chain,
                "confidence": confidence,
                "evidence": evidence,
                "affected_entities": response.get("affected_entities", []),
                "recommendations": response.get("recommendations", []),
                "answer": root_cause  # For context.answer
            }
        
        except Exception as e:
            logger.error(f"Root cause analysis failed: {e}")
            return {
                "root_cause": None,
                "causal_chain": [],
                "confidence": 0.0,
                "evidence": [],
                "error": str(e)
            }
    
    def _format_relationships(self, relationships: list) -> str:
        """Format entity relationships for LLM."""
        if not relationships:
            return "No relationships discovered yet"
        
        formatted = []
        for rel in relationships[:10]:  # Limit to 10
            if isinstance(rel, tuple) and len(rel) >= 2:
                formatted.append(f"  - {rel[0]} ↔ {rel[1]}")
            else:
                formatted.append(f"  - {rel}")
        
        return "\n".join(formatted) if formatted else "No relationships"

