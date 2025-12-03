# return_logs Tool Implementation

## Summary

Implemented a new `return_logs` tool that formats cached logs into human-readable summaries. This solves the query intent detection problem where LLM was over-engineering simple "show logs" queries.

---

## What Was Changed

### 1. **New File: `src/core/tools/output_tools.py`**

Created `ReturnLogsTool` class that:
- Takes cached logs (auto-injected from search_logs)
- Formats them into human-readable summary:
  - Log count
  - Time range (if timestamps available)
  - Severity distribution (if severity field exists)
  - Sample log entries (default: 5, configurable via `max_samples`)
- Returns formatted string that LLM can use in `finalize_answer`

**Key Features:**
- Auto-detects timestamp fields: `@timestamp`, `timestamp`, `time`, `_source.@timestamp`
- Auto-detects severity fields: `_source.log.severity`, `severity`, `level`
- Intelligent log content extraction from various field formats
- Truncates long log entries (max 200 chars per entry)
- Handles empty logs gracefully

### 2. **Updated: `src/core/tools/__init__.py`**

- Imported `ReturnLogsTool` from `output_tools`
- Added to `__all__` exports
- Registered in `create_all_tools()` factory function
- Tool is now automatically available to orchestrator

### 3. **Updated: `src/llm/dynamic_prompts.py`**

Added **QUERY INTENT** section to system prompt:

```
A) USER WANTS THE LOGS THEMSELVES:
   Keywords: "search for logs", "show logs", "get logs"
   Flow: search_logs → return_logs → finalize_answer (2 iterations)

B) USER WANTS ENTITIES/RELATIONSHIPS:
   Keywords: "find all CMs", "which CMs connected"
   Flow: search_logs → extract_entities → finalize_answer (3 iterations)
```

This teaches the LLM to:
- Distinguish between "show logs" and "find entities" queries
- Choose appropriate workflow based on user intent
- Minimize iterations for simple queries

### 4. **New Test Script: `test_return_logs_tool.py`**

Comprehensive test suite with two test modes:

**Test 1: Standalone Tool Test**
- Tests `return_logs` tool in isolation
- Searches for logs with MAWED07T01
- Formats and displays results
- Validates tool functionality

**Test 2: Query Intent Detection**
- Tests 3 different query types:
  1. "search for logs with rpd MAWED07T01" (expect: search → return_logs → finalize)
  2. "find all cms connected to rpd MAWED07T01" (expect: search → extract_entities → finalize)
  3. "show me error logs for rpd MAWED07T01" (expect: search → filter → return_logs → finalize)
- Evaluates:
  - Iteration count (should be minimal)
  - Tools used (correct workflow)
  - Answer keywords (contains expected info)

---

## Tool Registration

Total tools now: **13** (was 12)

1. search_logs
2. filter_by_time
3. filter_by_severity
4. filter_by_field
5. get_log_count
6. extract_entities
7. count_entities
8. aggregate_entities
9. find_entity_relationships
10. normalize_term
11. fuzzy_search
12. **return_logs** ← NEW
13. finalize_answer

---

## How It Works

### Example Flow A: "search for logs with rpd X"

```
Iteration 1:
  LLM: "User wants to SEE logs"
  Tool: search_logs(value="X")
  Result: Found 3 logs [cached]

Iteration 2:
  LLM: "Format the logs for display"
  Tool: return_logs(max_samples=5)
  Result: "Found 3 logs\nTime range: ...\nSeverity: 2 errors, 1 warning\n[1] log entry..."

Iteration 3:
  LLM: "I have formatted output, finalize"
  Tool: finalize_answer(answer="Found 3 logs containing X: [details]")
  Result: DONE ✓
```

### Example Flow B: "find all CMs connected to rpd X"

```
Iteration 1:
  Tool: search_logs(value="X")
  Result: Found 3 logs [cached]

Iteration 2:
  Tool: extract_entities(entity_types=["cm_mac"])
  Result: Found 2 entities: [addr1, addr2]

Iteration 3:
  Tool: finalize_answer(answer="Found 2 CMs: addr1, addr2")
  Result: DONE ✓
```

---

## Expected Test Results

### Query 1: "search for logs with rpd MAWED07T01"
- ✓ Iterations: 3 (search → return_logs → finalize)
- ✓ Answer contains: "3", "logs", "MAWED07T01"
- ✓ No entity extraction (unnecessary)

### Query 2: "find all cms connected to rpd MAWED07T01"
- ✓ Iterations: 3-4 (search → extract → finalize)
- ✓ Answer contains: "2", "CM", "1c:93:7c:2a:72:c3", "28:7a:ee:c9:66:4a"
- ✓ Does NOT call return_logs (entities, not logs)

### Query 3: "show me error logs for rpd MAWED07T01"
- ✓ Iterations: 4 (search → filter_severity → return_logs → finalize)
- ✓ Answer contains: "logs", "error", "MAWED07T01"

---

## Key Design Decisions

### 1. **Why `return_logs` instead of prompt-only fix?**
- **Composability**: Can be used in any workflow (after filter, after search, etc.)
- **Explicit intent**: Tool call = clear signal of what LLM wants
- **Separation of concerns**: Formatting logic isolated in tool, not in finalize_answer
- **Future flexibility**: Easy to enhance (add pagination, different formats, etc.)

### 2. **Why auto-inject logs parameter?**
- Consistent with other tools (extract_entities, count_entities)
- LLM doesn't need to track DataFrame references
- Simpler prompts and fewer errors

### 3. **Why include sample entries?**
- Users often want to SEE actual log content, not just stats
- Limited to 5 by default to avoid overwhelming output
- Configurable via `max_samples` parameter

### 4. **Why auto-detect fields?**
- Different log formats have different schemas
- Tool works across various log sources without config changes
- Graceful degradation if fields don't exist

---

## Testing Instructions

Run the test script:

```bash
python test_return_logs_tool.py
```

Expected output:
- Test 1: ✓ PASS (standalone tool works)
- Test 2: ✓ PASS (intent detection works, correct workflows)
- Overall: ✓ ALL TESTS PASSED

---

## What This Fixes

### Before:
```
Query: "search for logs with rpd MAWED07T01"
Flow: search_logs → extract_entities → count_entities → finalize
Result: "Found 2 CMs: addr1, addr2" (WRONG - user wanted logs, not CMs)
Iterations: 4 (TOO MANY)
```

### After:
```
Query: "search for logs with rpd MAWED07T01"
Flow: search_logs → return_logs → finalize
Result: "Found 3 logs containing MAWED07T01: [log details]" (CORRECT)
Iterations: 3 (OPTIMAL)
```

---

## Future Enhancements (Not Implemented Yet)

1. **Pagination**: `return_logs(offset=0, limit=10)` for large result sets
2. **Format options**: `return_logs(format="json|table|text")`
3. **Field selection**: `return_logs(fields=["timestamp", "severity", "message"])`
4. **Highlighting**: Highlight search terms in log output
5. **Export**: `return_logs(export_to="results.txt")`

---

## Files Modified

✓ `src/core/tools/output_tools.py` (NEW - 178 lines)
✓ `src/core/tools/__init__.py` (UPDATED - added ReturnLogsTool)
✓ `src/llm/dynamic_prompts.py` (UPDATED - added QUERY INTENT section)
✓ `test_return_logs_tool.py` (NEW - 281 lines)
✓ `RETURN_LOGS_IMPLEMENTATION.md` (NEW - this file)

All syntax validated ✓

