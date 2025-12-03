# Phase 4: Analysis Orchestrator - Quick Overview

## What Phase 4 Does

Phase 4 is the **"brain"** of the log analyzer. It coordinates all components built in Phases 1-3 to perform intelligent, iterative log analysis.

## 3 Main Workflows

### 1. 🔍 Entity Lookup (Simple Search)
**What it does:** Find all occurrences of a specific entity

```
User: "Find CM12345"
     ↓
Load logs → Filter for CM12345 → Chunk → LLM Analysis → Results
```

**Output:**
- Total occurrences: 13
- Related entities: [modem_mgr, provisioning, network]
- Summary: "CM12345 appears 13 times, mostly in modem management logs..."

---

### 2. 🔬 Root Cause Analysis (Deep Dive)
**What it does:** Iteratively explore to find why something happened

```
User: "Why did CM12345 fail?"
     ↓
Find CM12345 → FIND mode (discover related) → Extract: modem_mgr, network
     ↓                                                    ↓
Analyze modem_mgr → ANALYZE mode (find patterns) → Extract: timeout, retry
     ↓                                                       ↓
Analyze timeout → ANALYZE mode (root cause) → Confidence: 0.9 → STOP
```

**Output:**
- Observations: ["High latency", "3 retry attempts", "CMTS unreachable"]
- Patterns: ["Timeouts occur at 10:00 daily", "Network congestion"]
- Root Cause: "CMTS connection timeout during peak usage"
- Confidence: 90%

**Key Feature:** Iterative exploration (up to 5 iterations)
- Iteration 1: FIND mode - discover entities
- Iteration 2: ANALYZE mode - find patterns
- Iteration 3+: Continue based on LLM suggestions
- Stops when: high confidence OR no new entities OR max iterations

---

### 3. 📊 Flow Trace (Timeline Analysis)
**What it does:** Trace the sequence of events for an entity

```
User: "Trace flow for CM12345"
     ↓
Load logs → Sort by time → Chunk by time windows → TRACE mode → Timeline
```

**Output:**
- Timeline:
  - 10:00:00 - Registration started
  - 10:00:15 - Provisioning completed
  - 10:00:30 - Package assigned
  - 10:01:00 - Connection timeout
  - 10:01:15 - Retry attempt 1
- Flow Steps: [Register → Provision → Activate → **FAIL** → Retry]
- Bottleneck: "Connection timeout at activation step"

---

## How Iterative Exploration Works

```
┌─────────────────────────────────────────────────┐
│  Initial Query: "Why did CM12345 fail?"         │
└───────────────────┬─────────────────────────────┘
                    ↓
        ┌───────────────────────┐
        │  Iteration 1: FIND    │
        │  Entity: CM12345      │
        └──────────┬────────────┘
                   ↓
        Found: [modem_mgr, network, timeout]
                   ↓
        ┌───────────────────────┐
        │  Iteration 2: ANALYZE │
        │  Entity: modem_mgr    │
        └──────────┬────────────┘
                   ↓
        Pattern: "Timeout at CMTS connection"
        Confidence: 0.7 (continue)
                   ↓
        ┌───────────────────────┐
        │  Iteration 3: ANALYZE │
        │  Entity: CMTS         │
        └──────────┬────────────┘
                   ↓
        Root Cause: "CMTS overload during peak"
        Confidence: 0.92 (STOP)
```

## Stop Conditions

The analyzer stops iterating when:
1. ✅ **Max iterations reached** (default: 5)
2. ✅ **High confidence** (>0.9 in ANALYZE mode)
3. ✅ **No new entities** (nothing new to explore)
4. ✅ **Queue empty** (all entities processed)

## Components Involved

```
LogAnalyzer (orchestrator)
    ↓
    ├─ LogProcessor (load/filter logs)
    ├─ LogChunker (split into manageable pieces)
    ├─ EntityManager (track entity queue)
    ├─ OllamaClient (LLM communication)
    ├─ PromptBuilder (create prompts)
    └─ ResponseParser (parse LLM responses)
```

## Key Classes to Build

### 1. LogAnalyzer (main class)
```python
analyzer = LogAnalyzer("logs.csv")

# Simple entity lookup
result = analyzer.entity_lookup("CM12345")

# Deep root cause analysis
result = analyzer.root_cause_analysis("Why did CM12345 fail?")

# Timeline trace
result = analyzer.flow_trace("CM12345")
```

### 2. AnalysisState (track progress)
```python
state = AnalysisState()
state.iteration = 2
state.explored_entities = {"CM12345", "modem_mgr"}
state.current_mode = "analyze"
```

### 3. AnalyzerConfig (settings)
```python
config = AnalyzerConfig()
config.max_iterations = 5
config.confidence_threshold = 0.9
config.chunk_size_tokens = 3000
```

## Mode Selection Logic

```python
Iteration 0 → FIND mode    # Always discover entities first
Iteration 1 → ANALYZE mode # Then look for patterns
Iteration 2+ → LLM decides # Trust the AI's suggestion

Special cases:
- If confidence > 0.8 → Switch to ANALYZE
- If no new entities → ANALYZE
- If LLM suggests → Follow suggestion
```

## Example Output Formats

### Entity Lookup Result
```json
{
  "entity": "CM12345",
  "total_occurrences": 13,
  "entities_found": ["CM12345"],
  "related_entities": ["modem_mgr", "provisioning", "network"],
  "summary": "CM12345 appears in 13 log entries across modem management..."
}
```

### Root Cause Analysis Result
```json
{
  "query": "Why did CM12345 fail?",
  "iterations": 3,
  "observations": [
    "High latency detected",
    "3 retry attempts failed",
    "CMTS connection timeout"
  ],
  "patterns": [
    "Timeouts occur during peak hours",
    "Network congestion pattern"
  ],
  "correlations": [
    "CM12345 errors correlate with CMTS load"
  ],
  "root_causes": [
    "CMTS overload during peak usage",
    "Insufficient retry backoff"
  ],
  "confidence": 0.92,
  "summary": "The modem failed due to CMTS connection timeouts..."
}
```

### Flow Trace Result
```json
{
  "entity": "CM12345",
  "timeline": [
    {"time": "10:00:00", "event": "Registration", "status": "success"},
    {"time": "10:00:30", "event": "Activation", "status": "failed"}
  ],
  "flow_steps": ["Register", "Provision", "Activate", "Fail"],
  "bottlenecks": ["Connection timeout at activation"],
  "summary": "CM12345 successfully registered but failed at activation..."
}
```

## Performance Estimates

| Operation | Time | LLM Calls |
|-----------|------|-----------|
| Entity Lookup (50 logs) | ~10s | 2-3 |
| Root Cause (5 iterations) | ~30s | 8-10 |
| Flow Trace (100 logs) | ~15s | 3-5 |

**Note:** Time depends on:
- Number of log entries
- Chunk sizes
- LLM response time (~3-4s per call)
- Number of iterations

## Error Handling

| Error Type | Handling |
|------------|----------|
| LLM timeout | Retry (3x), then skip chunk |
| Invalid JSON | Use default structure, continue |
| Entity not found | Return empty, suggest alternatives |
| Log file error | Exit with clear message |
| Infinite loop | Max iteration limit prevents |

## Testing Approach

1. **Unit Tests:** Test each workflow independently
2. **Integration Tests:** Test with real logs end-to-end
3. **Edge Cases:** Empty logs, non-existent entities, max iterations
4. **Performance:** Verify <30s for typical analysis

## Implementation Checklist

- [ ] Create LogAnalyzer class skeleton
- [ ] Implement entity_lookup workflow
- [ ] Implement flow_trace workflow
- [ ] Implement root_cause_analysis workflow
- [ ] Add iterative exploration logic
- [ ] Add entity queue management
- [ ] Add mode selection logic
- [ ] Add stop conditions
- [ ] Add result aggregation
- [ ] Add summary generation
- [ ] Create AnalysisState class
- [ ] Create AnalyzerConfig class
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Test with sample logs
- [ ] Performance optimization

## Success Criteria

✅ **Functional:**
- All 3 workflows work correctly
- Iterative exploration doesn't loop infinitely
- Results are accurate and actionable

✅ **Performance:**
- <30 seconds for typical analysis
- <5 iterations for root cause
- Graceful handling of errors

✅ **Quality:**
- Clear, readable summaries
- High confidence scores (>0.8)
- Useful entity suggestions

## What's Next (Phase 5)

After Phase 4 is complete, Phase 5 will add:
- 🖥️ **CLI Interface** - User-friendly commands
- 🎨 **Pretty Output** - Formatted tables and colors
- 💾 **Export Options** - JSON, CSV, HTML reports
- ⚙️ **Config Files** - User preferences
- 📊 **Progress Bars** - Real-time feedback

**Phase 4 = The Engine**  
**Phase 5 = The Interface**

Ready to implement when you are! 🚀

