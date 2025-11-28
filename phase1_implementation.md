# Phase 1: Foundation Setup - Detailed Implementation Plan

## Overview
**Duration**: 3 Days  
**Goal**: Establish solid project foundation with core utilities, configuration system, and basic project structure.

## Day 1: Project Structure & Dependencies

### Task 1.1: Create Project Directory Structure
**Time**: 30 minutes

```bash
mkdir log-analyzer
cd log-analyzer

# Create main source directories
mkdir -p src/{cli,core,llm,utils}
mkdir -p config tests docs

# Create __init__.py files
touch src/__init__.py
touch src/cli/__init__.py
touch src/core/__init__.py
touch src/llm/__init__.py
touch src/utils/__init__.py
```

### Task 1.2: Setup Dependencies & Virtual Environment
**Time**: 45 minutes

#### Create `requirements.txt`:
```txt
# CLI Framework
click>=8.1.0

# HTTP Client for Ollama
requests>=2.31.0

# Configuration Management
pyyaml>=6.0

# Data Processing
pandas>=2.0.0

# CLI Formatting & Progress
rich>=13.0.0

# Development Dependencies
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0

# Optional: Type hints
types-requests>=2.31.0
types-PyYAML>=6.0.0
```

#### Create `setup.py`:
```python
from setuptools import setup, find_packages

setup(
    name="log-analyzer",
    version="0.1.0",
    description="AI-powered log analysis tool using Ollama",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.1.0",
        "requests>=2.31.0",
        "pyyaml>=6.0",
        "pandas>=2.0.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "log-analyzer=cli.main:main",
        ],
    },
    python_requires=">=3.8",
)
```

#### Setup Virtual Environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Task 1.3: Basic Project Files
**Time**: 30 minutes

#### Create `README.md`:
```markdown
# AI Log Analyzer

Python CLI tool for intelligent log analysis using Ollama-hosted Llama 3.2.

## Quick Start
```bash
pip install -e .
log-analyzer --help
```

## Features
- Entity lookup and extraction
- Root cause analysis
- Flow tracing
- Pattern detection

## Requirements
- Python 3.8+
- Ollama with Llama 3.2 model
```

#### Create `.gitignore`:
```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Config overrides
config/local_*
```

## Day 2: Configuration System

### Task 2.1: Configuration Schema Design
**Time**: 1 hour

#### Create `config/entity_mappings.yaml`:
```yaml
# Entity alias mappings - user terms to normalized entities
aliases:
  # Cable Modem mappings
  cm:
    - "cable modem"
    - "modem"
    - "CM"
    - "cablemodem"
  
  md_id:
    - "MdId"
    - "modem_id"
    - "ModemId"
    - "md-id"
  
  # Package/Service mappings
  package:
    - "pkg"
    - "service"
    - "plan"
    - "Package"
  
  # Error/Issue mappings
  error:
    - "err"
    - "exception"
    - "failure"
    - "issue"
    - "problem"

# Entity relationships for iterative exploration
relationships:
  cm:
    - md_id
    - mac_address
    - ip_address
  
  md_id:
    - cm
    - rpd
    - package
    - downstream_channel
  
  package:
    - md_id
    - service_group
    - billing_account
  
  error:
    - timestamp
    - severity
    - module
    - entity_id

# Entity extraction patterns (regex)
patterns:
  cm:
    - "CM\\d{4,6}"
    - "modem[_\\s]*(\\d+)"
  
  md_id:
    - "MdId[:\\s]*(\\d+)"
    - "modem_id[:\\s]*(\\d+)"
  
  mac_address:
    - "([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"
  
  ip_address:
    - "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b"
  
  timestamp:
    - "\\d{4}-\\d{2}-\\d{2}\\s\\d{2}:\\d{2}:\\d{2}"
```

#### Create `config/log_schema.yaml`:
```yaml
# Log file structure definitions
csv_schema:
  default:
    columns:
      - timestamp
      - severity
      - module
      - message
      - entity_id
    
    timestamp_format: "%Y-%m-%d %H:%M:%S"
    
    severity_levels:
      - DEBUG
      - INFO
      - WARN
      - ERROR
      - CRITICAL
  
  # Custom schema for specific log types
  system_logs:
    columns:
      - time
      - level
      - component
      - details
      - cm_id
    
    timestamp_format: "%m/%d/%Y %H:%M:%S"

# Chunking configuration
chunking:
  max_tokens: 4000
  overlap_lines: 10
  context_lines: 50
  
  # Chunk by entity context
  entity_context:
    before_lines: 25
    after_lines: 25

# LLM configuration
llm:
  model: "llama3.2"
  base_url: "http://localhost:11434"
  timeout: 30
  max_retries: 3
  
  # Token limits
  max_input_tokens: 4000
  max_output_tokens: 1000
```

#### Create `config/prompts.yaml`:
```yaml
# Prompt templates for different analysis modes

find_mode:
  system: |
    You are a log analysis expert. Your task is to extract specific entities and related information from log data.
    
    Always respond with valid JSON in this format:
    {
      "entities_found": ["entity1", "entity2"],
      "next_entities": ["related1", "related2"],
      "relevant_logs": ["log_line_1", "log_line_2"],
      "mode_suggestion": "find|analyze"
    }
  
  user_template: |
    Find all occurrences of "{entity}" in these log lines:
    
    {log_chunk}
    
    Extract related entities and suggest next exploration targets.

analyze_mode:
  system: |
    You are a log analysis expert specializing in root cause analysis and pattern detection.
    
    Always respond with valid JSON in this format:
    {
      "observations": ["observation1", "observation2"],
      "patterns": ["pattern1", "pattern2"],
      "correlations": ["correlation1", "correlation2"],
      "next_entities": ["entity1", "entity2"],
      "confidence": 0.85,
      "mode_suggestion": "find|analyze"
    }
  
  user_template: |
    Analyze these log entries for patterns, correlations, and root causes:
    
    Query: {user_query}
    Log data:
    {log_chunk}
    
    Focus on: {focus_entities}

trace_mode:
  system: |
    You are a log analysis expert specializing in flow tracing and timeline analysis.
    
    Always respond with valid JSON in this format:
    {
      "timeline": [
        {"timestamp": "...", "event": "...", "entity": "..."}
      ],
      "flow_steps": ["step1", "step2", "step3"],
      "next_entities": ["entity1", "entity2"],
      "bottlenecks": ["bottleneck1"],
      "mode_suggestion": "find|analyze"
    }
  
  user_template: |
    Trace the flow and timeline for "{entity}" in these logs:
    
    {log_chunk}
    
    Identify sequence of events, bottlenecks, and related entities.
```

### Task 2.2: Configuration Loader Implementation
**Time**: 1.5 hours

#### Create `src/utils/config.py`:
```python
"""Configuration management for log analyzer."""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class ConfigManager:
    """Manages application configuration from YAML files."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._entity_mappings: Optional[Dict[str, Any]] = None
        self._log_schema: Optional[Dict[str, Any]] = None
        self._prompts: Optional[Dict[str, Any]] = None
    
    @property
    def entity_mappings(self) -> Dict[str, Any]:
        """Load and cache entity mappings configuration."""
        if self._entity_mappings is None:
            self._entity_mappings = self._load_yaml("entity_mappings.yaml")
        return self._entity_mappings
    
    @property
    def log_schema(self) -> Dict[str, Any]:
        """Load and cache log schema configuration."""
        if self._log_schema is None:
            self._log_schema = self._load_yaml("log_schema.yaml")
        return self._log_schema
    
    @property
    def prompts(self) -> Dict[str, Any]:
        """Load and cache prompt templates."""
        if self._prompts is None:
            self._prompts = self._load_yaml("prompts.yaml")
        return self._prompts
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {filename}: {e}")
    
    def get_entity_aliases(self, entity_type: str) -> List[str]:
        """Get all aliases for a given entity type."""
        aliases = self.entity_mappings.get("aliases", {})
        return aliases.get(entity_type, [entity_type])
    
    def get_entity_relationships(self, entity_type: str) -> List[str]:
        """Get related entities for a given entity type."""
        relationships = self.entity_mappings.get("relationships", {})
        return relationships.get(entity_type, [])
    
    def get_entity_pattern(self, entity_type: str) -> List[str]:
        """Get regex patterns for entity extraction."""
        patterns = self.entity_mappings.get("patterns", {})
        return patterns.get(entity_type, [])
    
    def get_log_columns(self, schema_name: str = "default") -> List[str]:
        """Get column names for log schema."""
        schema = self.log_schema.get("csv_schema", {})
        return schema.get(schema_name, {}).get("columns", [])
    
    def get_chunking_config(self) -> Dict[str, Any]:
        """Get chunking configuration."""
        return self.log_schema.get("chunking", {})
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.log_schema.get("llm", {})
    
    def get_prompt_template(self, mode: str, template_type: str = "user_template") -> str:
        """Get prompt template for specific mode."""
        mode_prompts = self.prompts.get(f"{mode}_mode", {})
        return mode_prompts.get(template_type, "")


# Global configuration instance
config = ConfigManager()
```

### Task 2.3: Validation & Testing
**Time**: 30 minutes

#### Create `src/utils/validators.py`:
```python
"""Input validation utilities."""

import re
from typing import List, Optional
from pathlib import Path


def validate_log_file(file_path: str) -> bool:
    """Validate that log file exists and is readable."""
    path = Path(file_path)
    return path.exists() and path.is_file() and path.suffix.lower() == '.csv'


def validate_entity_query(query: str) -> bool:
    """Validate entity query format."""
    if not query or len(query.strip()) < 2:
        return False
    
    # Check for basic query patterns
    return bool(re.match(r'^[a-zA-Z0-9\s\-_.:]+$', query.strip()))


def validate_json_response(response: dict, required_fields: List[str]) -> bool:
    """Validate LLM JSON response structure."""
    if not isinstance(response, dict):
        return False
    
    return all(field in response for field in required_fields)


def sanitize_entity_name(entity: str) -> str:
    """Sanitize entity name for safe processing."""
    # Remove special characters, keep alphanumeric and common separators
    sanitized = re.sub(r'[^\w\-_.]', '', entity.strip())
    return sanitized[:50]  # Limit length
```

## Day 3: Logging & Error Handling

### Task 3.1: Logging System Setup
**Time**: 1 hour

#### Create `src/utils/logger.py`:
```python
"""Centralized logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console


def setup_logger(
    name: str = "log-analyzer",
    level: str = "INFO",
    log_file: Optional[str] = None,
    rich_console: bool = True
) -> logging.Logger:
    """Setup structured logging with optional file output and rich formatting."""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler with rich formatting
    if rich_console:
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            markup=True
        )
    else:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Global logger instance
logger = setup_logger()


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for this class."""
        return logging.getLogger(f"{__name__}.{self.__class__.__name__}")
```

### Task 3.2: Error Handling Framework
**Time**: 1 hour

#### Create `src/utils/exceptions.py`:
```python
"""Custom exceptions for log analyzer."""


class LogAnalyzerError(Exception):
    """Base exception for log analyzer."""
    pass


class ConfigurationError(LogAnalyzerError):
    """Raised when configuration is invalid or missing."""
    pass


class LogFileError(LogAnalyzerError):
    """Raised when log file cannot be read or processed."""
    pass


class LLMError(LogAnalyzerError):
    """Raised when LLM communication fails."""
    pass


class EntityExtractionError(LogAnalyzerError):
    """Raised when entity extraction fails."""
    pass


class ValidationError(LogAnalyzerError):
    """Raised when input validation fails."""
    pass
```

### Task 3.3: Basic CLI Structure
**Time**: 1 hour

#### Create `src/cli/main.py`:
```python
"""Main CLI entry point."""

import click
from rich.console import Console
from ..utils.logger import setup_logger
from ..utils.exceptions import LogAnalyzerError


console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-dir', default='config', help='Configuration directory path')
@click.option('--log-file', help='Log file for application logs')
@click.pass_context
def main(ctx, verbose, config_dir, log_file):
    """AI-powered log analysis tool using Ollama."""
    
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logger(level=log_level, log_file=log_file)
    
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['logger'] = logger
    ctx.obj['config_dir'] = config_dir
    ctx.obj['verbose'] = verbose


@main.command()
@click.argument('query')
@click.argument('log_file')
@click.option('--output-format', '-f', default='human',
              type=click.Choice(['json', 'human']),
              help='Output format')
@click.pass_context
def analyze(ctx, query, log_file, output_format):
    """Analyze logs using natural language query. LLM automatically determines the best approach (find/analyze/trace)."""
    try:
        console.print(f"[green]Processing: '{query}' in {log_file}[/green]")
        console.print("[blue]LLM will automatically determine whether to find entities, analyze patterns, or trace flows[/blue]")
        # TODO: Implement unified analysis functionality
        console.print("[yellow]Analysis engine not yet implemented[/yellow]")
        
    except LogAnalyzerError as e:
        console.print(f"[red]Error: {e}[/red]")
        ctx.exit(1)


@main.command()
@click.pass_context
def test_config(ctx):
    """Test configuration files."""
    try:
        from ..utils.config import config
        
        console.print("[green]Testing configuration...[/green]")
        
        # Test entity mappings
        aliases = config.get_entity_aliases('cm')
        console.print(f"CM aliases: {aliases}")
        
        # Test log schema
        columns = config.get_log_columns()
        console.print(f"Default columns: {columns}")
        
        # Test prompts
        prompt = config.get_prompt_template('find')
        console.print(f"Find prompt length: {len(prompt)} characters")
        
        console.print("[green]✓ Configuration test passed[/green]")
        
    except Exception as e:
        console.print(f"[red]Configuration test failed: {e}[/red]")
        ctx.exit(1)


if __name__ == '__main__':
    main()
```

## Testing & Validation

### Task 3.4: Basic Testing Setup
**Time**: 30 minutes

#### Create `tests/test_config.py`:
```python
"""Test configuration management."""

import pytest
from src.utils.config import ConfigManager
from src.utils.exceptions import ConfigurationError


def test_config_manager_initialization():
    """Test ConfigManager initialization."""
    config_manager = ConfigManager("config")
    assert config_manager.config_dir.name == "config"


def test_entity_aliases():
    """Test entity alias retrieval."""
    config_manager = ConfigManager("config")
    aliases = config_manager.get_entity_aliases('cm')
    assert isinstance(aliases, list)
    assert len(aliases) > 0


def test_invalid_config_file():
    """Test handling of missing config files."""
    config_manager = ConfigManager("nonexistent")
    with pytest.raises(FileNotFoundError):
        _ = config_manager.entity_mappings
```

### Task 3.5: Manual Testing
**Time**: 30 minutes

```bash
# Test CLI help
python -m src.cli.main --help

# Test configuration
python -m src.cli.main test-config

# Test pure natural language analysis (should show "not implemented" message)
python -m src.cli.main "find all CM12345 issues" logs/system.csv
python -m src.cli.main "what caused the outage yesterday?" logs/system.csv
python -m src.cli.main "trace the modem flow for CM12345" logs/system.csv

# Test configuration and verbose mode
python -m src.cli.main --test-config
python -m src.cli.main --verbose "root cause analysis" logs/system.csv
```

## Deliverables

### Files Created:
- [ ] Project structure with all directories
- [ ] `requirements.txt` with dependencies
- [ ] `setup.py` for package installation
- [ ] `config/entity_mappings.yaml`
- [ ] `config/log_schema.yaml`
- [ ] `config/prompts.yaml`
- [ ] `src/utils/config.py`
- [ ] `src/utils/logger.py`
- [ ] `src/utils/exceptions.py`
- [ ] `src/utils/validators.py`
- [ ] `src/cli/main.py`
- [ ] Basic test files
- [ ] `README.md` and `.gitignore`

### Validation Checklist:
- [ ] Virtual environment created and activated
- [ ] All dependencies installed successfully
- [ ] CLI commands execute without errors
- [ ] Configuration files load correctly
- [ ] Logging system works with rich formatting
- [ ] Basic error handling functional
- [ ] Project structure follows planned architecture

## CLI Usage Examples

**Pure Natural Language Interface:**
```bash
# Direct natural language queries - no subcommands needed!
python -m src.cli.main "find all CM12345 issues" logs/system.csv
python -m src.cli.main "what caused the outage yesterday?" logs/system.csv  
python -m src.cli.main "trace the modem flow for CM12345" logs/system.csv

# Test configuration
python -m src.cli.main --test-config

# Verbose mode
python -m src.cli.main --verbose "root cause analysis" logs/system.csv

# JSON output
python -m src.cli.main --output-format json "analyze error patterns" logs/system.csv
```

**Key Design Decision:**
- **No subcommands at all** - just ask your question naturally
- **LLM automatically determines** whether to find entities, analyze patterns, or trace flows
- **Pure natural language** - no CLI artifacts or command structure
- **Perfect match to original architecture** where mode switching is dynamic and controlled by backend

## Next Steps for Phase 2:
1. Implement log processing engine
2. Create CSV reader with streaming support
3. Build entity extraction utilities
4. Develop log chunking system

**Estimated Total Time**: 6-8 hours over 3 days
