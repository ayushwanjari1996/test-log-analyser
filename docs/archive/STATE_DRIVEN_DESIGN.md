# State-Driven Orchestration Design

## Honest Assessment First

**Will this work better than ReAct?** 
- **Maybe.** It's simpler, but still iterative.
- Risk: Could hit similar loops if LLM can't track state well.
- Success depends on: Can llama3.1 8B evaluate state reliably?

**Why it might work:**
- Evaluation ("what do we need?") easier than planning ("call this tool")
- State is explicit (not hidden in conversation)
- Engine controls execution (no hallucinated tools)

**Why it might fail:**
- Still multi-step (3-5 iterations)
- LLM must remember what's done
- Stopping condition still LLM's job

---

## Core Concept

**Each iteration, LLM answers ONE question:**
> "Given current state, what information do we still need?"

**Not:**
- ❌ Which tool to call
- ❌ What parameters to pass

**But:**
- ✅ "Need to find logs"
- ✅ "Need to filter by time"
- ✅ "Need entity extraction"
- ✅ "Have everything, ready to answer"

**Engine translates needs → tool calls**

---

## State Object

```python
class AnalysisState:
    # Data collected so far
    logs: DataFrame | None = None
    entities: dict | None = None
    counts: dict | None = None
    relationships: dict | None = None
    
    # What's been done
    searched: bool = False
    filtered_time: bool = False
    filtered_severity: bool = False
    extracted_entities: bool = False
    
    # User requirements (from initial evaluation)
    search_value: str | None = None
    entity_types: list | None = None
    time_filter: dict | None = None
    severity_filter: list | None = None
    
    # Progress tracking
    iteration: int = 0
    max_iterations: int = 5
```

**State is explicit, visible to LLM each iteration.**

---

## Architecture

```
User Query
    ↓
┌──────────────────────────────────────┐
│ Initial Evaluation (LLM - 1 call)    │
│ Extract: search_value, entity_types, │
│          filters, what user wants    │
└──────────────────────────────────────┘
    ↓
    Start Iteration Loop (max 5)
    ↓
┌──────────────────────────────────────┐
│ State Evaluator (LLM)                │
│ Input: Current state + Requirements  │
│ Question: "What info do we need next?"│
│ Output: next_need                    │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ Need-to-Tool Mapper (Engine)         │
│ Maps: need → tool call               │
│ Deterministic, no LLM                │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ Tool Execution (Engine)              │
│ Execute tool, update state           │
└──────────────────────────────────────┘
    ↓
    Repeat until: next_need = "done"
    ↓
┌──────────────────────────────────────┐
│ Answer Formatter (Engine)            │
│ Format answer from state             │
└──────────────────────────────────────┘
    ↓
Final Answer
```

---

## Need-to-Tool Mapping (Deterministic)

```python
NEED_TO_TOOL = {
    "search": ("search_logs", lambda state: {"value": state.search_value}),
    
    "filter_time": ("filter_by_time", lambda state: {
        "start": state.time_filter["start"],
        "end": state.time_filter["end"]
    }),
    
    "filter_severity": ("filter_by_severity", lambda state: {
        "severities": state.severity_filter
    }),
    
    "extract_entities": ("extract_entities", lambda state: {
        "entity_types": state.entity_types
    }),
    
    "count_entities": ("count_entities", lambda state: {
        "entity_type": state.entity_types[0]
    }),
    
    "find_relationships": ("find_entity_relationships", lambda state: {
        "target_value": state.search_value,
        "related_types": state.entity_types
    }),
    
    "display_logs": ("return_logs", lambda state: {
        "max_samples": 10
    }),
    
    "done": (None, None)
}
```

**Engine maps need → tool automatically. No LLM involved.**

---

## LLM Prompts

### Initial Evaluation (Once)
```
Extract requirements from user query.

Entity mappings:
{entity_aliases_from_config}

USER QUERY: {query}

Extract as JSON:
{
  "search_value": "what to search for",
  "entity_types": ["cm_mac", ...],
  "time_filter": {"start": "...", "end": "..."},
  "severity_filter": ["ERROR"],
  "user_wants": "see_logs" | "count" | "find_entities" | "relationships"
}
```

### State Evaluation (Each Iteration)
```
Current state:
- Logs: {state.logs is not None}
- Entities: {state.entities}
- Filtered: {state.filtered_time or state.filtered_severity}

Requirements:
- Search: {state.search_value}
- Need entities: {state.entity_types}
- Need filters: {state.time_filter or state.severity_filter}
- User wants: {state.user_wants}

What information do we still need?

Options:
- "search" - need to find logs first
- "filter_time" - need time filtering
- "filter_severity" - need severity filtering
- "extract_entities" - need to extract entities
- "find_relationships" - need entity relationships
- "count_entities" - need entity counts
- "display_logs" - need to format logs
- "done" - have everything, ready to answer

Output: {"next_need": "..."}
```

**Simple multiple-choice question for LLM.**

---

## Complete Example

### Query: "show me error logs for CM X from last hour"

**Step 1: Initial Evaluation**
```json
{
  "search_value": "X",
  "entity_types": null,
  "time_filter": {"start": "now-1h", "end": "now"},
  "severity_filter": ["ERROR"],
  "user_wants": "see_logs"
}
```

**Iteration 1:**
- State: {logs: null, searched: false}
- LLM: "next_need: search"
- Engine: search_logs(value="X") → 20 logs
- Update: {logs: 20, searched: true}

**Iteration 2:**
- State: {logs: 20, searched: true, time_filter: {...}}
- LLM: "next_need: filter_time"
- Engine: filter_by_time(start="now-1h") → 8 logs
- Update: {logs: 8, filtered_time: true}

**Iteration 3:**
- State: {logs: 8, filtered_time: true, severity_filter: ["ERROR"]}
- LLM: "next_need: filter_severity"
- Engine: filter_by_severity(["ERROR"]) → 3 logs
- Update: {logs: 3, filtered_severity: true}

**Iteration 4:**
- State: {logs: 3, filtered, user_wants: "see_logs"}
- LLM: "next_need: display_logs"
- Engine: return_logs(max_samples=10) → formatted
- Update: {display_ready: true}

**Iteration 5:**
- State: {logs: 3, display_ready: true}
- LLM: "next_need: done"
- Engine: Format answer → "Found 3 error logs for X from last hour: ..."

**Total: 5 LLM calls (1 initial + 4 state evaluations)**

---

## Advantages Over ReAct

| Aspect | ReAct | State-Driven |
|--------|-------|--------------|
| LLM Task | Plan + Execute + JSON | Evaluate state (multiple choice) |
| Tool Selection | LLM picks tool | Engine maps need → tool |
| Parameters | LLM constructs | Engine fills from state |
| Stopping | LLM decides vaguely | Explicit "done" option |
| State Tracking | Implicit in conversation | Explicit state object |
| Loop Risk | High (LLM forgets) | Lower (state visible) |

---

## Risk Analysis

### What Could Still Fail:

1. **LLM Can't Track State**
   - Mitigation: State is explicit in prompt each time
   - But: 8B models might still forget

2. **LLM Never Says "done"**
   - Mitigation: Max 5 iterations hard limit
   - Fallback: Format answer from partial state

3. **Wrong Need Selection**
   - Example: Says "search" when already searched
   - Mitigation: Engine checks if need already fulfilled
   - Skip redundant operations

4. **Entity Mapping Still Broken**
   - LLM might still use 'cm' instead of 'cm_mac'
   - Mitigation: Initial evaluation has aliases
   - But: Not guaranteed to work

### Honest Probability of Success:

- **60-70%** - Better than ReAct (10%), worse than pure rules (100%)
- Depends heavily on whether llama3.1 8B can do multiple-choice state evaluation

---

## Implementation Strategy

### Phase 1: Test State Evaluation Alone
```python
state = AnalysisState(logs=None, search_value="X", user_wants="see_logs")
need = llm.evaluate_state(state)
# Can LLM consistently return "search"?
```

### Phase 2: Test Need-to-Tool Mapping
```python
need = "search"
tool, params = map_need_to_tool(need, state)
# Verify correct tool + params
```

### Phase 3: Test Full Loop
```python
result = orchestrator.analyze("show error logs for X")
# Does it complete? Is answer correct?
```

**If Phase 1 fails, abort. LLM can't do this.**

---

## Alternative: Hybrid Dynamic Workflow

**If state-driven still fails, try this:**

**Step 1: LLM extracts ALL requirements (1 call)**
```json
{
  "operations": ["search", "filter_time", "filter_severity", "display"],
  "search_value": "X",
  "filters": {...}
}
```

**Step 2: Engine builds workflow dynamically**
```python
workflow = []
for op in operations:
    workflow.append(map_need_to_tool(op, requirements))
```

**Step 3: Execute workflow deterministically**

**Advantage:**
- Only 1 LLM call (like split agent)
- But LLM specifies operations, not full answer
- Engine builds sequence dynamically (not hardcoded)

**This handles any query without hardcoded patterns.**

---

## Comparison of All Approaches

| Approach | LLM Calls | Flexibility | Reliability | Token Cost |
|----------|-----------|-------------|-------------|------------|
| ReAct | 10 | High | 10% | 10K |
| Split Agent | 1 | Medium | 30% | 2K |
| Hardcoded Workflows | 1 | Low | 90% | 500 |
| **State-Driven** | 5 | High | 60%? | 3K |
| **Hybrid Dynamic** | 1 | High | 70%? | 1K |

---

## Recommendation

### Test in this order:

**1. Hybrid Dynamic (Recommended First)**
- 1 LLM call to list operations
- Engine builds workflow from operations
- Handles any query
- Only 1 LLM decision point

**2. State-Driven (If #1 fails)**
- Multiple LLM calls but simpler task
- Fallback if operation listing doesn't work

**3. Rule-Based (Last Resort)**
- No LLM complexity
- Will definitely work
- Limited flexibility

---

## Hybrid Dynamic Workflow Design

### LLM Extraction:
```json
{
  "operations": ["search", "filter_severity", "extract_entities"],
  "params": {
    "search_value": "X",
    "severity": ["ERROR"],
    "entity_types": ["cm_mac"]
  }
}
```

### Engine Workflow Builder:
```python
def build_workflow(operations, params):
    workflow = []
    for op in operations:
        tool, param_builder = NEED_TO_TOOL[op]
        tool_params = param_builder(params)
        workflow.append((tool, tool_params))
    return workflow
```

### Execute:
```python
for tool, params in workflow:
    result = execute_tool(tool, params)
    update_state(result)
```

**This is simpler than state-driven, more flexible than hardcoded.**

---

## My Honest Opinion

**State-driven might work, but risky.**
- Still 5 LLM calls
- Still depends on LLM tracking state
- Could hit similar issues as ReAct

**Hybrid dynamic workflow is safer:**
- 1 LLM call (list operations)
- No state tracking needed
- Engine does the rest
- Handles any query

**I'd recommend: Try hybrid dynamic first.**

---

## Next Steps

**Your choice:**

A) Implement state-driven (riskier, more LLM involvement)
B) Implement hybrid dynamic (safer, 1 LLM call)
C) Go pure rule-based (safest, limited flexibility)

**Which approach do you want to try?**

