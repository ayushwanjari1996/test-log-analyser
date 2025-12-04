# 🚀 Quick Start - Interactive Chat

## 1. First Time Setup

```bash
# Create the qwen3-react model
ollama create qwen3-react -f Modelfile.qwen3-react

# Verify it exists
ollama list
```

## 2. Start Chat

### Option A: Simple (Windows)
```bash
start_chat.bat
```

### Option B: Simple (Linux/Mac)
```bash
chmod +x start_chat.sh
./start_chat.sh
```

### Option C: Direct Python
```bash
python chat.py
```

## 3. Example Usage

```
You: count all logs
Assistant: Total: 500 logs

You: show error logs for MAWED07T01
Assistant: Found 25 error logs for MAWED07T01 ...

You: count unique CM MACs
Assistant: Found 12 unique CM MACs

You: /history
# Shows your last 10 queries

You: /stats
# Shows session statistics

You: /exit
```

## Command Line Options

```bash
# Use hybrid orchestrator instead
python chat.py --orchestrator hybrid

# Different log file
python chat.py --log-file mylog.csv

# Increase max iterations
python chat.py --max-iterations 15

# Enable verbose mode (see all details)
python chat.py --verbose

# Combine options
python chat.py --log-file test.csv --max-iterations 12 --verbose
```

## In-Chat Commands

| Command | What it does |
|---------|-------------|
| `/help` | Show help and query examples |
| `/history` | See your last 10 queries |
| `/stats` | View session statistics |
| `/clear` | Clear the screen |
| `/exit` | Exit chat |

## Example Queries

**Simple:**
- "count all logs"
- "show error logs"
- "how many warning logs?"

**With Filtering:**
- "count logs for MAWED07T01"
- "show errors from last hour"
- "find logs containing 1c:93:7c:2a:72:c3"

**Entity Extraction:**
- "count unique CM MACs"
- "list all RPD names"
- "find all cable modems"

**Complex:**
- "count unique CM MACs in error logs"
- "find all CMs connected to RPD MAWED07T01"
- "list RPDs with warning logs from last 24 hours"

## Troubleshooting

**Problem**: Model not found
```bash
ollama create qwen3-react -f Modelfile.qwen3-react
```

**Problem**: Ollama not running
```bash
ollama serve
```

**Problem**: Log file not found
```bash
python chat.py --log-file /path/to/your/logfile.csv
```

**Problem**: Too many iterations
```bash
python chat.py --max-iterations 20
```

## Tips

1. **Start simple** - Test with "count all logs" first
2. **Use /verbose** - See exactly what the AI is doing
3. **Check /history** - Learn from successful queries
4. **View /stats** - Monitor success rate
5. **Be specific** - Include entity names, timeframes, etc.

## What's Happening Behind the Scenes?

The **Iterative ReAct** orchestrator:
1. Reasons about your query
2. Picks the best tool to use
3. Executes the tool
4. Evaluates the result
5. Repeats until it has the answer
6. Returns the final answer

Average queries take **2-6 iterations** depending on complexity.

Enjoy! 🎉

