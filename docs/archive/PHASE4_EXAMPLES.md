# Phase 4: Query Examples & Expected Behavior

## Query Type Detection

### 1. Specific Value Searches (Search for VALUE)

```python
# Example 1: Full entity value
query = "find cm CM12345"
→ Search for VALUE "CM12345" in logs
→ NOT using pattern matching

# Example 2: Short value
query = "find cm x"
→ Search for VALUE "x" in logs  
→ NOT searching for pattern "cm"

# Example 3: IP address
query = "show logs for IP 192.168.1.100"
→ Search for VALUE "192.168.1.100"

# Example 4: Just the value
query = "find CM12345"
→ Detect "CM12345" matches CM pattern
→ Search for this specific VALUE
```

**Key Point:** When a specific value is given, search for that EXACT VALUE, not the pattern.

---

### 2. Aggregation Searches (Search with PATTERN)

```python
# Example 1: All of entity type
query = "find all cms"
→ Use regex PATTERN to extract ALL cm instances
→ Return: ["CM12345", "CM12346", "CM12347", ...]
→ Count: {"CM12345": 13, "CM12346": 8, ...}

# Example 2: List all
query = "list all IP addresses"
→ Use IP pattern to extract ALL IPs
→ Return: ["192.168.1.1", "192.168.1.2", ...]

# Example 3: With filter
query = "find all cms with errors"
→ Extract all CM values using pattern
→ Filter to only CMs that have ERROR severity logs
→ Return filtered list
```

**Key Point:** When "all" is specified, use PATTERN matching to extract all instances.

---

### 3. Relationship Queries (Two-step process)

```python
# Example 1: Find A connected to B value
query = "find rpdname connected to cm x"

Step 1: Search for VALUE "x" (the cm value)
  → Filter logs containing "x"
  
Step 2: Extract TARGET type "rpdname" from filtered logs
  → Use rpdname PATTERN on filtered logs
  → Return: ["RPD001", "RPD002"]

Result: {
  "source": {"type": "cm", "value": "x"},
  "target": {"type": "rpdname", "values": ["RPD001"]},
  "relationship": {"x": ["RPD001"]}
}

# Example 2: Reverse relationship
query = "find all cms connected to rpdname RPD001"

Step 1: Search for VALUE "RPD001"
  → Filter logs containing "RPD001"
  
Step 2: Extract "cm" values from filtered logs
  → Use cm PATTERN on filtered logs
  → Return: ["CM12345", "CM12346"]

Result: {
  "source": {"type": "rpdname", "value": "RPD001"},
  "target": {"type": "cm", "values": ["CM12345", "CM12346"]},
  "relationship": {"RPD001": ["CM12345", "CM12346"]}
}

# Example 3: Complex relationship
query = "find mac address for cm CM12345"

Step 1: Search for VALUE "CM12345"
Step 2: Extract MAC addresses from those logs
Result: {"CM12345": ["00:11:22:33:44:55"]}
```

**Key Point:** Always search for the VALUE first (after "connected to"), then extract the TYPE.

---

### 4. Analysis Queries

```python
# Example 1: Why query
query = "why did cm x fail"
→ Search for VALUE "x"
→ Perform root cause analysis
→ Return: observations, patterns, root causes

# Example 2: What caused
query = "what caused errors for CM12345"
→ Search for VALUE "CM12345"
→ Root cause analysis focused on errors

# Example 3: Investigate
query = "analyze issues with modem x"
→ Search for VALUE "x"
→ Deep analysis with iterations
```

**Key Point:** Extract the specific VALUE to analyze, not the type.

---

## Complete Examples with Expected Flow

### Example 1: "find rpdname connected to cm x"

```
Input: "find rpdname connected to cm x"

1. Query Parsing:
   {
     "query_type": "relationship",
     "primary_entity": {"type": "rpdname", "value": None},
     "secondary_entity": {"type": "cm", "value": "x"},
     "mode": "find"
   }

2. Execution:
   a. Load all logs
   b. Search for VALUE "x" in all text columns
      → Found in 5 log entries
   
   c. Filter logs to those 5 entries:
      timestamp,severity,module,message,entity_id
      10:00:00,INFO,modem_mgr,Cable modem x registered,x
      10:00:15,INFO,network,Processing x on RPD001,x
      10:00:30,DEBUG,provisioning,Package assigned to x,x
      10:01:00,INFO,network,x traffic on RPD001,x
      10:01:15,ERROR,modem_mgr,x connection timeout,x
   
   d. Extract rpdname pattern from these 5 logs
      → Found: "RPD001" (appears in 2 of the 5 logs)

3. Output:
   {
     "query": "find rpdname connected to cm x",
     "source": {"type": "cm", "value": "x"},
     "target": {"type": "rpdname", "values": ["RPD001"]},
     "connection_strength": {
       "RPD001": 2  // appears in 2 logs with x
     },
     "summary": "CM 'x' is connected to RPD001, appearing together in 2 log entries"
   }
```

---

### Example 2: "find all cms with errors"

```
Input: "find all cms with errors"

1. Query Parsing:
   {
     "query_type": "aggregation",
     "primary_entity": {"type": "cm", "value": None},
     "filter_conditions": ["error"],
     "mode": "find"
   }

2. Execution:
   a. Load all logs
   
   b. Extract ALL cm values using pattern
      → Found: {"CM12345": [0,2,3,5], "CM12346": [4,7,9], "CM12347": [11,13]}
   
   c. Apply filter "error":
      - Check CM12345's logs (indices 0,2,3,5) for "error"
        → Log #5 has ERROR severity ✓
      - Check CM12346's logs (indices 4,7,9) for "error"  
        → Log #4 has ERROR severity ✓
      - Check CM12347's logs (indices 11,13) for "error"
        → No errors ✗

3. Output:
   {
     "query": "find all cms with errors",
     "total_cms_found": 3,
     "cms_with_errors": 2,
     "entities": [
       {"value": "CM12345", "error_count": 1, "total_logs": 4},
       {"value": "CM12346", "error_count": 1, "total_logs": 3}
     ],
     "summary": "Found 2 cable modems with errors: CM12345, CM12346"
   }
```

---

### Example 3: "why did cm x fail"

```
Input: "why did cm x fail"

1. Query Parsing:
   {
     "query_type": "analysis",
     "primary_entity": {"type": "cm", "value": "x"},
     "mode": "analyze"
   }

2. Execution:
   a. Load all logs
   b. Search for VALUE "x"
   c. Root cause analysis workflow:
   
   Iteration 1 (FIND mode):
   - Find logs with "x"
   - Extract related entities: ["network", "timeout", "RPD001"]
   - Next entities to explore: ["timeout", "RPD001"]
   
   Iteration 2 (ANALYZE mode):
   - Analyze patterns in timeout logs
   - LLM finds: "Connection timeout pattern at 10:01"
   - Confidence: 0.75 (continue)
   
   Iteration 3 (ANALYZE mode):
   - Analyze RPD001 relationship
   - LLM finds: "RPD001 high load correlates with x failures"
   - Confidence: 0.92 (STOP - high confidence)

3. Output:
   {
     "query": "why did cm x fail",
     "entity": "x",
     "iterations": 3,
     "observations": [
       "Connection timeout occurred at 10:01:15",
       "RPD001 was experiencing high load",
       "Multiple retry attempts failed"
     ],
     "patterns": [
       "Timeout pattern during peak hours",
       "High RPD load correlates with modem failures"
     ],
     "root_causes": [
       "RPD001 overload prevented connection",
       "Insufficient retry backoff period"
     ],
     "confidence": 0.92,
     "summary": "CM 'x' failed due to connection timeout caused by RPD001 overload during peak traffic hours"
   }
```

---

## Decision Matrix

| Query | Has "all"? | Has specific value? | Has "connected to"? | Query Type |
|-------|------------|---------------------|---------------------|------------|
| "find cm CM12345" | No | Yes | No | specific_value |
| "find cm x" | No | Yes | No | specific_value |
| "find all cms" | Yes | No | No | aggregation |
| "list all IPs" | Yes | No | No | aggregation |
| "find rpdname connected to cm x" | No | Yes (x) | Yes | relationship |
| "find all cms connected to RPD001" | Yes | Yes (RPD001) | Yes | relationship + aggregation |
| "why did cm x fail" | No | Yes | No | analysis |
| "find all cms with errors" | Yes | No | No | aggregation + filter |

---

## Search Strategy Summary

```
┌─────────────────────────────────────┐
│  Is specific value given?           │
│  (not "all")                        │
└─────────┬───────────────────────────┘
          │
    ┌─────┴─────┐
    │           │
   YES         NO
    │           │
    ↓           ↓
Search for    Use PATTERN
VALUE         to extract
              all instances
    │           │
    ↓           ↓
"find cm x"   "find all cms"
Search "x"    Extract all CMs
              using regex

┌─────────────────────────────────────┐
│  Is it a relationship query?        │
│  ("connected to", "for", etc.)      │
└─────────┬───────────────────────────┘
          │
         YES
          │
          ↓
    1. Search SOURCE value first
    2. Extract TARGET type from results
    
Example: "find rpdname connected to cm x"
  → Search VALUE "x" (source)
  → Extract TYPE "rpdname" (target)
```

---

## Implementation Checklist

- [ ] QueryParser class with parse_query()
- [ ] Detect query type (specific/aggregation/relationship/analysis)
- [ ] Extract entity type vs entity value correctly
- [ ] Handle "all" keyword for aggregation
- [ ] Handle relationship keywords ("connected to", "for", etc.)
- [ ] Handle analysis keywords ("why", "cause", etc.)
- [ ] Extract filter conditions (errors, timeouts, etc.)
- [ ] Route to correct execution strategy
- [ ] Test all query examples above
- [ ] Handle edge cases (missing values, ambiguous queries)

Ready to implement! 🚀

