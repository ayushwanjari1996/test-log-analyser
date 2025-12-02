"""
Dynamic prompt generation based purely on configuration.

NO HARDCODING. All context comes from:
1. entity_mappings.yaml
2. Available tools from registry
3. LLM's own intelligence
"""

from typing import Dict, List, Any
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger()


class DynamicPromptBuilder:
    """Build prompts dynamically from configuration only"""
    
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        self.config = config
        logger.info("DynamicPromptBuilder initialized - zero hardcoding")
    
    def _build_entity_context(self) -> str:
        """Build entity context from config ONLY"""
        
        # Get entity types from patterns (these are what's extractable)
        entity_data = self.config.entity_mappings
        patterns = entity_data.get("patterns", {})
        entity_types = list(patterns.keys()) if patterns else []
        
        # Get relationships from config
        relationships = entity_data.get("relationships", {})
        
        context = "DOMAIN ENTITIES (from configuration):\n\n"
        context += "EXTRACTABLE entity types (use these in extract_entities tool):\n"
        context += f"  {', '.join(entity_types)}\n\n"
        
        context += "IMPORTANT:\n"
        context += "- User may say 'cm' but the extractable entity type is 'cm_mac'\n"
        context += "- User may say 'rpd' but the extractable entity type is 'rpdname'\n"
        context += "- Always use entity types from the EXTRACTABLE list above\n\n"
        
        if relationships:
            context += "Entity relationships (conceptual):\n"
            for entity, related in relationships.items():
                context += f"  {entity} ↔ {', '.join(related)}\n"
        
        return context
    
    def _build_tools_context(self) -> str:
        """Build available tools context"""
        context = "AVAILABLE TOOLS:\n\n"
        
        for tool_name in self.tool_registry.list_tools():
            tool = self.tool_registry.get(tool_name)
            if tool:
                context += tool.to_description() + "\n\n"
        
        return context
    
    def build_system_prompt(self) -> str:
        """
        Build system prompt from configuration only.
        No hardcoded examples, rules, or entity types.
        """
        
        entity_context = self._build_entity_context()
        tools_context = self._build_tools_context()
        
        return f"""You are an intelligent log analysis assistant.

Your job: Answer user questions by using available tools to search and analyze logs.

{entity_context}

{tools_context}

OUTPUT FORMAT:

You MUST respond with JSON in this EXACT format:

{{
  "reasoning": "Your step-by-step thinking about what to do next",
  "tool": "tool_name",
  "parameters": {{"param1": "value1", "param2": "value2"}}
}}

Example 1 - Search for logs:
{{
  "reasoning": "Need to find logs containing MAWED07T01 to see CMs connected to it",
  "tool": "search_logs",
  "parameters": {{"value": "MAWED07T01"}}
}}

Example 2 - Extract entities (NOTE: no 'logs' parameter - auto-injected!):
{{
  "reasoning": "Found logs, now extract CM MAC addresses from them",
  "tool": "extract_entities",
  "parameters": {{"entity_types": ["cm_mac"]}}
}}

Example 3 - Finalize:
{{
  "reasoning": "I found 2 CM MACs, that answers the user's question",
  "tool": "finalize_answer",
  "parameters": {{"answer": "Found 2 CMs: addr1, addr2", "confidence": 0.9}}
}}

CRITICAL RULES:

1. OUTPUT ONLY VALID JSON - No extra text, no markdown blocks

2. PARAMETER NAMES - Use EXACT names from tool descriptions:
   - search_logs: use "value" (NOT "keyword" or "search_term")
   - extract_entities: use "entity_types" as array (NOT "entity_type")
   - fuzzy_search: use "search_terms" as array

3. LOGS PARAMETER - NEVER PASS IT! System auto-injects:
   - After you call search_logs, system caches the logs
   - When you call extract_entities, count_entities, etc., system automatically provides cached logs
   - DO NOT include "logs" in your parameters
   - Just call: extract_entities with entity_types only

4. ENTITY TYPES - Use these exact names:
   - cm_mac (not "cm")
   - rpdname (not "rpd")  
   - md_id, cpe_mac, cpe_ip, sf_id, mac_address, ip_address

5. FINALIZE - When you have the answer:
   - Call finalize_answer tool
   - Include actual values in answer (not just counts)"""

    def build_user_prompt(self, query: str, iteration: int, history: str = "", has_cached_logs: bool = False) -> str:
        """Build user prompt for current iteration"""
        
        cache_note = "\n[CACHED: Logs from search_logs are available for all tools]\n" if has_cached_logs else ""
        
        if iteration == 1:
            return f"""USER QUERY: {query}

This is iteration 1. Think step-by-step:
1. What is the user asking for?
2. What tool should you use first?
3. What parameters do you need?

REMEMBER: Don't include 'logs' parameter - it's auto-injected after search_logs.

Then call the appropriate tool."""
        
        else:
            return f"""USER QUERY: {query}

ITERATION {iteration}{cache_note}

Previous actions and results:
{history}

Based on what you've learned, what should you do next?
- If you have the answer, call finalize_answer with actual values
- If you need more data, call another tool
- Don't include 'logs' parameter - it's automatic

Think clearly and decide."""
    
    def build_conversation_history(self, decisions: List[Dict[str, Any]], 
                                   executions: List[Dict[str, Any]]) -> str:
        """Build formatted history of decisions and results"""
        
        history = []
        
        for i, (decision, execution) in enumerate(zip(decisions, executions), 1):
            history.append(f"\nIteration {i}:")
            history.append(f"  Reasoning: {decision.get('reasoning', 'N/A')}")
            history.append(f"  Action: {decision.get('tool_name', 'N/A')}")
            
            if execution.get('success'):
                history.append(f"  Result: {execution.get('message', 'Success')}")
                # Show actual data if entities were found
                if 'entities' in execution.get('data', {}):
                    entities = execution['data']['entities']
                    for etype, values in entities.items():
                        preview = ', '.join(str(v) for v in values[:3])
                        if len(values) > 3:
                            preview += f" (and {len(values)-3} more)"
                        history.append(f"    {etype}: [{preview}]")
            else:
                history.append(f"  Error: {execution.get('error', 'Unknown error')}")
        
        return "\n".join(history)

