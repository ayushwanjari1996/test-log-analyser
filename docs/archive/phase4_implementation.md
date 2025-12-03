# Phase 4: Analysis Orchestrator - Implementation Plan

## Overview

Phase 4 builds the main orchestrator that coordinates all components (LogProcessor, Chunker, EntityManager, LLM) into complete analysis workflows. This is the "brain" that decides what to analyze, when to switch modes, and how to aggregate results.

## Architecture

```
User Query → LogAnalyzer → [Load Logs] → [Extract Entities] → [Entity Queue]
                              ↓              ↓                    ↓
                         [Filter/Chunk] → [LLM Analysis] → [Parse Results]
                              ↑              ↓                    ↓
                         [Continue?] ← [Update Queue] ← [Extract New Entities]
                              ↓
                         [Aggregate] → Final Results
```

## Components to Build

### 0. QueryParser (`src/core/query_parser.py`) - **NEW**

**Purpose:** Intelligently parse user queries to distinguish entity types vs values

**Critical Feature:**
```
"find rpdname connected to cm x"
  → Search for VALUE "x" (not pattern "cm")
  → Then extract rpdname TYPE from those logs

"find all cms"
  → Use PATTERN to extract all CM instances
  → Aggregate results
```

**Key Responsibilities:**
- Parse natural language queries
- Distinguish entity TYPE vs entity VALUE
- Handle relationship queries (A connected to B)
- Handle aggregation queries (all X)
- Handle analysis queries (why did X fail)
- Extract filter conditions

See `PHASE4_QUERY_PARSING.md` for detailed implementation.

### 1. LogAnalyzer (`src/core/analyzer.py`)

**Purpose:** Main orchestrator class that coordinates all components

**Key Responsibilities:**
- Initialize all components (processor, chunker, entity manager, LLM client)
- Load and preprocess log files
- Orchestrate analysis workflows
- Manage entity exploration queue
- Aggregate results from multiple iterations
- Generate final summaries

**Class Structure:**
```python
class LogAnalyzer:
    def __init__(self, log_file_path, config=None):
        # Initialize components
        self.processor = LogProcessor(log_file_path)
        self.chunker = LogChunker()
        self.entity_manager = EntityManager()
        self.llm_client = OllamaClient()
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        
        # State management
        self.logs = None
        self.entity_queue = None
        self.results = []
        self.explored_entities = set()
        
    # Main API methods
    def analyze_query(query, mode="auto")
    def entity_lookup(entity_name)
    def root_cause_analysis(query, initial_entity=None)
    def flow_trace(entity_name)
    
    # Internal workflow methods
    def _load_and_prepare_logs()
    def _iterative_exploration(max_iterations=5)
    def _process_entity(entity, mode="find")
    def _aggregate_results()
    def _generate_summary()
```

### 2. Analysis Workflows

#### Workflow 1: Entity Lookup (Simple)
**Purpose:** Find all occurrences of a specific entity

**Flow:**
1. Load logs
2. Extract/filter for target entity
3. Chunk filtered logs
4. For each chunk:
   - Build FIND prompt
   - Get LLM response
   - Parse entities found
5. Aggregate all findings
6. Return: entity locations, related entities, summary

**Use Case:** "Find all logs for CM12345"

```python
def entity_lookup(self, entity_name: str) -> Dict[str, Any]:
    # 1. Load logs
    logs = self.processor.read_all_logs()
    
    # 2. Filter to entity
    filtered = self.processor.filter_by_entity(logs, "entity_id", entity_name)
    
    # 3. Chunk logs
    chunks = self.chunker.chunk_by_size(filtered, max_tokens=3000)
    
    # 4. Process each chunk
    results = []
    for chunk in chunks:
        log_text = self.prompt_builder.format_log_chunk(chunk.logs.to_dict('records'))
        system, user = self.prompt_builder.build_find_prompt(entity_name, log_text)
        response = self.llm_client.generate_json(user, system_prompt=system)
        parsed = self.response_parser.parse_find_response(response)
        results.append(parsed)
    
    # 5. Merge results
    final = self.response_parser.merge_responses(results, mode="find")
    
    # 6. Generate summary
    summary = self._generate_entity_summary(entity_name, final)
    
    return {
        "entity": entity_name,
        "total_occurrences": len(filtered),
        "entities_found": final["entities_found"],
        "related_entities": final["next_entities"],
        "summary": summary
    }
```

#### Workflow 2: Root Cause Analysis (Iterative)
**Purpose:** Deep dive into why something happened

**Flow:**
1. Load logs
2. Identify initial entity (from query or auto-detect)
3. Initialize entity queue with initial entity
4. **Iterative Loop** (max 5 iterations):
   a. Get next entity from queue
   b. Get logs for entity
   c. Chunk logs
   d. **Mode Selection:**
      - First pass: FIND mode (discover related entities)
      - Second pass: ANALYZE mode (find patterns/correlations)
      - Later passes: Based on LLM suggestion
   e. Parse response
   f. Extract new entities → add to queue
   g. Store results
   h. Check stop conditions (max iterations, no new entities, high confidence)
5. Aggregate all results
6. Generate root cause summary

**Use Case:** "Why did CM12345 fail?", "What caused the network outage?"

```python
def root_cause_analysis(self, query: str, initial_entity: str = None) -> Dict[str, Any]:
    # 1. Load logs
    logs = self.processor.read_all_logs()
    
    # 2. Identify initial entity
    if not initial_entity:
        initial_entity = self._extract_entity_from_query(query)
    
    # 3. Initialize queue
    entity = Entity(entity_type="cm", entity_value=initial_entity, occurrences=[])
    self.entity_queue = self.entity_manager.build_entity_queue([entity], max_depth=5)
    
    # 4. Iterative exploration
    iteration = 0
    max_iterations = 5
    all_results = []
    
    while self.entity_queue.has_more() and iteration < max_iterations:
        depth, entity = self.entity_queue.get_next_entity()
        
        # Get logs for entity
        entity_logs = self._get_entity_logs(logs, entity)
        chunks = self.chunker.chunk_by_entity_context(
            entity_logs, 
            entity.occurrences, 
            entity.entity_value
        )
        
        # Determine mode
        mode = "find" if iteration == 0 else "analyze"
        
        # Process chunks
        for chunk in chunks:
            result = self._process_chunk(chunk, entity, mode, query)
            all_results.append(result)
            
            # Add new entities to queue
            for new_entity in result["next_entities"]:
                self.entity_queue.add_entity(
                    Entity(entity_type="unknown", entity_value=new_entity),
                    priority=5,
                    depth=depth + 1
                )
        
        iteration += 1
    
    # 5. Aggregate results
    final_result = self._aggregate_rca_results(all_results, query)
    
    return final_result
```

#### Workflow 3: Flow Trace (Timeline-based)
**Purpose:** Trace the sequence of events for an entity

**Flow:**
1. Load logs
2. Filter to entity
3. Sort by timestamp
4. Chunk by time windows
5. For each chunk:
   - Build TRACE prompt
   - Get LLM response
   - Parse timeline events
6. Merge timelines chronologically
7. Identify flow steps, bottlenecks
8. Return: timeline, flow diagram, bottlenecks

**Use Case:** "Trace the flow for CM12345", "What happened to the modem?"

```python
def flow_trace(self, entity_name: str) -> Dict[str, Any]:
    # 1. Load and filter
    logs = self.processor.read_all_logs()
    filtered = self.processor.filter_by_entity(logs, "entity_id", entity_name)
    
    # 2. Sort by time
    filtered = filtered.sort_values('timestamp')
    
    # 3. Chunk by time windows
    chunks = self.chunker.chunk_by_time_window(
        filtered, 
        timestamp_column='timestamp',
        window_minutes=5
    )
    
    # 4. Process each chunk
    timelines = []
    for chunk in chunks:
        log_text = self.prompt_builder.format_log_chunk(chunk.logs.to_dict('records'))
        system, user = self.prompt_builder.build_trace_prompt(entity_name, log_text)
        response = self.llm_client.generate_json(user, system_prompt=system)
        parsed = self.response_parser.parse_trace_response(response)
        timelines.append(parsed)
    
    # 5. Merge timelines
    final_timeline = self.response_parser.merge_responses(timelines, mode="trace")
    
    # 6. Generate flow summary
    summary = self._generate_flow_summary(entity_name, final_timeline)
    
    return {
        "entity": entity_name,
        "timeline": final_timeline["timeline"],
        "flow_steps": final_timeline["flow_steps"],
        "bottlenecks": final_timeline["bottlenecks"],
        "summary": summary
    }
```

### 3. Helper Methods

#### Mode Selection Logic
```python
def _select_analysis_mode(self, iteration: int, previous_results: List[Dict]) -> str:
    """
    Intelligently select next analysis mode.
    
    Rules:
    - Iteration 0: Always FIND (discover entities)
    - Iteration 1: ANALYZE (find patterns)
    - Iteration 2+: Use LLM's mode_suggestion
    - If confidence > 0.8: Switch to ANALYZE
    - If no new entities found: ANALYZE
    """
    if iteration == 0:
        return "find"
    
    if iteration == 1:
        return "analyze"
    
    # Check last result's suggestion
    if previous_results:
        last_suggestion = previous_results[-1].get("mode_suggestion", "analyze")
        return last_suggestion
    
    return "analyze"
```

#### Stop Condition Checker
```python
def _should_stop_exploration(self, iteration: int, results: List[Dict]) -> bool:
    """
    Determine if we should stop iterative exploration.
    
    Stop if:
    - Reached max iterations
    - No new entities discovered in last 2 iterations
    - Confidence score > 0.9 in ANALYZE mode
    - Queue is empty
    """
    if iteration >= self.max_iterations:
        return True
    
    if not self.entity_queue.has_more():
        return True
    
    # Check confidence
    analyze_results = [r for r in results[-2:] if r.get("confidence")]
    if analyze_results:
        avg_confidence = sum(r["confidence"] for r in analyze_results) / len(analyze_results)
        if avg_confidence > 0.9:
            return True
    
    # Check new entities
    if len(results) >= 2:
        last_entities = set(results[-1].get("next_entities", []))
        prev_entities = set(results[-2].get("next_entities", []))
        if len(last_entities & prev_entities) == 0:  # No new entities
            return True
    
    return False
```

#### Result Aggregator
```python
def _aggregate_results(self, results: List[Dict], mode: str) -> Dict[str, Any]:
    """
    Aggregate results from multiple iterations.
    
    For FIND mode:
    - Deduplicate entities
    - Count occurrences
    - Build entity relationship graph
    
    For ANALYZE mode:
    - Merge observations
    - Identify common patterns
    - Calculate average confidence
    - Extract root causes
    """
    if mode == "find":
        all_entities = []
        all_next = []
        for result in results:
            all_entities.extend(result.get("entities_found", []))
            all_next.extend(result.get("next_entities", []))
        
        return {
            "unique_entities": list(set(all_entities)),
            "entity_count": len(all_entities),
            "related_entities": list(set(all_next)),
            "entity_frequency": self._count_frequency(all_entities)
        }
    
    elif mode == "analyze":
        all_obs = []
        all_patterns = []
        all_correlations = []
        confidences = []
        
        for result in results:
            all_obs.extend(result.get("observations", []))
            all_patterns.extend(result.get("patterns", []))
            all_correlations.extend(result.get("correlations", []))
            if "confidence" in result:
                confidences.append(result["confidence"])
        
        return {
            "observations": all_obs,
            "patterns": list(set(all_patterns)),
            "correlations": list(set(all_correlations)),
            "confidence": sum(confidences) / len(confidences) if confidences else 0.5,
            "root_causes": self._extract_root_causes(all_patterns, all_correlations)
        }
```

#### Summary Generator
```python
def _generate_summary(self, results: Dict[str, Any], mode: str) -> str:
    """
    Generate human-readable summary from results.
    
    Uses LLM to create narrative summary from structured data.
    """
    if mode == "entity_lookup":
        prompt = f"""
        Summarize this entity analysis in 2-3 sentences:
        - Entity: {results['entity']}
        - Occurrences: {results['total_occurrences']}
        - Related entities: {', '.join(results['related_entities'][:5])}
        """
    
    elif mode == "root_cause":
        prompt = f"""
        Summarize this root cause analysis in 3-5 sentences:
        - Observations: {results['observations'][:3]}
        - Key patterns: {results['patterns'][:3]}
        - Confidence: {results['confidence']:.0%}
        Explain what likely caused the issue.
        """
    
    summary = self.llm_client.generate(prompt, temperature=0.3, max_tokens=200)
    return summary.strip()
```

### 4. State Management

```python
class AnalysisState:
    """Tracks analysis progress and state."""
    
    def __init__(self):
        self.iteration = 0
        self.explored_entities = set()
        self.current_mode = "find"
        self.results_history = []
        self.start_time = None
        self.end_time = None
    
    def add_result(self, result: Dict):
        self.results_history.append({
            "iteration": self.iteration,
            "mode": self.current_mode,
            "result": result,
            "timestamp": datetime.now()
        })
    
    def mark_entity_explored(self, entity: str):
        self.explored_entities.add(entity)
    
    def is_explored(self, entity: str) -> bool:
        return entity in self.explored_entities
    
    def get_statistics(self) -> Dict:
        return {
            "total_iterations": self.iteration,
            "entities_explored": len(self.explored_entities),
            "results_count": len(self.results_history),
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None
        }
```

### 5. Configuration

```python
class AnalyzerConfig:
    """Configuration for LogAnalyzer."""
    
    def __init__(self):
        # Iteration limits
        self.max_iterations = 5
        self.max_entities_per_iteration = 3
        self.max_depth = 5
        
        # Chunking
        self.chunk_size_tokens = 3000
        self.context_lines = 50
        
        # LLM settings
        self.temperature_find = 0.3
        self.temperature_analyze = 0.5
        self.temperature_trace = 0.3
        
        # Stop conditions
        self.confidence_threshold = 0.9
        self.min_new_entities = 1
        
        # Output
        self.verbose = True
        self.save_intermediate = False
```

## Workflow Decision Tree

```
User Query
    |
    ├─ Contains entity name + simple request → Entity Lookup
    |   Example: "Find CM12345", "Show logs for CM12345"
    |
    ├─ Contains "why", "cause", "reason" → Root Cause Analysis
    |   Example: "Why did X fail?", "What caused the error?"
    |
    ├─ Contains "trace", "flow", "timeline" → Flow Trace
    |   Example: "Trace CM12345", "Show flow for modem"
    |
    └─ Unclear/Complex → Auto Mode
        - Start with Entity Lookup
        - If issues found → Root Cause Analysis
        - If sequential events → Flow Trace
```

## Error Handling Strategy

1. **LLM Failures:**
   - Retry with exponential backoff (built into OllamaClient)
   - If still fails: skip chunk, continue with next
   - Log warning, don't crash entire analysis

2. **Invalid JSON Responses:**
   - Handled by ResponseParser
   - Returns default/empty structure
   - Continue processing

3. **Entity Not Found:**
   - Return empty result set
   - Suggest similar entities if available
   - Search in all columns, not just entity_id

4. **Log File Issues:**
   - Caught by LogProcessor
   - Clear error message to user
   - Exit gracefully

5. **Infinite Loops:**
   - Max iteration limit (5)
   - Track explored entities
   - Detect cycles in entity queue
   - Stop if no progress

## Performance Considerations

1. **Chunking Strategy:**
   - Balance chunk size vs. LLM calls
   - Larger chunks = fewer calls but slower per call
   - Recommended: 2000-3000 tokens per chunk

2. **Parallel Processing:**
   - Future: Process multiple chunks in parallel
   - Current: Sequential for simplicity
   - Estimate: ~4-5 seconds per chunk

3. **Caching:**
   - Future: Cache LLM responses for same log chunks
   - Would speed up repeated queries
   - Trade-off: storage vs. speed

4. **Progress Tracking:**
   - Show iteration progress
   - Display entities being processed
   - Estimated time remaining

## Testing Strategy

### Unit Tests
- Test each workflow independently
- Mock LLM responses
- Verify state management
- Test stop conditions

### Integration Tests
- Test full workflows with real logs
- Verify entity queue management
- Test mode switching
- Verify result aggregation

### Example Test Cases
1. Entity lookup for known entity → should find all occurrences
2. Entity lookup for non-existent entity → should return empty gracefully
3. Root cause with 1 iteration → should return initial findings
4. Root cause with max iterations → should stop at limit
5. Flow trace with time-ordered logs → should build correct timeline
6. Detect cycle in entity queue → should not infinite loop

## Success Metrics

- ✅ Can find entities in logs (>95% accuracy)
- ✅ Can identify patterns in <30 seconds for 1000 log entries
- ✅ Root cause analysis completes in <5 iterations
- ✅ No infinite loops or crashes
- ✅ Graceful handling of all error conditions
- ✅ Clear, actionable summaries generated

## File Structure

```
src/core/analyzer.py           # Main LogAnalyzer class (500+ lines)
src/core/analysis_state.py     # State management (100 lines)
src/core/analysis_config.py    # Configuration (50 lines)
tests/test_analyzer.py          # Comprehensive tests (400+ lines)
tests/test_workflows.py         # Workflow-specific tests (300+ lines)
```

## Implementation Order

1. ✅ Create basic LogAnalyzer class structure
2. ✅ Implement entity_lookup workflow (simplest)
3. ✅ Test entity_lookup with sample logs
4. ✅ Implement flow_trace workflow
5. ✅ Test flow_trace
6. ✅ Implement root_cause_analysis workflow
7. ✅ Add iterative exploration logic
8. ✅ Add mode selection logic
9. ✅ Add stop conditions
10. ✅ Test root_cause workflow
11. ✅ Add result aggregation
12. ✅ Add summary generation
13. ✅ Comprehensive integration testing
14. ✅ Performance optimization

## Next: Phase 5 Preview

Once Phase 4 is complete, Phase 5 will add:
- CLI commands wrapping the analyzer
- Pretty-printed output formatting
- Interactive mode
- Configuration file support
- Export to JSON/CSV/HTML

**Phase 4 is the core engine. Phase 5 is the user interface.**

