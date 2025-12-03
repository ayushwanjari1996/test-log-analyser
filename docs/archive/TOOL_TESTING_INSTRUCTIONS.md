# Tool Testing Instructions

## Step 1: Test Individual Tools

This validates that each tool works correctly in isolation BEFORE testing orchestration.

### Run the test:

```bash
python test_individual_tools.py
```

### What it tests:

**13 tools, grouped by category:**

1. **search_logs** - Basic search, column filtering, no results
2. **filter_by_time** - Time range filtering
3. **filter_by_severity** - Severity filtering (single and multiple)
4. **filter_by_field** - Field-based filtering
5. **get_log_count** - Count logs in DataFrame
6. **extract_entities** - Extract single, multiple, and all entity types
7. **count_entities** - Count specific entity type
8. **aggregate_entities** - Aggregate entity statistics
9. **find_entity_relationships** - Find related entities
10. **normalize_term** - Normalize search terms
11. **fuzzy_search** - Fuzzy search with normalized terms
12. **return_logs** - Format logs for human display
13. **finalize_answer** - Signal completion with answer

### Expected output:

```
✓ ALL TOOLS WORKING CORRECTLY
```

### If tests fail:

1. Check error messages in output
2. Fix the specific tool that failed
3. Re-run tests
4. **DO NOT proceed to orchestration until ALL tools pass**

---

## Step 2: After All Tools Pass

Once all individual tool tests pass:

1. **Verify tool descriptions are clear**
   - Run the test to see tool descriptions printed
   - Check that parameter names and types are obvious
   - Ensure no domain-specific hardcoding

2. **Check entity_mappings.yaml**
   - Verify all entity types are defined
   - Check patterns are correct
   - Ensure relationships are specified

3. **Test orchestrator with simple queries**
   - Start with 1-2 tool workflows
   - Gradually increase complexity
   - Monitor for parameter name errors

---

## Common Issues & Fixes

### Issue 1: "Missing required parameter 'logs'"

**Cause:** Tool has `required=True` for logs parameter

**Fix:** Change to `required=False` (logs are auto-injected)

```python
ToolParameter(
    name="logs",
    param_type=ParameterType.DATAFRAME,
    description="...",
    required=False  # ← Must be False
)
```

### Issue 2: LLM uses wrong parameter name

**Cause:** Tool description not clear enough

**Fix:** Enhance parameter description with type and example:

```python
ToolParameter(
    name="entity_types",
    param_type=ParameterType.LIST,
    description="List of entity types to extract (ARRAY of strings)",
    required=True,
    example=["cm_mac", "rpdname"]  # ← Shows it's an array
)
```

### Issue 3: DataFrame vs string confusion

**Cause:** Tool expecting DataFrame but getting string

**Fix:** Add type validation in tool.execute():

```python
if not isinstance(logs, pd.DataFrame):
    return ToolResult(
        success=False,
        error="Expected logs to be DataFrame",
        data={}
    )
```

### Issue 4: Entity extraction returns empty

**Cause:** Patterns in entity_mappings.yaml don't match log format

**Fix:** 
1. Check actual log content
2. Update regex patterns
3. Test pattern against sample logs

---

## What Changed (No More Hardcoding)

### ❌ REMOVED:
- Hardcoded examples with "cm_mac", "MAWED07T01", etc. in prompts
- Domain-specific parameter examples
- Assumptions about entity types

### ✅ NOW:
- Tool descriptions are self-documenting
- Parameter names include type info (STRING vs ARRAY)
- Examples derive from ToolParameter.example
- LLM learns from tool descriptions, not hardcoded prompts

---

## Next Steps After Tool Tests Pass

1. **Test orchestration with 1-2 tool queries:**
   - "search for logs with error"
   - "count logs"

2. **Test 3-tool workflows:**
   - "search for logs with X"
   - "find all entities of type Y"

3. **Test complex workflows:**
   - "find all X connected to Y"
   - "show error logs for entity Z"

4. **Monitor:**
   - Tool selection correctness
   - Parameter name accuracy
   - Iteration efficiency
   - Answer quality

---

## Files Modified

- ✅ `test_individual_tools.py` - Comprehensive unit tests for all 13 tools
- ✅ `src/llm/dynamic_prompts.py` - Removed ALL hardcoding
- ✅ `src/core/tools/base_tool.py` - Enhanced tool descriptions with type info
- ✅ `src/core/tools/output_tools.py` - Fixed logs parameter (required=False)

All changes focused on:
- Self-documenting tools
- Clear parameter types
- No domain-specific assumptions
- Generic, reusable architecture

