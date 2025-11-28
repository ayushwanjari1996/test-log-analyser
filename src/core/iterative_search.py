"""Iterative search strategy with bridge entities for finding relationships."""

from typing import Dict, Any, List, Tuple, Set, Optional
import pandas as pd
from ..utils.logger import setup_logger
from ..core.log_processor import LogProcessor

logger = setup_logger()

# Entity uniqueness scoring for bridge ranking
ENTITY_UNIQUENESS = {
    "mac_address": 10,    # Most unique - 1:1 mapping
    "ip_address": 9,      # Very unique
    "rpdname": 8,         # Highly specific - RPD name
    "md_id": 7,           # Specific ID - modem ID
    "sf_id": 6,           # Service flow ID
    "dc_id": 5,           # Downstream channel
    "cm": 4,              # Cable modem
    "package": 3,         # Package/service
    "module": 2,          # Too generic
    "severity": 1,        # Too generic
}


def rank_bridge_entities(entities: Dict[str, List[str]]) -> List[Tuple[str, str, int]]:
    """
    Rank extracted entities by their usefulness as bridges.
    
    Args:
        entities: {entity_type: [value1, value2, ...]}
        
    Returns:
        List of (entity_type, entity_value, score) sorted by score
    """
    ranked = []
    
    for entity_type, entity_values in entities.items():
        base_score = ENTITY_UNIQUENESS.get(entity_type, 3)
        
        for value in entity_values:
            score = base_score
            
            # Adjust score based on value characteristics
            if len(value) > 10:
                score += 2
            elif len(value) > 5:
                score += 1
            
            # IDs with numbers are more specific
            if any(c.isdigit() for c in value):
                score += 1
            
            # Avoid overly generic values
            if value.lower() in ['unknown', 'null', 'none', '', 'n/a']:
                score = 0
            
            if score > 0:
                ranked.append((entity_type, value, score))
    
    # Sort by score descending
    return sorted(ranked, key=lambda x: x[2], reverse=True)


class IterativeSearchStrategy:
    """
    Implements iterative entity bridging to find relationships.
    
    Uses bridge entities to navigate from source to target when
    direct connection doesn't exist.
    """
    
    def __init__(
        self,
        processor: LogProcessor,
        max_iterations: int = 5,
        max_bridges_per_iteration: int = 3
    ):
        """
        Initialize iterative search.
        
        Args:
            processor: LogProcessor instance for data access
            max_iterations: Maximum search iterations
            max_bridges_per_iteration: Max bridges to try per iteration
        """
        self.processor = processor
        self.max_iterations = max_iterations
        self.max_bridges_per_iteration = max_bridges_per_iteration
        self.explored_entities: Set[Tuple[str, str]] = set()
        
        logger.info(
            f"Initialized IterativeSearchStrategy "
            f"(max_iterations={max_iterations}, "
            f"max_bridges_per_iteration={max_bridges_per_iteration})"
        )
    
    def find_with_bridges(
        self,
        logs: pd.DataFrame,
        target_entity_type: str,
        source_entity_value: str,
        source_entity_type: str = None
    ) -> Dict[str, Any]:
        """
        Iteratively search for target entity using bridge entities.
        
        Args:
            logs: All log data
            target_entity_type: Entity type we're looking for
            source_entity_value: Starting value to search from
            source_entity_type: Starting entity type (optional)
            
        Returns:
            Result dictionary with found status, values, path, etc.
        """
        result = {
            "found": False,
            "target_values": [],
            "path": [],
            "iterations": 0,
            "bridge_entities": [],
            "confidence": 0.0,
            "logs_searched": 0
        }
        
        current_value = source_entity_value
        current_type = source_entity_type or "unknown"
        result["path"].append(f"{current_type}:{current_value}")
        
        self.explored_entities.add((current_type, current_value))
        
        # Iteration 1: Direct search
        logger.info(f"=== Iteration 1: Direct search ===")
        logger.info(f"Searching for {target_entity_type} in logs with '{current_value}'")
        
        direct_result = self._search_direct(logs, target_entity_type, current_value)
        result["iterations"] = 1
        result["logs_searched"] += direct_result.get("log_count", 0)
        
        if direct_result["found"]:
            result["found"] = True
            result["target_values"] = direct_result["values"]
            result["path"].extend([f"{target_entity_type}:{v}" for v in direct_result["values"]])
            result["confidence"] = 1.0
            logger.info(f"✓ Found {target_entity_type} directly: {direct_result['values']}")
            return result
        
        logger.info(f"✗ {target_entity_type} not found directly")
        
        # Get logs containing source value
        source_logs = self._filter_logs_by_value(logs, current_value)
        
        if len(source_logs) == 0:
            logger.warning(f"No logs found for '{current_value}'")
            return result
        
        logger.info(f"Found {len(source_logs)} logs containing '{current_value}'")
        
        # Extract all entities from source logs
        logger.info("Extracting bridge entities...")
        all_entities = self._extract_all_entity_types(source_logs)
        
        # Rank entities as potential bridges
        bridge_candidates = rank_bridge_entities(all_entities)
        
        logger.info(f"Found {len(bridge_candidates)} potential bridge entities")
        logger.debug(f"Top 5 bridges: {bridge_candidates[:5]}")
        
        # Iterative search through bridges
        for iteration in range(2, self.max_iterations + 1):
            result["iterations"] = iteration
            logger.info(f"\n=== Iteration {iteration}: Bridge search ===")
            
            # Try top N bridge entities
            bridges_to_try = bridge_candidates[:self.max_bridges_per_iteration]
            
            if not bridges_to_try:
                logger.info("No more bridge entities to try")
                break
            
            for bridge_type, bridge_value, score in bridges_to_try:
                # Skip if already explored
                if (bridge_type, bridge_value) in self.explored_entities:
                    logger.debug(f"Skipping already explored: {bridge_type}:{bridge_value}")
                    continue
                
                self.explored_entities.add((bridge_type, bridge_value))
                
                logger.info(
                    f"Trying bridge: {bridge_type}:{bridge_value} (score={score})"
                )
                
                # Search for target in logs containing bridge
                bridge_result = self._search_via_bridge(
                    logs,
                    target_entity_type,
                    bridge_type,
                    bridge_value
                )
                
                result["logs_searched"] += bridge_result.get("bridge_log_count", 0)
                
                if bridge_result["found"]:
                    result["found"] = True
                    result["target_values"] = bridge_result["values"]
                    result["path"].append(f"{bridge_type}:{bridge_value}")
                    result["path"].extend([f"{target_entity_type}:{v}" for v in bridge_result["values"]])
                    result["bridge_entities"].append({
                        "type": bridge_type,
                        "value": bridge_value,
                        "score": score
                    })
                    result["confidence"] = self._calculate_confidence(result)
                    
                    logger.info(
                        f"✓ SUCCESS! Found {target_entity_type} via bridge "
                        f"{bridge_type}:{bridge_value}: {bridge_result['values']}"
                    )
                    return result
                
                # If not found, extract more entities from bridge logs for next iteration
                bridge_logs = self._filter_logs_by_value(logs, bridge_value)
                if len(bridge_logs) > 0:
                    new_entities = self._extract_all_entity_types(bridge_logs)
                    new_bridges = rank_bridge_entities(new_entities)
                    
                    # Add to candidates for next iteration
                    for new_bridge in new_bridges:
                        if new_bridge not in bridge_candidates:
                            bridge_candidates.append(new_bridge)
            
            # Re-sort for next iteration
            bridge_candidates = sorted(bridge_candidates, key=lambda x: x[2], reverse=True)
        
        logger.warning(
            f"Could not find {target_entity_type} after {result['iterations']} iterations"
        )
        return result
    
    def _search_direct(
        self,
        logs: pd.DataFrame,
        target_type: str,
        source_value: str
    ) -> Dict[str, Any]:
        """Direct search: find target in logs containing source value."""
        filtered = self._filter_logs_by_value(logs, source_value)
        
        if len(filtered) == 0:
            return {"found": False, "values": [], "log_count": 0}
        
        # Extract target entity from filtered logs
        target_entities = self.processor.extract_entities(filtered, target_type)
        
        if target_entities:
            return {
                "found": True,
                "values": list(target_entities.keys()),
                "log_count": len(filtered)
            }
        
        return {"found": False, "values": [], "log_count": len(filtered)}
    
    def _search_via_bridge(
        self,
        logs: pd.DataFrame,
        target_type: str,
        bridge_type: str,
        bridge_value: str
    ) -> Dict[str, Any]:
        """Search for target in logs containing bridge entity."""
        bridge_logs = self._filter_logs_by_value(logs, bridge_value)
        
        if len(bridge_logs) == 0:
            return {"found": False, "values": [], "bridge_log_count": 0}
        
        # Extract target from bridge logs
        target_entities = self.processor.extract_entities(bridge_logs, target_type)
        
        if target_entities:
            return {
                "found": True,
                "values": list(target_entities.keys()),
                "bridge_log_count": len(bridge_logs)
            }
        
        return {"found": False, "values": [], "bridge_log_count": len(bridge_logs)}
    
    def _filter_logs_by_value(self, logs: pd.DataFrame, value: str) -> pd.DataFrame:
        """Search for value across all text columns."""
        if len(logs) == 0:
            return logs
        
        mask = pd.Series([False] * len(logs), index=logs.index)
        
        for col in logs.select_dtypes(include=['object']).columns:
            mask |= logs[col].astype(str).str.contains(
                value, case=False, na=False, regex=False
            )
        
        return logs[mask]
    
    def _extract_all_entity_types(self, logs: pd.DataFrame) -> Dict[str, List[str]]:
        """Extract all entity types from logs."""
        from ..utils.config import config
        
        all_entities = {}
        entity_types = list(config.entity_mappings.get("patterns", {}).keys())
        
        for etype in entity_types:
            entities = self.processor.extract_entities(logs, etype)
            if entities:
                all_entities[etype] = list(entities.keys())
        
        return all_entities
    
    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate confidence based on search path."""
        path_length = len(result["path"])
        
        if path_length == 2:
            # Direct: source → target
            return 1.0
        elif path_length == 3:
            # One bridge
            if result["bridge_entities"]:
                bridge_score = result["bridge_entities"][0]["score"]
                if bridge_score >= 9:
                    return 0.9
                else:
                    return 0.8
            return 0.8
        elif path_length == 4:
            # Two bridges
            return 0.7
        elif result["iterations"] > 3:
            # Many iterations
            return 0.6
        else:
            return 0.5
