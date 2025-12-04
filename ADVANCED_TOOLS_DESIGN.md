# Advanced Tools Design Document

## Current Tool Inventory

### ✅ WORKING (Grep-Based - 5 tools):
1. **grep_logs** - Search CSV for pattern (streaming, memory-efficient)
2. **parse_json_field** - Extract specific field from JSON
3. **extract_unique** - Deduplicate list
4. **count_values** - Count unique in list
5. **grep_and_parse** - Combined grep+parse (shortcut)

### ✅ WORKING (Meta - 2 tools):
6. **return_logs** - Display log samples
7. **finalize_answer** - Stop and return answer

### ⚠️ OLD BUT USEFUL (Keep):
8. **aggregate_entities** - Extracts entities using regex patterns from config (more robust than parse_json_field)

### ❌ OLD (Deprecated - Remove):
- search_logs (loads all - slow)
- filter_by_severity (use grep with severity pattern)
- filter_by_field (use grep)
- get_log_count (just count grep results)
- extract_entities (use parse_json_field)
- count_entities (use count_values)
- normalize_term (not needed with clear field names)
- fuzzy_search (grep is better)
- find_entity_relationships (will be replaced by relationship_chain)

### 🆕 NEED TO BUILD (6 new tools):
1. find_relationship_chain - Tree search for CPE→RPD→MdId
2. sort_by_time - Chronological ordering
3. extract_time_range - Time window filtering
4. summarize_logs - Statistics overview
5. aggregate_by_field - Simple groupby
6. analyze_logs - LLM deep analysis

---

## NEW TOOLS TO IMPLEMENT

## 1. find_relationship_chain (CRITICAL - Tree Search)

### Purpose
Find connection between start entity and target field by traversing log relationships.
Solves the "CPE→RPD→MdId" problem where data is split across multiple log entries.

### How It Works
- BFS (Breadth-First Search) through log entries
- Level 1: Grep start value → extract ALL JSON fields
- Level 2: For each field value found, grep it → extract fields again
- Continue until target field found OR max depth (default 4)
- Returns shortest path with values

### Algorithm
1. Start with initial value (CPE MAC)
2. Grep logs containing this value
3. Parse ALL JSON fields from matching logs
4. Store field→value pairs (RpdName: TestRpd123, CmMacAddress: abc, etc.)
5. For each discovered value: recursively grep (next level)
6. Stop when target field found OR max_depth reached
7. Return path and target value

### Inputs
- start_value: Initial search value (MAC, IP, ID, etc.)
- target_field: Field we're looking for (MdId, RpdName, etc.)
- max_depth: How deep to search (default 4, range 1-5)

### Outputs
- path: List of field:value pairs showing connection
- value: Target field value found
- depth: How many levels traversed
- success: Whether target found

### Example Use Cases
- "Find MdId for CPE 2c:ab:a4:47:1a:d2" → CPE→RPD→MdId (depth 2)
- "Find all related entities for CM" → discovers everything connected
- "Trace CM to infrastructure" → finds RPD, MDID, cluster

### Edge Cases
- Start value not found → return empty
- Target in same log as start → depth 0
- Circular references → track visited to avoid loops
- Multiple paths → return shortest
- Max depth reached → return partial path

---

## 2. summarize_logs (Statistics & Overview)

### Purpose
Generate statistical summary of log collection.
Answers "what's in these logs?" without showing raw data.

### What It Summarizes
- Total count
- Time range (earliest to latest)
- Severity distribution (ERROR: 20, WARN: 50, INFO: 100)
- Top entities (most common CM MACs, RPDs, etc.)
- Event types (top 10 functions/messages)
- Patterns detected (repeated errors, time gaps)

### Inputs
- logs: DataFrame from grep_logs
- detail_level: basic/full (basic = counts only, full = includes patterns)

### Outputs
- summary dict with counts, distributions, top values
- human-readable summary text
- metadata for further analysis

### When To Use
- Before diving into details
- For large result sets (100+ logs)
- To understand scope of issue
- Report generation

---

## 3. aggregate_by_field (Group & Count)

### Purpose
Group logs by field value and count occurrences.
Like SQL: GROUP BY field, COUNT(*)

### How It Works
- Takes grep results or parsed values
- Groups by specified field
- Counts occurrences per unique value
- Sorts by count (descending)
- Returns top N

### Inputs
- logs: DataFrame or list of values
- field_name: Field to group by
- top_n: Return top N results (default 10)

### Outputs
- dict: {value: count, value2: count2, ...}
- sorted by count descending

### Examples
- aggregate_by_field(logs, "CmMacAddress") → {mac1: 50, mac2: 30, ...}
- aggregate_by_field(logs, "Severity") → {ERROR: 20, WARN: 15, ...}
- aggregate_by_field(logs, "RpdName") → {rpd1: 100, rpd2: 50, ...}

### When To Use
- "Which CM has most errors?"
- "Top 10 RPDs by log volume"
- "Distribution of event types"

---

## 4. sort_by_time (Chronological Ordering)

### Purpose
Sort logs by timestamp in chronological order.
Essential for flow analysis and timeline tracing.

### How It Works
- Parse timestamp from logs (multiple formats supported)
- Convert to datetime objects
- Sort ascending or descending
- Return ordered DataFrame

### Inputs
- logs: DataFrame from grep
- order: asc (oldest first) or desc (newest first)
- time_field: Which field has timestamp (default: auto-detect)

### Outputs
- Sorted DataFrame
- Time-ordered log sequence

### When To Use
- Before analyzing flow/sequence
- Timeline reconstruction
- "What happened next?"
- Event correlation

### Supported Formats
- ISO 8601: "2025-11-05T15:30:50.911Z"
- Human: "Nov 5, 2025 @ 15:30:50.911"
- Unix timestamp
- Relative: "5 minutes ago"

---

## 5. extract_time_range (Time Window Filtering)

### Purpose
Get logs between two timestamps.
Narrows analysis to specific time window.

### How It Works
- Parse start and end times
- Filter logs where timestamp in range
- Supports relative times ("now-1h", "now-30m")
- Supports absolute times ("2025-11-05T15:00:00")

### Inputs
- logs: DataFrame
- start_time: Start of window (inclusive)
- end_time: End of window (inclusive)
- time_format: auto-detect or specify

### Outputs
- Filtered DataFrame with logs in time range
- Count of logs in window

### Examples
- extract_time_range(logs, "now-1h", "now") → last hour
- extract_time_range(logs, "15:30:00", "15:35:00") → 5 minute window
- extract_time_range(logs, after_error_time, "now") → everything after error

### When To Use
- "Logs from last 30 minutes"
- "What happened between 15:30 and 15:35?"
- Correlation window analysis
- Before/after event analysis

---

## 6. analyze_logs (SUPER IMPORTANT - LLM Analysis)

### Purpose
Send log sample to LLM for deep analysis.
Detects patterns, correlations, root causes, anomalies.

### How It Works
- Takes log collection (up to 50 logs to fit context)
- Formats for LLM readability
- Sends to LLM with analysis prompt
- LLM identifies: patterns, errors, causes, timeline, relationships
- Returns structured analysis

### What LLM Analyzes
- Error patterns (same error repeating?)
- Temporal patterns (errors clustered in time?)
- Entity correlations (same CM causing issues?)
- Severity progression (INFO→WARN→ERROR?)
- Causal chains (A caused B caused C?)
- Anomalies (unusual values, gaps, spikes)

### Inputs
- logs: DataFrame (auto-samples if >50 logs)
- focus: What to analyze (errors/patterns/timeline/all)
- query_context: Original user question for context

### Outputs
- analysis: Dict with findings
  - patterns_found: List of patterns
  - likely_root_cause: Best guess at cause
  - timeline_analysis: Sequence of events
  - recommendations: What to check next
- summary: Human-readable analysis text

### Example Output
```
Patterns Found:
- Same CM MAC (abc) appears in 20/30 error logs
- Errors clustered in 5-minute window (15:30-15:35)
- All errors reference RPD "TestRpd123"

Likely Root Cause:
- RPD TestRpd123 had connectivity issue at 15:30
- Caused cascading failures for all connected CMs

Timeline:
1. 15:30:00 - RPD disconnect event
2. 15:30:05 - First CM registration failures
3. 15:30-15:35 - 20 CMs failed registration
4. 15:35:00 - RPD reconnected
5. 15:35-15:40 - CMs successfully re-registered

Recommendations:
- Check RPD TestRpd123 infrastructure logs
- Verify network stability during 15:30-15:35
- Review why RPD disconnected
```

### When To Use
- Complex issues (not simple lookups)
- Pattern detection needed
- Root cause analysis
- User asks "why?" or "what happened?"
- Flow analysis
- Correlation detection

### Limitations
- Max 50 logs (context limit)
- Takes longer (LLM call)
- Costs more tokens
- Not for simple queries (use grep instead)

---

## Tool Selection Guide

### Use grep tools WHEN:
- Simple lookup ("find X")
- Counting/aggregating
- Exact value search
- Fast response needed

### Use relationship chain WHEN:
- Data split across multiple logs
- Need to traverse connections
- "Find Y from X" where Y not in same log

### Use time tools WHEN:
- Need chronological order
- Specific time window
- Before/after analysis
- Timeline reconstruction

### Use analyze WHEN:
- Pattern detection needed
- Root cause analysis
- "Why" questions
- Complex correlations
- User confused about what's happening

---

## Tool Interaction Patterns

### Pattern 1: Grep → Analyze
```
Step 1: grep_logs("error") → 30 error logs
Step 2: analyze_logs(those_30_logs) → finds pattern
Step 3: finalize_answer(pattern_explanation)
```

### Pattern 2: Relationship → Summarize
```
Step 1: find_relationship_chain(CPE, MdId) → discovers path
Step 2: grep all entities in path
Step 3: summarize_logs(all_results) → overview
```

### Pattern 3: Time Window → Analyze
```
Step 1: grep_logs(entity)
Step 2: sort_by_time(asc)
Step 3: extract_time_range(error_time-5min, error_time+5min)
Step 4: analyze_logs(window) → what happened around error
```

### Pattern 4: Aggregate → Drill Down
```
Step 1: grep_logs(severity=ERROR)
Step 2: aggregate_by_field(CmMacAddress)
Step 3: grep_logs(top_cm_mac) → investigate worst offender
Step 4: analyze_logs(that_cm_logs)
```

---

## Implementation Priority

### Phase 1 (Critical - Do First):
1. find_relationship_chain - solves CPE→MdId problem
2. sort_by_time - needed for flow analysis
3. extract_time_range - needed for temporal queries

### Phase 2 (Important - Do Next):
4. summarize_logs - useful for large result sets
5. aggregate_by_field - common query pattern

### Phase 3 (Advanced - Do Last):
6. analyze_logs - most complex, needs LLM integration

---

## Performance Considerations

### find_relationship_chain:
- Expensive: Multiple grep operations (one per level)
- Mitigate: Cache visited values, limit depth
- Worst case: 4 levels × 10 values = 40 grep operations
- Best case: Target in same log = 1 grep

### analyze_logs:
- Expensive: LLM call (3-10 seconds)
- Mitigate: Sample large datasets, use only when needed
- Token cost: ~1K-2K tokens per analysis

### Time tools:
- Cheap: In-memory operations on already-grepped data
- Fast: <100ms for sorting/filtering

### Aggregate:
- Cheap: Simple groupby operation
- Fast: <50ms even for 1000 logs

---

## Error Handling

### Relationship chain not found:
- Return partial path with what was found
- Suggest alternative fields to try
- Don't fail silently

### Time parsing fails:
- Try multiple formats
- Fall back to string comparison
- Return error with detected format

### Analyze gets too many logs:
- Auto-sample to 50 logs
- Prioritize: errors > warnings > info
- Time-based sampling (spread across time range)

### Empty results:
- All tools handle gracefully
- Return empty with clear message
- Suggest next steps

---

## Testing Strategy

### Unit Tests:
- Each tool tested independently
- Mock grep results
- Verify output format

### Integration Tests:
- Chain tools together
- Use real test.csv
- Verify end-to-end flow

### Real-World Tests:
- CPE→MdId relationship
- Time-based flow analysis
- Error pattern detection
- Complex multi-hop relationships

---

## Final Tool Set (14 tools total)

### Grep Tools (5):
1. grep_logs
2. parse_json_field
3. extract_unique
4. count_values
5. grep_and_parse

### Relationship (2):
6. find_relationship_chain (NEW - implement)
7. aggregate_entities (OLD - keep, uses regex patterns)

### Time Tools (2):
8. sort_by_time (NEW - implement)
9. extract_time_range (NEW - implement)

### Analysis Tools (3):
10. summarize_logs (NEW - implement)
11. aggregate_by_field (NEW - implement)
12. analyze_logs (NEW - implement)

### Meta (2):
13. return_logs
14. finalize_answer

This covers:
- ✓ Simple lookups (grep tools)
- ✓ Relationships (chain + aggregate_entities)
- ✓ Time analysis (time tools)
- ✓ Statistics (aggregate/summarize)
- ✓ Deep analysis (analyze tool)
- ✓ Everything user needs!

---

## Implementation Status

**Done (7):** grep_logs, parse_json_field, extract_unique, count_values, grep_and_parse, return_logs, finalize_answer

**Keep From Old (1):** aggregate_entities

**To Build (6):** find_relationship_chain, sort_by_time, extract_time_range, summarize_logs, aggregate_by_field, analyze_logs

