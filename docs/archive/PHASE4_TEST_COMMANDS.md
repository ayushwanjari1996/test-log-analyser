# Phase 4 Testing Commands

## Quick Tests (No LLM Required)

### 1. Test Imports
```bash
python -c "from src.core import LogAnalyzer; print('✓ All imports successful')"
```

### 2. Test Basic Flow (Entity extraction, iterative search)
```bash
python test_basic_flow.py
```

**Expected output:**
- ✓ Loaded 46 logs
- ✓ Found 4 CM entities
- ✓ Text search working
- ✓ Iterative search working

---

## Full LLM Tests (Requires Ollama Running)

### 3. Comprehensive Automated Test
```bash
python test_phase4_analyzer.py
```

**What it tests:**
- Specific value search: "find cm CM12345"
- Aggregation: "find all cms"
- Aggregation with filter: "find all cms with errors"
- Simple relationship: "find rpdname connected to cm CM12345"
- Complex relationship (iterative): "find mdid for cm CM12345"
- Analysis (LLM): "why did cm CM12345 fail"
- Trace: "trace cm CM12345"

**Expected output:**
- Each query shows success/failure
- Duration for each query
- Query type detection
- Results summary
- Final detailed JSON example

---

### 4. Interactive CLI Testing
```bash
python test_interactive.py
```

**What it does:**
- Interactive prompt where you can type ANY query
- Real-time query parsing and analysis
- Full JSON output for each query
- Type 'quit' or 'exit' to stop

**Example queries to try:**
```
find cm CM12345
find all cms
find all modems with errors
find rpdname for cm CM12345
find mdid for cm x
why did cm CM12345 fail
analyze errors for modem CM12345
trace cm CM12345
show timeline for modem CM12345
```

---

## Component-Specific Tests

### 5. Test LLM Query Parser Only
```bash
python test_llm_query_parser.py
```

**What it tests:**
- Query parsing accuracy
- Entity extraction
- Intent detection
- Reasoning output

---

### 6. Test Single Query via Python
```bash
python -c "from src.core import LogAnalyzer; a = LogAnalyzer('tests/sample_logs/system.csv'); print(a.analyze_query('find all cms'))"
```

---

## Troubleshooting

### If Ollama is not running:
```bash
# Start Ollama service (if not already running)
# Then verify:
curl http://localhost:11434/api/version
```

### If model not found:
The system will auto-detect available models. If you want to specify:
```python
from src.llm import OllamaClient
client = OllamaClient(model="llama3.1")  # or any installed model
```

### Check logs:
All components use centralized logging. Check console output for detailed execution traces.

---

## Expected Performance

### Query Types & Speed:
- **Specific value**: <1s
- **Aggregation**: <2s
- **Relationship (direct)**: 1-2s
- **Relationship (iterative)**: 3-8s (depends on iterations)
- **Analysis (LLM)**: 5-15s (depends on log volume)
- **Trace**: <1s

### Success Criteria:
✅ All imports work  
✅ Basic flow completes without errors  
✅ Query parser correctly identifies intent  
✅ Entity extraction finds expected values  
✅ Iterative search explores bridges  
✅ LLM analysis returns observations  
✅ Results include confidence scores  

---

## Test Data

Using: `tests/sample_logs/system.csv`
- **46 log entries**
- **4 unique CM entities** (CM12345, CM67890, CM11111, CM22222)
- Various severities: INFO, WARNING, ERROR
- Multiple modules: DHCP, TFTP, Registration, System

---

## Next Steps After Testing

1. **Try with your own logs**: Replace CSV path in LogAnalyzer
2. **Adjust configurations**: Modify YAML files in `config/`
3. **Add custom entity types**: Update `entity_mappings.yaml`
4. **Tune iteration limits**: Adjust `max_iterations` in IterativeSearchStrategy
5. **Enable LLM bridge selection**: Pass `use_llm_bridges=True`

---

## File Outputs

All test scripts provide:
- ✅ Console output with colored formatting (Rich library)
- 📊 JSON results for programmatic use
- 🔍 Detailed reasoning and confidence scores
- 📈 Performance metrics (duration, iterations, logs searched)

---

## Common Issues & Solutions

**Issue**: "No patterns defined for entity type 'rpdname'"
- **Solution**: Add regex pattern in `config/entity_mappings.yaml`

**Issue**: "Could not find X after N iterations"
- **Solution**: Entity may not exist in logs, or needs more iterations
- Try: Increase `max_iterations` or check log data

**Issue**: LLM timeout
- **Solution**: Reduce log volume, increase timeout, or use smaller model

**Issue**: Query parsing returns wrong type
- **Solution**: LLM may misunderstand query - try rephrasing or check reasoning output

---

## Quick Start Command

**One command to test everything (requires Ollama):**
```bash
python test_basic_flow.py && python test_phase4_analyzer.py
```

This will:
1. Test basic components (no LLM)
2. Run full test suite with LLM
3. Show all query types working
4. Provide detailed results

**Estimated time**: 30-60 seconds

