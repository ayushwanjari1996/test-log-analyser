# Cleanup & Implementation Plan
## Single-Step LLM Planning Architecture

---

## Part 1: Cleanup

### Files to DELETE (Old Designs)

**Orchestrators (replace with ONE new one):**
```
src/core/react_orchestrator.py      # Old ReAct loop
src/core/smart_orchestrator.py      # Failed smart design
src/core/split_orchestrator.py      # Split agent attempt
src/core/workflow_orchestrator.py   # Old workflow
src/core/planning_agent.py          # Part of split design
src/core/decision_agent.py          # Old decision logic
```

**Prompts (replace with ONE simple prompt):**
```
src/llm/dynamic_prompts.py    # Over-engineered
src/llm/react_prompts.py      # ReAct specific
src/llm/prompts.py            # Old prompts
```

**Old Test Files:**
```
test_phase1_react.py
test_phase2_react.py
test_smart_architecture.py
test_split_orchestrator.py
test_qwen3_think_mode.py
test_qwen3_complex.py
test_qwen3_operations.py
test_orchestration_progressive.py
test_query2_only.py
test_single_query.py
test_workflow_simple.py
test_return_logs_tool.py
test_llm_query_parser.py
test_query_parser_manual.py
```

**Old Documentation (archive to docs/archive/):**
```
PHASE1_COMPLETE.md, PHASE2_*.md, PHASE3_*.md, PHASE4_*.md
BUGFIX_*.md, BUG_FIX_SUMMARY.md
ENGINE_PLANNER_DESIGN.md
STATE_DRIVEN_DESIGN.md
SPLIT_ORCHESTRATOR_APPROACH.md
SMART_ARCHITECTURE_IMPLEMENTATION.md
HLD_SMART_ARCHITECTURE.md
OPTION_A_COMPLETE.md
(keep only: README.md, HYBRID_DYNAMIC_DESIGN.md)
```

### Files to KEEP

**Core Infrastructure (working, tested):**
```
src/core/log_processor.py       # Log file handling
src/core/entity_manager.py      # Entity extraction
src/core/tool_registry.py       # Tool management
src/core/react_state.py         # Can reuse for state (rename later)
src/core/chunker.py             # Log chunking
src/core/analyzer.py            # Keep if useful
```

**Tools (all working):**
```
src/core/tools/base_tool.py
src/core/tools/search_tools.py
src/core/tools/entity_tools.py
src/core/tools/smart_search_tools.py
src/core/tools/output_tools.py
src/core/tools/meta_tools.py    # Keep finalize_answer
```

**LLM:**
```
src/llm/ollama_client.py        # Working, keep
src/llm/response_parser.py      # JSON parsing
```

**Config:**
```
config/entity_mappings.yaml     # Entity aliases & patterns
config/log_schema.yaml          # Log format config
```

**Tests to Keep:**
```
test_individual_tools.py        # Tool unit tests
test_qwen3_planner.py           # Update for new design
tests/                          # Unit tests folder
```

---

## Part 2: New Architecture

### Component Overview

```
┌────────────────────────────────────────────────────────────┐
│                      USER QUERY                            │
│              "find all cms for rpd MAWED07T01"             │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│              1. QueryNormalizer (Python)                   │
│         "cms" → "cm_mac", "rpd" → "rpdname"                │
│         Extract search_value from query                    │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│              2. QwenPlanner (Single LLM Call)              │
│         Input: normalized query                            │
│         Output: {"operations": [...], "params": {...}}     │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│              3. PlanExecutor (Python)                      │
│         Step 1: search_logs(search_value) [HARDCODED]      │
│         Step 2+: Execute LLM's operations in order         │
│         Auto-inject logs between steps                     │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│              4. AnswerFormatter (Python)                   │
│         Format results based on what was found             │
└────────────────────────────────────────────────────────────┘
```

### New Files to Create

```
src/core/query_normalizer.py    # Step 1: Normalize query
src/core/plan_executor.py       # Step 3: Execute plan
src/core/answer_formatter.py    # Step 4: Format answer
src/llm/qwen_planner.py         # Step 2: LLM planning
src/core/hybrid_orchestrator.py # Main orchestrator
```

---

## Part 3: Implementation Details

### 3.1 QueryNormalizer

**File:** `src/core/query_normalizer.py`

```python
class QueryNormalizer:
    """Normalize user terms to extractable entity types."""
    
    def __init__(self, config):
        self.config = config
        self.entity_map = {
            'cm': 'cm_mac', 'cms': 'cm_mac', 'cable modem': 'cm_mac',
            'rpd': 'rpdname', 'rpds': 'rpdname',
            'cpe': 'cpe_mac', 'cpes': 'cpe_mac',
            'modem_id': 'md_id', 'mdid': 'md_id',
        }
    
    def normalize(self, query: str) -> dict:
        """
        Returns:
            {
                "normalized_query": "find all cm_mac for rpdname MAWED07T01",
                "search_value": "MAWED07T01",  # extracted value to search
                "detected_entities": ["cm_mac", "rpdname"]
            }
        """
```

### 3.2 QwenPlanner

**File:** `src/llm/qwen_planner.py`

```python
class QwenPlanner:
    """Single LLM call to generate execution plan."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.model = "qwen3-loganalyzer"  # Custom model
    
    def create_plan(self, normalized_query: str) -> dict:
        """
        Input: "find all cm_mac for rpdname MAWED07T01"
        Output: {
            "operations": ["filter_by_severity", "extract_entities"],
            "params": {"severities": ["ERROR"], "entity_types": ["cm_mac"]}
        }
        
        NOTE: search_logs is NOT included - hardcoded by executor
        """
```

### 3.3 PlanExecutor

**File:** `src/core/plan_executor.py`

```python
class PlanExecutor:
    """Execute plan with hardcoded search_logs first."""
    
    def __init__(self, tool_registry, log_processor):
        self.registry = tool_registry
        self.log_processor = log_processor
        self.cached_logs = None
    
    def execute(self, search_value: str, plan: dict) -> dict:
        """
        1. ALWAYS run search_logs first (hardcoded)
        2. Run each operation from plan
        3. Auto-inject logs between steps
        4. Return all results
        """
        results = {}
        
        # Step 1: HARDCODED - always search first
        search_tool = self.registry.get("search_logs")
        search_result = search_tool.execute(value=search_value)
        self.cached_logs = search_result.data
        results["search_logs"] = search_result
        
        # Step 2+: Execute plan operations
        for op in plan.get("operations", []):
            tool = self.registry.get(op)
            params = self._get_params(op, plan.get("params", {}))
            params["logs"] = self.cached_logs  # Auto-inject
            
            result = tool.execute(**params)
            results[op] = result
            
            # Update cached logs if filter
            if op.startswith("filter_") and result.success:
                self.cached_logs = result.data
        
        return results
```

### 3.4 AnswerFormatter

**File:** `src/core/answer_formatter.py`

```python
class AnswerFormatter:
    """Format execution results into human-readable answer."""
    
    def format(self, results: dict, original_query: str) -> str:
        """
        Priority:
        1. If extract_entities → show entities
        2. If count_entities → show count
        3. If return_logs → show log summary
        4. If get_log_count → show total
        5. Fallback → show search result count
        """
```

### 3.5 HybridOrchestrator

**File:** `src/core/hybrid_orchestrator.py`

```python
class HybridOrchestrator:
    """Main orchestrator - coordinates all components."""
    
    def __init__(self, config, log_file: str):
        self.normalizer = QueryNormalizer(config)
        self.planner = QwenPlanner(OllamaClient())
        self.executor = PlanExecutor(tool_registry, log_processor)
        self.formatter = AnswerFormatter()
    
    def process(self, query: str) -> str:
        # Step 1: Normalize
        normalized = self.normalizer.normalize(query)
        
        # Step 2: Plan (single LLM call)
        plan = self.planner.create_plan(normalized["normalized_query"])
        
        # Step 3: Execute
        results = self.executor.execute(
            search_value=normalized["search_value"],
            plan=plan
        )
        
        # Step 4: Format
        answer = self.formatter.format(results, query)
        
        return answer
```

---

## Part 4: Updated Modelfile

**File:** `Modelfile.qwen3-loganalyzer` (simplified)

```
FROM qwen3:8b

PARAMETER temperature 0.1
PARAMETER num_ctx 4096

SYSTEM """
You are a log analysis planner. Given a query, output a JSON plan.

IMPORTANT: Do NOT include search_logs - it runs automatically first.

AVAILABLE OPERATIONS (use after logs are loaded):
- filter_by_time: Filter by time. Params: start_time, end_time
- filter_by_severity: Filter by level. Params: severities (array: ["ERROR"])
- filter_by_field: Filter by field. Params: field, value
- extract_entities: Get entity values. Params: entity_types (array: ["cm_mac"])
- count_entities: Count unique. Params: entity_type (string)
- aggregate_entities: List unique. Params: entity_types (array)
- get_log_count: Count logs. No params
- return_logs: Show samples. Params: max_samples (int)

VALID ENTITY TYPES: cm_mac, rpdname, md_id, cpe_mac, sf_id, ip_address

OUTPUT FORMAT:
{"operations": ["op1", "op2"], "params": {"key": "value"}}

EXAMPLES:

Query: "count all logs"
{"operations": ["get_log_count"], "params": {}}

Query: "find cm_mac for rpdname MAWED07T01"
{"operations": ["extract_entities"], "params": {"entity_types": ["cm_mac"]}}

Query: "show error logs"
{"operations": ["filter_by_severity", "return_logs"], "params": {"severities": ["ERROR"]}}

Query: "how many unique rpdname"
{"operations": ["count_entities"], "params": {"entity_type": "rpdname"}}

Query: "analyze errors for X"
{"operations": ["filter_by_severity", "extract_entities"], "params": {"severities": ["ERROR", "WARN"], "entity_types": ["cm_mac", "md_id"]}}
"""
```

---

## Part 5: Implementation Order

### Phase 1: Cleanup (30 min)
1. [ ] Create `docs/archive/` folder
2. [ ] Move old .md files to archive
3. [ ] Delete old orchestrators
4. [ ] Delete old prompt files
5. [ ] Delete old test files

### Phase 2: Core Components (1 hour)
1. [ ] Create `query_normalizer.py`
2. [ ] Create `plan_executor.py`
3. [ ] Create `answer_formatter.py`
4. [ ] Create `qwen_planner.py`
5. [ ] Create `hybrid_orchestrator.py`

### Phase 3: Modelfile Update (15 min)
1. [ ] Update `Modelfile.qwen3-loganalyzer`
2. [ ] Rebuild model: `ollama create qwen3-loganalyzer -f Modelfile.qwen3-loganalyzer`

### Phase 4: Testing (30 min)
1. [ ] Update `test_qwen3_planner.py` for new format
2. [ ] Create `test_hybrid_orchestrator.py`
3. [ ] Run end-to-end tests

### Phase 5: CLI Integration (15 min)
1. [ ] Update `src/cli/main.py` to use HybridOrchestrator

---

## Part 6: Test Queries

| # | Query | Expected Operations |
|---|-------|---------------------|
| 1 | count all logs | get_log_count |
| 2 | find cm_mac for rpd X | extract_entities |
| 3 | show error logs | filter_by_severity, return_logs |
| 4 | logs from last hour | filter_by_time, return_logs |
| 5 | how many unique rpdname | count_entities |
| 6 | list all md_id values | aggregate_entities |
| 7 | analyze issues for X | filter_by_severity, extract_entities |
| 8 | show warning and error logs | filter_by_severity, return_logs |
| 9 | trace registration for X | return_logs |
| 10 | find cm_mac in errors for X | filter_by_severity, extract_entities |

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Orchestrators | 5 files | 1 file |
| Prompt files | 4 files | 0 (in Modelfile) |
| LLM calls/query | 3-10 | 1 |
| Code complexity | High | Low |
| Success rate | ~40% | Target 85%+ |

---

## Approval Checklist

- [ ] Cleanup plan approved
- [ ] New architecture approved
- [ ] Modelfile changes approved
- [ ] Ready to implement

**Please review and confirm to proceed.**

