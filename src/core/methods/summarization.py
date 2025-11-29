"""
Summarization Method - Create comprehensive summary of all findings.
"""

import logging
from typing import Dict
from .base_method import BaseMethod

logger = logging.getLogger(__name__)


class SummarizationMethod(BaseMethod):
    """Create comprehensive summary of all findings."""
    
    def __init__(self, llm_client):
        super().__init__("summarization")
        self.llm_client = llm_client
    
    def execute(self, params: Dict, context) -> Dict:
        """
        Create final summary of the entire analysis.
        
        Args:
            params: Not used
            context: AnalysisContext with all findings
            
        Returns:
            Dict with comprehensive summary
        """
        logger.info("Creating final summary of analysis")
        
        if context.logs_analyzed == 0:
            return {
                "summary": "No logs found for the query.",
                "status": "no_data",
                "confidence": 0.0
            }
        
        # Build comprehensive prompt
        prompt = f"""You are creating a final summary of a log analysis session.

ORIGINAL QUERY: "{context.original_query}"
GOAL: {context.goal}

ANALYSIS PROCESS:
{context.get_step_history_summary()}

FINDINGS:
- Total logs analyzed: {context.logs_analyzed}
- Entities discovered: {sum(len(v) for v in context.entities.values())}
- Errors found: {len(context.errors_found)}
- Patterns detected: {len(context.patterns)}

ENTITIES DISCOVERED:
{self._format_entities(context.entities)}

ERRORS (if any):
{self._format_logs_for_llm(context.errors_found, limit=10)}

SAMPLE LOGS:
{context.get_recent_logs_summary(limit=10)}

Your task: Create a comprehensive summary that explains:
1. What the user asked for
2. What we found
3. Key insights or timeline of events
4. Status assessment (healthy/issues found)
5. Any errors or root causes discovered
6. Recommendations or next steps

Return JSON:
{{
  "summary": "High-level summary (2-3 sentences)",
  "key_findings": [
    "Finding 1",
    "Finding 2"
  ],
  "timeline": [
    {{
      "time": "HH:MM:SS",
      "event": "What happened"
    }}
  ],
  "status": "healthy|warning|error|critical",
  "observations": [
    "Observation about the logs or entity behavior"
  ],
  "entities_involved": {{
    "entity_type": ["value1", "value2"]
  }},
  "severity_distribution": {{
    "INFO": 10,
    "ERROR": 2
  }},
  "recommendations": [
    "Next step or recommendation"
  ],
  "confidence": 0.0-1.0
}}
"""
        
        try:
            response = self.llm_client.generate_json(prompt)
            
            # Add metadata
            response["logs_analyzed"] = context.logs_analyzed
            response["iterations"] = context.iteration
            response["methods_used"] = list(context.methods_tried)
            
            logger.info(f"Summary created (status: {response.get('status', 'unknown')})")
            
            return response
        
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            
            # Fallback summary
            return {
                "summary": f"Analyzed {context.logs_analyzed} logs. " + 
                          (f"Found {len(context.errors_found)} errors." if context.errors_found 
                           else "No errors found."),
                "status": "error" if context.errors_found else "healthy",
                "key_findings": [f"Analyzed {context.logs_analyzed} log entries"],
                "observations": [],
                "confidence": 0.5,
                "error": str(e)
            }
    
    def _format_entities(self, entities: Dict) -> str:
        """Format entities dictionary for LLM."""
        if not entities:
            return "No entities discovered"
        
        formatted = []
        for entity_type, values in entities.items():
            formatted.append(f"  - {entity_type}: {', '.join(values[:5])}" + 
                           (f" (and {len(values)-5} more)" if len(values) > 5 else ""))
        
        return "\n".join(formatted)

