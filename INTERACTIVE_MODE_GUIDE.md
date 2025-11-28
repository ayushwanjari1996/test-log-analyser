# Interactive Mode Guide

## Overview

The interactive test script (`test_interactive.py`) now supports two modes:

### 1. **Prod Mode** (Default) 
Clean, user-friendly output with LLM reasoning and search process visualization.

### 2. **Verbose Mode**
Full debug logs with all system information.

---

## Starting the Interactive CLI

```bash
python test_interactive.py
```

On startup, you'll be asked to select a mode:

```
Select Mode:
  1. Prod Mode - Clean output with reasoning (default)
  2. Verbose Mode - Full debug logs

Enter mode (1 or 2):
```

---

## Prod Mode Features

### Clean Output
- ✅ No debug logs cluttering the screen
- ✅ Shows LLM reasoning for decisions
- ✅ Visualizes search path step-by-step
- ✅ Color-coded results (green = success, red = failed)
- ✅ Formatted tables for aggregation results

### Example Output (Relationship Query)

```
============================================================
✓ Query Successful (relationship)

Intent: Find the RPD name associated with a specific CM.
Confidence: 90%
Primary Entity Reasoning: User wants to find rpdname value
Secondary Entity Reasoning: Searching for specific CM MAC address

Search Process:
  • Iterations: 1
  • Path taken:
    Start: cm:10:e1:77:08:63:8a
    Found: rpdname:MAWED06P01

Answer: MAWED06P01
Confidence: 100%

Completed in 5.88s
============================================================
```

### What Prod Mode Shows

#### For Relationship Queries:
- LLM intent and confidence
- Search iterations count
- Step-by-step path (Start → Bridge → Found)
- Bridge entities used with scores
- Final answer with confidence
- Duration

#### For Aggregation Queries:
- Total unique entities found
- Nice table of top results
- Value and occurrence count

#### For Analysis Queries:
- Number of chunks analyzed
- Key observations from LLM
- Patterns detected
- Total logs examined

#### For Trace Queries:
- Timeline of events
- Timestamp, severity, message preview
- Event count

---

## Verbose Mode Features

### Full Debug Output
- ✅ All INFO/DEBUG logs from components
- ✅ Step-by-step execution trace
- ✅ Entity extraction details
- ✅ LLM request/response details
- ✅ Complete JSON result

### Example Output (Verbose)

```
[11/29/25 01:38:34] INFO     Initializing LogAnalyzer for test.csv
                    INFO     Initialized LogProcessor...
                    INFO     Step 1: Parsing query...
                    INFO     Using LLM to parse query...
                    INFO     Generation successful: 509 chars, took 3.82s
                    INFO     === Iteration 1: Direct search ===
                    INFO     Extracted 1 unique 'rpdname' entities
                    INFO     ✓ Found rpdname directly: ['MAWED06P01']

Result:
{
  "query_type": "relationship",
  "source": {...},
  "target": {...},
  ... full JSON ...
}
```

---

## Switching Modes

You can switch modes without restarting by typing `mode`:

```
❯ mode

Switch Mode:
  1. Prod Mode - Clean output
  2. Verbose Mode - Full debug logs
Enter mode (1 or 2):
```

---

## Commands

| Command | Action |
|---------|--------|
| `quit`, `exit`, `q` | Exit the program |
| `mode` | Switch between prod/verbose mode |
| Any other text | Treated as a query |

---

## Example Queries to Try

### Prod Mode is Great For:
```
find rpdname for cm 10:e1:77:08:63:8a
find all cms
why did cm x fail
trace cm x
```

**Why?** You see the reasoning and path clearly without log noise.

### Verbose Mode is Great For:
- Debugging issues
- Understanding system internals
- Seeing LLM request/response details
- Tracking performance bottlenecks

---

## Prod Mode Output Sections

### 1. Header
```
✓ Query Successful (relationship)
```
Shows success status and query type.

### 2. LLM Reasoning
```
Intent: Find the RPD name associated with a specific CM.
Confidence: 90%
Primary Entity Reasoning: ...
Secondary Entity Reasoning: ...
```
Shows what the LLM understood and why.

### 3. Search Process (for relationship queries)
```
Search Process:
  • Iterations: 2
  • Path taken:
    Start: cm:x
    Bridge: ip:172.17.91.21
    Found: rpdname:MAWED06P01

Bridge Entities Used:
  • ip_address:172.17.91.21 (score: 12)
```
Shows exactly how the answer was found.

### 4. Answer
```
Answer: MAWED06P01
Confidence: 90%
```
The final result with confidence.

### 5. Footer
```
Completed in 5.88s
```
Performance metric.

---

## Tips

### Use Prod Mode When:
- Demonstrating the system to others
- You want to understand the reasoning
- You care about the "why" and "how"
- You want clean, professional output

### Use Verbose Mode When:
- Debugging an issue
- Something isn't working as expected
- You need full technical details
- You want to see all system logs

### Switch Modes:
- Start with **prod mode** for normal use
- Switch to **verbose** when something looks wrong
- Switch back to **prod** for the next query

---

## Comparison

| Feature | Prod Mode | Verbose Mode |
|---------|-----------|--------------|
| Debug logs | ❌ Hidden | ✓ Shown |
| LLM reasoning | ✓ Highlighted | ✓ In JSON |
| Search path | ✓ Visual | ✓ In logs |
| Result format | Clean summary | Full JSON |
| Best for | Users/Demos | Debugging |
| Readability | High | Technical |

---

## Example Session

```bash
$ python test_interactive.py

Select Mode:
  1. Prod Mode - Clean output with reasoning (default)
  2. Verbose Mode - Full debug logs

Enter mode (1 or 2): 1
✓ Prod mode enabled - clean output with reasoning

Example queries:
  - find rpdname for cm 10:e1:77:08:63:8a
  - find all cms
  - why did cm CM12345 fail

Type 'quit', 'exit', or 'mode' to change mode

❯ find rpdname for cm 10:e1:77:08:63:8a

============================================================
✓ Query Successful (relationship)
...
Answer: MAWED06P01
============================================================

❯ mode

Switch Mode:
  1. Prod Mode - Clean output
  2. Verbose Mode - Full debug logs
Enter mode (1 or 2): 2
✓ Switched to verbose mode

❯ find all cms

[11/29/25 01:40:00] INFO     Step 1: Parsing query...
...
Result: {...full JSON...}

❯ quit
Goodbye!
```

---

## Customization

Want to modify the output? Edit `print_prod_mode_result()` function in `test_interactive.py`.

You can:
- Change colors
- Add/remove sections
- Modify formatting
- Add new query type displays

---

Enjoy the clean, insightful output! 🚀

