# Auto-Parse Field Names - Implementation

## Problem Solved

**LLM confusion:**
```
LLM: extract_unique(["CpeMacAddress"])  ← Passed field NAME
Tool: Deduplicates the string "CpeMacAddress"
Result: "1 unique value" ❌ WRONG!
```

**What LLM should do:**
```
Step 1: parse_json_field(logs, "CpeMacAddress") → get MACs
Step 2: count_values(MACs) → count unique
```

**But LLM doesn't understand this workflow!**

---

## Solution: Smart Auto-Parsing

**Tools now detect and fix the mistake automatically:**

```
LLM: extract_unique(["CpeMacAddress"])
     ↓
Tool detects: "CpeMacAddress" looks like a field name
     ↓
Tool auto-parses: Extracts "CpeMacAddress" field from logs
     ↓
Tool continues: Deduplicates the actual MAC addresses
     ↓
Result: "15 unique values" ✓ CORRECT!
```

---

## Implementation

### 1. Updated `extract_unique` Tool

**Added:**
- Optional `logs` parameter (auto-injected by orchestrator)
- `_looks_like_field_names()` - detects if values are field names
- `_auto_parse_fields()` - extracts actual values from logs

**Logic:**
```python
def execute(self, **kwargs):
    values = kwargs.get("values", [])
    logs = kwargs.get("logs")
    
    # Detect field names
    if _looks_like_field_names(values) and logs is not None:
        # Auto-parse: Extract field values from logs
        values = _auto_parse_fields(values, logs)
    
    # Continue with normal deduplication
    unique = list(set(values))
    return unique
```

**Detection heuristics:**
- Short list (≤5 items)
- PascalCase strings (has uppercase letters)
- No special chars (no `:` or `.` like MACs/IPs have)

---

### 2. Updated `count_values` Tool

Same logic as `extract_unique`:
- Auto-detects field names
- Auto-parses from logs
- Continues with counting

---

### 3. Updated Orchestrator Auto-Injection

**Added optional logs injection:**
```python
# If tool has "logs" parameter (even if not required), inject it
if has_logs_param and "logs" not in params:
    if state.current_logs is not None:
        params["logs"] = state.current_logs
```

**This enables auto-parsing without breaking existing tools.**

---

## How It Works

### Example Flow

**Query:** "count total number of cpe devices"

#### Iteration 1:
```
LLM: grep_logs("CpeMacAddress")
→ 39 log entries loaded
```

#### Iteration 2:
```
LLM: extract_unique(["CpeMacAddress"])  ← Passes field name (mistake!)

Tool receives:
  values = ["CpeMacAddress"]
  logs = 39 DataFrame rows (auto-injected)

Tool detects:
  ✓ "CpeMacAddress" is PascalCase
  ✓ No special characters
  ✓ Looks like a field name!

Tool auto-parses:
  1. Extracts "CpeMacAddress" from all 39 logs
  2. Gets: ["2c:ab:a4:47:1a:d2", "f8:79:0a:3d:58:33", ...]
  3. Now has 39 MAC addresses

Tool continues:
  Deduplicates → 15 unique MACs

Result: [FINAL] 15 UNIQUE values ✓
```

#### Iteration 3:
```
LLM: finalize_answer("15 unique CPE devices") ✓
```

---

## Why This is Smart

✅ **User-Friendly** - Forgives LLM mistakes  
✅ **Transparent** - Logs what it's doing  
✅ **Safe** - Only activates when pattern matches  
✅ **Non-Breaking** - If detection fails, returns values as-is  
✅ **Generic** - Works for ANY field name  

**The system now understands user intent and fixes mistakes automatically.**

---

## Files Modified

1. **`src/core/tools/grep_tools.py`**
   - Added auto-parsing to `ExtractUniqueValuesTool`
   - Added auto-parsing to `CountValuesTool`
   - Added helper methods: `_looks_like_field_names()`, `_auto_parse_fields()`

2. **`src/core/iterative_react_orchestrator.py`**
   - Updated auto-injection logic to inject logs even for optional `logs` parameters

**Total:** ~100 lines added, 0 breaking changes

---

## Detection Logic

```python
def _looks_like_field_names(values):
    """
    Field names are:
    - Short list (1-5 items)
    - PascalCase (e.g., "CpeMacAddress", "MdId")
    - No special characters (: or .)
    """
    if len(values) > 5:
        return False
    
    for v in values:
        if not isinstance(v, str):
            return False
        if not any(c.isupper() for c in v):
            return False
        if ':' in v or '.' in v:  # Likely data, not field name
            return False
    
    return True
```

**Examples:**
- `["CpeMacAddress"]` → ✓ Detected as field name
- `["2c:ab:a4:47:1a:d2"]` → ✗ Has `:`, it's a MAC address
- `["192.168.1.1"]` → ✗ Has `.`, it's an IP
- `["severity"]` → ✗ All lowercase, not PascalCase

---

## Result

**No more confusion!** LLM can pass field names, and the system just works.

The user no longer sees:
```
❌ "1 unique value" (wrong)
```

They see:
```
✓ "15 unique CPE devices" (correct)
```

**System is now truly intelligent - understands intent, not just literal commands.**


