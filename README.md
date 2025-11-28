# AI Log Analyzer

Python CLI tool for intelligent log analysis using Ollama-hosted Llama 3.2.

## Project Status

### ✅ Phase 1: Foundation Setup (Complete)
- Configuration system with YAML files
- Logging and error handling
- CLI framework with Click
- Validators and utilities

### ✅ Phase 2: Log Processing Engine (Complete)
- CSV reading and streaming for large files
- Entity extraction and management
- Log chunking for LLM context windows
- Advanced filtering and search capabilities

### 🚧 Phase 3: LLM Integration (Upcoming)
- Ollama API client
- Prompt engineering system
- Response parsing
- Dual-mode processing (FIND/ANALYZE)

## Quick Start
```bash
pip install -e .
log-analyzer --help
```

## Features

### Current Features (Phases 1-2)
- ✅ **Streaming CSV Processing** - Handle multi-GB log files efficiently
- ✅ **Entity Extraction** - Pattern-based extraction using configurable regex
- ✅ **Smart Chunking** - Multiple chunking strategies for LLM context windows
- ✅ **Advanced Filtering** - By entity, time range, severity, text search
- ✅ **Entity Relationships** - Track and explore related entities
- ✅ **Queue-Based Exploration** - Iterative entity discovery with cycle prevention
- ✅ **Configurable Patterns** - YAML-based entity and log schema configuration

### Coming Soon (Phases 3-6)
- 🚧 Natural language query interface
- 🚧 Root cause analysis
- 🚧 Flow tracing
- 🚧 Pattern detection
- 🚧 Ollama/Llama 3.2 integration

## Requirements
- Python 3.8+
- Ollama with Llama 3.2 model (for Phase 3+)

## Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

## Usage

### Phase 2: Log Processing (Current)

#### Process and Filter Logs
```python
from src.core.log_processor import LogProcessor

# Initialize processor
processor = LogProcessor("logs/system.csv")

# Read logs
logs = processor.read_all_logs()

# Filter by entity
cm_logs = processor.filter_by_entity(logs, "entity_id", "CM12345")

# Filter by severity
errors = processor.filter_by_severity(logs, min_severity="ERROR")

# Extract entities
entities = processor.extract_entities(logs, "cm")
```

#### Chunk Logs for LLM
```python
from src.core.chunker import LogChunker

# Initialize chunker
chunker = LogChunker()

# Size-based chunking
chunks = chunker.chunk_by_size(logs, max_tokens=4000)

# Entity-focused chunking
entity_chunks = chunker.chunk_by_entity_context(
    logs, 
    entity_indices=[0, 5, 10],
    entity_name="CM12345"
)

# Convert to text for LLM
text = chunks[0].to_text()
```

#### Manage Entities
```python
from src.core.entity_manager import EntityManager

# Initialize manager
manager = EntityManager()

# Extract all entities
entities = manager.extract_all_entities_from_logs(logs, ["cm", "md_id"])

# Find specific entity
cm_entity = manager.find_entity_in_logs(logs, "CM12345")

# Build exploration queue
queue = manager.build_entity_queue([cm_entity], max_depth=3)
```

### CLI (Coming in Phase 3+)
```bash
# Pure natural language queries - just ask your question!
python -m src.cli.main "find all CM12345 issues" logs/system.csv
python -m src.cli.main "what caused the outage yesterday?" logs/system.csv
python -m src.cli.main "trace the modem flow for CM12345" logs/system.csv

# Test configuration
python -m src.cli.main --test-config

# Get JSON output
python -m src.cli.main --output-format json "analyze error patterns" logs/system.csv
```

## Testing

### Run Phase 2 Tests
```bash
# Run all Phase 2 tests
python tests/run_phase2_tests.py

# Run specific module tests
python tests/run_phase2_tests.py --module log_processor
python tests/run_phase2_tests.py --module chunker
python tests/run_phase2_tests.py --module entity_manager

# Verbose output
python tests/run_phase2_tests.py --verbose
```

### Manual Testing
```bash
# Interactive demonstration of Phase 2 features
python tests/manual_test_phase2.py
```

## Configuration
Configuration files are located in the `config/` directory:
- `entity_mappings.yaml` - Entity aliases, patterns, and relationships
- `log_schema.yaml` - Log structure definitions and chunking settings
- `prompts.yaml` - LLM prompt templates (for Phase 3+)

### Sample Entity Configuration
```yaml
# config/entity_mappings.yaml
patterns:
  cm:
    - "CM\\d{4,6}"
    - "modem[_\\s]*(\\d+)"
  md_id:
    - "MdId[:\\s]*(\\d+)"

relationships:
  cm:
    - md_id
    - mac_address
```

## Project Structure
```
log-analyzer/
├── src/
│   ├── cli/              # CLI interface (Phase 1)
│   ├── core/             # Core processing (Phase 2) ✅
│   │   ├── log_processor.py   # CSV reading & filtering
│   │   ├── chunker.py         # Log chunking
│   │   └── entity_manager.py  # Entity extraction
│   ├── llm/              # LLM integration (Phase 3)
│   └── utils/            # Utilities (Phase 1) ✅
├── config/               # Configuration files ✅
├── tests/                # Test suite ✅
│   ├── sample_logs/      # Sample data
│   ├── test_*.py         # Unit tests
│   └── run_phase2_tests.py  # Test runner
├── phase1_implementation.md  # Phase 1 docs ✅
├── phase2_implementation.md  # Phase 2 docs ✅
└── implementation_plan.md    # Overall plan
```

## Documentation

- **[Implementation Plan](implementation_plan.md)** - High-level roadmap
- **[Phase 1 Documentation](phase1_implementation.md)** - Foundation setup
- **[Phase 2 Documentation](phase2_implementation.md)** - Log processing engine

## Performance

### Phase 2 Benchmarks
- **CSV Reading**: ~10k-50k rows/second
- **Entity Extraction**: ~1k-5k rows/second  
- **Memory**: Streaming support for multi-GB files
- **Chunking**: Near-instantaneous for <100k rows

## Contributing

This project follows a phased implementation approach:
1. ✅ Phase 1: Foundation (Days 1-3)
2. ✅ Phase 2: Log Processing (Days 4-6)
3. 🚧 Phase 3: LLM Integration (Days 7-10)
4. Phase 4: Analysis Orchestrator (Days 11-13)
5. Phase 5: CLI Interface (Days 14-16)
6. Phase 6: Advanced Features (Days 17-20)

## License

See LICENSE file for details.
