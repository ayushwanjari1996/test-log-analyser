# Smart Summarization Design Document

## Problem Statement

Current issue: Tools return large DataFrames that can't fit in LLM context.
- 1000 logs = ~500K tokens (exceeds limit)
- LLM can't make smart decisions without seeing data
- Need intelligent compression that preserves important information

## Goals

1. **Token-efficient**: Send only essential info to LLM
2. **Entity-aware**: Extract and highlight key entities (MACs, IPs, IDs)
3. **Context-preserving**: LLM gets enough info to decide next step
4. **Flexible**: Works with any tool output (logs, values, stats)

## Architecture

### Components

```
Tool Result (1000 logs)
    ↓
Smart Summarizer
    ↓
├─→ Compact Summary (to LLM prompt)
└─→ Full Data (to state for next tool)
```

### Smart Summarizer Responsibilities

1. **Entity Extraction**: Find key entities using `entity_mappings.yaml`
2. **Aggregation**: Group by entities, count occurrences
3. **Sampling**: Select top N representative logs
4. **Stat Generation**: Severity, time range, patterns
5. **Format**: Human-readable summary for LLM

## Design: Smart Summarizer

### Input
```python
{
    "data": DataFrame or list,
    "tool_name": str,
    "metadata": dict
}
```

### Output
```python
{
    "summary_text": str,          # For LLM prompt
    "entities": dict,              # Extracted entities
    "stats": dict,                 # Counts, distributions
    "samples": list,               # Top N representative logs
    "full_data_ref": str           # State reference for next tool
}
```

### Algorithm

#### Step 1: Entity Extraction
- Parse JSON logs
- Use `entity_mappings.yaml` to identify entity types
- Extract values for each entity type
- Count unique values per entity

Example:
```
Input: 1000 logs
Output: {
    "cm_mac": ["2c:ab:a4:40:a8:bc", ...],  # 23 unique
    "rpdname": ["TestRpd123", "RPD-AA6"],  # 2 unique
    "md_id": ["0x64030000", ...]           # 5 unique
}
```

#### Step 2: Aggregation
- Group logs by top entities
- Count occurrences per entity value
- Identify top N entities by frequency

Example:
```
CmMacAddress:
  - 2c:ab:a4:40:a8:bc: 45 logs
  - f8:79:0a:1f:58:d6: 32 logs
  - ...

RpdName:
  - TestRpd123: 320 logs
  - RPD-AA6: 180 logs
```

#### Step 3: Smart Sampling
Select representative logs using:

**Strategy A: Diversity Sampling**
- Pick logs from different entities
- Include different severities (ERROR > WARN > INFO)
- Span time range (earliest, middle, latest)

**Strategy B: Importance Sampling**
- Prioritize ERROR/WARN logs
- Include logs with rare entities
- Include logs with multiple entities (relationships)

**Combined**: Mix of both (60% importance, 40% diversity)

#### Step 4: Statistical Summary
Calculate:
- Total log count
- Severity distribution
- Time range (earliest → latest, span)
- Top 5 entities per type
- Top 5 functions/messages (if present)

#### Step 5: Format for LLM
Generate compact text summary:

```
Found 847 logs [15:30:00 → 15:35:00, span: 5min]

Key Entities:
  • CmMacAddress: 23 unique (top: 2c:ab:a4:40:a8:bc [45 logs], f8:79:0a:1f:58:d6 [32 logs])
  • RpdName: 2 unique (TestRpd123 [320 logs], RPD-AA6 [180 logs])
  • MdId: 5 unique (0x64030000 [500 logs], 0x7a030000 [200 logs])

Severities: ERROR: 12, WARN: 35, INFO: 800

Top 10 Sample Logs:
1. [ERROR] Function: ProcessFecStats, CM: 2c:ab:a4:40:a8:bc, Msg: FEC uncorrectable
2. [WARN] Function: CmDsa, RpdName: TestRpd123, Msg: DSA timeout
...

Full data cached for next tool.
```

## Implementation Plan

### Phase 1: Core Summarizer (New Component)
File: `src/core/smart_summarizer.py`

Classes:
1. **EntityExtractor**: Extract entities using `entity_mappings.yaml`
2. **LogAggregator**: Group and count by entities
3. **SmartSampler**: Select representative logs
4. **SummaryFormatter**: Format for LLM

### Phase 2: Integration with Orchestrator
File: `src/core/iterative_react_orchestrator.py`

Changes:
1. After tool execution, pass result to `SmartSummarizer`
2. Store summary in context for LLM
3. Store full data in state for next tool
4. Update `ContextBuilder` to use summaries

### Phase 3: Tool Result Handling
File: `src/core/tools/base_tool.py`

Enhancement to `ToolResult`:
```python
class ToolResult:
    ...
    summary: Optional[str] = None  # Auto-generated summary
    sample_data: Optional[list] = None  # Representative samples
```

### Phase 4: Context Builder Update
File: `src/core/context_builder.py`

Changes:
- Use summaries instead of raw data in LLM prompt
- Include entity highlights
- Show sample logs (not all logs)

## Entity-Aware Features

### Using entity_mappings.yaml

**Aliases**: Map field names to entity types
```yaml
cm:
  - "CmMacAddress"
  - "cm_mac"
md_id:
  - "MdId"
  - "md_id"
```

**Relationships**: Understand which entities connect
```yaml
relationships:
  cm:
    - md_id
    - rpdname
  cpe:
    - cm
    - md_id
```

**Patterns**: Regex for entity extraction
```yaml
patterns:
  cm_mac:
    - "\"CmMacAddress\"\\s*:\\s*\"([0-9a-fA-F:]+)\""
```

### Smart Features

1. **Relationship Hints**: If log has CM + RpdName, mark as "relationship log"
2. **Entity Prioritization**: Prioritize entity types relevant to query
3. **Anomaly Detection**: Highlight rare entities or unusual patterns

## Example Scenarios

### Scenario 1: Simple Grep
```
Tool: grep_logs("2c:ab:a4:40:a8:bc")
Result: 45 logs

Summary to LLM:
"Found 45 logs for '2c:ab:a4:40:a8:bc'. Entities: CmMacAddress (1), MdId (2), RpdName (1). 
Severities: INFO:40, DEBUG:5. Sample: [log1, log2, log3]. Full data available."
```

### Scenario 2: Large Result Set
```
Tool: grep_logs("INFO")
Result: 1500 logs

Summary to LLM:
"Found 1500 INFO logs [15:30:00 → 16:45:00]. 
Top entities: CmMacAddress (234 unique), RpdName (12 unique), MdId (8 unique).
Top functions: ScheduleCmReplication (450), ProcessFecStats (320), CmDsa (280).
Top 10 diverse samples provided. Full data cached."
```

### Scenario 3: Relationship Query
```
Tool: find_relationship_chain(start="2c:ab:a4:47:1a:d2", target="MdId")
Result: Path found

Summary to LLM:
"Relationship found: CpeMacAddress → RpdName:TestRpd123 → MdId:0x7a030000 (depth: 2).
Path includes 3 logs. All entities extracted."
```

## Configuration

### Summarizer Settings
```yaml
# config/summarizer_config.yaml
smart_summarizer:
  max_sample_logs: 10
  entity_top_n: 5
  sampling_strategy: "mixed"  # diversity, importance, mixed
  importance_weight: 0.6
  diversity_weight: 0.4
  max_summary_length: 500  # chars
  include_timestamps: true
  include_severities: true
  highlight_errors: true
```

## Benefits

1. **Token Efficiency**: 1000 logs → 500 chars summary (1000x reduction)
2. **Better Decisions**: LLM sees key info, not noise
3. **Flexible**: Works with any tool output
4. **Scalable**: Handles 10K+ logs without issues
5. **Entity-Aware**: Understands log structure and relationships

## Trade-offs

**Pros:**
- Massive token savings
- LLM gets focused, relevant info
- Preserves important patterns

**Cons:**
- Summary generation adds ~100ms overhead
- Might miss edge cases in sampling
- Requires entity config to be accurate

**Mitigation:**
- Parallel processing for speed
- Multiple sampling strategies
- Fallback to simple summary if entity extraction fails

## Future Enhancements

1. **ML-based Sampling**: Use embeddings to find diverse logs
2. **Query-Aware Summarization**: Tailor summary to user's question
3. **Adaptive Sampling**: Adjust sample size based on complexity
4. **Caching**: Cache entity extractions for frequently seen logs
5. **Streaming Summarization**: Summarize as logs stream in

## Testing Strategy

1. **Unit Tests**: Each component (extractor, aggregator, sampler)
2. **Integration Tests**: Full summarization pipeline
3. **Performance Tests**: Large log sets (1K, 10K, 100K logs)
4. **Quality Tests**: Verify summary preserves important info
5. **Token Tests**: Confirm summaries fit in context window

## Success Metrics

1. **Token Reduction**: >95% reduction for large datasets
2. **Information Preservation**: LLM can answer queries correctly
3. **Performance**: <200ms for 10K logs
4. **Coverage**: Works with all tool types
5. **Accuracy**: Entity extraction >98% correct

---

## Implementation Priority

**Phase 1 (Critical)**: Core SmartSummarizer + EntityExtractor
**Phase 2 (High)**: Orchestrator integration + ContextBuilder update
**Phase 3 (Medium)**: Smart sampling strategies
**Phase 4 (Low)**: ML enhancements, caching

