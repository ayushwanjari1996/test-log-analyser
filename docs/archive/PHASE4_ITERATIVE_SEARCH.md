# Phase 4: Iterative Search Strategy for Relationship Queries

## Problem: Direct Search May Not Find Answer

### Example Scenario

```
Query: "find mdid for cm x"

Iteration 1 (Direct Search):
- Search logs for VALUE "x"
- Found 3 logs containing "x"
- Check if these logs contain "mdid"
- Result: NO mdid found in these 3 logs ❌

What now? GIVE UP? NO!
→ Extract OTHER entities from these logs
→ Use them as "bridges" to find mdid
```

## Iterative Bridge Strategy

### Concept: Entity Bridging

```
Query: "find mdid for cm x"

Direct path not found:
  cm x → mdid ❌

Use bridges:
  cm x → rpdname → mdid ✓
  cm x → dc_id → mdid ✓
  cm x → sf_id → mdid ✓
```

### Complete Iterative Flow

```
┌─────────────────────────────────────────────┐
│ Query: "find mdid for cm x"                 │
└─────────────┬───────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ ITERATION 1: Direct Search                  │
│ Search for: "x"                             │
│ Found: 3 logs                               │
│ Extract target: mdid                        │
│ Result: NOT FOUND                           │
└─────────────┬───────────────────────────────┘
              ↓
         mdid found? NO
              ↓
┌─────────────────────────────────────────────┐
│ ITERATION 2: Bridge via extracted entities  │
│ From 3 logs, extract ALL entities:          │
│  - rpdname: RPD001                          │
│  - dc_id: DC123                             │
│  - sf_id: SF456                             │
│  - ip_address: 192.168.1.1                  │
└─────────────┬───────────────────────────────┘
              ↓
    Rank entities by uniqueness:
    1. rpdname (most unique/specific)
    2. ip_address
    3. dc_id
    4. sf_id (least unique)
              ↓
┌─────────────────────────────────────────────┐
│ Try Bridge #1: rpdname RPD001               │
│ Search logs for: "RPD001"                   │
│ Found: 25 logs                              │
│ Extract target: mdid                        │
│ Result: FOUND! mdid = 98765 ✓              │
└─────────────┬───────────────────────────────┘
              ↓
         RETURN RESULT
```

## Implementation Strategy

### 1. Entity Ranking System

**Uniqueness Score** - Higher = more likely to be a good bridge

```python
ENTITY_UNIQUENESS = {
    "mac_address": 10,    # Most unique - 1:1 mapping
    "ip_address": 9,      # Very unique
    "rpdname": 8,         # Highly specific
    "md_id": 7,           # Specific ID
    "sf_id": 6,           # Service flow ID
    "dc_id": 5,           # Downstream channel
    "cm": 4,              # Cable modem
    "module": 2,          # Too generic
    "severity": 1,        # Too generic
    "timestamp": 1,       # Not useful for bridging
}

def rank_bridge_entities(entities: Dict[str, List[str]]) -> List[Tuple[str, str, int]]:
    """
    Rank extracted entities by their usefulness as bridges.
    
    Returns: [(entity_type, entity_value, score), ...]
    Sorted by score (descending)
    """
    ranked = []
    
    for entity_type, entity_values in entities.items():
        base_score = ENTITY_UNIQUENESS.get(entity_type, 3)
        
        for value in entity_values:
            # Adjust score based on value specificity
            score = base_score
            
            # Longer values are more unique
            if len(value) > 10:
                score += 2
            elif len(value) > 5:
                score += 1
            
            # IDs with numbers are more specific
            if any(c.isdigit() for c in value):
                score += 1
            
            # Avoid overly generic values
            if value.lower() in ['unknown', 'null', 'none', '']:
                score = 0
            
            if score > 0:
                ranked.append((entity_type, value, score))
    
    # Sort by score (descending)
    return sorted(ranked, key=lambda x: x[2], reverse=True)
```

### 2. Iterative Search Algorithm

```python
class IterativeSearchStrategy:
    """
    Implements iterative entity bridging to find relationships.
    """
    
    def __init__(self, max_iterations=5, max_bridges_per_iteration=3):
        self.max_iterations = max_iterations
        self.max_bridges_per_iteration = max_bridges_per_iteration
        self.explored_entities = set()
    
    def find_with_bridges(
        self,
        logs: pd.DataFrame,
        target_entity_type: str,  # What we want to find (mdid)
        source_entity_value: str,  # What we start with (x)
        source_entity_type: str = None  # Optional (cm)
    ) -> Dict[str, Any]:
        """
        Iteratively search for target entity using bridge entities.
        
        Args:
            logs: All log data
            target_entity_type: Entity type we're looking for (e.g., "mdid")
            source_entity_value: Starting value (e.g., "x")
            source_entity_type: Starting entity type (e.g., "cm")
        
        Returns:
            {
                "found": True/False,
                "target_values": ["98765"],
                "path": ["cm:x", "rpdname:RPD001", "mdid:98765"],
                "iterations": 2,
                "bridge_entities": [...]
            }
        """
        result = {
            "found": False,
            "target_values": [],
            "path": [],
            "iterations": 0,
            "bridge_entities": [],
            "confidence": 0.0
        }
        
        # Track the search path
        current_value = source_entity_value
        current_type = source_entity_type or "unknown"
        result["path"].append(f"{current_type}:{current_value}")
        
        # Mark as explored
        self.explored_entities.add((current_type, current_value))
        
        # Iteration 1: Direct search
        logger.info(f"Iteration 1: Direct search for {target_entity_type} in logs with {current_value}")
        
        direct_result = self._search_direct(
            logs, 
            target_entity_type, 
            current_value
        )
        
        result["iterations"] = 1
        
        if direct_result["found"]:
            result["found"] = True
            result["target_values"] = direct_result["values"]
            result["path"].extend([f"{target_entity_type}:{v}" for v in direct_result["values"]])
            result["confidence"] = 1.0
            logger.info(f"✓ Found {target_entity_type} directly: {direct_result['values']}")
            return result
        
        logger.info(f"✗ {target_entity_type} not found directly, extracting bridge entities...")
        
        # Get logs containing source value
        source_logs = self._filter_logs_by_value(logs, current_value)
        
        if len(source_logs) == 0:
            logger.warning(f"No logs found for {current_value}")
            return result
        
        # Extract all entities from source logs
        all_entities = self._extract_all_entity_types(source_logs)
        
        # Rank entities as potential bridges
        bridge_candidates = rank_bridge_entities(all_entities)
        
        logger.info(f"Found {len(bridge_candidates)} potential bridge entities")
        
        # Iterative search through bridges
        for iteration in range(2, self.max_iterations + 1):
            result["iterations"] = iteration
            
            # Try top N bridge entities
            bridges_to_try = bridge_candidates[:self.max_bridges_per_iteration]
            
            if not bridges_to_try:
                logger.info("No more bridge entities to try")
                break
            
            for bridge_type, bridge_value, score in bridges_to_try:
                # Skip if already explored
                if (bridge_type, bridge_value) in self.explored_entities:
                    continue
                
                self.explored_entities.add((bridge_type, bridge_value))
                
                logger.info(
                    f"Iteration {iteration}: Trying bridge {bridge_type}:{bridge_value} "
                    f"(score={score})"
                )
                
                # Search for target in logs containing bridge
                bridge_result = self._search_via_bridge(
                    logs,
                    target_entity_type,
                    bridge_type,
                    bridge_value
                )
                
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
                    result["confidence"] = 0.8  # Indirect find = lower confidence
                    
                    logger.info(
                        f"✓ Found {target_entity_type} via bridge {bridge_type}:{bridge_value}: "
                        f"{bridge_result['values']}"
                    )
                    return result
                
                # If not found, extract more entities from bridge logs for next iteration
                bridge_logs = self._filter_logs_by_value(logs, bridge_value)
                new_entities = self._extract_all_entity_types(bridge_logs)
                new_bridges = rank_bridge_entities(new_entities)
                
                # Add to candidates for next iteration
                for new_bridge in new_bridges:
                    if new_bridge not in bridge_candidates:
                        bridge_candidates.append(new_bridge)
            
            # Re-sort for next iteration
            bridge_candidates = sorted(bridge_candidates, key=lambda x: x[2], reverse=True)
        
        logger.warning(f"Could not find {target_entity_type} after {result['iterations']} iterations")
        return result
    
    def _search_direct(
        self, 
        logs: pd.DataFrame, 
        target_type: str, 
        source_value: str
    ) -> Dict[str, Any]:
        """
        Direct search: find target in logs containing source value.
        """
        # Filter logs to those containing source value
        filtered = self._filter_logs_by_value(logs, source_value)
        
        if len(filtered) == 0:
            return {"found": False, "values": []}
        
        # Extract target entity from filtered logs
        target_entities = self.processor.extract_entities(filtered, target_type)
        
        if target_entities:
            return {
                "found": True,
                "values": list(target_entities.keys()),
                "log_count": len(filtered)
            }
        
        return {"found": False, "values": []}
    
    def _search_via_bridge(
        self,
        logs: pd.DataFrame,
        target_type: str,
        bridge_type: str,
        bridge_value: str
    ) -> Dict[str, Any]:
        """
        Search for target in logs containing bridge entity.
        """
        # Filter logs to those containing bridge value
        bridge_logs = self._filter_logs_by_value(logs, bridge_value)
        
        if len(bridge_logs) == 0:
            return {"found": False, "values": []}
        
        # Extract target from bridge logs
        target_entities = self.processor.extract_entities(bridge_logs, target_type)
        
        if target_entities:
            return {
                "found": True,
                "values": list(target_entities.keys()),
                "bridge_log_count": len(bridge_logs)
            }
        
        return {"found": False, "values": []}
    
    def _filter_logs_by_value(
        self, 
        logs: pd.DataFrame, 
        value: str
    ) -> pd.DataFrame:
        """Search for value across all text columns."""
        mask = pd.Series([False] * len(logs), index=logs.index)
        
        for col in logs.select_dtypes(include=['object']).columns:
            mask |= logs[col].astype(str).str.contains(
                value, case=False, na=False, regex=False
            )
        
        return logs[mask]
    
    def _extract_all_entity_types(
        self, 
        logs: pd.DataFrame
    ) -> Dict[str, List[str]]:
        """
        Extract all entity types from logs.
        
        Returns: {entity_type: [value1, value2, ...]}
        """
        from ..utils.config import config
        
        all_entities = {}
        
        # Get all entity types from config
        entity_types = list(config.entity_mappings.get("patterns", {}).keys())
        
        for etype in entity_types:
            entities = self.processor.extract_entities(logs, etype)
            if entities:
                all_entities[etype] = list(entities.keys())
        
        return all_entities
```

### 3. Integration with LogAnalyzer

```python
class LogAnalyzer:
    def execute_relationship_search(self, parsed: Dict) -> Dict[str, Any]:
        """
        Execute: "find mdid for cm x"
        
        Uses iterative bridge search if direct search fails.
        """
        target_type = parsed["primary_entity"]["type"]  # mdid
        source_type = parsed["secondary_entity"]["type"]  # cm
        source_value = parsed["secondary_entity"]["value"]  # x
        
        logs = self.processor.read_all_logs()
        
        # Initialize iterative searcher
        searcher = IterativeSearchStrategy(
            max_iterations=5,
            max_bridges_per_iteration=3
        )
        searcher.processor = self.processor  # Give it access to processor
        
        # Execute iterative search
        result = searcher.find_with_bridges(
            logs=logs,
            target_entity_type=target_type,
            source_entity_value=source_value,
            source_entity_type=source_type
        )
        
        # Format result
        if result["found"]:
            return {
                "query": f"find {target_type} for {source_type} {source_value}",
                "source": {"type": source_type, "value": source_value},
                "target": {"type": target_type, "values": result["target_values"]},
                "found": True,
                "search_path": result["path"],
                "iterations": result["iterations"],
                "bridges_used": result["bridge_entities"],
                "confidence": result["confidence"],
                "summary": self._generate_relationship_summary(result)
            }
        else:
            return {
                "query": f"find {target_type} for {source_type} {source_value}",
                "source": {"type": source_type, "value": source_value},
                "target": {"type": target_type, "values": []},
                "found": False,
                "iterations": result["iterations"],
                "tried_bridges": len(result["bridge_entities"]),
                "summary": f"Could not find {target_type} for {source_value} after {result['iterations']} iterations"
            }
    
    def _generate_relationship_summary(self, result: Dict) -> str:
        """Generate human-readable summary of search path."""
        if result["confidence"] == 1.0:
            # Direct find
            return f"Found {result['target_values']} directly"
        else:
            # Indirect find via bridges
            path_str = " → ".join(result["path"])
            bridges = ", ".join([b["value"] for b in result["bridge_entities"]])
            return f"Found {result['target_values']} via bridges: {bridges}. Path: {path_str}"
```

## Example Execution

### Query: "find mdid for cm x"

```python
Input: "find mdid for cm x"

Execution Log:
───────────────────────────────────────────────────────────
Iteration 1: Direct search for mdid in logs with x
  → Searching logs for value "x"
  → Found 3 logs containing "x"
  → Extracting mdid from these 3 logs
  → Result: NOT FOUND ✗

✗ mdid not found directly, extracting bridge entities...

From 3 logs, extracted entities:
  - rpdname: RPD001 (score: 8)
  - ip_address: 192.168.1.1 (score: 9)
  - dc_id: DC123 (score: 5)
  - sf_id: SF456 (score: 6)

Ranked bridges:
  1. ip_address:192.168.1.1 (score: 10 - long + has digits)
  2. rpdname:RPD001 (score: 9 - has digits)
  3. sf_id:SF456 (score: 7)
  4. dc_id:DC123 (score: 6)

───────────────────────────────────────────────────────────
Iteration 2: Trying bridge ip_address:192.168.1.1 (score=10)
  → Searching logs for "192.168.1.1"
  → Found 8 logs
  → Extracting mdid from these 8 logs
  → Result: NOT FOUND ✗

───────────────────────────────────────────────────────────
Iteration 2: Trying bridge rpdname:RPD001 (score=9)
  → Searching logs for "RPD001"
  → Found 25 logs
  → Extracting mdid from these 25 logs
  → Result: FOUND! mdid = 98765 ✓

✓ Found mdid via bridge rpdname:RPD001: 98765

Final Result:
{
  "found": true,
  "target_values": ["98765"],
  "path": ["cm:x", "rpdname:RPD001", "mdid:98765"],
  "iterations": 2,
  "confidence": 0.8,
  "bridge_entities": [
    {"type": "rpdname", "value": "RPD001", "score": 9}
  ],
  "summary": "Found mdid 98765 via bridge RPD001. Path: cm:x → rpdname:RPD001 → mdid:98765"
}
```

## Confidence Scoring

```python
def calculate_confidence(result: Dict) -> float:
    """
    Calculate confidence based on search path.
    
    1.0 - Direct find
    0.9 - One bridge, high-score entity (mac, ip)
    0.8 - One bridge, medium-score entity (rpdname, md_id)
    0.7 - Multiple bridges
    0.6 - Many iterations (>3)
    0.5 - Found but uncertain path
    """
    if len(result["path"]) == 2:
        # Direct: source → target
        return 1.0
    
    elif len(result["path"]) == 3:
        # One bridge: source → bridge → target
        bridge_score = result["bridge_entities"][0]["score"]
        if bridge_score >= 9:
            return 0.9
        else:
            return 0.8
    
    elif len(result["path"]) == 4:
        # Two bridges
        return 0.7
    
    elif result["iterations"] > 3:
        # Many iterations
        return 0.6
    
    else:
        return 0.5
```

## Stop Conditions

```python
def should_stop_iteration(iteration: int, result: Dict, candidates: List) -> bool:
    """
    Determine if we should stop searching.
    
    Stop if:
    - Found target (success)
    - Max iterations reached
    - No more bridge candidates
    - All candidates already explored
    """
    if result["found"]:
        return True
    
    if iteration >= MAX_ITERATIONS:
        logger.info(f"Stopping: reached max iterations ({MAX_ITERATIONS})")
        return True
    
    if not candidates:
        logger.info("Stopping: no more bridge candidates")
        return True
    
    unexplored = [c for c in candidates if (c[0], c[1]) not in explored_entities]
    if not unexplored:
        logger.info("Stopping: all candidates already explored")
        return True
    
    return False
```

## Summary

**Key Innovation:** Iterative entity bridging

```
Query: "find mdid for cm x"

Not found directly?
    ↓
Extract bridge entities from "x" logs
    ↓
Rank by uniqueness (IP > RPD > DC > SF)
    ↓
Try each bridge:
  - Search logs for bridge value
  - Check if target exists there
  - If not, extract MORE entities → repeat
    ↓
Return path + confidence
```

**Benefits:**
✅ Finds relationships even when not directly connected
✅ Intelligently ranks bridge entities
✅ Avoids infinite loops (max iterations, explored tracking)
✅ Provides confidence score
✅ Shows complete search path

**Ready to implement!** 🚀

