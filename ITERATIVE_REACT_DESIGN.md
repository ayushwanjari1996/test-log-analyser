# Iterative ReAct Architecture with Smart Context Management

## Overview

A hybrid iterative ReAct system where:
- **LLM**: Reasons and selects next tool (stateless, fresh prompt each iteration)
- **Engine**: Tracks state, executes tools, manages context (stateful)
- **Context**: Curated summaries (logs + history) fed to LLM each iteration

## Core Principles

1. **Stateless LLM**: Each iteration gets fresh, curated context (no memory burden)
2. **Stateful Engine**: Tracks tool history, logs, results in Python
3. **Smart Context**: Feed log summaries (not full logs) to avoid overflow
4. **Clear Decisions**: LLM returns JSON with next tool OR finalize_answer

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Iteration Loop                         │
│                                                         │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐    │
│  │  Build   │─────▶│   LLM    │─────▶│ Execute  │    │
│  │ Context  │      │ Decision │      │   Tool   │    │
│  └──────────┘      └──────────┘      └──────────┘    │
│       ▲                                      │         │
│       │              ┌──────────┐            │         │
│       └──────────────│  Update  │◀───────────┘         │
│                      │  State   │                      │
│                      └──────────┘                      │
└─────────────────────────────────────────────────────────┘

State Store:
- tool_history: [{"tool": "search_logs", "result": "150 logs"}]
- current_logs: DataFrame
- log_summary: "150 logs, 25 errors, top entities: ..."
- iteration_count: 3
```

## State Manager (Python)

```python
class ReactState:
    def __init__(self):
        self.tool_history = []      # [{tool, params, result, summary}]
        self.current_logs = None    # DataFrame
        self.entities_extracted = {}
        self.iteration = 0
        self.max_iterations = 10
        
    def add_tool_call(self, tool, params, result_df, summary):
        self.tool_history.append({
            "iteration": self.iteration,
            "tool": tool,
            "params": params,
            "result_summary": summary,
            "timestamp": datetime.now()
        })
        if result_df is not None:
            self.current_logs = result_df
    
    def get_log_summary(self, max_samples=3):
        """Generate compact log summary for LLM"""
        if self.current_logs is None or len(self.current_logs) == 0:
            return "No logs available"
        
        total = len(self.current_logs)
        sample = self.current_logs.head(max_samples)
        
        return {
            "total_count": total,
            "sample_logs": sample.to_dict('records'),
            "severity_distribution": self._get_severity_dist(),
            "time_range": self._get_time_range()
        }
    
    def get_context_for_llm(self, query):
        """Build curated context for LLM prompt"""
        return {
            "query": query,
            "iteration": self.iteration,
            "tool_history": self.tool_history[-5:],  # Last 5 tools
            "current_state": self.get_log_summary(),
            "available_tools": self._get_remaining_tools()
        }
```

## Context Building Strategy

### Iteration 1 (Bootstrap)
```json
{
  "query": "Count unique CM MACs in warning logs",
  "iteration": 1,
  "instruction": "Start by loading logs. Return first action."
}
```

### Iteration 2+ (With Context)
```json
{
  "query": "Count unique CM MACs in warning logs",
  "iteration": 2,
  
  "previous_actions": [
    {
      "step": 1,
      "tool": "search_logs",
      "params": {"value": ""},
      "result": "Loaded 150 logs"
    }
  ],
  
  "current_state": {
    "logs": {
      "total": 150,
      "sample": [
        {"severity": "ERROR", "message": "CM disconnected..."},
        {"severity": "WARN", "message": "High latency..."},
        {"severity": "INFO", "message": "Registration..."}
      ],
      "severities": {"ERROR": 40, "WARN": 60, "INFO": 50}
    }
  },
  
  "instruction": "Based on above, what's the NEXT action? Return tool JSON OR finalize_answer if done."
}
```

## LLM Prompt Template

```
You are analyzing logs. Decide the NEXT action based on context.

QUERY: {query}
ITERATION: {iteration}/{max_iterations}

PREVIOUS ACTIONS:
{for each in tool_history:}
  Step {step}: {tool}({params}) → {result}
{endfor}

CURRENT STATE:
  Total logs: {log_count}
  Sample logs:
    1. {sample_1}
    2. {sample_2}
    3. {sample_3}
  
  Severity: {severity_dist}
  Entities extracted: {entities}

DECISION POINT:
- Have you gathered enough data to answer the query?
  YES → Call finalize_answer with the answer
  NO → Call the next tool needed

Return JSON:
{
  "reasoning": "why this action",
  "action": "tool_name",
  "params": {...}
}

OR if done:
{
  "reasoning": "task complete because...",
  "action": "finalize_answer",
  "params": {"answer": "final answer here"}
}
```

## Iteration Flow

```python
class IterativeReactOrchestrator:
    def __init__(self, log_file):
        self.state = ReactState()
        self.llm = OllamaClient(model="qwen3-react")
        self.tools = ToolRegistry()
        self.query = None
    
    def process_query(self, query):
        self.query = query
        
        while self.state.iteration < self.state.max_iterations:
            self.state.iteration += 1
            
            # 1. Build context
            context = self._build_llm_context()
            
            # 2. LLM decides next action
            decision = self._get_llm_decision(context)
            
            # 3. Check if done
            if decision["action"] == "finalize_answer":
                return decision["params"]["answer"]
            
            # 4. Execute tool
            result = self._execute_tool(
                decision["action"],
                decision["params"]
            )
            
            # 5. Update state
            summary = self._generate_result_summary(result)
            self.state.add_tool_call(
                tool=decision["action"],
                params=decision["params"],
                result_df=result.data,
                summary=summary
            )
        
        # Max iterations reached
        return self._fallback_answer()
    
    def _build_llm_context(self):
        """Curate context: query + history + log summary"""
        ctx = {
            "query": self.query,
            "iteration": self.state.iteration,
            "max_iterations": self.state.max_iterations
        }
        
        # Add history (last 5 actions)
        ctx["history"] = [
            f"{h['tool']}({h['params']}) → {h['result_summary']}"
            for h in self.state.tool_history[-5:]
        ]
        
        # Add current state
        log_summary = self.state.get_log_summary(max_samples=3)
        ctx["current_state"] = log_summary
        
        # Add extracted entities
        ctx["entities"] = self.state.entities_extracted
        
        return ctx
    
    def _get_llm_decision(self, context):
        """Call LLM with context, parse JSON response"""
        prompt = self._format_prompt(context)
        response = self.llm.generate(prompt)
        
        # Extract JSON (handle <think> tags)
        json_str = self._extract_json(response)
        decision = json.loads(json_str)
        
        return decision
    
    def _execute_tool(self, tool_name, params):
        """Execute tool with auto-injection"""
        tool = self.tools.get(tool_name)
        
        # Auto-inject logs if needed
        if tool.requires_logs and self.state.current_logs is not None:
            params["logs"] = self.state.current_logs
        
        result = tool.execute(**params)
        
        # Track entities if extracted
        if tool_name == "extract_entities" and result.success:
            self._update_entities(result.data)
        
        return result
    
    def _generate_result_summary(self, result):
        """Create compact summary of tool result"""
        if not result.success:
            return f"Error: {result.error}"
        
        if isinstance(result.data, pd.DataFrame):
            return f"{len(result.data)} logs"
        elif isinstance(result.data, dict):
            return f"{result.data}"
        else:
            return str(result.data)[:100]
```

## Stop Conditions

LLM calls `finalize_answer` when:
1. **Query answered**: "Found 12 unique CM MACs"
2. **No results**: "No error logs found for MAWED07T01"
3. **Sufficient data**: "Extracted entities: 15 cm_mac, ready to answer"

Engine forces stop when:
1. Max iterations reached (default: 10)
2. Error in tool execution
3. LLM returns invalid JSON 3 times in a row

## Example Scenarios

### Scenario 1: Simple Query
**Query**: "Count all logs"

**Iteration 1:**
- Context: query only
- LLM: `{"action": "search_logs", "params": {"value": ""}}`
- Result: 150 logs loaded

**Iteration 2:**
- Context: query + "search_logs → 150 logs"
- LLM: `{"action": "get_log_count", "params": {}}`
- Result: 150

**Iteration 3:**
- Context: query + history + "150 logs"
- LLM: `{"action": "finalize_answer", "params": {"answer": "Total: 150 logs"}}`
- ✓ Done in 3 steps

### Scenario 2: Complex Query
**Query**: "Count unique CM MACs in error logs from last hour"

**Iteration 1:**
- LLM: `search_logs("")` → 200 logs

**Iteration 2:**
- Context: 200 logs, sample shows mixed severities
- LLM: `filter_by_severity(["ERROR"])` → 50 logs

**Iteration 3:**
- Context: 50 error logs, sample shows CM MACs present
- LLM: `filter_by_time("now-1h", "now")` → 30 logs

**Iteration 4:**
- Context: 30 logs from last hour
- LLM: `extract_entities(["cm_mac"])` → 25 entities

**Iteration 5:**
- Context: 25 cm_mac entities extracted
- LLM: `count_entities("cm_mac")` → 18 unique

**Iteration 6:**
- Context: Count = 18
- LLM: `finalize_answer("18 unique CM MACs in error logs from last hour")`
- ✓ Done

## Implementation Plan

### Phase 1: Core Components (2 hours)
1. `ReactState` class - state tracking
2. `ContextBuilder` - curate LLM context
3. `ResultSummarizer` - compact tool results

### Phase 2: Orchestrator (2 hours)
1. `IterativeReactOrchestrator` - main loop
2. Tool execution with auto-injection
3. Entity tracking

### Phase 3: Prompt Engineering (1 hour)
1. Update `Modelfile.qwen3-react`
2. Add explicit stop conditions
3. Test prompt with 5 queries

### Phase 4: Testing (1 hour)
1. Simple queries (1-2 steps)
2. Complex queries (4-6 steps)
3. Edge cases (no results, errors)

## Advantages Over Previous Approaches

| Approach | LLM Burden | Flexibility | Reliability |
|----------|------------|-------------|-------------|
| Old ReAct (llama3.1) | High (track state) | High | Low (failed) |
| Single-call Planner | Low (one call) | Low (fixed plan) | High |
| **New Iterative ReAct** | **Medium (curated)** | **High (adaptive)** | **High (qwen3)** |

## Key Improvements

1. **Stateless LLM**: No memory burden, fresh context each time
2. **Smart Summaries**: Log samples, not full logs (3-5 examples)
3. **Explicit History**: "You did X, got Y, now what?"
4. **Stop Clarity**: "Answer ready? Call finalize_answer"
5. **Context Limits**: Last 5 tools + 3 log samples = ~1K tokens/iteration

## Expected Performance

- **Simple queries**: 2-3 iterations (search → count → finalize)
- **Complex queries**: 4-6 iterations (search → filter → filter → extract → count → finalize)
- **Max context**: ~1K tokens/iteration × 10 iterations = 10K tokens total
- **Success rate**: 90%+ (based on qwen3's JSON reliability)

## Files to Create/Modify

### New Files:
1. `src/core/react_state.py` - State tracking
2. `src/core/iterative_react_orchestrator.py` - Main orchestrator
3. `src/core/context_builder.py` - LLM context generation
4. `test_iterative_react_full.py` - Full integration test

### Modified Files:
1. `Modelfile.qwen3-react` - Better stop instructions
2. `src/core/__init__.py` - Export new orchestrator

## Success Criteria

✓ LLM makes correct tool decisions 90%+ of time
✓ LLM calls finalize_answer when appropriate
✓ No context overflow (< 4K tokens/prompt)
✓ 7/7 test queries pass
✓ Adaptive behavior (adjusts based on results)

