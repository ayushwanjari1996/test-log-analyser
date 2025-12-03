# Engine-as-Planner + LLM-as-Evaluator Design

## Core Concept

**Flip the responsibility:**
- ❌ OLD: LLM plans and decides tools
- ✅ NEW: Engine plans, LLM only evaluates simple questions

---

## Architecture

```
User Query
    ↓
┌─────────────────────────────────────┐
│  LLM Evaluator (Simple Questions)   │
│  - What type of query?               │
│  - Extract: search value, entities   │
│  - Returns: structured data          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Engine Planner (Deterministic)     │
│  - Maps query type → tool sequence  │
│  - Executes tools                    │
│  - Formats answer                    │
└─────────────────────────────────────┘
    ↓
Final Answer
```

---

## What LLM Does (Evaluation Only)

### Single LLM Call - Extract Structured Info:

**Input:** User query
**Output:** JSON with simple facts

```json
{
  "query_type": "search_logs" | "count" | "find_relationship" | "filter",
  "search_value": "MAWED07T01",
  "entity_types": ["cm_mac"],
  "filters": {"severity": ["ERROR"]},
  "needs_count": true,
  "needs_display": false
}
```

**LLM Questions (All Simple):**
1. "Is user asking to count/search/find relationships?"
2. "What value to search for?"
3. "What entity types mentioned?" (with alias mapping)
4. "Any filters requested?"

**Why This Works:**
- ✅ No multi-step reasoning
- ✅ No tool decisions
- ✅ Just information extraction
- ✅ 8B models excel at this

---

## What Engine Does (Planning & Execution)

### Engine Has Predefined Workflows:

```python
WORKFLOWS = {
    "count_all": [
        ("search_logs", {}),
        ("get_log_count", {})
    ],
    
    "search_logs": [
        ("search_logs", {"value": "<search_value>"}),
        ("return_logs", {"max_samples": 5})
    ],
    
    "find_relationship": [
        ("search_logs", {"value": "<search_value>"}),
        ("extract_entities", {"entity_types": "<entity_types>"}),
        ("aggregate_entities", {"entity_types": "<entity_types>"})
    ],
    
    "filter_and_show": [
        ("search_logs", {"value": "<search_value>"}),
        ("filter_by_severity", {"severities": "<severities>"}),
        ("return_logs", {"max_samples": 10})
    ]
}
```

**Engine Steps:**
1. Get evaluation from LLM
2. Select workflow based on query_type
3. Fill in parameters from evaluation
4. Execute tools sequentially
5. Format answer from results

**Why This Works:**
- ✅ Deterministic (no randomness)
- ✅ Debuggable (see exact flow)
- ✅ Reliable (no loops)
- ✅ Fast (no multi-step LLM calls)

---

## Complete Flow Example

### Query: "find all cms connected to rpd MAWED07T01"

**Step 1: LLM Evaluation (1 call)**
```python
evaluation = llm.evaluate(query)
# Returns:
{
  "query_type": "find_relationship",
  "search_value": "MAWED07T01",
  "entity_types": ["cm_mac"],  # LLM mapped 'cms' → 'cm_mac'
  "needs_count": false,
  "needs_display": false
}
```

**Step 2: Engine Selects Workflow**
```python
workflow = WORKFLOWS["find_relationship"]
# [
#   ("search_logs", {"value": "MAWED07T01"}),
#   ("extract_entities", {"entity_types": ["cm_mac"]}),
#   ("aggregate_entities", {"entity_types": ["cm_mac"]})
# ]
```

**Step 3: Engine Executes**
```python
logs = search_logs(value="MAWED07T01")  # → 3 logs
entities = extract_entities(logs, types=["cm_mac"])  # → 2 CMs
summary = aggregate_entities(logs, types=["cm_mac"])  # → counts
```

**Step 4: Engine Formats Answer**
```python
answer = f"Found {len(entities['cm_mac'])} CMs connected to MAWED07T01: {', '.join(entities['cm_mac'])}"
# "Found 2 CMs connected to MAWED07T01: 1c:93:7c:2a:72:c3, 28:7a:ee:c9:66:4a"
```

---

## Components to Implement

### 1. **LLMEvaluator** (`src/core/llm_evaluator.py`)
- Single method: `evaluate(query) → dict`
- Prompt with entity aliases from config
- Returns structured extraction
- ~80 lines

### 2. **EnginePlanner** (`src/core/engine_planner.py`)
- Workflow definitions (count, search, relationship, filter)
- Workflow selection logic
- Parameter substitution
- ~120 lines

### 3. **ExecutionEngine** (`src/core/execution_engine.py`)
- Execute workflow step-by-step
- Auto-inject logs
- Collect results
- Format final answer
- ~100 lines

### 4. **Orchestrator** (`src/core/engine_orchestrator.py`)
- Ties everything together
- evaluate → plan → execute → format
- ~50 lines

---

## LLM Prompt Design

```
You are an information extractor. Extract structured data from user queries.

ENTITY TYPE MAPPINGS (from config):
- 'cm', 'cms', 'cable modem' → use 'cm_mac'
- 'rpd', 'remote phy' → use 'rpdname'
- 'md', 'mac domain' → use 'md_id'

QUERY TYPES:
1. count_all: user wants total log count
2. search_logs: user wants to see logs
3. find_relationship: user asks "find X connected to Y"
4. filter: user wants filtered logs (by severity/time)

Extract these fields:
- query_type: (one of above)
- search_value: what to search for (if any)
- entity_types: which entities to extract (use mappings!)
- filters: {severity: [...], time: [...]}
- needs_count: boolean
- needs_display: boolean

USER QUERY: {query}

Output valid JSON only.
```

**Key:** Prompt has aliases, asks simple questions, returns structured data.

---

## Answer Formatting Templates

```python
ANSWER_TEMPLATES = {
    "count_all": "Found {count} total logs in the system.",
    
    "search_logs": "Found {count} logs matching '{search_value}':\n{log_samples}",
    
    "find_relationship": "Found {count} {entity_type} connected to {search_value}: {entity_list}",
    
    "filter": "Found {count} {filter_type} logs matching '{search_value}':\n{log_samples}"
}
```

Engine fills templates with actual results.

---

## Advantages

### vs ReAct:
- **1 LLM call** (not 10)
- **No loops** (deterministic workflow)
- **No state tracking** (engine remembers)
- **Debuggable** (see workflow)

### vs Pure Rules:
- **Flexible** (LLM handles natural language variations)
- **Entity mapping** (LLM translates user terms)
- **Extensible** (add workflows, not regex)

### With 8B Models:
- **Simple task** (evaluation, not planning)
- **Structured output** (one JSON, not multi-step)
- **Reliable** (extraction is easy)

---

## Workflow Extension (Easy)

**Add new query type:**
```python
# 1. Add workflow
WORKFLOWS["timeline"] = [
    ("search_logs", {"value": "<search_value>"}),
    ("filter_by_time", {"start": "<start>", "end": "<end>"}),
    ("return_logs", {"max_samples": 20})
]

# 2. Add template
ANSWER_TEMPLATES["timeline"] = "Timeline of {count} logs from {start} to {end}:\n{logs}"

# Done! Engine handles rest.
```

---

## Error Handling

**If LLM evaluation fails:**
- Fallback to basic search (search_logs + return_logs)
- User gets something, not failure

**If workflow fails:**
- Execute partial workflow
- Return what was found
- Clear error message

---

## Testing Strategy

### Test 1: LLM Evaluator Alone
```python
evaluate("count all logs")
# Expected: {"query_type": "count_all", ...}

evaluate("find cms connected to rpd X")
# Expected: {"query_type": "find_relationship", "entity_types": ["cm_mac"], ...}
```

### Test 2: Engine Workflows
```python
execute_workflow("count_all", {})
# Expected: "Found 2115 total logs"

execute_workflow("find_relationship", {"search_value": "X", "entity_types": ["cm_mac"]})
# Expected: "Found 2 cm_mac connected to X: ..."
```

### Test 3: End-to-End
```python
orchestrator.analyze("find all cms connected to rpd MAWED07T01")
# Expected: Correct answer with entity values
```

---

## Implementation Order

1. **LLMEvaluator** (evaluate query → JSON)
2. **EnginePlanner** (workflows + selection)
3. **ExecutionEngine** (run workflow)
4. **Orchestrator** (tie together)
5. **Test with 3 queries**
6. **Add more workflows as needed**

---

## Success Criteria

✅ **3/3 queries pass** with correct answers
✅ **No loops** (deterministic)
✅ **1 LLM call** per query
✅ **Entity mapping works** (cm → cm_mac)
✅ **Answer quality** (actual values, not empty)
✅ **Extensible** (easy to add workflows)

---

## Expected Token Usage

- ReAct: ~10K tokens per query (10 iterations)
- Split Agent: ~2K tokens per query (1 planning call)
- **Engine Planner: ~500 tokens per query** (1 evaluation call)

**20x more efficient than ReAct.**

---

## Why This Will Work

1. **LLM task is simple** (just extraction)
2. **Engine is reliable** (deterministic code)
3. **No multi-step reasoning** (single evaluation)
4. **No state tracking** (engine manages state)
5. **8B models can do this** (proven pattern)

---

## Ready to Implement

Total code: ~350 lines across 4 files
Complexity: Medium (clear separation of concerns)
Success probability: **High** (proven approach)

**This is the right architecture.**

