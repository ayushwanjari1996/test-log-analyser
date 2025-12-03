"""
Qwen Planner - Single LLM call to generate execution plan
"""

import json
from typing import Dict, Optional
from .ollama_client import OllamaClient
from ..utils.logger import setup_logger

logger = setup_logger()


class QwenPlanner:
    """
    Single LLM call planner using Qwen3 custom model.
    
    Input: Normalized query
    Output: JSON plan with operations and params
    
    NOTE: search_logs is NOT included in plan - it's hardcoded by executor
    """
    
    def __init__(self, llm_client: OllamaClient = None, model: str = "qwen3-loganalyzer"):
        """
        Initialize planner.
        
        Args:
            llm_client: OllamaClient instance (creates new if not provided)
            model: Model name (default: qwen3-loganalyzer custom model)
        """
        self.llm = llm_client or OllamaClient(model=model)
        self.model = model
        logger.info(f"QwenPlanner initialized with model: {model}")
    
    def create_plan(self, normalized_query: str) -> Dict:
        """
        Generate execution plan from normalized query.
        
        Args:
            normalized_query: Query with entity types normalized
            
        Returns:
            {
                "operations": ["filter_by_severity", "extract_entities"],
                "params": {"severities": ["ERROR"], "entity_types": ["cm_mac"]}
            }
        """
        prompt = f'Query: "{normalized_query}"\nOutput JSON plan: {{"operations": [...], "params": {{...}}}}'
        
        logger.info(f"Generating plan for: {normalized_query}")
        
        try:
            response = self.llm.generate(prompt)
            plan = self._parse_response(response)
            
            logger.info(f"Plan generated: {plan}")
            return plan
            
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            # Return empty plan (will just search and return logs)
            return {"operations": [], "params": {}}
    
    def _parse_response(self, response: str) -> Dict:
        """Parse LLM response to extract JSON plan."""
        
        # Remove thinking tags if present (Qwen3 feature)
        if "<think>" in response:
            response = response.split("</think>")[-1]
        
        response = response.strip()
        
        # Strategy 1: Direct parse
        try:
            return json.loads(response)
        except:
            pass
        
        # Strategy 2: Find JSON in response
        start = response.find("{")
        end = response.rfind("}") + 1
        
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except:
                pass
        
        # Strategy 3: Handle nested operations format
        # LLM sometimes returns operations as objects instead of strings
        try:
            parsed = json.loads(response[start:end] if start >= 0 else response)
            if "operations" in parsed:
                # Flatten if operations are objects
                ops = parsed["operations"]
                if ops and isinstance(ops[0], dict):
                    flat_ops = []
                    flat_params = parsed.get("params", {})
                    
                    for op in ops:
                        op_name = op.get("operation") or op.get("name")
                        if op_name:
                            flat_ops.append(op_name)
                            # Merge params
                            op_params = op.get("params") or op.get("parameters", {})
                            flat_params.update(op_params)
                    
                    return {"operations": flat_ops, "params": flat_params}
                
                return parsed
        except:
            pass
        
        logger.warning(f"Could not parse plan, returning empty: {response[:100]}")
        return {"operations": [], "params": {}}

