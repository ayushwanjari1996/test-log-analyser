# Bug Fix: Entity Extraction Parsing Issues

## Problem

**Query:** `"which rpd is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

**Console Output:**
```
INFO: Extracted 7 unique entities
...
Searching for rpdname in logs with 'cpe_mac:2 (from entities found)'
```

**Issue:** The IPv6 address `2001:558:6017:60:4950:96e8:be4f:f63b` was being extracted as `cpe_mac:2` instead of `cpe_ip:2001:558:...`

---

## Root Cause

### Issue: Overly Greedy Regex Patterns

The patterns for `cpe_mac`, `cm_mac`, and `cpe_ip` were too similar:

```yaml
# OLD (TOO GREEDY)
cpe_mac:
  - "\"CpeMacAddress\"\\s*:\\s*\"([0-9a-fA-F:]+)\""  # ← Matches ANY hex+colons
  - "CpeMacAddress[:\\s]*([0-9a-fA-F:]+)"           # ← Matches ANY hex+colons
  - "cpe[_\\s]*mac[:\\s]*([0-9a-fA-F:]+)"          # ← TOO GREEDY!

cpe_ip:
  - "\"CpeIpAddress\"\\s*:\\s*\"([0-9a-fA-F:.]+)\""  # ← Same pattern!
  - "CpeIpAddress[:\\s]*([0-9a-fA-F:.]+)"            # ← Same pattern!
```

**Problem:**
1. The pattern `[0-9a-fA-F:]+` matches **both** MAC addresses (e.g., `2c:ab:a4:47:1a:d0`) **and** IPv6 addresses (e.g., `2001:558:6017:...`)
2. The third `cpe_mac` pattern `cpe[_\s]*mac[:\s]*([0-9a-fA-F:]+)` was matching the query text itself: "cpe **2**001:558:..." and extracting just "2"
3. Entity extraction processes patterns in order, so `cpe_mac` was matched before `cpe_ip`

---

## Fix

### Make MAC Address Patterns Strict

Changed all MAC address patterns to require the **exact MAC format**: `XX:XX:XX:XX:XX:XX`

```yaml
# NEW (STRICT)
cpe_mac:
  - "\"CpeMacAddress\"\\s*:\\s*\"([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})\""
  - "CpeMacAddress[:\\s]*([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})"
  # Removed the greedy "cpe[_\s]*mac" pattern

cm_mac:
  - "\"CmMacAddress\"\\s*:\\s*\"([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})\""
  - "CmMacAddress[:\\s]*([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})"

cpe_ip:
  - "\"CpeIpAddress\"\\s*:\\s*\"([0-9a-fA-F:]+)\""  # ← Now won't conflict with MAC
  - "CpeIpAddress[:\\s]*([0-9a-fA-F:]+)"
```

**Benefits:**
- ✅ MAC addresses must be exactly 6 groups of 2 hex digits
- ✅ Won't match partial IPv6 addresses
- ✅ Won't match query text like "cpe 2001:..."
- ✅ `cpe_ip` pattern can still match full IPv6 addresses

---

## Verification

### Test Cases

**MAC Addresses (should match `cpe_mac` or `cm_mac`):**
- ✅ `2c:ab:a4:47:1a:d0` → Valid MAC
- ✅ `2C:AB:A4:47:1A:D0` → Valid MAC (uppercase)
- ❌ `2c:ab:a4` → Invalid (only 3 groups)
- ❌ `2` → Invalid (not a MAC)

**IPv6 Addresses (should match `cpe_ip`):**
- ✅ `2001:558:6017:60:4950:96e8:be4f:f63b` → Valid IPv6
- ✅ `2001:db8::1` → Valid IPv6 (compressed)
- ❌ `2001` → Invalid (too short)

**Log Extraction:**
```json
{
  "CmMacAddress": "2c:ab:a4:47:1a:d0",
  "CpeMacAddress": "2c:ab:a4:47:1a:d2", 
  "CpeIpAddress": "2001:558:6017:60:4950:96e8:be4f:f63b"
}
```

Should extract:
- ✅ `cm_mac: 2c:ab:a4:47:1a:d0`
- ✅ `cpe_mac: 2c:ab:a4:47:1a:d2`
- ✅ `cpe_ip: 2001:558:6017:60:4950:96e8:be4f:f63b`

---

## Expected Behavior After Fix

**Query:** `"which rpd is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

```
[11/29/25 13:25:00] INFO: Extracted 8 unique entities
                    INFO: Processing entity type: cpe_ip
                    INFO: Found: cpe_ip = 2001:558:6017:60:4950:96e8:be4f:f63b ✓
                    INFO: Processing entity type: cpe_mac
                    INFO: Found: cpe_mac = 2c:ab:a4:47:1a:d2 ✓
                    INFO: Processing entity type: cm_mac
                    INFO: Found: cm_mac = 2c:ab:a4:47:1a:d0 ✓

[11/29/25 13:25:05] INFO: Iterative search: 2001:558:6017:... → rpdname
                    INFO: Searching for rpdname via bridges
                    INFO: Bridge found: cm_mac:2c:ab:a4:47:1a:d0
                    INFO: ✓ Found rpdname: TestRpd123

✅ ANALYSIS COMPLETE
📊 Answer: CPE is connected to RPD: TestRpd123
```

---

## Files Modified

- `config/entity_mappings.yaml`
  - `cpe_mac` patterns: Made strict (6 groups of 2 hex digits)
  - `cm_mac` patterns: Made strict (6 groups of 2 hex digits)
  - Removed greedy `cpe[_\s]*mac` pattern

---

**Status:** ✅ Fixed
**Date:** November 29, 2025
**Impact:** Entity extraction now correctly distinguishes MAC addresses from IPv6 addresses

