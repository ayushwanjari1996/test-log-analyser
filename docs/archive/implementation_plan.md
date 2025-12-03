# AI Log Analyzer - High-Level Implementation Plan

## Project Overview
Python CLI tool for analyzing large log files using Ollama-hosted Llama 3.2 model. Supports entity lookup, root-cause analysis, flow tracing, and pattern detection through iterative AI-powered exploration.

## Project Structure
```
log-analyzer/
├── src/
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py          # Main CLI entry point
│   │   ├── commands.py      # CLI command definitions
│   │   └── formatters.py    # Output formatting
│   ├── core/
│   │   ├── __init__.py
│   │   ├── log_processor.py # Log reading and filtering
│   │   ├── entity_manager.py # Entity mapping and queue management
│   │   ├── analyzer.py      # Main analysis orchestrator
│   │   └── chunker.py       # Log chunking utilities
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── ollama_client.py # Ollama API integration
│   │   ├── prompts.py       # Prompt templates
│   │   └── response_parser.py # JSON response handling
│   └── utils/
│       ├── __init__.py
│       ├── config.py        # Configuration management
│       ├── logger.py        # Logging setup
│       └── validators.py    # Input validation
├── config/
│   ├── entity_mappings.yaml # Entity aliases and mappings
│   ├── log_schema.yaml      # Log structure definitions
│   └── prompts.yaml         # LLM prompt templates
├── tests/
├── requirements.txt
├── setup.py
└── README.md
```

## Implementation Phases

### Phase 1: Foundation Setup (Days 1-3)
**Goal**: Basic project structure and core utilities

#### Tasks:
1. **Project Scaffolding**
   - Create directory structure
   - Setup `requirements.txt` with dependencies:
     - `click` (CLI framework)
     - `requests` (HTTP client for Ollama)
     - `pyyaml` (configuration files)
     - `pandas` (CSV processing)
     - `rich` (CLI formatting)

2. **Configuration System**
   - `config/entity_mappings.yaml`: User terms → normalized entities
   - `config/log_schema.yaml`: Log column definitions and relationships
   - `utils/config.py`: Configuration loader and validator

3. **Logging & Error Handling**
   - `utils/logger.py`: Structured logging setup
   - Global error handling patterns
   - Progress indicators for long operations

### Phase 2: Log Processing Engine (Days 4-6)
**Goal**: Efficient log reading, filtering, and chunking

#### Tasks:
1. **Log Reader (`core/log_processor.py`)**
   ```python
   class LogProcessor:
       def read_csv_stream(file_path, chunk_size=1000)
       def filter_by_entity(logs, entity_value)
       def filter_by_timerange(logs, start, end)
       def extract_entities(logs, entity_patterns)
   ```

2. **Chunking System (`core/chunker.py`)**
   ```python
   class LogChunker:
       def chunk_by_size(logs, max_tokens=4000)
       def chunk_by_entity_context(logs, entity, context_lines=50)
       def merge_overlapping_chunks(chunks)
   ```

3. **Entity Management (`core/entity_manager.py`)**
   ```python
   class EntityManager:
       def normalize_entity(user_term)
       def get_related_entities(entity_type)
       def build_entity_queue(initial_entities)
   ```

### Phase 3: LLM Integration (Days 7-10)
**Goal**: Ollama integration with dual-mode processing

#### Tasks:
1. **Ollama Client (`llm/ollama_client.py`)**
   ```python
   class OllamaClient:
       def __init__(base_url="http://localhost:11434")
       def generate(prompt, model="llama3.2", format="json")
       def health_check()
   ```

2. **Prompt System (`llm/prompts.py`)**
   - FIND mode prompts: Entity extraction templates
   - ANALYZE mode prompts: Pattern analysis templates
   - Dynamic prompt building based on context

3. **Response Parser (`llm/response_parser.py`)**
   ```python
   class ResponseParser:
       def parse_find_response(json_response)
       def parse_analyze_response(json_response)
       def validate_json_structure(response)
   ```

### Phase 4: Analysis Orchestrator (Days 11-13)
**Goal**: Iterative analysis engine with queue management

#### Tasks:
1. **Main Analyzer (`core/analyzer.py`)**
   ```python
   class LogAnalyzer:
       def analyze_query(query, log_file, mode="auto")
       def iterative_exploration(initial_entities)
       def aggregate_results(intermediate_jsons)
   ```

2. **Analysis Modes**
   - **Entity Lookup**: Simple FIND-only workflow
   - **Root Cause Analysis**: FIND → ANALYZE loops
   - **Flow Tracing**: Timeline-based entity following
   - **Pattern Detection**: Chunk-based pattern analysis

3. **Queue Management**
   - Entity processing queue with priority
   - Cycle detection to prevent infinite loops
   - Progress tracking and intermediate result storage

### Phase 5: CLI Interface (Days 14-16)
**Goal**: User-friendly command-line interface

#### Tasks:
1. **Main CLI (`cli/main.py`)**
   ```bash
   log-analyzer find "CM12345" logs/system.csv
   log-analyzer analyze "root cause for error X" logs/system.csv
   log-analyzer trace "modem flow for CM12345" logs/system.csv
   ```

2. **Command Definitions (`cli/commands.py`)**
   - `find`: Entity lookup command
   - `analyze`: Root cause analysis command
   - `trace`: Flow tracing command
   - Global options: `--output-format`, `--verbose`, `--config`

3. **Output Formatting (`cli/formatters.py`)**
   - JSON output for structured data
   - Human-readable summaries with `rich` formatting
   - Progress bars and status indicators

### Phase 6: Advanced Features (Days 17-20)
**Goal**: Performance optimization and advanced analysis

#### Tasks:
1. **Caching System**
   - Cache LLM responses for repeated queries
   - Intermediate result persistence
   - Smart cache invalidation

2. **Performance Optimizations**
   - Async LLM calls where beneficial
   - Memory-efficient streaming for large files
   - Parallel processing for independent chunks

3. **Advanced Analysis Features**
   - Time-series pattern detection
   - Cross-entity correlation analysis
   - Anomaly detection in log patterns

## Key Technical Decisions

### Dependencies
- **CLI Framework**: `click` - Robust CLI with subcommands
- **HTTP Client**: `requests` - Simple Ollama API integration
- **Data Processing**: `pandas` - CSV handling and filtering
- **Configuration**: `pyyaml` - Human-readable config files
- **Output Formatting**: `rich` - Beautiful CLI output

### Data Flow Architecture
1. **Input**: User query + log file path
2. **Preprocessing**: Entity normalization + initial log filtering
3. **Iterative Processing**: Queue-based entity exploration
4. **LLM Integration**: FIND/ANALYZE mode switching
5. **Output**: Aggregated JSON + human-readable summary

### Error Handling Strategy
- Graceful degradation for LLM failures
- Retry logic with exponential backoff
- Comprehensive input validation
- Clear error messages with suggestions

## Success Criteria
- [ ] Process 10k+ line log files efficiently
- [ ] Support natural language queries
- [ ] Provide both JSON and human-readable outputs
- [ ] Handle entity relationships iteratively
- [ ] Integrate seamlessly with Ollama
- [ ] Maintain <5 second response time for simple queries

## Next Steps
1. Set up development environment
2. Create project structure
3. Implement Phase 1 foundation components
4. Test with sample log files
5. Iterate based on real-world usage patterns
