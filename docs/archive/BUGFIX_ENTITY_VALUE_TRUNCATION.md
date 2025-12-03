# Bug Fix: Entity Value Truncation in LLM Decision Prompts

## Problem

**Console Output:**
```
INFO: Extracted 5 unique entities
INFO: Searching for rpdname in logs with 'cpe_mac:1'
WARNING: No logs found for 'cpe_mac:1'
```

**Issue:** LLM was using truncated entity value `'cpe_mac:1'` instead of full value `'cpe_mac:2c:ab:a4:47:1a:d2'`

**Result:** Search failed because it was looking for literal string `"cpe_mac:1"` which doesn't exist.

---

## Root Cause

### Issue 1: Entity Summary Only Showed Counts

In `AnalysisContext.summary()`:
```python
# OLD (WRONG)
f"Entities found: {entity_count} ({', '.join(f'{k}:{len(v)}' for k, v in self.entities.items())})"

# Showed: "Entities found: 5 (cpe_mac:1, cm_mac:1, cpe_ip:1, ...)"
#                                         ↑ only the COUNT, not the VALUE!
```

**Problem:** LLM saw `cpe_mac:1` (count of 1) and thought it was the entity value!

### Issue 2: No Entity Values in Decision Prompt

The decision prompt in `_build_decision_prompt()` used `context.summary()` which didn't show actual entity values.

**LLM saw:**
```
Entities found: 5 (cpe_mac:1, cm_mac:1, cpe_ip:1, mac_address:1, ip_address:1)
```

**LLM interpreted:**
- `cpe_mac` has value `"1"` ❌ WRONG
- Should see: `cpe_mac` has value `"2c:ab:a4:47:1a:d2"` ✓

### Issue 3: No Validation for Truncated Values

When LLM returned:
```json
{
  "params": {
    "start_entity": "1"  // ← Clearly wrong, but not caught
  }
}
```

No validation caught this obviously truncated value.

---

## Fixes Applied

### Fix 1: Added `get_entities_detailed()` Method

In `src/core/analysis_context.py`:

```python
def get_entities_detailed(self) -> str:
    """
    Get detailed entity list with actual values (for LLM decision making).
    Shows first few values of each entity type.
    """
    if not self.entities:
        return "No entities discovered yet"
    
    detailed = []
    for entity_type, values in self.entities.items():
        # Show first 3 values, with count if more
        if len(values) <= 3:
            value_str = ", ".join(values)
        else:
            value_str = ", ".join(values[:3]) + f" (and {len(values)-3} more)"
        
        detailed.append(f"  - {entity_type}: {value_str}")
    
    return "\n".join(detailed)
```

**Output:**
```
  - cpe_mac: 2c:ab:a4:47:1a:d2
  - cm_mac: 2c:ab:a4:47:1a:d0
  - cpe_ip: 2001:558:6017:60:4950:96e8:be4f:f63b
  - mac_address: 2c:ab:a4:47:1a:d2
  - ip_address: 2001:558:6017:60:4950:96e8:be4f:f63b
```

### Fix 2: Updated Decision Prompt

In `src/core/decision_agent.py`:

```python
# Added to prompt
ENTITIES DISCOVERED (with values):
{context.get_entities_detailed()}
```

**Now LLM sees:**
```
ENTITIES DISCOVERED (with values):
  - cpe_mac: 2c:ab:a4:47:1a:d2
  - cm_mac: 2c:ab:a4:47:1a:d0
  - cpe_ip: 2001:558:6017:60:4950:96e8:be4f:f63b
```

### Fix 3: Enhanced Prompt Instructions

Added clear instructions:
```
IMPORTANT:
- Do NOT hardcode entity values - use ACTUAL values from "ENTITIES DISCOVERED" above
- When using entity values in params, use the FULL VALUE (e.g., "2c:ab:a4:47:1a:d2", NOT "1" or truncated)
- For iterative_search, use the ACTUAL entity value from context (e.g., CPE IP address)
```

### Fix 4: Added Validation for Truncated Values

In `_validate_decision()`:

```python
# Check entity_value is not truncated
entity_value = decision.params.get("entity_value") or decision.params.get("start_entity")
if entity_value and len(entity_value) <= 2:
    # Suspiciously short - likely truncated
    logger.warning(f"Entity value suspiciously short: '{entity_value}' - likely truncated")
    
    # Try to fix using context.target_entity
    if context.target_entity and len(context.target_entity) > 2:
        logger.info(f"Using context target_entity instead: {context.target_entity}")
        if "entity_value" in decision.params:
            decision.params["entity_value"] = context.target_entity
        if "start_entity" in decision.params:
            decision.params["start_entity"] = context.target_entity
    else:
        return False  # Can't fix, reject decision
```

**Benefits:**
- ✅ Catches obviously truncated values (1-2 chars)
- ✅ Auto-corrects using `context.target_entity`
- ✅ Rejects decision if can't fix
- ✅ Logs warning for debugging

---

## Expected Behavior After Fix

### Before (WRONG):

**LLM Prompt:**
```
CURRENT STATE:
Entities found: 5 (cpe_mac:1, cm_mac:1, cpe_ip:1, ...)
```

**LLM Decision:**
```json
{
  "method": "iterative_search",
  "params": {
    "start_entity": "1"  // ← Used the count!
  }
}
```

**Result:** ❌ Search for `"1"` fails

### After (CORRECT):

**LLM Prompt:**
```
CURRENT STATE:
Entities found: 5 (cpe_mac:1, cm_mac:1, ...)

ENTITIES DISCOVERED (with values):
  - cpe_mac: 2c:ab:a4:47:1a:d2
  - cm_mac: 2c:ab:a4:47:1a:d0
  - cpe_ip: 2001:558:6017:60:4950:96e8:be4f:f63b
```

**LLM Decision:**
```json
{
  "method": "iterative_search",
  "params": {
    "start_entity": "2001:558:6017:60:4950:96e8:be4f:f63b"  // ← Full value!
  }
}
```

**Result:** ✅ Search succeeds

**If LLM still truncates:**
```
WARNING: Entity value suspiciously short: '1' - likely truncated
INFO: Using context target_entity instead: 2001:558:6017:60:4950:96e8:be4f:f63b
```

Result: ✅ Auto-corrected and search succeeds

---

## Files Modified

1. `src/core/analysis_context.py`
   - Added `get_entities_detailed()` method
   - Shows actual entity values (first 3 per type)

2. `src/core/decision_agent.py`
   - Updated `_build_decision_prompt()` to include entity values
   - Enhanced prompt instructions
   - Added validation in `_validate_decision()` to catch and fix truncated values

---

## Impact

✅ **LLM sees actual entity values**  
✅ **Clear instructions to use full values**  
✅ **Automatic detection of truncated values**  
✅ **Auto-correction using context**  
✅ **Prevents search failures from truncation**  

---

**Status:** ✅ Fixed  
**Date:** November 29, 2025  
**Impact:** LLM decisions now use correct full entity values

