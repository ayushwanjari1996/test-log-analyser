# Bug Fix: RpdName Entity Extraction

## Issue
Query: `"find rpdname connected to cm 10:e1:77:08:63:8a"`

**Problem**: Could not find `rpdname` even though it existed in logs with the CM MAC address.

**Log Data**:
```json
{
  "MdId": "0x7a030000",
  "CmMacAddress": "10:e1:77:08:63:8a",
  "RpdName": "MAWED06P01",
  "SfIds": ["0xa7a"]
}
```

## Root Causes

### 1. Missing Entity Patterns
`rpdname` and `sf_id` had no regex patterns defined in `config/entity_mappings.yaml`.

**Symptoms**:
- Warning: "No patterns defined for entity type 'rpdname'"
- Entity extraction returned 0 results
- Iterative search exhausted all iterations

### 2. LLM Query Misclassification
LLM was parsing "find A for B x" as `specific_value` instead of `relationship`.

**Symptoms**:
- Query routed to wrong handler
- Attempted to search for `None` value
- KeyError on result fields

## Solutions

### Solution 1: Added Entity Patterns

**Updated `config/entity_mappings.yaml`**:

```yaml
patterns:
  rpdname:
    - "\"RpdName\"\\s*:\\s*\"([A-Z0-9]+)\""  # JSON format
    - "RpdName[:\\s]*([A-Z0-9]+)"             # Plain format
    - "rpd[_\\s]*name[:\\s]*([A-Z0-9]+)"      # Variations
  
  sf_id:
    - "\"SfIds\"\\s*:\\s*\\[\"(0x[0-9a-fA-F]+)\""
    - "SfId[:\\s]*(0x[0-9a-fA-F]+)"
    - "sf[_\\s]*id[:\\s]*(0x[0-9a-fA-F]+)"
  
  md_id:
    - "\"MdId\"\\s*:\\s*\"(0x[0-9a-fA-F]+)\""  # Added JSON format
    - "MdId[:\\s]*(\\d+)"
    - "modem_id[:\\s]*(\\d+)"
  
  ip_address:
    - "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b"    # IPv4
    - "\\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\\b"  # IPv6
```

**Added Aliases**:
```yaml
aliases:
  rpdname:
    - "rpd_name"
    - "rpd name"
    - "RpdName"
    - "RPD"
  
  sf_id:
    - "service_flow_id"
    - "service flow id"
    - "SfId"
    - "SFID"
```

**Added Relationships**:
```yaml
relationships:
  cm:
    - rpdname
    - sf_id
    # ... existing
  
  rpdname:
    - cm
    - md_id
    - ip_address
    - sf_id
```

**Updated Bridge Ranking** (`src/core/iterative_search.py`):
```python
ENTITY_UNIQUENESS = {
    "mac_address": 10,
    "ip_address": 9,
    "rpdname": 8,      # Added
    "md_id": 7,
    "sf_id": 6,        # Added
    "dc_id": 5,
    "cm": 4,
    "package": 3,      # Added
    "module": 2,
    "severity": 1,
}
```

### Solution 2: Smart Query Type Correction

**Updated `src/core/analyzer.py`**:

Added logic to auto-detect relationship queries when LLM misclassifies:

```python
# Smart correction: If there's a secondary entity with value and primary has no value,
# this is likely a relationship query (find A for B value)
secondary = parsed.get("secondary_entity")
primary = parsed.get("primary_entity")
if (secondary and secondary.get("value") and 
    primary and not primary.get("value") and 
    query_type == "specific_value"):
    logger.info("Correcting query type: specific_value → relationship")
    query_type = "relationship"
```

**Pattern detected**: "find A for B x"
- A (primary): target entity type, no value
- B (secondary): source entity type, HAS value "x"
- → This is a **relationship query**

## Test Results

### Before Fix:
```
WARNING  No patterns defined for entity type 'rpdname'
INFO     Could not find rpdname after 5 iterations
Result: {"found": false, "target_values": [], "iterations": 5}
```

### After Fix:
```
INFO     Correcting query type: specific_value → relationship
INFO     === Iteration 1: Direct search ===
INFO     Extracted 1 unique 'rpdname' entities
INFO     ✓ Found rpdname directly: ['MAWED06P01']
Result: {
  "found": true,
  "target_values": ["MAWED06P01"],
  "iterations": 1,
  "confidence": 1.0,
  "path": ["cm:10:e1:77:08:63:8a", "rpdname:MAWED06P01"]
}
```

## Verification

```bash
# Test entity extraction
python -c "from src.core.log_processor import LogProcessor; p = LogProcessor('test.csv'); logs = p.read_all_logs(); rpds = p.extract_entities(logs, 'rpdname'); print(f'Found {len(rpds)} rpdname entities: {list(rpds.keys())}')"
# Output: Found 3 rpdname entities: ['MAWED06P01', 'MAWED07T01', 'MAWED08501']

# Test relationship search
python -c "from src.core.analyzer import LogAnalyzer; a = LogAnalyzer('test.csv'); r = a.analyze_query('find rpdname for cm 10:e1:77:08:63:8a'); print(f'Found: {r[\"found\"]}, Values: {r[\"target\"][\"values\"]}')"
# Output: Found: True, Values: ['MAWED06P01']
```

## Impact

✅ **Entity coverage expanded**:
- Added `rpdname` extraction
- Added `sf_id` extraction
- Improved `md_id` for JSON format
- Added IPv6 support

✅ **Query routing robustness**:
- Auto-corrects LLM misclassifications
- Handles "find A for B x" pattern
- More reliable relationship detection

✅ **Real-world compatibility**:
- Works with JSON log format
- Handles hex values (0x...)
- Supports multiple naming conventions

## Future Improvements

1. **More entity types**: Add patterns for other entities in your logs
2. **LLM prompt tuning**: Improve query type classification accuracy
3. **Pattern validation**: Add tests for all entity patterns
4. **Dynamic pattern learning**: Extract patterns from sample logs

## Files Changed

- `config/entity_mappings.yaml` - Added patterns, aliases, relationships
- `src/core/iterative_search.py` - Updated bridge ranking scores
- `src/core/analyzer.py` - Added smart query type correction

