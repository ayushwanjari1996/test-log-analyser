# Bug Fix: MAC Address Regex Capture Groups Truncating Values

## Problem

**Query:** `"which rpd is cpe 2001:558:6017:60:4950:96e8:be4f:f63b connected to?"`

**Output:**
```
🔗 Related Entities:
  • cpe_mac: 2c:ab:a4:47:1a:d2   ✅ Full MAC
  • cm_mac: 2c:ab:a4:47:1a:d0    ✅ Full MAC
  • mac_address: 1a:             ❌ TRUNCATED! Should be full MAC
```

---

## Root Cause

### The Regex Pattern Had Multiple Capture Groups

**BEFORE (config/entity_mappings.yaml):**
```yaml
mac_address:
  - "([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"
     └─────────────────┘      └──────────────┘
       Group 1 (repeated)       Group 2
```

**Problem:**

This pattern has **TWO capture groups**:
1. `([0-9A-Fa-f]{2}[:-])` - Matched 5 times (but only LAST match is captured)
2. `([0-9A-Fa-f]{2})` - Final pair

**What Python regex does:**

When a capture group is inside a quantifier like `{5}`, Python only keeps the **LAST captured value** for that group!

**Example:**
```python
import re
pattern = r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"
text = "MAC: 2c:ab:a4:47:1a:d2"
match = re.search(pattern, text)

print(match.group(0))  # Full match: '2c:ab:a4:47:1a:d2'
print(match.group(1))  # Group 1: '1a:'  ← LAST iteration only!
print(match.group(2))  # Group 2: 'd2'   ← Final pair
```

**Result:** `'1a:'` ❌

**Why `cpe_mac` and `cm_mac` worked:**

These patterns explicitly wrote out all 6 pairs:
```yaml
cpe_mac:
  - "([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})"
     └────────────────────────────────────────────────────────────────────────────────────────────┘
       Single capture group = entire MAC ✅
```

---

## Fix

### Expand the Pattern (Single Capture Group)

**AFTER:**
```yaml
mac_address:
  - "([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})"
     └────────────────────────────────────────────────────────────────────────────────────────────┘
       Single capture group = entire MAC ✅
```

Now there's only **ONE capture group** that captures the entire MAC address.

**Test:**
```python
pattern = r"([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})"
text = "MAC: 2c:ab:a4:47:1a:d2"
match = re.search(pattern, text)
print(match.group(1))  # '2c:ab:a4:47:1a:d2' ✅
```

---

## Alternative Fix (Non-Capturing Groups)

Another approach would be to use **non-capturing groups** `(?:...)`:

```yaml
# Alternative (not used, but valid):
mac_address:
  - "((?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})"
      └──┘ non-capturing = don't save this group
```

This tells regex: "Match this pattern but don't create a capture group for it."

We chose the explicit expansion approach for clarity and consistency with `cpe_mac` and `cm_mac`.

---

## Why This Matters

### Impact on Entity Extraction

When `EntityManager.extract_entities()` uses regex:
```python
matches = re.finditer(pattern, text)
for match in matches:
    entity_value = match.group(1)  # Get first capture group
    # Store entity_value
```

If `match.group(1)` returns `'1a:'` instead of `'2c:ab:a4:47:1a:d2'`, then:
- ❌ Entity stored as `mac_address: 1a:`
- ❌ Search for this entity fails (can't find `1a:` in logs)
- ❌ LLM sees incomplete value
- ❌ User sees truncated value in output

---

## Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `config/entity_mappings.yaml` | Expand `mac_address` pattern | Capture full MAC with single group |
| `test_interactive.py` | Add note about emoji | Remind user to restart Python |

---

## Testing

### Before Fix:
```python
>>> pattern = r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"
>>> match = re.search(pattern, "MAC: 2c:ab:a4:47:1a:d2")
>>> match.group(1)
'1a:'  ❌ Truncated
```

### After Fix:
```python
>>> pattern = r"([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})"
>>> match = re.search(pattern, "MAC: 2c:ab:a4:47:1a:d2")
>>> match.group(1)
'2c:ab:a4:47:1a:d2'  ✅ Full MAC
```

### Expected Output After Fix:
```
🔗 Related Entities:
  • cpe_mac: 2c:ab:a4:47:1a:d2    ✅
  • cm_mac: 2c:ab:a4:47:1a:d0     ✅
  • mac_address: 2c:ab:a4:47:1a:d2  ✅ Now full!
```

---

## Related Issues

1. **Emoji in Logs** (`2c🆎a4:47:1a:d0`)
   - Fixed in: `BUGFIX_MAC_ADDRESS_EMOJI.md`
   - Requires: Restart Python to reload logger with `emoji=False`

2. **Colon Stripping** (`2caba4471ad0`)
   - Fixed in: `BUGFIX_MAC_ADDRESS_EMOJI.md`
   - Fixed by: Adding `:` to `sanitize_entity_name()` allowed chars

---

**Status:** ✅ Fixed  
**Date:** November 29, 2025  
**Root Cause:** Regex pattern with repeated capture group only returned last match  
**Fix:** Expanded pattern to single capture group for entire MAC address  
**Impact:** All generic MAC addresses now captured correctly

