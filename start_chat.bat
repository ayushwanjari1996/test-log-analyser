@echo off
REM Windows launcher for AI Log Analyzer Chat

echo ========================================
echo AI Log Analyzer - Interactive Chat
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama might not be running
    echo Please run: ollama serve
    echo.
)

REM Run chat
echo Starting chat...
echo.
python chat.py %*

pause

