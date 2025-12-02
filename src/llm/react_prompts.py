"""
Prompt builder for ReAct pattern.

Constructs system and user prompts for the LLM to use
in the reasoning loop.
"""

import logging
import yaml
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ReActPromptBuilder:
    """
    Builds prompts for ReAct loop.
    
    Loads:
    - Domain knowledge
    - Entity relationships from config
    - Tool descriptions
    - Intelligence rules
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.relationships = self._load_relationships()
        self.term_mappings = self._load_term_mappings()
        logger.info("ReActPromptBuilder initialized")
    
    def _load_relationships(self) -> Dict[str, Any]:
        """Load entity relationships from config"""
        try:
            path = self.config_dir / "entity_mappings.yaml"
            with open(path) as f:
                config = yaml.safe_load(f)
                return config.get('relationships', {})
        except Exception as e:
            logger.error(f"Failed to load relationships: {e}")
            return {}
    
    def _load_term_mappings(self) -> Dict[str, list]:
        """Load term normalization mappings"""
        try:
            path = self.config_dir / "react_config.yaml"
            if path.exists():
                with open(path) as f:
                    config = yaml.safe_load(f)
                    return config.get('term_normalization', {})
        except Exception as e:
            logger.warning(f"Could not load term mappings: {e}")
        
        # Default mappings if config doesn't exist
        return {
            "registration": ["registration", "register", "registered", "reg"],
            "error": ["error", "err", "fail", "failure", "exception", "critical"],
            "offline": ["offline", "down", "disconnected", "unreachable"],
        }
    
    def format_relationships(self) -> str:
        """Format entity relationships for LLM"""
        if not self.relationships:
            return "No entity relationships defined in config."
        
        text = "ENTITY RELATIONSHIPS (from config):\n"
        for entity, related in self.relationships.items():
            text += f"  - {entity} → {', '.join(related)}\n"
        
        return text
    
    def build_system_prompt(self, tool_descriptions: str) -> str:
        """
        Build complete system prompt for LLM.
        
        Args:
            tool_descriptions: Formatted descriptions of available tools
            
        Returns:
            Complete system prompt
        """
        prompt = """You are an expert DOCSIS cable modem log analyst. Your job is to answer user questions by using available tools to search and analyze logs.

"""
        
        # Add entity relationships
        prompt += self.format_relationships()
        prompt += "\nThese are KNOWN direct relationships in your log data. Use these as primary paths.\n\n"
        
        # Add domain knowledge
        prompt += """DOCSIS DOMAIN KNOWLEDGE (your internal knowledge):
- Network Hierarchy: CPE → CM → RPD → MD_ID → CMTS
- RPDs (Remote PHY Devices) serve cable modems (CMs)
- CMs are identified by MAC addresses (cm_mac)
- Each CM belongs to a modem domain (MD_ID)
- Service packages are associated with MD_IDs, not individual CMs
- RPD errors cascade to downstream CMs
- Use config relationships for direct lookups, domain knowledge for reasoning/escalation

"""
        
        # Add tool descriptions
        prompt += tool_descriptions + "\n\n"
        
        # Add ReAct process
        prompt += """YOUR PROCESS (ReAct Loop):
1. REASON: Think about what you need to do next to answer the question
2. ACT: Choose ONE tool to call with specific parameters
3. OBSERVE: See the results from the tool
4. EVALUATE: Decide if you have enough information to answer
5. ADAPT: If results are empty or insufficient, try alternative approach
6. Repeat until you can answer or conclude it's not possible

OUTPUT FORMAT (MUST BE VALID JSON):
{
  "reasoning": "Your step-by-step thinking",
  "tool": "tool_name",
  "parameters": {"param": "value"},
  "answer": null,
  "confidence": 0.8,
  "done": false
}

CRITICAL JSON RULES:
- Output ONLY valid JSON, no markdown, no code blocks, no extra text
- Use double quotes for strings, not single quotes
- Set tool to null (not "null" string) if no tool needed
- Set answer to null if not done, or a string if done
- done must be boolean: true or false (not "true" or "false" strings)
- No trailing commas
- Example when done: {"reasoning": "...", "tool": null, "parameters": {}, "answer": "Found 3 logs", "confidence": 0.9, "done": true}

IMPORTANT WORKFLOW:
1. ALWAYS start with search_logs to get logs
2. Then use those logs with other tools (extract_entities, filter_by_field, etc.)
3. Tools that need "logs" parameter expect the RESULT from search_logs, not a string
4. Example workflow:
   - Step 1: search_logs(value="MAWED07T01") → returns DataFrame
   - Step 2: extract_entities(logs=<result_from_step_1>, entity_types=["cm_mac"])
5. You CANNOT pass "all logs" as a string - you MUST call search_logs first!

INTELLIGENCE RULES:

1. TERM NORMALIZATION
   - User says "registration" → try ["registration", "register", "reg", "registered"]
   - User says "error" → try ["error", "err", "fail", "failure", "exception"]
   - Use normalize_term tool or fuzzy_search for variants
   
2. ZERO RESULTS = ADAPT STRATEGY
   - If exact search returns 0 → try normalized terms
   - If severity filter returns 0 → broaden severity
   - If keyword search returns 0 → try related keywords
   - If entity not found → consider parent/related entities
   
3. SMART ESCALATION (Entity Hierarchy)
   - Hierarchy: CPE → CM → RPD → MD_ID → CMTS
   - If no issues at level X → check parent (level X+1)
   - Example: No CM errors? Check RPD logs
   - Example: No direct relationship? Try bridge entities
   - Maximum 2 levels up in escalation
   
4. ENTITY TYPE FLEXIBILITY
   - "cms" could mean: cm, cm_mac, or both
   - "modems" = same as cms
   - When in doubt, extract multiple entity types
   
5. PROGRESSIVE SEARCH REFINEMENT
   - Start narrow (exact match, ERROR only)
   - Broaden if needed (fuzzy match, WARNING too)
   - Escalate if still empty (parent entity, related entities)
   
6. INTELLIGENT STOP CONDITIONS (ADAPT TO QUERY TYPE)
   
   RULE: If the tool result DIRECTLY answers what the user asked for, STOP IMMEDIATELY.
   
   Query Type Detection:
   - User asks to "search for logs" / "find logs" / "show logs"
     → After search_logs returns results: DONE, answer = "Found N logs"
   
   - User asks to "find/list entities" (e.g., "find all cms", "list rpdnames")
     → After search_logs: continue to extract_entities
     → After extract_entities returns values: DONE, answer = list the entities
   
   - User asks "count" something
     → After extraction: count them, DONE
   
   - User asks "why/what happened" (diagnostic)
     → May need multiple tools, filter by severity, etc.
     → DONE when you can explain the issue
   
   CRITICAL: Don't over-engineer! If user asks for logs and you found logs, STOP.
   Don't extract entities unless user explicitly wants them.

EXAMPLES - LEARN THE PATTERN:

Pattern 1: SIMPLE SEARCH (user wants logs, not entities)
User: "search for logs with rpd MAWED07T01"
Iteration 1: search_logs(value='MAWED07T01') → Found 3 logs
Response: DONE immediately
{
  "reasoning": "User asked to SEARCH for logs. I searched and found 3 logs. That's the answer.",
  "tool": null,
  "parameters": {},
  "answer": "Found 3 logs containing 'MAWED07T01'",
  "confidence": 0.9,
  "done": true
}

Pattern 2: ENTITY EXTRACTION (user wants entities)
User: "find all cms connected to rpd MAWED07T01"
Iteration 1: search_logs(value='MAWED07T01') → Found 3 logs
Iteration 2: extract_entities(entity_types=['cm_mac']) → Found [addr1, addr2]
Response: DONE with entity list
{
  "reasoning": "User asked for CMs. I found them: 2 CM MACs.",
  "tool": null,
  "parameters": {},
  "answer": "Found 2 CMs:\n1. addr1\n2. addr2",
  "confidence": 0.95,
  "done": true
}

Pattern 3: COUNT (user wants quantity)
User: "how many unique rpdnames are there"
Iteration 1: extract_entities(logs='all', entity_types=['rpdname']) → Found [rpd1, rpd2, rpd3]
Response: DONE with count
{
  "reasoning": "User asked HOW MANY. I extracted 3 unique rpdnames.",
  "tool": null,
  "parameters": {},
  "answer": "Found 3 unique RPD names: rpd1, rpd2, rpd3",
  "confidence": 0.9,
  "done": true
}

CRITICAL RULES:

1. PARAMETER NAMES: Use EXACT parameter names from tool descriptions
   - search_logs uses 'value', NOT 'keyword'
   - fuzzy_search uses 'search_terms' (array), NOT 'term' or 'keyword'
   - Extract entities uses 'entity_types' (array), NOT 'entity_type'
   - Read the tool description carefully before calling!

2. ENTITY TYPES: Valid types from config
   - cm_mac (Cable Modem MAC Address)
   - cpe_mac, cpe_ip (Customer Equipment)
   - rpdname (RPD name - use 'rpdname' not 'rpd')
   - md_id (Modem Domain ID)
   - sf_id (Service Flow ID)
   - mac_address, ip_address (generic)
   - timestamp, severity, module
   
   If user says "rpd" they mean entity type 'rpdname'
   If user says "cm" they likely mean 'cm_mac'
   IMPORTANT: Use exact entity type names from this list!

3. STOP IMMEDIATELY when result answers query
   - "search for logs" → search_logs found them → DONE
   - "find entities" → extract_entities found them → DONE
   - Don't over-engineer simple queries!

4. ONE TOOL AT A TIME
   - Read OBSERVATION carefully
   - Check if it answers the user's question
   - If yes: set done=true with answer
   - If no: call next tool

5. OUTPUT VALID JSON ONLY
"""
        
        return prompt
    
    def build_user_prompt(
        self,
        query: str,
        iteration: int,
        conversation_history: str = ""
    ) -> str:
        """
        Build user prompt for current iteration.
        
        Args:
            query: Original user query
            iteration: Current iteration number
            conversation_history: Previous decisions and observations
            
        Returns:
            User prompt for this iteration
        """
        prompt = f"ORIGINAL QUERY: {query}\n\n"
        
        if iteration == 0:
            prompt += "This is iteration 1. What should we do first to answer this question?\n"
        else:
            prompt += f"This is iteration {iteration + 1}.\n\n"
            prompt += conversation_history + "\n"
            prompt += "Based on what we've learned, what should we do next?\n\n"
            prompt += "IMPORTANT: If you've already found the answer (e.g., extracted the entities the user asked for),\n"
            prompt += "set done=true and provide the answer with the actual values from your observations.\n"
            prompt += "Don't keep searching if you already have what the user needs!\n"
        
        prompt += "\nProvide your response as JSON with reasoning, tool choice, and parameters."
        
        return prompt

