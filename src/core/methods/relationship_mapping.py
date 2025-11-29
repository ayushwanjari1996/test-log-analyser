"""
Relationship Mapping Method - Map relationships between entities.
"""

import logging
from typing import Dict
from .base_method import BaseMethod

logger = logging.getLogger(__name__)


class RelationshipMappingMethod(BaseMethod):
    """Map relationships between entities."""
    
    def __init__(self, entity_manager):
        super().__init__("relationship_mapping")
        self.entity_manager = entity_manager
    
    def execute(self, params: Dict, context) -> Dict:
        """
        Map relationships between entities found in logs.
        
        Args:
            params: Not used
            context: AnalysisContext with all_logs
            
        Returns:
            Dict with relationships and entity graph
        """
        if not context.all_logs:
            logger.warning("No logs available for relationship mapping")
            return {"relationships": [], "entities": {}}
        
        logger.info(f"Mapping relationships in {len(context.all_logs)} logs")
        
        try:
            # Build relationships from context (entities that appear together in logs)
            relationships = []
            
            # For each log, find which entities appear together
            for log in context.all_logs[:100]:  # Limit to first 100 for performance
                entities_in_log = []
                
                # Check which known entities appear in this log
                log_str = str(log)
                for etype, values in context.entities.items():
                    for value in values:
                        if value in log_str:
                            entities_in_log.append(f"{etype}:{value}")
                
                # Create relationships between co-occurring entities
                for i, e1 in enumerate(entities_in_log):
                    for e2 in entities_in_log[i+1:]:
                        if (e1, e2) not in relationships and (e2, e1) not in relationships:
                            relationships.append((e1, e2))
            
            # Build entity graph representation
            graph = self._build_relationship_graph(relationships, context.entities)
            
            logger.info(f"Found {len(relationships)} relationships")
            
            return {
                "relationships": relationships,
                "graph": graph,
                "entities": context.entities
            }
        
        except Exception as e:
            logger.error(f"Relationship mapping failed: {e}")
            return {
                "relationships": [],
                "entities": context.entities,
                "error": str(e)
            }
    
    def _build_relationship_graph(self, relationships: list, entities: Dict) -> Dict:
        """
        Build a graph representation of entity relationships.
        
        Returns:
            Dict with nodes and edges for visualization
        """
        graph = {
            "nodes": [],
            "edges": []
        }
        
        # Add nodes (entities)
        node_ids = set()
        for entity_type, values in entities.items():
            for value in values:
                node_id = f"{entity_type}:{value}"
                if node_id not in node_ids:
                    graph["nodes"].append({
                        "id": node_id,
                        "type": entity_type,
                        "value": value
                    })
                    node_ids.add(node_id)
        
        # Add edges (relationships)
        for rel in relationships:
            if isinstance(rel, tuple) and len(rel) >= 2:
                source, target = rel[0], rel[1]
                graph["edges"].append({
                    "source": source,
                    "target": target,
                    "type": "related"
                })
        
        return graph

