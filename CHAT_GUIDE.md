# Interactive Chat Guide

## Quick Start

### Windows
```bash
# Double-click or run:
start_chat.bat
```

### Linux/Mac
```bash
chmod +x start_chat.sh
./start_chat.sh
```

### Direct Python
```bash
python chat.py
```

## Usage Examples

### Basic Usage (Default: Iterative ReAct)
```bash
python chat.py
```

### Use Hybrid Planner Instead
```bash
python chat.py --orchestrator hybrid
```

### Specify Different Log File
```bash
python chat.py --log-file my_logs.csv
```

### Use Different Model
```bash
python chat.py --model qwen3-loganalyzer
```

### Adjust Max Iterations
```bash
python chat.py --max-iterations 15
```

### Enable Verbose Mode (See all details)
```bash
python chat.py --verbose
```

### Combined Options
```bash
python chat.py --log-file test.csv --model qwen3-react --max-iterations 12 --verbose
```

## In-Chat Commands

Once in chat, you can use these commands:

| Command | Description |
|---------|-------------|
| `/help` | Show help and examples |
| `/history` | View your last 10 queries |
| `/stats` | Show session statistics |
| `/clear` | Clear the screen |
| `/exit` or `/quit` | Exit the chat |

## Example Chat Session

```
🤖 AI Log Analyzer - Interactive Chat

Orchestrator: Iterative ReAct
Log File: test.csv
Max Iterations: 10

Ready to analyze! 🚀

You: count all logs
Thinking...