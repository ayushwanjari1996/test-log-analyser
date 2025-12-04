# Iterative ReAct Orchestrator - Quick Start Guide

## Overview

The Iterative ReAct Orchestrator implements a hybrid architecture where:
- **LLM (qwen3)**: Stateless reasoning - decides next tool at each iteration
- **Engine (Python)**: Stateful tracking - manages logs, entities, context
- **Context**: Curated summaries fed to LLM (not full logs)

## Prerequisites

1. **Ollama** running with `qwen3-react` model
2. **Log file** in CSV format (e.g., `test.csv`)
3. **Python 3.8+** with dependencies installed

## Setup

### 1. Create the Model

```bash
# Create qwen3-react model with updated Modelfile
ollama create qwen3-react -f Modelfile.qwen3-react

# Verify it exists
ollama list | grep qwen3-react
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Logs

Ensure your log CSV has these columns:
- `timestamp`
- `severity` (ERROR, WARN, INFO, etc.)
- `message`
- Other fields as needed

## Basic Usage

### Python API

```python
from src.core import IterativeReactOrchestrator

# Initialize orchestrator
orchestrator = IterativeReactOrchestrator(
    log_file="test.csv",
    model="qwen3-react",
    max_iterations=10
)

# Process a query
result = orchestrator.process("count unique CM MACs in error logs")

print(result["answer"])
# Output: "Found 12 unique CM MACs in error logs"

print(f"Iterations: {result['iterations']}")
print(f"Tools used: {result['tools_used']}")
```

### Simple Interface

```python
# Just get the answer string
answer = orchestrator.process_simple("show error logs for MAWED07T01")
print(answer)
```

## Example Queries

### Simple Queries (2-3 iterations)
```python
orchestrator.process_simple("count all logs")
orchestrator.process_simple("show error logs")
```

### Medium Queries (3-5 iterations)
```python
orchestrator.process_simple("count unique CM MACs")
orchestrator.process_simple("find logs for MAWED07T01")
orchestrator.process_simple("show warning logs from last hour")
```

### Complex Queries (5-7 iterations)
```python
orchestrator.process_simple("count unique CM MACs in warning logs")
orchestrator.process_simple("find all CMs connected to RPD MAWED07T01")
orchestrator.process_simple("list all unique RPD names in error logs from last 24 hours")
```

## Architecture Flow

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
```

**Each Iteration:**
1. **Build Context**: Query + last 5 actions + log summary (3 samples)
2. **LLM Decision**: Reasons and picks next tool OR finalizes answer
3. **Execute Tool**: Run tool with auto-injected logs
4. **Update State**: Track results, update current_logs/entities

## Key Features

### 1. Stateless LLM
- Fresh prompt each iteration
- No memory burden
- Clear decision points

### 2. Smart Context Management
- Log summaries (not full logs)
- Last 5 tool actions only
- 3 sample logs shown
- ~1K tokens per iteration

### 3. Auto-Injection
- Logs cached after `search_logs`
- Automatically passed to tools that need them
- No manual log passing required

### 4. Entity Tracking
- Entities extracted once
- Tracked across iterations
- Available for counting/relationships

### 5. Clear Stop Conditions
- LLM calls `finalize_answer` when done
- Max iterations fallback (default: 10)
- Error handling with graceful degradation

## Configuration

### Adjust Max Iterations

```python
orchestrator = IterativeReactOrchestrator(
    log_file="test.csv",
    max_iterations=15  # Increase for complex queries
)
```

### Enable Verbose Logging

```python
orchestrator = IterativeReactOrchestrator(
    log_file="test.csv",
    verbose=True  # See detailed prompts and responses
)
```

### Use Different Model

```python
orchestrator = IterativeReactOrchestrator(
    log_file="test.csv",
    model="qwen3-loganalyzer"  # Or any other Ollama model
)
```

## Testing

### Run Full Test Suite

```bash
python test_iterative_react_full.py
```

This runs:
- 7 main test queries (simple to complex)
- 3 edge case tests
- 1 state management test

Expected success rate: **90%+**

### Quick Smoke Test

```python
from src.core import IterativeReactOrchestrator

orchestrator = IterativeReactOrchestrator(log_file="test.csv")

# Simple test
print(orchestrator.process_simple("count all logs"))

# Medium test
print(orchestrator.process_simple("count unique CM MACs"))
```

## Troubleshooting

### Issue: "Model not found"

```bash
# Check if model exists
ollama list

# Create it
ollama create qwen3-react -f Modelfile.qwen3-react
```

### Issue: "LLM returns invalid JSON"

Check model temperature:
- Should be 0.1-0.3 for JSON output
- Higher temps (>0.5) may break JSON format

### Issue: "Max iterations reached"

Query might be too complex:
- Increase `max_iterations`
- Simplify the query
- Check if tools are working correctly

### Issue: "No logs loaded"

Ensure:
- CSV file exists
- Has correct columns
- Is not empty

## Performance Expectations

| Query Complexity | Iterations | Time | Context Tokens |
|-----------------|------------|------|----------------|
| Simple (count)  | 2-3        | 5-10s | 1-2K |
| Medium (filter) | 3-5        | 10-20s | 3-4K |
| Complex (entity)| 5-7        | 20-30s | 5-6K |

**Total context budget**: ~10K tokens max (at 10 iterations × 1K/iteration)

## Comparison with Other Approaches

| Approach | LLM Burden | Flexibility | Reliability |
|----------|------------|-------------|-------------|
| Old ReAct (llama3.1) | High | High | Low (failed) |
| Single-call Planner | Low | Low | High |
| **Iterative ReAct** | **Medium** | **High** | **High** |

## Advanced Usage

### Custom Tools

Register custom tools before processing:

```python
from src.core.tools.base_tool import Tool, ToolResult

class MyCustomTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Does something custom"
        )
    
    def execute(self, **params):
        # Your logic here
        return ToolResult(success=True, data=result, message="Done")

# Register
orchestrator.registry.register(MyCustomTool())
```

### Access State After Processing

```python
result = orchestrator.process("your query")

# Get detailed summary
summary = result["summary"]
print(f"Iterations: {summary['iterations']}")
print(f"Tools: {summary['tool_sequence']}")
print(f"Duration: {summary['duration_seconds']}s")
```

### Batch Processing

```python
queries = [
    "count all logs",
    "show error logs",
    "count unique CM MACs"
]

for query in queries:
    result = orchestrator.process(query)
    print(f"Q: {query}")
    print(f"A: {result['answer']}\n")
```

## Next Steps

1. **Test with your logs**: Run test suite with your actual log files
2. **Tune parameters**: Adjust max_iterations based on query complexity
3. **Monitor performance**: Track iterations and success rate
4. **Extend tools**: Add domain-specific tools as needed

## Support

For issues or questions:
1. Check logs: `app_logs.txt`
2. Review design: `ITERATIVE_REACT_DESIGN.md`
3. Run tests: `test_iterative_react_full.py`

