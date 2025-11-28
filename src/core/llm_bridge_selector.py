"""LLM-guided bridge selection for intelligent iterative search."""

from typing import Dict, Any, List
import pandas as pd
from ..llm import OllamaClient, PromptBuilder
from ..utils.logger import setup_logger
from .iterative_search import rank_bridge_entities

logger = setup_logger()


class LLMGuidedBridgeSelector:
    """
    Uses LLM to intelligently select which bridge entity to explore next.
    
    Considers semantic relationships, domain knowledge, and log context
    to rank bridges by likelihood of leading to target.
    """
    
    def __init__(self, llm_client: OllamaClient, prompt_builder: PromptBuilder):
        """
        Initialize LLM bridge selector.
        
        Args:
            llm_client: OllamaClient for LLM interaction
            prompt_builder: PromptBuilder for formatting prompts
        """
        self.llm = llm_client
        self.prompt_builder = prompt_builder
        self.reasoning_cache = {}  # Cache LLM decisions
        
        logger.info("Initialized LLMGuidedBridgeSelector")
    
    def select_next_bridge(
        self,
        query: str,
        source_entity: Dict[str, str],
        target_entity_type: str,
        bridge_candidates: List[Dict],
        context_logs: pd.DataFrame,
        iteration: int
    ) -> List[Dict]:
        """
        Use LLM to rank bridge entities by likelihood of leading to target.
        
        Args:
            query: Original user query for context
            source_entity: {"type": "cm", "value": "x"}
            target_entity_type: "md_id"
            bridge_candidates: [{"type": "rpdname", "value": "RPD001"}, ...]
            context_logs: Logs where source was found
            iteration: Current iteration number
            
        Returns:
            Sorted list of bridge entities with LLM confidence and rationale
        """
        # Create cache key
        cache_key = (
            source_entity["type"],
            target_entity_type,
            tuple(sorted([(b["type"], b["value"]) for b in bridge_candidates]))
        )
        
        if cache_key in self.reasoning_cache:
            logger.info("Using cached LLM bridge reasoning")
            return self.reasoning_cache[cache_key]
        
        # Build reasoning prompt
        prompt = self._build_reasoning_prompt(
            query=query,
            source_entity=source_entity,
            target_entity_type=target_entity_type,
            bridge_candidates=bridge_candidates,
            context_logs=context_logs,
            iteration=iteration
        )
        
        logger.info("Asking LLM to reason about bridge selection...")
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for consistent reasoning
                system_prompt=self._get_system_prompt()
            )
            
            # Parse LLM response
            ranked_bridges = self._parse_reasoning_response(response, bridge_candidates)
            
            # Cache the result
            self.reasoning_cache[cache_key] = ranked_bridges
            
            logger.info(f"LLM ranked {len(ranked_bridges)} bridges")
            
            return ranked_bridges
            
        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}, falling back to static ranking")
            return self._static_ranking(bridge_candidates)
    
    def _get_system_prompt(self) -> str:
        """System prompt for bridge reasoning."""
        return """You are a log analysis expert specializing in entity relationships.

Your task: Given a search query and potential bridge entities, reason about which bridge is most likely to lead to the target entity.

Consider:
1. Semantic relationships (which entities are typically connected in log systems?)
2. Technical domain knowledge (cable modem systems, networking, provisioning)
3. Log context (what do the sample logs tell us?)
4. Entity specificity (more specific entities are better bridges)

Provide clear reasoning and confidence scores."""
    
    def _build_reasoning_prompt(
        self,
        query: str,
        source_entity: Dict,
        target_entity_type: str,
        bridge_candidates: List[Dict],
        context_logs: pd.DataFrame,
        iteration: int
    ) -> str:
        """Build prompt asking LLM to reason about bridge selection."""
        # Format bridge candidates
        bridges_str = "\n".join([
            f"  {i+1}. {b['type']}: {b['value']}"
            for i, b in enumerate(bridge_candidates)
        ])
        
        # Get sample log context (first 5 logs)
        sample_logs = context_logs.head(5).to_dict('records') if len(context_logs) > 0 else []
        logs_str = self.prompt_builder.format_log_chunk(sample_logs) if sample_logs else "No logs available"
        
        return f"""You are helping find entity relationships in log data.

QUERY: {query}

CURRENT SITUATION:
- We are looking for: {target_entity_type}
- We started with: {source_entity['type']} = {source_entity['value']}
- The target '{target_entity_type}' was NOT found directly in logs with {source_entity['value']}
- This is iteration {iteration} of our search

SAMPLE LOGS WHERE SOURCE WAS FOUND:
{logs_str}

BRIDGE ENTITIES EXTRACTED FROM THESE LOGS:
{bridges_str}

YOUR TASK:
Reason about which bridge entity is most likely to lead us to '{target_entity_type}'.

Think about:
- Which entities are semantically related in typical log systems?
- What technical relationships exist between these entity types?
- What do the sample logs suggest about entity connections?
- Which bridge is most specific and likely to contain the target?

Respond in JSON format:
{{
  "reasoning": "Your detailed thought process explaining the relationships",
  "ranked_bridges": [
    {{
      "type": "entity_type",
      "value": "entity_value",
      "confidence": 0.92,
      "rationale": "Specific reason why this bridge is the best choice"
    }},
    ...
  ],
  "alternative_strategy": "If these bridges all fail, what else could we try?"
}}

Rank ALL bridges provided, from most to least likely."""
        
        return prompt
    
    def _parse_reasoning_response(
        self,
        response: Dict,
        original_candidates: List[Dict]
    ) -> List[Dict]:
        """Parse LLM reasoning and create ranked bridge list."""
        ranked = []
        
        reasoning = response.get("reasoning", "")
        bridges = response.get("ranked_bridges", [])
        
        logger.info(f"LLM Reasoning: {reasoning[:200]}...")
        
        # Match LLM ranked bridges with original candidates
        for bridge_data in bridges:
            matching = [
                c for c in original_candidates
                if c["type"] == bridge_data.get("type") and 
                   c["value"] == bridge_data.get("value")
            ]
            
            if matching:
                bridge = matching[0].copy()
                bridge["llm_confidence"] = bridge_data.get("confidence", 0.5)
                bridge["llm_rationale"] = bridge_data.get("rationale", "")
                ranked.append(bridge)
        
        # Add any candidates not ranked by LLM at the end
        ranked_values = {(b["type"], b["value"]) for b in ranked}
        for candidate in original_candidates:
            if (candidate["type"], candidate["value"]) not in ranked_values:
                candidate["llm_confidence"] = 0.3
                candidate["llm_rationale"] = "Not prioritized by LLM"
                ranked.append(candidate)
        
        return ranked
    
    def _static_ranking(self, candidates: List[Dict]) -> List[Dict]:
        """Fallback static ranking if LLM fails."""
        # Convert to ranking format
        tuples = [(c["type"], c["value"], c.get("score", 5)) for c in candidates]
        ranked_tuples = sorted(tuples, key=lambda x: x[2], reverse=True)
        
        # Convert back
        result = []
        for etype, evalue, score in ranked_tuples:
            result.append({
                "type": etype,
                "value": evalue,
                "llm_confidence": 0.5,
                "llm_rationale": "Static ranking fallback (LLM unavailable)"
            })
        
        return result

