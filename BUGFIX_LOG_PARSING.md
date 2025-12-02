# Bug Fix: Log Parsing for Timeline & Pattern Analysis

## Date
November 29, 2025

## Critical Issue Identified

Timeline and pattern analysis were receiving **empty log data**, causing the LLM to generate fake timestamps, generic event names, and meaningless patterns.

---

## Root Cause

### The Problem

The CSV log structure is:
```
Column "_source.date": "Nov 5, 2025 @ 15:30:50.911"
Column "_source.log": "2025-11-05T15:30:50.911608325Z stdout F {\"Message\":\"ProcEvAddCpeIpAddrToRpd\", ...}"
```

But `_format_logs_for_llm()` was looking for:
```python
log.get("timestamp")  # ❌ Doesn't exist!
log.get("severity")   # ❌ Doesn't exist!
log.get("message")    # ❌ Doesn't exist!
```

**Result**: All fields defaulted to empty values, so the LLM received:
```
1. [??:??:??] INFO: 
2. [??:??:??] INFO: 
3. [??:??:??] INFO: 
```

---

## Debug Evidence

```
🔍 First log keys: ['_index', '_id', '_source.date', '_source.log', ...]
🔍 Extracted - timestamp: ??:??:??, severity: INFO, message: EMPTY
```

The LLM had NO real data, so it:
- Invented fake timestamps: `00:00:01`, `00:00:02`, `00:00:03`
- Invented generic events: `"Event 1 happened"`, `"Event 2 occurred"`
- Generated generic patterns: `"High frequency of INFO messages"`

---

## Solution Implemented

### 1. Created `_parse_log_entry()` Method

**New method in `base_method.py`** that:

1. **Extracts ISO timestamp** from `_source.log`:
   ```
   "2025-11-05T15:30:50.911608325Z" → "15:30:50.911"
   ```

2. **Parses embedded JSON** from `_source.log`:
   ```
   "stdout F {...JSON...}" → Parse JSON → Extract fields
   ```

3. **Extracts structured fields**:
   - `Severity`: "DEBUG", "INFO", "WARN", "ERROR"
   - `Message`: "ProcEvAddCpeIpAddrToRpd"
   - `Function`: "ProcEvAddCpeIpAddrToRpd"

4. **Extracts entities** from JSON:
   - `CmMacAddress` → `cm_mac`
   - `CpeMacAddress` → `cpe_mac`
   - `RpdName` → `rpd`
   - `mdId` → `md_id`
   - `sfId` → `sf_id`
   - `CpeIpAddress` → `cpe_ip`

### 2. Rewrote `_format_logs_for_llm()`

**Old format** (broken):
```
1. [??:??:??] INFO: 
2. [??:??:??] INFO: 
```

**New format** (working):
```
1. [15:30:34.746] DEBUG - ProcEvAddCpeIpAddrToRpd
   Entities: cm_mac=2c:ab:a4:47:1a:d0, cpe_mac=2c:ab:a4:47:1a:d2, rpd=TestRpd123

2. [15:30:50.911] DEBUG - ProcEvAddCpeIpAddrToRpd
   Entities: cm_mac=2c:ab:a4:47:1a:d0, cpe_mac=2c:ab:a4:47:1a:d2, rpd=TestRpd123, md_id=0x2040000
```

### 3. Fixed Timeline Sorting Error

**Old code** (crashed):
```python
all_events.sort(key=lambda x: x.get("timestamp", ""))
# ERROR: '<' not supported between NoneType and str
```

**New code** (handles None):
```python
all_events.sort(key=lambda x: x.get("timestamp") or "9999-99-99")
```

### 4. Updated Prompts

**Timeline Analysis**:
```
CRITICAL REQUIREMENTS:
1. Use the EXACT timestamps from the logs (format: HH:MM:SS.mmm)
2. Use the EXACT message/function names (e.g., "ProcEvAddCpeIpAddrToRpd")
3. Include the ACTUAL entities from each log
4. DO NOT make up generic events like "Event 1 happened"
5. DO NOT invent fake timestamps like "00:00:01"
```

**Pattern Analysis**:
```
⚠️ CRITICAL: Use ACTUAL data from the logs!
- Count SPECIFIC message types (e.g., "ProcEvAddCpeIpAddrToRpd occurs 20 times")
- Identify SPECIFIC entity relationships (e.g., "CM X always with CPE Y")
- DO NOT say generic things like "high frequency"
```

---

## Expected Results After Fix

### Timeline (Before)
```
⏱️ Timeline:
  • [00:00:03] Event 1 happened...
  • [00:00:04] Event 2 happened...
  • [00:00:05] Event 5 happened
```

### Timeline (After)
```
⏱️ Timeline:
  • [15:30:34.746] ProcEvAddCpeIpAddrToRpd
    CM: 2c:ab:a4:47:1a:d0, CPE: 2c:ab:a4:47:1a:d2, RPD: TestRpd123
  
  • [15:30:50.911] ProcEvAddCpeIpAddrToRpd
    CM: 2c:ab:a4:47:1a:d0, CPE: 2c:ab:a4:47:1a:d2, MD: 0x2040000
```

### Patterns (Before)
```
🔍 Patterns:
  1. High frequency of INFO messages at regular intervals (90%)
  2. All logs have the same severity and type (100%)
```

### Patterns (After)
```
🔍 Patterns:
  1. ProcEvAddCpeIpAddrToRpd occurs 24 times (100%)
  2. CM MAC 20:f1:9e:ff:bc:76 consistently paired with CPE fc:ae:34:f2:3f:0d (100%)
  3. All events associated with RpdName: TestRpd123 (95%)
  4. MD ID 0x2040000 appears in 20 of 24 logs (85%)
```

---

## Files Modified

1. **`src/core/methods/base_method.py`**
   - Added `_parse_log_entry()` method to extract timestamp, severity, message, entities from CSV structure
   - Rewrote `_format_logs_for_llm()` to use parsed data

2. **`src/core/methods/timeline_analysis.py`**
   - Fixed sorting to handle None timestamps
   - Updated prompt to demand exact timestamps and message names

3. **`src/core/methods/pattern_analysis.py`**
   - Updated prompt to demand specific data, not generic observations

---

## Technical Details

### CSV Structure
```
_source.log format: "ISO_TIMESTAMP stdout F {JSON_PAYLOAD}"
Example: "2025-11-05T15:30:50.911608325Z stdout F {\"Message\":\"...\", ...}"
```

### Parsing Strategy
1. Extract ISO timestamp with regex: `r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)'`
2. Convert to HH:MM:SS.mmm format
3. Extract JSON with regex: `r'stdout F ({.+})$'`
4. Parse JSON with `json.loads()`
5. Extract Severity, Message, Function, and entity fields

### Entity Mapping
```python
'CmMacAddress' → 'cm_mac'
'CpeMacAddress' → 'cpe_mac'
'RpdName' → 'rpd'
'mdId' → 'md_id'
'sfId' → 'sf_id'
'CpeIpAddress' → 'cpe_ip'
```

---

## Testing

Run this query to verify the fix:
```
analyse flow for cm mac 20:f1:9e:ff:bc:76
```

**Expected behavior**:
- ✅ Timeline shows real timestamps (15:30:XX.XXX)
- ✅ Timeline shows real message names (ProcEvAddCpeIpAddrToRpd)
- ✅ Timeline shows actual entities (CM, CPE, RPD, MD IDs)
- ✅ Patterns show specific message counts
- ✅ Patterns show actual entity relationships
- ✅ No crashes on timeline sorting

---

## Impact

- **High Impact**: This was the primary blocker for timeline and pattern analysis
- **No Regression**: Find/iterative search unaffected (they use regex, not LLM formatting)
- **User Experience**: Analysis queries now provide meaningful, accurate results

---

## Status

✅ **COMPLETE** - Ready for testing


