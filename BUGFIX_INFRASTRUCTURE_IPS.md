# Bug Fix: Infrastructure IPs in Entity Extraction

## Problem

**Query:** `"which rpd is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

**Console Output:**
```
INFO: Extracted 2 unique 'ip_address' entities
INFO: Trying bridge: ip_address:172.17.13.5 (score=12)
INFO: ✓ SUCCESS! Found rpdname via bridge ip_address:172.17.13.5
```

**Issue:** The system was using infrastructure IP `172.17.13.5` (pod_ip from CSV metadata) as a bridge entity, leading to incorrect results.

---

## Root Cause

Entity extraction was searching **ALL columns** including CSV metadata:
- `_source.log` - ✅ JSON log content (actual entities)
- `_source.pod_ip` - ❌ Infrastructure IP (172.17.13.5)
- `_source.node_name` - ❌ Infrastructure name
- `_source.cluster_name` - ❌ Infrastructure name
- etc.

**Three places needed fixing:**

### 1. `DirectSearchMethod` - ✅ Already Fixed
```python
search_columns = ["_source.log"]
entity_objects = self.entity_manager.extract_all_entities_from_logs(
    logs_for_extraction,
    search_columns=search_columns  # ← Fixed
)
```

### 2. `IterativeSearchStrategy._extract_all_entity_types()` - ❌ NOT Fixed
```python
# OLD (WRONG)
for etype in entity_types:
    entities = self.processor.extract_entities(logs, etype)  # ← No search_columns!
```

### 3. `IterativeSearchStrategy._search_direct()` - ❌ NOT Fixed
```python
# OLD (WRONG)
target_entities = self.processor.extract_entities(filtered, target_type)  # ← No search_columns!
```

### 4. `IterativeSearchStrategy._search_via_bridge()` - ❌ NOT Fixed
```python
# OLD (WRONG)
target_entities = self.processor.extract_entities(bridge_logs, target_type)  # ← No search_columns!
```

---

## Fixes Applied

### Fix 1: `_extract_all_entity_types()`

```python
def _extract_all_entity_types(self, logs: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Extract all entity types from logs.
    ONLY extracts from _source.log column to avoid infrastructure IPs/names.
    """
    from ..utils.config import config
    
    all_entities = {}
    entity_types = list(config.entity_mappings.get("patterns", {}).keys())
    
    # ONLY search in _source.log column (ignore CSV metadata)
    search_columns = ["_source.log"] if "_source.log" in logs.columns else None
    
    for etype in entity_types:
        entities = self.processor.extract_entities(
            logs, 
            etype, 
            search_columns=search_columns  # ← FIXED
        )
        if entities:
            all_entities[etype] = list(entities.keys())
    
    return all_entities
```

### Fix 2: `_search_direct()`

```python
def _search_direct(self, logs, target_type, source_value):
    filtered = self._filter_logs_by_value(logs, source_value)
    
    if len(filtered) == 0:
        return {"found": False, "values": [], "log_count": 0}
    
    # Extract target entity from filtered logs (ONLY from _source.log column)
    search_columns = ["_source.log"] if "_source.log" in filtered.columns else None
    target_entities = self.processor.extract_entities(
        filtered, 
        target_type, 
        search_columns=search_columns  # ← FIXED
    )
    
    if target_entities:
        return {
            "found": True,
            "values": list(target_entities.keys()),
            "log_count": len(filtered)
        }
    
    return {"found": False, "values": [], "log_count": len(filtered)}
```

### Fix 3: `_search_via_bridge()`

```python
def _search_via_bridge(self, logs, target_type, bridge_type, bridge_value):
    bridge_logs = self._filter_logs_by_value(logs, bridge_value)
    
    if len(bridge_logs) == 0:
        return {"found": False, "values": [], "bridge_log_count": 0}
    
    # Extract target from bridge logs (ONLY from _source.log column)
    search_columns = ["_source.log"] if "_source.log" in bridge_logs.columns else None
    target_entities = self.processor.extract_entities(
        bridge_logs, 
        target_type, 
        search_columns=search_columns  # ← FIXED
    )
    
    if target_entities:
        return {
            "found": True,
            "values": list(target_entities.keys()),
            "bridge_log_count": len(bridge_logs)
        }
    
    return {"found": False, "values": [], "bridge_log_count": len(bridge_logs)}
```

---

## Expected Behavior After Fix

**Query:** `"which rpd is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

### Before (WRONG):
```
INFO: Search columns: ['_source.log', '_source.pod_ip', '_source.node_name', ...]
INFO: Extracted 2 unique 'ip_address' entities
  - 2001:558:6017:60:4950:96e8:be4f:f63b  ✓ (from JSON)
  - 172.17.13.5                          ✗ (from CSV pod_ip)

INFO: Trying bridge: ip_address:172.17.13.5
INFO: Found rpdname via bridge: ['TestRpd123', 'MAWED07T01']  ✗ WRONG
```

### After (CORRECT):
```
INFO: Search columns: ['_source.log']
INFO: Extracted 1 unique 'ip_address' entities
  - 2001:558:6017:60:4950:96e8:be4f:f63b  ✓ (from JSON only)

INFO: Bridge entities:
  - cpe_mac: 2c:ab:a4:47:1a:d2
  - cm_mac: 2c:ab:a4:47:1a:d0
  (NO infrastructure IPs!)

INFO: Trying bridge: cm_mac:2c:ab:a4:47:1a:d0
INFO: Found rpdname: TestRpd123  ✓ CORRECT
```

---

## Files Modified

1. `src/core/methods/direct_search.py`
   - Added `search_columns=["_source.log"]` to entity extraction

2. `src/core/iterative_search.py`
   - Updated `_extract_all_entity_types()` 
   - Updated `_search_direct()`
   - Updated `_search_via_bridge()`
   - All now use `search_columns=["_source.log"]`

---

## Impact

✅ **Entities extracted ONLY from JSON log content**  
✅ **Infrastructure IPs/names ignored**  
✅ **More accurate bridge entity selection**  
✅ **Correct results for relationship queries**  
✅ **Future-ready for infrastructure entity support** (see TODO.md)

---

**Status:** ✅ Fixed  
**Date:** November 29, 2025  
**Impact:** All entity extraction now limited to `_source.log` column

