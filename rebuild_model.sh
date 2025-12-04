#!/bin/bash
# Rebuild qwen3-react model with updated Modelfile

echo "========================================"
echo "Rebuilding qwen3-react model"
echo "========================================"
echo

echo "Removing old model..."
ollama rm qwen3-react 2>/dev/null

echo
echo "Creating new model from Modelfile.qwen3-react..."
ollama create qwen3-react -f Modelfile.qwen3-react

if [ $? -ne 0 ]; then
    echo
    echo "[ERROR] Failed to create model!"
    exit 1
fi

echo
echo "========================================"
echo "SUCCESS! Model rebuilt."
echo "========================================"
echo
echo "Changes:"
echo "- Temperature: 0.1 (was 0.3)"
echo "- Max tokens: 2048 (was 512)"
echo "- System prompt: Emphasizes BRIEF thinking"
echo "- Examples: Show concise thinking"
echo
echo "Try it now:"
echo "  python chat.py"
echo

