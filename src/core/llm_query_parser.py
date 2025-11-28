"""LLM-based intelligent query parsing for complex natural language queries."""

import json
from typing import Dict, Any
from ..llm import OllamaClient, PromptBuilder
from ..utils.logger import setup_logger
from ..utils.exceptions import LLMError

logger = setup_logger()


class LLMQueryParser:
    """
    Uses LLM to parse natural language queries into structured format.
    Handles complex queries that rule-based parsing can't handle.
    """
    
    def __init__(self, llm_client: OllamaClient = None):
        """Initialize LLM query parser."""
        self.llm = llm_client or OllamaClient()
        
        # Load entity types from config
        from ..utils.config import config
        self.entity_types = list(config.entity_mappings.get("patterns", {}).keys())
        self.entity_aliases = config.entity_mappings.get("aliases", {})
        
        logger.info(f"Initialized LLMQueryParser with {len(self.entity_types)} entity types")
        logger.debug(f"Available entity types: {self.entity_types}")
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Use LLM to parse query into structured format.
        
        Args:
            query: Natural language query
            
        Returns:
            Parsed query dictionary with entities, types, values, intent
        """
        logger.info(f"Using LLM to parse query: '{query}'")
        
        prompt = self._build_parsing_prompt(query)
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent parsing
                system_prompt=self._get_system_prompt()
            )
            
            # Validate and normalize response
            parsed = self._validate_and_normalize(response, query)
            
            logger.info(f"LLM parsed as: {parsed['query_type']}")
            return parsed
            
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            # Return fallback structure
            return self._fallback_parse(query)
    
    def _get_system_prompt(self) -> str:
        """System prompt for query parsing."""
        return """You are a log analysis query parser. Your job is to understand what the user wants to find in log files.

Parse the user's natural language query and extract:
1. What they want to find (target entity type)
2. What they're searching for (source entity and its value)
3. The type of query (specific search, aggregation, relationship, analysis, or trace)
4. Any filter conditions

Be smart about distinguishing entity TYPES (like "cm", "modem") from entity VALUES (like "CM12345", "x").

Always respond in JSON format."""
    
    def _build_parsing_prompt(self, query: str) -> str:
        """Build prompt for LLM to parse query."""
        # Format entity types and aliases for the prompt
        entity_info = []
        for etype in self.entity_types:
            aliases = self.entity_aliases.get(etype, [])
            entity_info.append(f"  - {etype}: aliases = {aliases}")
        
        entity_types_str = "\n".join(entity_info)
        
        return f"""You are parsing a log analysis query. The system tracks these entity types:

AVAILABLE ENTITY TYPES:
{entity_types_str}

User Query: "{query}"

Your task:
1. Understand what the user wants to find
2. Identify entity types mentioned (use the list above)
3. Distinguish entity TYPES (patterns like "cm", "modem") from entity VALUES (specific instances like "CM12345", "x")
4. Determine if it's a simple search, aggregation, relationship query, analysis, or trace

Respond in this JSON format:
{{
  "query_type": "specific_value | aggregation | relationship | analysis | trace",
  "intent": "What the user wants in one sentence",
  "target_entity": {{
    "type": "Entity type from the list above",
    "value": "Specific value if mentioned, or null if searching for all",
    "reasoning": "Your reasoning for this choice"
  }},
  "source_entity": {{
    "type": "Entity type to search from (or null)",
    "value": "Specific value to search for (or null)",
    "is_value": true,
    "reasoning": "Explain if this is searching for a specific VALUE or a TYPE pattern"
  }},
  "filter_conditions": ["error", "timeout", "warning", etc.],
  "search_strategy": "direct | aggregation | iterative | analysis | trace",
  "confidence": 0.0-1.0
}}

KEY DISTINCTIONS:
- "find cm x" → search for VALUE "x" (specific instance)
- "find all cms" → search for TYPE "cm" pattern (all instances)
- "find A for B x" → search VALUE "x" of type B, then extract TYPE A
- "why did x fail" → analyze VALUE "x"
- "trace x" → follow timeline of VALUE "x"

Think step by step:
1. What entity types are mentioned?
2. Are there specific values (like "x", "CM12345") or requesting all?
3. Is it asking about one specific thing or many things?
4. Is it a simple find, a relationship between entities, or deep analysis?

Now parse: "{query}"
"""
    
    def _validate_and_normalize(self, response: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """
        Validate LLM response and normalize to expected format.
        """
        # Ensure required fields
        result = {
            "query_type": response.get("query_type", "specific_value"),
            "intent": response.get("intent", "Find entities in logs"),
            "original_query": original_query,
            "llm_parsed": True,
            "confidence": response.get("confidence", 0.8)
        }
        
        # Normalize target entity
        target = response.get("target_entity", {})
        result["primary_entity"] = {
            "type": target.get("type", "unknown"),
            "value": target.get("value"),
            "reasoning": target.get("reasoning", "")
        }
        
        # Normalize source entity
        source = response.get("source_entity", {})
        if source and source.get("type"):
            result["secondary_entity"] = {
                "type": source.get("type"),
                "value": source.get("value"),
                "is_value": source.get("is_value", True),
                "reasoning": source.get("reasoning", "")
            }
        else:
            result["secondary_entity"] = None
        
        # Filter conditions
        result["filter_conditions"] = response.get("filter_conditions", [])
        
        # Search strategy
        result["search_strategy"] = response.get("search_strategy", "direct")
        
        # Mode for LLM interaction
        query_type = result["query_type"]
        if query_type == "analysis":
            result["mode"] = "analyze"
        elif query_type == "trace":
            result["mode"] = "trace"
        else:
            result["mode"] = "find"
        
        logger.debug(f"Normalized parse result: {result}")
        
        return result
    
    def _fallback_parse(self, query: str) -> Dict[str, Any]:
        """
        Fallback parsing if LLM fails.
        Simple extraction of last word as entity value.
        """
        logger.warning("Using fallback parsing")
        
        words = query.split()
        value = words[-1] if words else None
        
        return {
            "query_type": "specific_value",
            "intent": "Search for entity",
            "original_query": query,
            "llm_parsed": False,
            "confidence": 0.3,
            "primary_entity": {
                "type": "unknown",
                "value": value,
                "reasoning": "Fallback: extracted last word"
            },
            "secondary_entity": None,
            "filter_conditions": [],
            "search_strategy": "direct",
            "mode": "find"
        }
    
    def should_search_value(self, parsed: Dict[str, Any]) -> bool:
        """
        Determine if we should search for value or pattern.
        """
        if parsed["query_type"] == "aggregation":
            return False  # Use pattern
        
        primary = parsed["primary_entity"]
        if primary.get("value") is not None:
            return True
        
        if parsed["secondary_entity"]:
            secondary = parsed["secondary_entity"]
            if secondary.get("value") is not None and secondary.get("is_value", True):
                return True
        
        return False


class HybridQueryParser:
    """
    Combines rule-based and LLM-based parsing.
    Uses rule-based for speed, falls back to LLM for complex queries.
    """
    
    def __init__(self, llm_client: OllamaClient = None):
        """Initialize hybrid parser."""
        from .query_parser import QueryParser
        
        self.rule_parser = QueryParser()
        self.llm_parser = LLMQueryParser(llm_client)
        self.use_llm = True  # Can be toggled
        
        logger.info("Initialized HybridQueryParser")
    
    def parse_query(self, query: str, force_llm: bool = False) -> Dict[str, Any]:
        """
        Parse query using rule-based first, LLM if needed.
        
        Args:
            query: User query
            force_llm: Force LLM parsing even for simple queries
            
        Returns:
            Parsed query dictionary
        """
        # Always use LLM for maximum flexibility
        if self.use_llm or force_llm:
            logger.info("Using LLM-based parsing")
            return self.llm_parser.parse_query(query)
        else:
            # Fallback to rule-based
            logger.info("Using rule-based parsing")
            return self.rule_parser.parse_query(query)
    
    def set_llm_mode(self, enabled: bool):
        """Enable or disable LLM parsing."""
        self.use_llm = enabled
        logger.info(f"LLM parsing: {'enabled' if enabled else 'disabled'}")
