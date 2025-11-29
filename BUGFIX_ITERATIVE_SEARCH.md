# Bug Fix: Iterative Search Method Failures

## Issues Found

### Issue 1: Wrong Method Name
**Error:** `'IterativeSearchStrategy' object has no attribute 'search'`

**Root Cause:** Called `strategy.search()` but actual method is `find_with_bridges()`

### Issue 2: Wrong Parameters
**Error:** Method signature mismatch

**Root Cause:** `find_with_bridges()` expects:
```python
find_with_bridges(
    logs: pd.DataFrame,           # All logs
    target_entity_type: str,      # What we're looking for
    source_entity_value: str,     # What we start from
    source_entity_type: str       # Optional
)
```

But we were calling it with completely different parameters.

### Issue 3: Context Initialization Wrong for Relationship Queries
**Error:** `target_type` was set to secondary entity's type instead of primary

**Root Cause:** For "find X for Y", the target TYPE should be X (what we're looking for), not Y (what we start from).

---

## Fixes Applied

### Fix 1: Correct Method Call in `iterative_search.py`

```python
# BEFORE (WRONG)
result = strategy.search(
    target_entity=start_entity,
    max_iterations=max_depth
)

# AFTER (CORRECT)
result = strategy.find_with_bridges(
    logs=all_logs,
    target_entity_type=target_type,      # What we're looking for (e.g., "rpdname")
    source_entity_value=start_entity,    # What we start from (e.g., CPE IP)
    source_entity_type=None              # Auto-detect
)
```

### Fix 2: Proper Parameter Extraction

```python
def execute(self, params: Dict, context) -> Dict:
    start_entity = params.get("start_entity") or params.get("entity_value")
    target_type = params.get("target_type") or context.target_entity_type  # ✓ Get from context
    max_depth = params.get("max_depth", 2)
    
    # Read all logs first
    all_logs = self.processor.read_all_logs()
    
    # Create strategy with correct params
    strategy = IterativeSearchStrategy(
        processor=self.processor,
        max_iterations=max_depth
    )
    
    # Execute with all required parameters
    result = strategy.find_with_bridges(
        logs=all_logs,
        target_entity_type=target_type,
        source_entity_value=start_entity,
        source_entity_type=None
    )
```

### Fix 3: Correct Context Initialization for Relationship Queries

In `workflow_orchestrator.py`:

```python
# BEFORE (WRONG) - For "find rpdname for cpe X"
if secondary and secondary.get("value"):
    target_value = secondary["value"]   # X (correct)
    target_type = secondary.get("type") # "cpe_ip" ❌ WRONG!

# AFTER (CORRECT)
if query_type == "relationship" and secondary and secondary.get("value"):
    # We're searching FOR primary type, STARTING FROM secondary value
    target_value = secondary["value"]    # X (what we start from)
    target_type = primary.get("type")    # "rpdname" ✓ CORRECT! (what we're looking for)
```

### Fix 4: Proper Result Conversion

```python
# Convert IterativeSearchStrategy result to our format
entities_dict = {}

# Add found target entities
if result.get("found") and result.get("target_values"):
    if target_type not in entities_dict:
        entities_dict[target_type] = []
    entities_dict[target_type].extend(result["target_values"])

# Add bridge entities (intermediate entities found during search)
for bridge in result.get("bridge_entities", []):
    btype = bridge.get("type")
    bvalue = bridge.get("value")
    if btype and bvalue:
        if btype not in entities_dict:
            entities_dict[btype] = []
        if bvalue not in entities_dict[btype]:
            entities_dict[btype].append(bvalue)

return {
    "logs": [],  # IterativeSearchStrategy doesn't return logs directly
    "entities": entities_dict,
    "errors": [],
    "path": result.get("path", []),
    "iterations": result.get("iterations", 0),
    "found": result.get("found", False),
    "confidence": result.get("confidence", 0.0)
}
```

---

## Expected Behavior After Fix

**Query:** `"which rpd is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

### Context Initialization:
```
Primary: {type: "rpdname"}
Secondary: {type: "cpe_ip", value: "2001:558:6017:60:4950:96e8:be4f:f63b"}

→ target_type = "rpdname"  ✓ (what we're looking for)
→ target_value = "2001:558:6017:60:4950:96e8:be4f:f63b"  ✓ (what we start from)
```

### Execution Flow:
```
Iteration 1: direct_search("2001:558:6017:60:4950:96e8:be4f:f63b")
  → Found 1 log with cpe_ip, cpe_mac, cm_mac
  → No rpdname found yet
  → Success criteria NOT MET (looking for "rpdname")

Iteration 2: iterative_search
  → Strategy.find_with_bridges(
      logs=all_logs,
      target_entity_type="rpdname",         ← What we want
      source_entity_value="2001:558:...",   ← Where we start
      source_entity_type=None
    )
  → Strategy searches for rpdname through bridges:
     CPE IP → CPE MAC → CM MAC → RpdName
  → Found: rpdname="TestRpd123" ✓
  → Success criteria MET!

Iteration 3: summarization
  → Create final answer
```

### Result:
```
✅ ANALYSIS COMPLETE

📊 Answer:
  CPE 2001:558:6017:60:4950:96e8:be4f:f63b is connected to RPD: TestRpd123

🔗 Search Path:
  cpe_ip:2001:558:... → cpe_mac:2c:ab:a4:47:1a:d2 → cm_mac:2c:ab:a4:47:1a:d0 → rpdname:TestRpd123

Confidence: 95%
```

---

## Files Modified

1. `src/core/methods/iterative_search.py`
   - Fixed method call from `.search()` to `.find_with_bridges()`
   - Added proper parameter passing
   - Added result conversion logic

2. `src/core/workflow_orchestrator.py`
   - Fixed context initialization for relationship queries
   - `target_type` now correctly set to primary entity type

---

**Status:** ✅ All Fixed
**Date:** November 29, 2025
**Impact:** Iterative search now works correctly for relationship queries

