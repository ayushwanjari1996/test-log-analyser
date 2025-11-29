"""Iterative search strategy with bridge entities for finding relationships."""

from typing import Dict, Any, List, Tuple, Set, Optional
import pandas as pd
from ..utils.logger import setup_logger
from ..core.log_processor import LogProcessor

logger = setup_logger()

# LLM client will be injected if available
_llm_client = None

def set_llm_client(llm_client):
    """Set LLM client for smart bridge scoring."""
    global _llm_client
    _llm_client = llm_client

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


def rank_bridge_entities(
    entities: Dict[str, List[str]], 
    target_type: str = None,
    query: str = None
) -> List[Tuple[str, str, int]]:
    """
    Rank extracted entities by their usefulness as bridges.
    Uses rule-based scoring + optional LLM-based relevance scoring.
    
    Args:
        entities: {entity_type: [value1, value2, ...]}
        target_type: Target entity type we're looking for (for LLM scoring)
        query: Original query (for LLM scoring)
        
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
    
    # Sort by rule-based score
    ranked = sorted(ranked, key=lambda x: x[2], reverse=True)
    
    # SMART OPTIMIZATION: Use LLM to boost relevance if available
    if _llm_client and target_type and ranked and len(ranked) > 3:
        try:
            ranked = _apply_llm_relevance_boost(ranked, target_type, query)
        except Exception as e:
            logger.warning(f"LLM bridge scoring failed, using rule-based only: {e}")
    
    return ranked


def _apply_llm_relevance_boost(
    bridges: List[Tuple[str, str, int]], 
    target_type: str,
    query: str
) -> List[Tuple[str, str, int]]:
    """
    Use LLM to boost scores of bridges most likely to lead to target.
    
    Args:
        bridges: List of (type, value, score) tuples
        target_type: What we're trying to find
        query: Original user query
        
    Returns:
        Re-ranked bridges with LLM relevance boost applied
    """
    # Only analyze top 10 bridges (cost control)
    top_bridges = bridges[:10]
    
    # Format for LLM
    bridge_list = "\n".join([
        f"{i+1}. {t}:{v} (score={s})" 
        for i, (t, v, s) in enumerate(top_bridges)
    ])
    
    prompt = f"""You are helping rank entity bridges for iterative search.

GOAL: Find entity type "{target_type}"
QUERY: "{query or 'N/A'}"

AVAILABLE BRIDGES:
{bridge_list}

Your task: Identify which bridges are MOST LIKELY to lead to "{target_type}".

Consider:
- Domain knowledge (e.g., cm_mac often connects to md_id, cpe_mac connects to cm_mac)
- Entity relationships (which entities typically appear together in logs?)
- Query context (what's the user actually looking for?)

Return JSON with bridge numbers ranked by relevance (1 = most relevant):
{{
  "most_relevant": [3, 1, 5],
  "reasoning": "cm_mac is most likely to have md_id in same logs because..."
}}
"""
    
    try:
        response = _llm_client.generate_json(prompt, timeout=5)
        most_relevant = response.get("most_relevant", [])
        
        if most_relevant:
            logger.info(f"🧠 LLM bridge prioritization: {most_relevant[:3]} (top 3)")
            
            # Apply relevance boost
            boosted = []
            for idx in most_relevant:
                if 0 < idx <= len(top_bridges):
                    bridge_type, bridge_value, score = top_bridges[idx - 1]
                    # Boost score significantly for LLM-suggested bridges
                    boosted_score = score + 10
                    boosted.append((bridge_type, bridge_value, boosted_score))
            
            # Add remaining bridges (not mentioned by LLM)
            mentioned_indices = set(most_relevant)
            for i, bridge in enumerate(top_bridges):
                if (i + 1) not in mentioned_indices:
                    boosted.append(bridge)
            
            # Add rest of original bridges
            boosted.extend(bridges[10:])
            
            # Re-sort by new scores
            return sorted(boosted, key=lambda x: x[2], reverse=True)
    
    except Exception as e:
        logger.debug(f"LLM relevance boost failed: {e}")
    
    # Fallback to original ranking
    return bridges


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
        max_bridges_per_iteration: int = 3,
        max_total_searches: int = 20,
        timeout_seconds: int = 30
    ):
        """
        Initialize iterative search.
        
        Args:
            processor: LogProcessor instance for data access
            max_iterations: Maximum search depth/iterations
            max_bridges_per_iteration: Max bridges to try per iteration
            max_total_searches: Maximum total entity searches (cost control)
            timeout_seconds: Maximum time allowed for search
        """
        self.processor = processor
        self.max_iterations = max_iterations
        self.max_bridges_per_iteration = max_bridges_per_iteration
        self.max_total_searches = max_total_searches
        self.timeout_seconds = timeout_seconds
        self.explored_entities: Set[Tuple[str, str]] = set()
        self.total_searches = 0
        
        logger.info(
            f"Initialized IterativeSearchStrategy "
            f"(max_iterations={max_iterations}, "
            f"max_bridges_per_iteration={max_bridges_per_iteration}, "
            f"max_total_searches={max_total_searches}, "
            f"timeout={timeout_seconds}s)"
        )
    
    def find_with_bridges(
        self,
        logs: pd.DataFrame,
        target_entity_type: str,
        source_entity_value: str,
        source_entity_type: str = None
    ) -> Dict[str, Any]:
        """
        Recursively search for target entity using bridge entities (N-level deep).
        
        Args:
            logs: All log data
            target_entity_type: Entity type we're looking for
            source_entity_value: Starting value to search from
            source_entity_type: Starting entity type (optional)
            
        Returns:
            Result dictionary with found status, values, path, etc.
        """
        import time
        start_time = time.time()
        
        result = {
            "found": False,
            "target_values": [],
            "path": [],
            "iterations": 0,
            "bridge_entities": [],
            "confidence": 0.0,
            "logs_searched": 0,
            "total_searches": 0
        }
        
        current_value = source_entity_value
        current_type = source_entity_type or "unknown"
        result["path"].append(f"{current_type}:{current_value}")
        
        # Reset per-search state
        self.explored_entities = set()
        self.total_searches = 0
        self.explored_entities.add((current_type, current_value))
        
        # Iteration 1: Direct search
        logger.info(f"=== Iteration 1: Direct search ===")
        logger.info(f"Searching for {target_entity_type} in logs with '{current_value}'")
        
        direct_result = self._search_direct(logs, target_entity_type, current_value)
        result["iterations"] = 1
        result["logs_searched"] += direct_result.get("log_count", 0)
        self.total_searches += 1
        result["total_searches"] = self.total_searches
        
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
        logger.info("Extracting bridge entities from source logs...")
        all_entities = self._extract_all_entity_types(source_logs)
        
        # Rank entities as potential bridges (with LLM smart scoring if available)
        bridge_candidates = rank_bridge_entities(
            all_entities, 
            target_type=target_entity_type,
            query=f"find {target_entity_type} for {current_type} {current_value}"
        )
        
        logger.info(f"Found {len(bridge_candidates)} initial bridge entities")
        
        # Remove source entity from candidates to avoid loops
        bridge_candidates = [
            (t, v, s) for t, v, s in bridge_candidates 
            if (t, v) not in self.explored_entities
        ]
        
        # Recursive multi-level search through bridge entities
        for iteration in range(2, self.max_iterations + 1):
            result["iterations"] = iteration
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > self.timeout_seconds:
                logger.warning(f"⏱️ Timeout reached ({self.timeout_seconds}s)")
                break
            
            # Check search limit
            if self.total_searches >= self.max_total_searches:
                logger.warning(f"🛑 Max searches reached ({self.max_total_searches})")
                break
            
            logger.info(f"\n=== Iteration {iteration}: Bridge search (depth {iteration-1}) ===")
            logger.info(f"Available bridges: {len(bridge_candidates)}, Explored: {len(self.explored_entities)}")
            
            # Try top N bridge entities from current level
            bridges_to_try = bridge_candidates[:self.max_bridges_per_iteration]
            
            if not bridges_to_try:
                logger.info("No more bridge entities to try")
                break
            
            # Track newly discovered entities from this iteration
            new_bridges_this_iteration = []
            
            for bridge_type, bridge_value, score in bridges_to_try:
                # Skip if already explored
                if (bridge_type, bridge_value) in self.explored_entities:
                    continue
                
                self.explored_entities.add((bridge_type, bridge_value))
                
                # Check limits before each search
                if self.total_searches >= self.max_total_searches:
                    logger.warning(f"🛑 Max searches reached ({self.max_total_searches})")
                    break
                
                logger.info(
                    f"Trying bridge: {bridge_type}:{bridge_value} (score={score}, depth={iteration-1})"
                )
                
                # Search for target in logs containing bridge
                bridge_result = self._search_via_bridge(
                    logs,
                    target_entity_type,
                    bridge_type,
                    bridge_value
                )
                
                self.total_searches += 1
                result["total_searches"] = self.total_searches
                result["logs_searched"] += bridge_result.get("bridge_log_count", 0)
                
                if bridge_result["found"]:
                    result["found"] = True
                    result["target_values"] = bridge_result["values"]
                    result["path"].append(f"{bridge_type}:{bridge_value}")
                    result["path"].extend([f"{target_entity_type}:{v}" for v in bridge_result["values"]])
                    result["bridge_entities"].append({
                        "type": bridge_type,
                        "value": bridge_value,
                        "score": score,
                        "depth": iteration - 1
                    })
                    result["confidence"] = self._calculate_confidence(result)
                    
                    logger.info(
                        f"✓ SUCCESS! Found {target_entity_type} via bridge "
                        f"{bridge_type}:{bridge_value} at depth {iteration-1}: {bridge_result['values']}"
                    )
                    return result
                
                # KEY IMPROVEMENT: Extract NEW entities from this bridge's logs for NEXT iteration
                bridge_logs = self._filter_logs_by_value(logs, bridge_value)
                if len(bridge_logs) > 0:
                    logger.debug(f"Extracting entities from {len(bridge_logs)} logs for bridge {bridge_value}")
                    new_entities = self._extract_all_entity_types(bridge_logs)
                    new_ranked = rank_bridge_entities(
                        new_entities,
                        target_type=target_entity_type,
                        query=f"find {target_entity_type} via {bridge_type}"
                    )
                    
                    # Filter out already explored entities
                    new_ranked = [
                        (t, v, s) for t, v, s in new_ranked 
                        if (t, v) not in self.explored_entities
                    ]
                    
                    if new_ranked:
                        logger.info(f"Discovered {len(new_ranked)} new potential bridges from {bridge_value}")
                        new_bridges_this_iteration.extend(new_ranked)
            
            # RECURSIVE DEPTH: Add newly discovered bridges for next iteration
            if new_bridges_this_iteration:
                # Remove used bridges from current list
                bridge_candidates = [
                    bc for bc in bridge_candidates 
                    if bc not in bridges_to_try
                ]
                
                # Add new bridges discovered in this iteration
                bridge_candidates.extend(new_bridges_this_iteration)
                
                # Re-sort by score for next iteration (prioritize high-score bridges)
                bridge_candidates = sorted(bridge_candidates, key=lambda x: x[2], reverse=True)
                
                logger.info(f"Updated bridge pool: {len(bridge_candidates)} candidates for next iteration")
            else:
                # No new entities discovered, remove tried bridges
                bridge_candidates = [
                    bc for bc in bridge_candidates 
                    if bc not in bridges_to_try
                ]
                
                if not bridge_candidates:
                    logger.info("No more unexplored bridges available")
                    break
        
        logger.warning(
            f"Could not find {target_entity_type} after {result['iterations']} iterations "
            f"({self.total_searches} total searches, {len(self.explored_entities)} entities explored)"
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
        
        # Extract target entity from filtered logs (ONLY from _source.log column)
        search_columns = ["_source.log"] if "_source.log" in filtered.columns else None
        target_entities = self.processor.extract_entities(filtered, target_type, search_columns=search_columns)
        
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
        
        # Extract target from bridge logs (ONLY from _source.log column)
        search_columns = ["_source.log"] if "_source.log" in bridge_logs.columns else None
        target_entities = self.processor.extract_entities(bridge_logs, target_type, search_columns=search_columns)
        
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
        """
        Extract all entity types from logs.
        ONLY extracts from _source.log column to avoid infrastructure IPs/names.
        """
        from ..utils.config import config
        
        all_entities = {}
        entity_types = list(config.entity_mappings.get("patterns", {}).keys())
        
        # ONLY search in _source.log column (ignore CSV metadata like pod_ip, node_name)
        search_columns = ["_source.log"] if "_source.log" in logs.columns else None
        
        for etype in entity_types:
            entities = self.processor.extract_entities(logs, etype, search_columns=search_columns)
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
