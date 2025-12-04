#!/bin/bash
# Linux/Mac launcher for AI Log Analyzer Chat

echo "========================================"
echo "AI Log Analyzer - Interactive Chat"
echo "========================================"
echo

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python not found!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "WARNING: Ollama might not be running"
    echo "Please run: ollama serve"
    echo
fi

# Run chat
echo "Starting chat..."
echo
python3 chat.py "$@"

