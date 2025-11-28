# Phase 3 Quick Start Guide

## Running the Tests

```bash
# Make sure Ollama is running
ollama serve

# Run Phase 3 tests
python tests/test_llm_integration.py
```

## Quick Usage Examples

### 1. Simple Text Generation

```python
from src.llm import OllamaClient

client = OllamaClient()  # Auto-detects model
response = client.generate("Explain what a cable modem is")
print(response)
```

### 2. JSON Generation

```python
client = OllamaClient()
response = client.generate_json(
    prompt="List 3 common network errors in JSON format",
    temperature=0.3
)
print(response)  # Dictionary with parsed JSON
```

### 3. Entity Extraction from Logs

```python
from src.llm import OllamaClient, PromptBuilder, ResponseParser
from src.core.log_processor import LogProcessor

# Load logs
processor = LogProcessor("tests/sample_logs/system.csv")
logs = processor.read_all_logs()

# Setup LLM components
client = OllamaClient()
builder = PromptBuilder()
parser = ResponseParser()

# Filter to specific entity
cm_logs = processor.filter_by_entity(logs, "entity_id", "CM12345")

# Format for LLM
log_dicts = cm_logs.to_dict('records')[:10]  # First 10 entries
log_text = builder.format_log_chunk(log_dicts)

# Build prompt
system, user = builder.build_find_prompt("CM12345", log_text)

# Generate and parse
response = client.generate_json(user, system_prompt=system)
result = parser.parse_find_response(response)

print(f"Entities found: {result['entities_found']}")
print(f"Next to explore: {result['next_entities']}")
```

### 4. Root Cause Analysis

```python
# Build analyze prompt
system, user = builder.build_analyze_prompt(
    user_query="Why is CM12345 experiencing errors?",
    log_chunk=log_text,
    focus_entities=["CM12345"]
)

# Generate response
response = client.generate_json(user, system_prompt=system, temperature=0.5)
result = parser.parse_analyze_response(response)

print("Observations:")
for obs in result['observations']:
    print(f"  - {obs}")

print(f"\nConfidence: {result['confidence']:.0%}")
```

### 5. Full Pipeline Example

```python
from src.core.log_processor import LogProcessor
from src.core.chunker import LogChunker
from src.llm import OllamaClient, PromptBuilder, ResponseParser

# 1. Load and filter logs
processor = LogProcessor("logs.csv")
logs = processor.read_all_logs()
filtered = processor.filter_by_entity(logs, "entity_id", "CM12345")

# 2. Chunk logs
chunker = LogChunker()
chunks = chunker.chunk_by_size(filtered, max_tokens=2000)

# 3. Setup LLM
client = OllamaClient()
builder = PromptBuilder()
parser = ResponseParser()

# 4. Process each chunk
all_results = []
for chunk in chunks:
    # Format chunk
    log_dicts = chunk.logs.to_dict('records')
    log_text = builder.format_log_chunk(log_dicts)
    
    # Generate analysis
    system, user = builder.build_find_prompt("CM12345", log_text)
    response = client.generate_json(user, system_prompt=system)
    result = parser.parse_find_response(response)
    
    all_results.append(result)

# 5. Merge results
final_result = parser.merge_responses(all_results, mode="find")
print(f"Total entities found: {len(final_result['entities_found'])}")
print(f"Entities: {final_result['entities_found']}")
```

## Available Models Check

```python
client = OllamaClient()
print("Ollama is healthy:", client.health_check())
print("Available models:", client.list_models())
print("Current model:", client.model)
```

## Prompt Modes

### FIND Mode
**Purpose:** Extract entities and relationships
```python
system, user = builder.build_find_prompt(entity="CM12345", log_chunk=logs)
```

### ANALYZE Mode
**Purpose:** Detect patterns and correlations
```python
system, user = builder.build_analyze_prompt(
    user_query="What caused the outage?",
    log_chunk=logs,
    focus_entities=["CM12345", "network"]
)
```

### TRACE Mode
**Purpose:** Timeline and flow analysis
```python
system, user = builder.build_trace_prompt(entity="CM12345", log_chunk=logs)
```

## Configuration

### Change Default Model
```python
client = OllamaClient(model="llama3.1:latest")
```

### Adjust Timeouts
```python
client = OllamaClient(timeout=60, max_retries=5)
```

### Change Base URL
```python
client = OllamaClient(base_url="http://remote-server:11434")
```

## Error Handling

```python
from src.utils.exceptions import LLMError

try:
    client = OllamaClient()
    response = client.generate("Your prompt here")
except LLMError as e:
    print(f"LLM error: {e}")
    # Handle error (retry, fallback, etc.)
```

## Tips

1. **Token Management:** Keep log chunks under 3000 tokens for best results
2. **Temperature:** Use 0.1-0.3 for factual extraction, 0.5-0.7 for analysis
3. **Retries:** LLM calls include automatic retry on failure
4. **JSON Mode:** Always use `generate_json()` for structured responses
5. **Model Selection:** llama3.1 and llama3 work best for log analysis

## Troubleshooting

### Ollama Not Running
```bash
# Start Ollama server
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### No Models Available
```bash
# Pull a model
ollama pull llama3.1

# Or use your custom model
ollama list
```

### Slow Responses
- Reduce log chunk size
- Use smaller model
- Decrease temperature
- Add timeout limits

### Invalid JSON Responses
- Lower temperature (0.1-0.3)
- Simplify prompts
- Use retry logic (built-in)

## Next Steps

Run the full test suite:
```bash
python tests/manual_test_phase2.py  # Phase 2 tests
python tests/test_llm_integration.py  # Phase 3 tests
```

Ready for Phase 4! 🚀

