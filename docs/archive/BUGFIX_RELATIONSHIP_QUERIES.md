# Bug Fix: Relationship Queries Stopping Too Early

## Problem

**Query:** `"which rpdname is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

**What Happened:**
```
Iteration 1: direct_search → Found 1 log with 7 entities (but no rpdname!)
Iteration 2: summarization → STOPPED ❌
```

**What Should Have Happened:**
```
Iteration 1: direct_search → Found 1 log with 7 entities (no rpdname yet)
Iteration 2: iterative_search → Search related entities (cm_mac, cpe_mac, etc.)
Iteration 3: Extract rpdname from related logs
Iteration 4: summarization → SUCCESS ✅
```

---

## Root Cause

### Issue 1: Success Criteria Too Lenient

In `src/core/workflow_orchestrator.py`, the `_check_success()` method:

```python
# OLD (WRONG)
if parsed.get("query_type") in ["specific_value", "relationship"]:
    return context.logs_analyzed > 0  # ❌ Stops as soon as ANY logs found!
```

**Problem:** For relationship queries like "find A for B", just finding logs for B is NOT enough - we need to actually find entity type A!

### Issue 2: Regex Pattern Too Restrictive

In `config/entity_mappings.yaml`:

```yaml
# OLD (WRONG)
rpdname:
  - "\"RpdName\"\\s*:\\s*\"([A-Z0-9]+)\""  # ❌ Only uppercase!
```

**Problem:** Pattern only matches uppercase letters (e.g., `MAWED06P01`) but log had mixed case `TestRpd123`.

---

## Fixes

### Fix 1: Smarter Success Criteria for Relationship Queries

```python
# NEW (CORRECT)
# For relationship queries - need to find the TARGET entity type
if parsed.get("query_type") == "relationship":
    # Get what entity type user is looking for (primary entity)
    primary = parsed.get("primary_entity", {})
    target_type = primary.get("type")
    
    # Check if we found entities of that type
    if target_type and target_type in context.entities:
        logger.info(f"✓ Found target entity type '{target_type}'")
        return True
    
    # If we found logs but not the target entity, keep searching
    # Only stop if we've tried iterative search or exhausted options
    if context.has_tried("iterative_search") and context.iteration >= 3:
        return True  # Tried hard enough
    
    return False  # Keep searching!
```

**Now:**
- ✅ Checks if we actually found the **target entity type** (e.g., `rpdname`)
- ✅ Keeps searching if not found yet
- ✅ Triggers iterative search automatically
- ✅ Only stops after genuine effort (3+ iterations + iterative search tried)

### Fix 2: More Flexible Regex Pattern

```yaml
# NEW (CORRECT)
rpdname:
  - "\"RpdName\"\\s*:\\s*\"([A-Za-z0-9_-]+)\""  # ✅ Mixed case, underscores, hyphens
  - "RpdName[:\\s]*([A-Za-z0-9_-]+)"
  - "rpd[_\\s]*name[:\\s]*([A-Za-z0-9_-]+)"
```

**Now matches:**
- ✅ `MAWED06P01` (all uppercase)
- ✅ `TestRpd123` (mixed case)
- ✅ `rpd-name-123` (with hyphens)
- ✅ `rpd_name_456` (with underscores)

---

## Expected Behavior After Fix

**Query:** `"which rpdname is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

```
======================================================================
🧠 ITERATION 1
======================================================================
Decision: direct_search
Reasoning: Search for the CPE IP directly
Result: Found 1 log with 7 entities
  ✗ Target entity 'rpdname' NOT found yet
  ✓ Found related: cpe_ip, cpe_mac, cm_mac
Success criteria: NOT MET (no rpdname found)

======================================================================
🧠 ITERATION 2
======================================================================
Decision: direct_search (on cm_mac found in iteration 1)
Reasoning: CPE is connected to CM, search CM logs to find RPD connection
Result: Found 1 log
  ✓ Target entity 'rpdname' FOUND: TestRpd123
Success criteria: MET!

======================================================================
🧠 ITERATION 3
======================================================================
Decision: summarization
Reasoning: Target entity found, create final answer
Result: Success!

======================================================================
✅ ANALYSIS COMPLETE

📊 Answer:
  CPE 2001:558:6017:60:4950:96e8:be4f:f63b is connected to rpdname: TestRpd123

🔗 Causal Chain:
  1. CPE IP: 2001:558:6017:60:4950:96e8:be4f:f63b
  2. CPE MAC: 2c:ab:a4:47:1a:d2
  3. CM MAC: 2c:ab:a4:47:1a:d0
  4. RPD Name: TestRpd123

Confidence: 95%
======================================================================
```

---

## Testing

**Test queries to verify:**

```bash
# Relationship queries (should find target entity)
which rpdname is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?
find rpdname for cm 2c:ab:a4:47:1a:d0
find cm for rpdname TestRpd123
which ip is associated with cpe 2c:ab:a4:47:1a:d2

# Should do multiple iterations until target found
# Should use iterative search if direct search doesn't find target
# Should extract rpdname with mixed case (TestRpd123)
```

---

## Related Enhancements

Also added **CPE entities** to `config/entity_mappings.yaml`:

- `cpe_mac` - CPE MAC address
- `cpe_ip` - CPE IP address (IPv4/IPv6)
- `cm_mac` - Cable Modem MAC address
- Relationships: `cpe` ↔ `cm`, `mac_address`, `ip_address`, `md_id`

---

**Status:** ✅ Fixed
**Date:** November 29, 2025
**Impact:** Relationship queries now work correctly with multi-hop search

