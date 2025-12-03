# Hybrid Dynamic Workflow Design
## Qwen3 Single-Call Planning with Query Normalization

---

## Architecture Overview

```
User Query: "find all cms connected to rpd X"
                    |
                    v
+------------------------------------------+
|     STEP 1: QUERY NORMALIZER (Python)    |
|   "cms" -> "cm_mac", "rpd" -> "rpdname"  |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|     STEP 2: LLM PLANNER (Qwen3)          |
|   Single call -> JSON plan               |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|     STEP 3: ENGINE EXECUTOR (Python)     |
|   Execute operations, auto-inject logs   |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|     STEP 4: ANSWER FORMATTER (Python)    |
|   Format results for user                |
+------------------------------------------+
```

---

## Step 1: Query Normalizer

### Purpose
Convert user terms to extractable entity types BEFORE LLM sees query.

### Normalization Rules (from entity_mappings.yaml)

| User Says          | Normalized To   |
|--------------------|-----------------|
| cm, cable modem    | cm_mac          |
| rpd, RPD           | rpdname         |
| cpe, CPE           | cpe_mac         |
| modem_id, MdId     | md_id           |
| error, issue       | ERROR (severity)|

### Implementation

```python
class QueryNormalizer:
    def __init__(self, config):
        self.aliases = config.entity_mappings.get('aliases', {})
        
    def normalize(self, query: str) -> str:
        normalized = query.lower()
        
        replacements = {
            'cm': 'cm_mac', 'cms': 'cm_mac', 'cable modem': 'cm_mac',
            'rpd': 'rpdname', 'cpe': 'cpe_mac', 'modem_id': 'md_id',
        }
        
        for term, canonical in replacements.items():
            normalized = re.sub(rf'\b{term}\b', canonical, normalized, flags=re.I)
        
        return normalized
```

### Examples

| Original Query                    | Normalized Query                        |
|-----------------------------------|-----------------------------------------|
| find all cms connected to rpd X   | find all cm_mac connected to rpdname X  |
| show errors for cm Y              | show ERROR for cm_mac Y                 |
| count rpds in the logs            | count rpdname in the logs               |

---

## Step 2: LLM Planner (Qwen3)

### Single Call Output

```json
{
  "operations": ["search_logs", "extract_entities"],
  "params": {
    "search_value": "MAWED07T01",
    "entity_types": ["cm_mac"]
  }
}
```

---

## Available Tools

| Tool | Purpose | Required Params |
|------|---------|-----------------|
| search_logs | Load logs (MUST BE FIRST) | search_value |
| filter_by_time | Filter by time range | start_time, end_time |
| filter_by_severity | Filter by level | severities (array) |
| get_log_count | Count logs | - |
| extract_entities | Extract values | entity_types (array) |
| count_entities | Count unique | entity_type (string) |
| find_relationships | Find related | target_value, related_types |
| return_logs | Display samples | max_samples |

**RULE:** search_logs must ALWAYS be first operation.

---

## Query Type Patterns

### Pattern 1: Simple Search
Query: "show logs for X"
```json
{"operations": ["search_logs", "return_logs"], "params": {"search_value": "X"}}
```

### Pattern 2: Count Query
Query: "count all logs"
```json
{"operations": ["search_logs", "get_log_count"], "params": {}}
```

### Pattern 3: Entity Extraction
Query: "find all cm_mac for X"
```json
{"operations": ["search_logs", "extract_entities"], "params": {"search_value": "X", "entity_types": ["cm_mac"]}}
```

### Pattern 4: Severity Filter
Query: "show errors for X"
```json
{"operations": ["search_logs", "filter_by_severity", "return_logs"], "params": {"search_value": "X", "severities": ["ERROR"]}}
```

### Pattern 5: Time Filter
Query: "logs from last hour"
```json
{"operations": ["search_logs", "filter_by_time", "return_logs"], "params": {"start_time": "now-1h"}}
```

### Pattern 6: Error Analysis
Query: "analyze issues with X"
```json
{"operations": ["search_logs", "filter_by_severity", "extract_entities"], "params": {"search_value": "X", "severities": ["ERROR", "WARN"], "entity_types": ["cm_mac", "rpdname"]}}
```

### Pattern 7: Flow Tracing
Query: "trace registration for X"
```json
{"operations": ["search_logs", "return_logs"], "params": {"search_value": "X", "max_samples": 20}}
```

### Pattern 8: Entity Counting
Query: "how many unique cm_mac"
```json
{"operations": ["search_logs", "count_entities"], "params": {"entity_type": "cm_mac"}}
```

### Pattern 9: Relationship Discovery
Query: "find cm_mac connected to rpdname X"
```json
{"operations": ["search_logs", "extract_entities"], "params": {"search_value": "X", "entity_types": ["cm_mac"]}}
```

### Pattern 10: Combined Analysis
Query: "show error cm_mac for X in last hour"
```json
{"operations": ["search_logs", "filter_by_time", "filter_by_severity", "extract_entities"], "params": {"search_value": "X", "start_time": "now-1h", "severities": ["ERROR"], "entity_types": ["cm_mac"]}}
```

---

## Updated Modelfile System Prompt

```
SYSTEM """
You are a log analysis planner. Output JSON plan for queries.

CRITICAL: search_logs MUST always be FIRST operation.

TOOLS:
- search_logs: Load logs. Params: search_value (string, empty for all)
- filter_by_time: Filter time. Params: start_time, end_time
- filter_by_severity: Filter level. Params: severities (array)
- get_log_count: Count logs. No params
- extract_entities: Get values. Params: entity_types (array)
- count_entities: Count unique. Params: entity_type (string)
- return_logs: Show samples. Params: max_samples (int)

VALID ENTITY TYPES: cm_mac, rpdname, md_id, cpe_mac, sf_id, ip_address

OUTPUT: {"operations": [...], "params": {...}}

EXAMPLES:

"count all logs"
{"operations": ["search_logs", "get_log_count"], "params": {}}

"find cm_mac connected to rpdname MAWED07T01"
{"operations": ["search_logs", "extract_entities"], "params": {"search_value": "MAWED07T01", "entity_types": ["cm_mac"]}}

"show error logs for X"
{"operations": ["search_logs", "filter_by_severity", "return_logs"], "params": {"search_value": "X", "severities": ["ERROR"]}}

"analyze issues with X"
{"operations": ["search_logs", "filter_by_severity", "extract_entities"], "params": {"search_value": "X", "severities": ["ERROR", "WARN"], "entity_types": ["cm_mac", "md_id"]}}
"""
```

---

## Step 3: Engine Executor

```python
class PlanExecutor:
    def __init__(self, registry):
        self.registry = registry
        self.cached_logs = None
        
    def execute_plan(self, plan: dict) -> dict:
        operations = plan.get("operations", [])
        params = plan.get("params", {})
        results = {}
        
        for op in operations:
            tool = self.registry.get(op)
            tool_params = self._get_params(op, params)
            
            # Auto-inject logs
            if self.cached_logs is not None and op != "search_logs":
                tool_params["logs"] = self.cached_logs
            
            result = tool.execute(**tool_params)
            results[op] = result
            
            # Cache from search_logs
            if op == "search_logs" and result.success:
                self.cached_logs = result.data
        
        return results
```

---

## Step 4: Answer Formatter

```python
class AnswerFormatter:
    def format(self, results: dict) -> str:
        if "extract_entities" in results:
            r = results["extract_entities"]
            if r.success and r.data:
                return self._format_entities(r.data)
        
        if "get_log_count" in results:
            return f"Total: {results['get_log_count'].data['count']} logs"
        
        if "return_logs" in results:
            return results["return_logs"].message
        
        if "search_logs" in results:
            return f"Found {len(results['search_logs'].data)} logs"
        
        return "No results"
```

---

## Complete Example

### Query: "find all cms connected to rpd MAWED07T01"

**Step 1 - Normalize:**
```
Input:  "find all cms connected to rpd MAWED07T01"
Output: "find all cm_mac connected to rpdname MAWED07T01"
```

**Step 2 - LLM Plan:**
```json
{"operations": ["search_logs", "extract_entities"], "params": {"search_value": "MAWED07T01", "entity_types": ["cm_mac"]}}
```

**Step 3 - Execute:**
```
search_logs("MAWED07T01") -> 3 logs
extract_entities(logs, ["cm_mac"]) -> ["1c:93:7c:2a:72:c3", "28:7a:ee:c9:66:4a"]
```

**Step 4 - Format:**
```
"Found 2 cm_mac: 1c:93:7c:2a:72:c3, 28:7a:ee:c9:66:4a"
```

---

## Error Handling

| Issue | Solution |
|-------|----------|
| Invalid JSON from LLM | Return "Could not parse. Rephrase query." |
| Missing search_logs | Auto-insert at start |
| No logs found | Return "No logs found for X" |
| Unknown tool | Skip with warning |

---

## Implementation Files

```
src/
  core/
    query_normalizer.py   # Step 1
    plan_executor.py      # Step 3
    answer_formatter.py   # Step 4
  llm/
    qwen_planner.py       # Step 2
  orchestrator/
    hybrid_orchestrator.py
```

---

## Comparison: Old vs New

| Aspect | Old ReAct | New Hybrid |
|--------|-----------|------------|
| LLM calls | 3-10 | 1 |
| Latency | 15-60s | 3-8s |
| JSON errors | Frequent | Rare |
| Entity mapping | LLM guesses | Pre-normalized |
| Success rate | ~40% | ~85% |

---

## Testing Plan

1. Test QueryNormalizer (unit tests)
2. Test LLM plans via ollama chat
3. Test PlanExecutor (unit tests)
4. Test end-to-end with 10 queries

---

## Next Steps

1. [ ] Implement QueryNormalizer
2. [ ] Update Modelfile
3. [ ] Build HybridOrchestrator
4. [ ] Test with real queries

