"""
Direct Search Method - Search for specific entity directly in logs.
"""

import logging
from typing import Dict
from .base_method import BaseMethod

logger = logging.getLogger(__name__)


class DirectSearchMethod(BaseMethod):
    """Search for specific entity directly in logs."""
    
    def __init__(self, processor, entity_manager):
        super().__init__("direct_search")
        self.processor = processor
        self.entity_manager = entity_manager
    
    def execute(self, params: Dict, context) -> Dict:
        """
        Execute direct search for an entity.
        
        Args:
            params: Must contain 'entity_value', optionally 'entity_type'
            context: AnalysisContext
            
        Returns:
            Dict with logs, entities, errors found
        """
        entity_value = params.get("entity_value")
        entity_type = params.get("entity_type")
        
        if not entity_value:
            logger.error("No entity_value provided for direct_search")
            return {"logs": [], "entities": {}, "errors": []}
        
        logger.info(f"Searching for: {entity_type or 'entity'} = {entity_value}")
        
        # Read all logs first
        all_logs = self.processor.read_all_logs()
        
        # Search in logs
        logs_df = self.processor.search_text(all_logs, entity_value)
        
        # Convert to list of dicts
        logs = logs_df.to_dict('records') if not logs_df.empty else []
        
        logger.info(f"Found {len(logs)} logs for {entity_value}")
        
        # Extract entities from found logs
        entities_dict = {}
        if logs and len(logs) > 0:
            # Convert back to DataFrame for entity extraction
            import pandas as pd
            logs_for_extraction = pd.DataFrame(logs) if logs else pd.DataFrame()
            
            # Extract entities - ONLY from _source.log column (ignore CSV metadata)
            # This prevents extracting infrastructure IPs/names from pod_ip, node_name, etc.
            search_columns = ["_source.log"] if "_source.log" in logs_for_extraction.columns else None
            
            entity_objects = self.entity_manager.extract_all_entities_from_logs(
                logs_for_extraction,
                search_columns=search_columns
            )
            
            # Convert Entity objects to dict of type -> list of values
            for (etype, evalue), entity_obj in entity_objects.items():
                if etype not in entities_dict:
                    entities_dict[etype] = []
                if evalue not in entities_dict[etype]:
                    entities_dict[etype].append(evalue)
            
            logger.info(f"Extracted entities: {', '.join(f'{k}:{len(v)}' for k, v in entities_dict.items())}")
        
        # Detect errors
        errors = [log for log in logs if log.get("severity") in ["ERROR", "CRITICAL", "WARNING"]]
        if errors:
            logger.info(f"Found {len(errors)} error/warning logs")
        
        return {
            "logs": logs,
            "entities": entities_dict,
            "errors": errors,
            "search_term": entity_value
        }

