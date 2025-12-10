# AI Log Analyzer - Architecture

## Overview (What It Does)

This tool helps you ask questions about log files in plain English. Think of it like having a smart assistant who reads through thousands of log lines and answers questions like "how many errors are there?" or "which devices had problems?"

The system analyzes CSV log files (can be 10,000+ lines) and uses an AI model (Qwen3 or Llama 3.2) running locally through Ollama to understand your questions and figure out how to answer them.

## How It Works (The Simple Version)

When you ask a question:

1. **You talk** → The AI listens to your question
2. **AI thinks** → "What do I need to find this out?"
3. **AI picks a tool** → "I'll use this tool to look at the logs"
4. **Tool runs** → Searches through logs, extracts data, counts things, etc.
5. **AI looks at results** → "Do I have enough to answer? Or do I need more?"
6. **Repeat** → AI picks the next tool if needed
7. **Final answer** → AI gives you the answer in plain English

This process is called **ReAct** (Reasoning + Acting). The AI reasons about what to do, takes an action, sees the result, then reasons again.

## The Main Parts

### 1. Chat Interface (chat.py)
This is where you interact with the system. You type questions, and it shows you answers. Simple as that.

### 2. The Orchestrator (The Director)
This is the main brain that manages everything. It's called `IterativeReactOrchestrator`.

**What it does each round:**
- **Builds a summary** of what's happened so far (what tools were used, what data we have)
- **Asks the AI** "based on everything we know, what should we do next?"
- **Gets AI's decision** in the form: "Use this tool with these settings"
- **Runs the tool** and gets results
- **Updates the memory** with new information
- **Repeats** until the AI says "I have enough information to answer"

### 3. The AI Model (The Thinker)
The AI (Qwen3 or Llama 3.2) doesn't directly read your logs. Instead, each round it receives:
- Your original question
- A summary of what's been done so far
- A sample of current data (not all 10,000 lines!)
- List of available tools it can use

The AI thinks through this and returns a JSON response like:
```
{
  "reasoning": "I need to count error logs first",
  "action": "filter_logs",
  "params": {"severity": "ERROR"}
}
```

The AI doesn't hold any memory between rounds - it's **stateless**. All memory is kept by the Orchestrator.

### 4. Tools (The Workers)
Tools are like specialized workers that do specific jobs:
- **filter_logs**: Find logs matching certain criteria (like "severity = ERROR")
- **parse_json_field**: Pull out specific values from logs (like MAC addresses)
- **count_values**: Count how many unique values you have
- **count_unique_per_group**: Count things grouped by category
- ... and more

**Smart Auto-Injection:**
When a tool needs log data, the system automatically provides it - the AI doesn't need to specify "give it these logs". The system knows what data each tool needs.

### 5. Context Builder (The Summarizer)
This prevents overwhelming the AI with too much information. 

**The problem:** Log files can have 10,000+ lines. The AI can't read all that each round.

**The solution:** The Context Builder creates compact summaries:
- Shows a few sample logs (just to show structure)
- Lists what fields are available (like "you have fields: timestamp, severity, mac_address")
- Shows counts ("you have 1,523 error logs loaded")
- Tracks what's been extracted ("you already pulled out 45 unique MAC addresses")

For huge result sets (>50 rows), the **SmartSummarizer** creates intelligent summaries instead of showing all data.

### 6. State Tracker (The Memory)
The `ReActState` object keeps track of everything across iterations:
- **Original query**: What you asked
- **Tool history**: What tools were used and what they found
- **Current logs**: The working set of logs (filtered DataFrame)
- **Extracted entities**: Things we've pulled out (like list of MAC addresses)
- **Last result**: The most recent tool output


## The Actual Flow (Step by Step)

Let's say you ask: **"How many unique cable modems had errors?"**

**Round 1:**
- AI receives: Your question + empty history + "No logs loaded"
- AI thinks: "First I need to filter logs to just errors"
- AI decides: `filter_logs(severity="ERROR")`
- Tool runs: Finds 1,523 error logs
- Memory updated: "Currently have 1,523 ERROR logs loaded"

**Round 2:**
- AI receives: Your question + history ("Step 1 loaded 1,523 ERROR logs") + "1,523 logs available with fields: timestamp, severity, mac_address, ..."
- AI thinks: "Now I need to extract MAC addresses from these logs"
- AI decides: `parse_json_field(field_name="mac_address")`
- Tool runs: Extracts 1,845 MAC addresses (some devices appear multiple times)
- Memory updated: "Have list of 1,845 MAC addresses (may have duplicates)"

**Round 3:**
- AI receives: Your question + history + "Have 1,845 MAC address values"
- AI thinks: "Need to count unique ones"
- AI decides: `count_values(values=<auto-injected>)`
- Tool runs: Counts unique values = 47
- Memory updated: "Found 47 unique MAC addresses"

**Round 4:**
- AI receives: Your question + full history + "Found 47 unique MAC addresses"
- AI thinks: "I have the answer now!"
- AI decides: `finalize_answer(answer="There are 47 unique cable modems that had errors")`
- System returns your answer

## Key Design Principles

1. **AI is the brain, tools are the hands**
   - AI decides WHAT to do
   - Tools actually DO it

2. **Stateless AI + Stateful Engine**
   - AI gets a fresh summary each round (doesn't remember previous rounds itself)
   - The Orchestrator remembers everything and provides summaries
   - This prevents the AI from getting confused or hallucinating

3. **Keep context small**
   - Never show the AI all 10,000 logs
   - Always use summaries, samples, and counts
   - This makes the AI faster and more accurate

4. **Step by step, not all at once**
   - Don't try to do everything in one shot
   - Filter → Extract → Count → Answer
   - Each step builds on the previous one

5. **Auto-injection of data**
   - AI doesn't need to know "which logs to use"
   - System automatically provides the current working set
   - Reduces mistakes and makes AI's job easier

6. **Safety limits**
   - Maximum 10 iterations (configurable)
   - If AI gets stuck in a loop, system stops and gives best answer available
   - Tracks consecutive failures

## What Makes This Different from Simple AI Chat?

Regular AI chat: You ask → AI tries to answer from memory → Done
- Problem: AI can't actually read your log files, just guesses

This system: You ask → AI plans steps → Executes tools on real data → Reasons about results → Answers
- AI actually analyzes your real data, doesn't just guess
- Works with huge log files that wouldn't fit in AI context window
- Breaks complex questions into simple steps

## Configuration Files

- **entity_mappings.yaml**: Maps human terms to log field names (e.g., "cable modem" → "mac_address")
- **log_schema.yaml**: Defines what fields exist and how they relate
- **prompts.yaml**: System instructions for the AI
- **react_config.yaml**: Tool definitions and instructions

## Tools Available

The AI can choose from 15 tools (organized by category):

**Basic Log Operations (5 tools):**
1. **grep_logs**: Search logs by pattern or criteria (fast, memory-efficient)
2. **parse_json_field**: Extract values from a specific field in logs
3. **extract_unique**: Remove duplicates from a list of values
4. **count_values**: Count unique values in a list
5. **grep_and_parse**: Combined search + extract in one step (efficient)

**Relationship Tools (1 tool):**
6. **find_relationship_chain**: Discover connections between entities (e.g., CM → RPD → Package)

**Aggregation Tools (2 tools):**
7. **count_unique_per_group**: Count distinct values per category (e.g., errors per device)
8. **count_via_relationship**: Count through entity relationships (e.g., count CMs per RPD)

**Time-Based Tools (2 tools):**
9. **sort_by_time**: Sort logs chronologically
10. **extract_time_range**: Filter logs by time period

**Analysis Tools (3 tools):**
11. **summarize_logs**: Create text summary of log patterns
12. **aggregate_by_field**: Group and aggregate statistics by field
13. **analyze_logs**: Deep LLM-based analysis of log patterns

**Output & Control (2 tools):**
14. **return_logs**: Show sample logs to user
15. **finalize_answer**: Return final answer and stop iteration

The AI learns what each tool does and when to use it from the configuration files (react_config.yaml).