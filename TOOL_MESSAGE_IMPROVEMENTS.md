# Tool Message Improvements

## Problem
LLM was confusing intermediate data with final answers:
- Saw "Found 39 logs" → thought that's the answer
- Query asked "how many unique CPEs?" but LLM returned 39 (log count, not unique count)

## Solution
Updated ALL tool messages to clearly distinguish data types using prefixes:

---

## RAW DATA (Intermediate - Need Further Processing)

**grep_logs:**
- Before: `"Found 39 logs matching 'CpeMacAddress'"`
- After: `"[RAW DATA] Found 39 log entries matching 'CpeMacAddress' - may contain duplicates"`

**parse_json_field:**
- Before: `"Extracted 25 values for 'CpeMacAddress'"`
- After: `"[RAW DATA] Extracted 25 raw values for 'CpeMacAddress' - may contain duplicates"`

**sort_by_time:**
- Before: `"Sorted 20 logs oldest→newest"`
- After: `"[RAW DATA] Sorted 20 log entries oldest→newest"`

**extract_time_range:**
- Before: `"Extracted 15 logs between..."`
- After: `"[RAW DATA] Extracted 15 log entries between..."`

**grep_and_parse (unique_only=false):**
- Before: `"Found 30 values for 'MdId'"`
- After: `"[RAW DATA] Found 30 raw values for 'MdId'"`

---

## FINAL/AGGREGATED (Ready Answers)

**extract_unique:**
- Before: `"Found 15 unique values (from 39 total)"`
- After: `"[FINAL] 15 UNIQUE values (deduplicated from 39 raw entries)"`

**count_values:**
- Before: `"15 unique values (from 39 total)"`
- After: `"[FINAL COUNT] 15 unique values (from 39 total entries)"`

**grep_and_parse (unique_only=true):**
- Before: `"Found 15 values for 'CpeMacAddress'"`
- After: `"[FINAL] Found 15 UNIQUE values for 'CpeMacAddress'"`

**find_relationship_chain:**
- Before: `"Found MdId='0x2040000' via path: CPE → CM → RPD → MdId"`
- After: `"[FINAL] Found MdId='0x2040000' via path: CPE → CM → RPD → MdId"`

**count_unique_per_group:**
- Before: `"Counted unique 'CmMacAddress' per 'MdId': 5 groups..."`
- After: `"[FINAL AGGREGATION] Counted unique 'CmMacAddress' per 'MdId': 5 groups..."`

**count_via_relationship:**
- Before: `"Counted 'CpeMacAddress' per 'MdId' via relationship chain..."`
- After: `"[FINAL AGGREGATION] Counted 'CpeMacAddress' per 'MdId' via relationship chain..."`

**aggregate_by_field:**
- Before: `"Grouped by 'MdId': 100 unique values..."`
- After: `"[FINAL AGGREGATION] Grouped by 'MdId': 100 unique values..."`

---

## METADATA/INFORMATIONAL (Helper Tools)

**summarize_logs:**
- Before: `"Summary: 2115 logs | Time range: 2h | Severities: ERROR:5, INFO:2110"`
- After: `"[METADATA] Summary: 2115 logs | Time range: 2h | Severities: ERROR:5, INFO:2110"`

**analyze_logs:**
- Before: `"Analysis complete: The logs show..."`
- After: `"[LLM ANALYSIS] The logs show..."`

**return_logs:**
- Before: `"Formatted 39 logs for display"`
- After: `"[FORMATTED OUTPUT] 39 logs formatted for display"`

---

## Benefits

✅ **Clear Signal to LLM:**
- `[RAW DATA]` → "This is NOT the answer, keep processing"
- `[FINAL]` / `[FINAL COUNT]` / `[FINAL AGGREGATION]` → "This IS the answer"

✅ **Forces Correct Reasoning:**
```
Before: grep_logs → "39 logs found" → LLM thinks: "Done!" → WRONG
After:  grep_logs → "[RAW DATA] 39 log entries - may contain duplicates" 
        → LLM thinks: "Raw data, need to count unique" 
        → count_values → "[FINAL COUNT] 15 unique" 
        → LLM: "Done!" → CORRECT
```

✅ **Programmatic Checks:**
- Added `metadata.data_type` to all results:
  - `"raw_logs"` / `"raw_values"` for intermediate
  - `"unique_values"` / `"final_count"` / `"aggregated"` for final

✅ **Self-Documenting:**
- Anyone reading logs/debug output can instantly see data type
- No guessing if result is intermediate or final

---

## Files Modified

1. `src/core/tools/grep_tools.py` - 5 tools updated
2. `src/core/tools/aggregation_tools.py` - 2 tools updated
3. `src/core/tools/analysis_tools.py` - 3 tools updated (AggregateByFieldTool, SummarizeLogsTool, AnalyzeLogsTool)
4. `src/core/tools/time_tools.py` - 2 tools updated
5. `src/core/tools/relationship_tools.py` - 1 tool updated (FindRelationshipChainTool)
6. `src/core/tools/output_tools.py` - 1 tool updated (ReturnLogsTool)

**Total:** 14/15 active tools updated (FinalizeAnswerTool is a meta tool, no label needed), 0 breaking changes

