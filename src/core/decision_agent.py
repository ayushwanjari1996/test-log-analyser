"""
LLM Decision Agent - The intelligent orchestrator for analysis workflows.

This module implements the "brain" that decides what to do next during analysis.
Uses LLM reasoning with regex fallback for robustness.
"""

import logging
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .analysis_context import AnalysisContext
from ..llm.ollama_client import OllamaClient
from ..utils.config import config

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Represents a decision made by the agent."""
    method: str
    params: Dict = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0
    should_stop: bool = False
    expected_outcome: str = ""


class LLMDecisionAgent:
    """
    Intelligent orchestrator that decides analysis flow.
    
    At each step, it:
    1. Reviews current context (what we know)
    2. Evaluates available methods
    3. Decides the best next action
    4. Provides reasoning for the decision
    5. Falls back to regex rules if LLM fails
    """
    
    def __init__(
        self, 
        llm_client: OllamaClient,
        max_iterations: int = 10
    ):
        self.llm = llm_client
        self.max_iterations = max_iterations
        
        # Available methods (loaded dynamically)
        self.available_methods = [
            "direct_search",
            "iterative_search",
            "pattern_analysis",
            "timeline_analysis",
            "root_cause_analysis",
            "summarization",
            "relationship_mapping"
        ]
        
        # Load entity types dynamically from config
        self.entity_types = self._load_entity_types()
        
        logger.info(f"Decision Agent initialized (max_iterations={max_iterations})")
    
    def _load_entity_types(self) -> Dict[str, int]:
        """
        Load entity types and their priorities from config.
        Returns dict of entity_type -> default_priority.
        """
        entity_mappings = config.entity_mappings
        
        # Extract all entity types from patterns
        entity_types = {}
        if "patterns" in entity_mappings:
            for entity_type in entity_mappings["patterns"].keys():
                entity_types[entity_type] = 5  # Default priority
        
        logger.debug(f"Loaded {len(entity_types)} entity types from config")
        return entity_types
    
    def decide_next_step(
        self,
        query_intent: str,
        current_context: AnalysisContext,
        iteration: int
    ) -> Decision:
        """
        Decide what to do next in the analysis workflow.
        
        Args:
            query_intent: What user wants (e.g., "find_root_cause")
            current_context: Everything we know so far
            iteration: Current iteration number
            
        Returns:
            Decision object with method, params, reasoning, confidence
        """
        
        logger.info(f"\n{'='*60}")
        logger.info(f"DECISION AGENT - Iteration {iteration + 1}")
        logger.info(f"{'='*60}")
        
        # Safety: Prevent infinite loops
        if iteration >= self.max_iterations:
            logger.warning(f"Max iterations ({self.max_iterations}) reached")
            return Decision(
                method="summarization",
                reasoning=f"Max iterations ({self.max_iterations}) reached, finalizing results",
                should_stop=True,
                confidence=1.0
            )
        
        # Check if we're going in circles
        if current_context.is_going_in_circles():
            logger.warning("Circular reasoning detected, forcing strategy change")
            return self._get_alternative_decision(current_context)
        
        # Try LLM decision first
        try:
            decision = self._llm_decision(query_intent, current_context)
            
            # Validate decision
            if self._validate_decision(decision, current_context):
                logger.info(f"✓ LLM decision: {decision.method} (confidence: {decision.confidence:.2f})")
                return decision
            else:
                logger.warning("LLM decision invalid, using fallback")
                return self._fallback_decision(query_intent, current_context)
        
        except Exception as e:
            logger.error(f"LLM decision failed: {e}, using fallback")
            return self._fallback_decision(query_intent, current_context)
    
    def _llm_decision(self, intent: str, context: AnalysisContext) -> Decision:
        """Ask LLM to decide next step."""
        
        prompt = self._build_decision_prompt(intent, context)
        
        # Get LLM response
        response = self.llm.generate_json(prompt)
        
        # Parse decision
        decision = Decision(
            method=response.get("method", "summarization"),
            params=response.get("params", {}),
            reasoning=response.get("reasoning", "LLM decision"),
            confidence=response.get("confidence", 0.5),
            should_stop=response.get("should_stop", False),
            expected_outcome=response.get("expected_outcome", "")
        )
        
        return decision
    
    def _build_decision_prompt(self, intent: str, context: AnalysisContext) -> str:
        """Build prompt asking LLM what to do next."""
        
        # Get dynamic information
        entity_types_list = ", ".join(self.entity_types.keys())
        
        prompt = f"""You are an intelligent log analysis orchestrator. Decide the next best action.

QUERY: "{context.original_query}"
INTENT: {intent}
GOAL: {context.goal}
SUCCESS CRITERIA: {context.success_criteria}

CURRENT STATE:
{context.summary()}

ENTITIES DISCOVERED (with values):
{context.get_entities_detailed()}

RECENT LOGS:
{context.get_recent_logs_summary()}

STEPS TAKEN SO FAR:
{context.get_step_history_summary()}

AVAILABLE METHODS:
1. direct_search - Search for specific entity directly in logs
2. iterative_search - Find entity through related entities (multi-hop)
3. pattern_analysis - Analyze patterns in found logs using LLM
4. timeline_analysis - Build chronological timeline of events
5. root_cause_analysis - Find causal chains for errors
6. summarization - Summarize all findings (final step)
7. relationship_mapping - Map relationships between entities

ENTITY TYPES AVAILABLE:
{entity_types_list}

DECISION RULES:
- If query answered satisfactorily → choose 'summarization' and set should_stop=true
- If no logs found yet → try 'direct_search' on target entity
- If direct search failed (no logs) → try 'iterative_search' to find through related entities
- If found errors → do 'root_cause_analysis' to build causal chain
- If found logs but no errors and query asks "why" → still try 'iterative_search' for related entities
- If found interesting entities → do 'direct_search' on highest priority entity
- If many logs found → do 'pattern_analysis' or 'timeline_analysis' for insights
- If going in circles → try different method or 'summarization'
- If exhausted options → 'summarization' and stop

IMPORTANT:
- Do NOT hardcode entity values - use ACTUAL values from "ENTITIES DISCOVERED" above
- When using entity values in params, use the FULL VALUE (e.g., "2c:ab:a4:47:1a:d2", NOT "1" or truncated)
- For iterative_search, use the ACTUAL entity value from context (e.g., CPE IP address)
- Prioritize network entities (rpdname, ip_address) for connectivity issues
- Prioritize service flow entities (sf_id, md_id) for performance issues
- If iteration > 5, lean towards 'summarization' unless finding new information

Return ONLY valid JSON (no markdown):
{{
  "method": "method_name",
  "params": {{
    "entity_value": "FULL entity value from ENTITIES DISCOVERED (e.g., 2c:ab:a4:47:1a:d2)",
    "entity_type": "type if known",
    "search_scope": "focused or broad",
    "max_depth": 2
  }},
  "reasoning": "Why this method is the best next step (2-3 sentences max)",
  "confidence": 0.85,
  "should_stop": false,
  "expected_outcome": "What we hope to find with this action"
}}
"""
        
        return prompt
    
    def _validate_decision(self, decision: Decision, context: AnalysisContext) -> bool:
        """Validate that LLM decision makes sense."""
        
        # Check method exists
        if decision.method not in self.available_methods:
            logger.warning(f"Invalid method: {decision.method}")
            return False
        
        # Check confidence is reasonable
        if not (0.0 <= decision.confidence <= 1.0):
            logger.warning(f"Invalid confidence: {decision.confidence}")
            return False
        
        # Check entity_value is not truncated (common LLM mistake)
        entity_value = decision.params.get("entity_value") or decision.params.get("start_entity")
        if entity_value and len(entity_value) <= 2:
            # Suspiciously short - likely truncated (e.g., "1" instead of "2c:ab:a4:47:1a:d2")
            logger.warning(f"Entity value suspiciously short: '{entity_value}' - likely truncated")
            
            # Try to find the actual value from context
            if context.target_entity and len(context.target_entity) > 2:
                logger.info(f"Using context target_entity instead: {context.target_entity}")
                if "entity_value" in decision.params:
                    decision.params["entity_value"] = context.target_entity
                if "start_entity" in decision.params:
                    decision.params["start_entity"] = context.target_entity
            else:
                return False  # Can't fix it
        
        # Check not repeating same method with same params
        if context.step_history:
            last_step = context.step_history[-1]
            if (last_step.method == decision.method and 
                last_step.params.get("entity_value") == decision.params.get("entity_value")):
                logger.warning("Decision repeats last step exactly")
                return False
        
        return True
    
    def _fallback_decision(self, intent: str, context: AnalysisContext) -> Decision:
        """
        Regex-based fallback decision making.
        Used when LLM fails or gives invalid response.
        """
        
        logger.info("Using fallback decision logic")
        
        # Rule 1: No logs found yet → start with direct search
        if context.logs_analyzed == 0:
            return Decision(
                method="direct_search",
                params={
                    "entity_value": context.target_entity,
                    "entity_type": context.target_entity_type
                },
                reasoning="Fallback: No logs yet, starting with direct search of target entity",
                confidence=0.9
            )
        
        # Rule 2: Logs found but no errors and haven't tried iterative → try iterative
        if context.logs_analyzed > 0 and len(context.errors_found) == 0:
            if not context.has_tried("iterative_search"):
                return Decision(
                    method="iterative_search",
                    params={
                        "start_entity": context.target_entity,
                        "max_depth": 2
                    },
                    reasoning="Fallback: No direct errors found, exploring related entities",
                    confidence=0.75
                )
        
        # Rule 3: Errors found → analyze them
        if len(context.errors_found) > 0:
            if not context.has_tried("root_cause_analysis"):
                return Decision(
                    method="root_cause_analysis",
                    params={
                        "error_logs": context.errors_found[:10]  # Limit to 10
                    },
                    reasoning="Fallback: Errors detected, analyzing root cause",
                    confidence=0.85
                )
        
        # Rule 4: New entities in queue → search most important one
        if len(context.pending_entities) > 0:
            next_entity = context.pending_entities[0]  # Highest priority
            return Decision(
                method="direct_search",
                params={
                    "entity_value": next_entity.value,
                    "entity_type": next_entity.type
                },
                reasoning=f"Fallback: Exploring high-priority entity {next_entity.type}:{next_entity.value}",
                confidence=0.7
            )
        
        # Rule 5: Have logs but haven't analyzed patterns → analyze
        if context.logs_analyzed > 5 and not context.has_tried("pattern_analysis"):
            return Decision(
                method="pattern_analysis",
                params={},
                reasoning="Fallback: Analyzing patterns in found logs",
                confidence=0.6
            )
        
        # Rule 6: Nothing else to try → summarize
        return Decision(
            method="summarization",
            params={},
            reasoning="Fallback: Exhausted all strategies, summarizing findings",
            confidence=1.0,
            should_stop=True
        )
    
    def _get_alternative_decision(self, context: AnalysisContext) -> Decision:
        """
        Get alternative decision when stuck in a loop.
        Forces a different method.
        """
        
        # Find methods we haven't tried yet
        untried_methods = [
            m for m in self.available_methods 
            if not context.has_tried(m) and m != "summarization"
        ]
        
        if untried_methods:
            # Try pattern analysis or timeline if we have logs
            if context.logs_analyzed > 0:
                if "pattern_analysis" in untried_methods:
                    return Decision(
                        method="pattern_analysis",
                        params={},
                        reasoning="Breaking loop: Trying pattern analysis",
                        confidence=0.6
                    )
                elif "timeline_analysis" in untried_methods:
                    return Decision(
                        method="timeline_analysis",
                        params={},
                        reasoning="Breaking loop: Trying timeline analysis",
                        confidence=0.6
                    )
            
            # Otherwise try first untried method
            method = untried_methods[0]
            return Decision(
                method=method,
                params={},
                reasoning=f"Breaking loop: Trying alternative method {method}",
                confidence=0.5
            )
        
        # All methods tried, summarize
        return Decision(
            method="summarization",
            params={},
            reasoning="Breaking loop: All methods tried, summarizing",
            confidence=1.0,
            should_stop=True
        )
    
    def get_entity_priority(self, entity_type: str, intent: str, query: str = "") -> int:
        """
        Determine entity exploration priority based on type and query intent.
        Higher = more important to explore.
        
        This is dynamic based on query context, not hardcoded.
        """
        
        query_lower = query.lower()
        
        # For connectivity/offline issues - prioritize network entities
        if any(kw in query_lower for kw in ["offline", "down", "unreachable", "disconnect", "lost"]):
            priorities = {
                "rpdname": 10,  # Critical for connectivity
                "ip_address": 9,
                "interface": 8,
                "cm_mac": 7,
                "md_id": 6,
                "sf_id": 4
            }
        
        # For performance issues - prioritize service flow entities
        elif any(kw in query_lower for kw in ["slow", "latency", "timeout", "delay", "performance"]):
            priorities = {
                "sf_id": 10,  # Service flows critical for performance
                "md_id": 9,
                "ip_address": 7,
                "cm_mac": 6,
                "rpdname": 5,
                "interface": 4
            }
        
        # For error analysis - prioritize based on error context
        elif any(kw in query_lower for kw in ["error", "fail", "crash", "abort"]):
            priorities = {
                "md_id": 9,
                "cm_mac": 8,
                "sf_id": 7,
                "rpdname": 7,
                "ip_address": 6,
                "interface": 5
            }
        
        # Default priorities (balanced)
        else:
            priorities = {
                "cm_mac": 8,
                "rpdname": 7,
                "ip_address": 6,
                "md_id": 6,
                "sf_id": 5,
                "interface": 4
            }
        
        # Return priority for this entity type, default to 5 if not found
        return priorities.get(entity_type, 5)

