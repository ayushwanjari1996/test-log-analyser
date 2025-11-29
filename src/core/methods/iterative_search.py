"""
Iterative Search Method - Find entity through chains of related entities.
"""

import logging
from typing import Dict
from .base_method import BaseMethod

logger = logging.getLogger(__name__)


class IterativeSearchMethod(BaseMethod):
    """Find entity through chains of related entities (multi-hop search)."""
    
    def __init__(self, processor, entity_manager, llm_client):
        super().__init__("iterative_search")
        self.processor = processor
        self.entity_manager = entity_manager
        self.llm_client = llm_client
    
    def execute(self, params: Dict, context) -> Dict:
        """
        Execute iterative search through entity relationships.
        
        Args:
            params: Contains 'start_entity', 'target_type', optionally 'max_depth'
            context: AnalysisContext with target entity info
            
        Returns:
            Dict with logs, entities, errors found through iterative search
        """
        start_entity = params.get("start_entity") or params.get("entity_value")
        target_type = params.get("target_type") or context.target_entity_type
        max_depth = params.get("max_depth", 2)
        
        if not start_entity:
            logger.error("No start_entity provided for iterative_search")
            return {"logs": [], "entities": {}, "errors": []}
        
        logger.info(f"Iterative search: {start_entity} → {target_type} (max_depth={max_depth})")
        
        # Import here to avoid circular dependency
        from ..iterative_search import IterativeSearchStrategy, set_llm_client
        
        # Set LLM client for smart bridge scoring
        if self.llm_client:
            set_llm_client(self.llm_client)
        
        # Read all logs
        all_logs = self.processor.read_all_logs()
        
        # Create strategy instance with enhanced limits
        # Note: max_iterations is DEPTH (how many levels to traverse)
        # Use fixed value of 5 instead of max_depth param which might be too small
        strategy = IterativeSearchStrategy(
            processor=self.processor,
            max_iterations=5,  # ✅ Fixed depth = 5 levels
            max_bridges_per_iteration=3,
            max_total_searches=20,
            timeout_seconds=30
        )
        
        # Execute search
        result = strategy.find_with_bridges(
            logs=all_logs,
            target_entity_type=target_type,
            source_entity_value=start_entity,
            source_entity_type=None  # Let it auto-detect
        )
        
        # Convert result to our format
        entities_dict = {}
        if result.get("found") and result.get("target_values"):
            # Add found target entities
            if target_type not in entities_dict:
                entities_dict[target_type] = []
            entities_dict[target_type].extend(result["target_values"])
        
        # Add bridge entities
        for bridge in result.get("bridge_entities", []):
            btype = bridge.get("type")
            bvalue = bridge.get("value")
            if btype and bvalue:
                if btype not in entities_dict:
                    entities_dict[btype] = []
                if bvalue not in entities_dict[btype]:
                    entities_dict[btype].append(bvalue)
        
        # No direct log results from IterativeSearchStrategy - it returns metadata
        # We'll just mark that we found entities
        logs = []
        errors = []
        
        logger.info(f"Iterative search completed: found={result.get('found')}, iterations={result.get('iterations')}")
        
        return {
            "logs": logs,
            "entities": entities_dict,
            "errors": errors,
            "path": result.get("path", []),
            "iterations": result.get("iterations", 0),
            "found": result.get("found", False),
            "confidence": result.get("confidence", 0.0)
        }

