# High-Level Design: Smart LLM-Orchestrated Log Analysis Engine

**Version**: 2.0  
**Date**: December 2, 2025  
**Status**: DRAFT for Review  
**Objective**: Transform from method-centric to tool-centric architecture for truly intelligent log analysis

---

## Executive Summary

**Current Problem**: System has predefined methods with hardcoded workflows. LLM only picks from a menu, limiting flexibility and intelligence.

**Proposed Solution**: Shift to ReAct (Reason + Act) pattern where LLM orchestrates analysis using primitive tools, making decisions at each step based on observations.

**Key Change**: LLM becomes the brain that plans and executes; code becomes hands that provide atomic operations.

**Scope**: Single-query focused system. Multi-query context management deferred to future phase.

---

## 1. Architecture Comparison

### 1.1 Current Architecture (Method-Centric)

```
┌─────────────────────────────────────────────┐
│           User Query                        │
└──────────────────┬──────────────────────────┘
                   ↓
         ┌─────────────────────┐
         │  LLMQueryParser     │ Parse query
         └──────────┬──────────┘
                   ↓
         ┌─────────────────────┐
         │ WorkflowOrchestrator│ Code orchestrates
         │  + DecisionAgent    │ LLM picks method
         └──────────┬──────────┘
                   ↓
     ┌─────────────┴─────────────┐
     │   7 Predefined Methods    │
     │ ┌─────────────────────┐   │
     │ │ direct_search       │   │ ← Rigid
     │ │ iterative_search    │   │ ← Hardcoded
     │ │ pattern_analysis    │   │ ← Fixed workflow
     │ │ timeline_analysis   │   │
     │ │ root_cause_analysis │   │
     │ │ relationship_mapping│   │
     │ │ summarization       │   │
     │ └─────────────────────┘   │
     └───────────────────────────┘
                   ↓
         Hardcoded Success Check
```

**Limitations**:
- ❌ Fixed 7 methods - what if query needs method #8?
- ❌ Hardcoded workflows inside each method
- ❌ LLM just picks from menu, doesn't truly think
- ❌ Success criteria rigid
- ❌ Can't handle novel query patterns

---

### 1.2 New Architecture (Tool-Centric, ReAct Pattern)

```
┌─────────────────────────────────────────────┐
│           User Query                        │
└──────────────────┬──────────────────────────┘
                   ↓
         ┌─────────────────────┐
         │   Query Analyzer    │ Understand intent
         │   (LLM)             │ Identify entities
         └──────────┬──────────┘
                   ↓
    ┌──────────────────────────────────┐
    │   ReAct Orchestrator (LLM Loop)  │
    │                                   │
    │  Loop until satisfied:            │
    │  1. REASON (LLM thinks)          │ ← LLM orchestrates
    │  2. ACT (call tool)              │ ← Code executes
    │  3. OBSERVE (see results)        │ ← LLM evaluates
    │  4. DECIDE (continue or stop)    │ ← LLM decides
    └──────────────┬───────────────────┘
                   ↓
     ┌─────────────────────────────────┐
     │    Primitive Tool Library        │
     │  (Atomic operations only)        │
     │                                  │
     │  🔧 search_logs(value)           │ ← Simple
     │  🔧 filter_logs(condition)       │ ← Composable
     │  🔧 extract_entities(types)      │ ← Flexible
     │  🔧 count_by(entity_type)        │
     │  🔧 aggregate(entity_type)       │
     │  🔧 analyze_errors()             │
     │  🔧 build_timeline()             │
     └──────────────────────────────────┘
```

**Advantages**:
- ✅ LLM composes tools to solve ANY query
- ✅ No hardcoded workflows
- ✅ Adapts if first approach fails
- ✅ Handles novel queries naturally
- ✅ LLM decides when to stop (not code)

---

## 2. Components to Remove

### 2.1 Deprecated Components

| Component | File | Reason for Removal |
|-----------|------|-------------------|
| `WorkflowOrchestrator` | `src/core/workflow_orchestrator.py` | Replaced by ReActOrchestrator |
| `DecisionAgent` | `src/core/decision_agent.py` | LLM now makes all decisions |
| `DirectSearchMethod` | `src/core/methods/direct_search.py` | Replaced by primitive tools |
| `IterativeSearchMethod` | `src/core/methods/iterative_search.py` | LLM decides iteration strategy |
| `PatternAnalysisMethod` | `src/core/methods/pattern_analysis.py` | Becomes tool |
| `TimelineAnalysisMethod` | `src/core/methods/timeline_analysis.py` | Becomes tool |
| `RootCauseAnalysisMethod` | `src/core/methods/root_cause_analysis.py` | LLM does reasoning |
| `RelationshipMappingMethod` | `src/core/methods/relationship_mapping.py` | LLM handles relationships |
| `SummarizationMethod` | `src/core/methods/summarization.py` | LLM summarizes naturally |
| `BaseMethod` | `src/core/methods/base_method.py` | No longer needed |
| `AnalysisContext` | `src/core/analysis_context.py` | Replaced by simpler state |
| `LLMBridgeSelector` | `src/core/llm_bridge_selector.py` | LLM decides bridges directly |
| `IterativeSearchStrategy` | `src/core/iterative_search.py` | LLM plans iteration |

### 2.2 Components to Keep and Refactor

| Component | File | New Role |
|-----------|------|----------|
| `LogProcessor` | `src/core/log_processor.py` | Core tool: search/filter logs |
| `EntityManager` | `src/core/entity_manager.py` | Core tool: extract entities |
| `LogChunker` | `src/core/chunker.py` | Tool: chunk large results |
| `OllamaClient` | `src/llm/ollama_client.py` | Keep as-is (LLM interface) |
| `PromptBuilder` | `src/llm/prompts.py` | Enhanced for ReAct prompts |
| `ConfigManager` | `src/utils/config.py` | Keep as-is |

---

## 3. New Architecture Components

### 3.1 Core Components

#### **3.1.1 ReActOrchestrator**
**File**: `src/core/react_orchestrator.py`

**Responsibility**: Main engine that runs LLM reasoning loop

**Interface**:
```python
class ReActOrchestrator:
    def execute(self, query: str) -> AnalysisResult:
        """
        Execute ReAct loop for user query.
        
        Loop:
        1. Ask LLM: What to do next?
        2. Execute tool LLM requested
        3. Show results to LLM
        4. Ask LLM: Are we done?
        5. Repeat until done or max iterations
        """
```

**Key Features**:
- Maintains conversation with LLM
- Tracks tool usage history
- Enforces max iterations (safety)
- Returns comprehensive result with reasoning trace

---

#### **3.1.2 ToolRegistry**
**File**: `src/core/tool_registry.py`

**Responsibility**: Catalog of all available tools with descriptions

**Interface**:
```python
class ToolRegistry:
    def register_tool(self, tool: Tool):
        """Register a tool for LLM to use"""
    
    def get_tool(self, name: str) -> Tool:
        """Get tool by name"""
    
    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions for LLM"""
```

**Tool Description Format**:
```
Tool: search_logs
Description: Search for logs containing a specific value
Parameters:
  - value (str): Text to search for
  - columns (list[str], optional): Specific columns to search
Returns: DataFrame with matching logs
Example: search_logs("MAWED07T01")
```

---

#### **3.1.3 Tool Base Class**
**File**: `src/core/tools/base_tool.py`

**Responsibility**: Abstract base for all tools

**Interface**:
```python
class Tool:
    name: str
    description: str
    parameters: Dict[str, ParameterSpec]
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute tool operation"""
    
    def to_description(self) -> str:
        """Format for LLM consumption"""
```

---

### 3.2 Primitive Tools Library

#### **3.2.1 Log Search & Filter Tools**

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `search_logs` | Find logs containing value | `value: str` | DataFrame of matching logs |
| `filter_by_time` | Filter logs by time range | `start: str, end: str` | Filtered DataFrame |
| `filter_by_severity` | Filter by log level | `severities: list[str]` | Filtered DataFrame |
| `filter_by_field` | Filter by field condition | `field: str, value: str` | Filtered DataFrame |
| `get_log_count` | Count logs | `logs: DataFrame` | int |

#### **3.2.2 Entity Tools**

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `extract_entities` | Extract entities from logs | `logs: DataFrame, types: list[str]` | Dict[type, list[values]] |
| `count_entities` | Count occurrences of entity | `logs: DataFrame, entity_type: str` | Dict[value, count] |
| `find_entity_relationships` | Find co-occurring entities | `logs: DataFrame, entity1: str, entity2: str` | List[tuples] |
| `aggregate_entities` | Get all unique entities | `logs: DataFrame, entity_types: list[str]` | Dict[type, list[values]] |

#### **3.2.3 Analysis Tools**

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `detect_errors` | Find error logs | `logs: DataFrame` | List[error_logs] |
| `build_timeline` | Create chronological event list | `logs: DataFrame` | List[events] |
| `find_patterns` | Identify patterns (LLM-assisted) | `logs: DataFrame, sample_size: int` | List[patterns] |
| `calculate_statistics` | Get stats on entities/logs | `logs: DataFrame` | Dict[metric, value] |

#### **3.2.4 Utility Tools**

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `sample_logs` | Get sample of logs | `logs: DataFrame, n: int` | DataFrame |
| `format_logs` | Format logs for display | `logs: DataFrame, format: str` | str |
| `check_empty` | Check if result is empty | `data: any` | bool |
| `normalize_term` | Expand search term with variants | `term: str` | List[str] (variants) |
| `fuzzy_search` | Search with term variations | `term: str, logs: DataFrame` | DataFrame |

---

### 3.3 ReAct Prompt System

#### **3.3.1 System Prompt**

```markdown
You are an expert DOCSIS cable modem log analyst. Your job is to answer user questions 
by using available tools to search and analyze logs.

ENTITY RELATIONSHIPS (loaded from config/entity_mappings.yaml):
{formatted_relationships_from_config}

These are KNOWN direct relationships in your log data. Use these as primary paths.

DOCSIS DOMAIN KNOWLEDGE (your internal knowledge):
- Network Hierarchy: CPE → CM → RPD → MD_ID → CMTS
- RPDs (Remote PHY Devices) serve cable modems (CMs)
- CMs are identified by MAC addresses (cm_mac)
- Each CM belongs to a modem domain (MD_ID)
- Service packages are associated with MD_IDs, not individual CMs
- RPD errors cascade to downstream CMs
- Use config relationships for direct lookups, domain knowledge for reasoning/escalation

AVAILABLE TOOLS:
{tool_descriptions}

YOUR PROCESS (ReAct Loop):
1. REASON: Think about what you need to do next to answer the question
2. ACT: Choose ONE tool to call with specific parameters
3. OBSERVE: See the results from the tool
4. EVALUATE: Decide if you have enough information to answer
5. ADAPT: If results are empty or insufficient, try alternative approach
6. Repeat until you can answer or conclude it's not possible

OUTPUT FORMAT:
{
  "reasoning": "Your step-by-step thinking, including why you chose this approach",
  "tool": "tool_name" | null,
  "parameters": {"param": "value"},
  "answer": "Final answer if done" | null,
  "confidence": 0.0-1.0,
  "done": true/false,
  "adaptation_needed": true/false
}

INTELLIGENCE RULES:

1. TERM NORMALIZATION
   - User says "registration" → try ["registration", "register", "reg", "registered"]
   - User says "error" → try ["error", "err", "fail", "failure", "exception"]
   - Use normalize_term tool or fuzzy_search for variants
   
2. ZERO RESULTS = ADAPT STRATEGY
   - If exact search returns 0 → try normalized terms
   - If severity filter returns 0 → broaden severity
   - If keyword search returns 0 → try related keywords
   - If entity not found → consider parent/related entities
   
3. SMART ESCALATION (Entity Hierarchy)
   - Hierarchy: CPE → CM → RPD → MD_ID → CMTS
   - If no issues at level X → check parent (level X+1)
   - Example: No CM errors? Check RPD logs
   - Example: No direct relationship? Try bridge entities
   
4. ENTITY TYPE FLEXIBILITY
   - "cms" could mean: cm, cm_mac, or both
   - "modems" = same as cms
   - When in doubt, extract multiple entity types
   
5. PROGRESSIVE SEARCH REFINEMENT
   - Start narrow (exact match, ERROR only)
   - Broaden if needed (fuzzy match, WARNING too)
   - Escalate if still empty (parent entity, related entities)
   
6. STOP CONDITIONS
   - Found what user asked for → DONE
   - Tried 3+ reasonable approaches with no results → explain why
   - Max iterations reached → return best effort answer
```

#### **3.3.2 Conversation Template**

```
[Iteration 1]
USER: find all cms connected to rpd MAWED07T01

ASSISTANT (Reasoning):
{
  "reasoning": "User wants all CMs (cable modems) connected to RPD MAWED07T01. 
   In DOCSIS, RPD logs directly mention CMs. I should:
   1. Search for logs containing 'MAWED07T01'
   2. Extract cm_mac entities from those logs
   Starting with step 1.",
  "tool": "search_logs",
  "parameters": {"value": "MAWED07T01"},
  "answer": null,
  "done": false
}

[Iteration 2]
SYSTEM (Observation):
Tool 'search_logs' returned: 3 logs found
Sample: [log1, log2, log3]

ASSISTANT (Reasoning):
{
  "reasoning": "Found 3 logs with MAWED07T01. Now I need to extract CM entities.
   CMs are typically identified by MAC addresses (cm_mac). Let me extract those.",
  "tool": "extract_entities",
  "parameters": {
    "logs": "<from_previous>",
    "types": ["cm_mac", "cm"]
  },
  "answer": null,
  "done": false
}

[Iteration 3]
SYSTEM (Observation):
Tool 'extract_entities' returned: 
{
  "cm_mac": ["1c:93:7c:2a:72:c3", "28:7a:ee:c9:66:4a"],
  "cm": []
}

ASSISTANT (Final Answer):
{
  "reasoning": "Found 2 CM MAC addresses in logs with MAWED07T01. 
   These are the CMs connected to this RPD. Question is answered.",
  "tool": null,
  "parameters": null,
  "answer": "Found 2 CMs connected to RPD MAWED07T01:\n1. 1c:93:7c:2a:72:c3\n2. 28:7a:ee:c9:66:4a",
  "confidence": 0.95,
  "done": true
}
```

---

## 4. Data Flow

### 4.1 Request Flow

```
1. User Query
   ↓
2. Query Analyzer (LLM)
   - Understand intent
   - Identify entities/values in query
   - Suggest entity type mappings
   ↓
3. ReAct Loop Initialization
   - Create empty tool history
   - Set max_iterations = 10
   - Load tool registry
   ↓
4. ReAct Iteration
   ├─ Build prompt with:
   │  ├─ Original query
   │  ├─ Tool descriptions
   │  ├─ Previous tool calls & results
   │  └─ Domain knowledge
   ├─ LLM decides:
   │  ├─ Reasoning
   │  ├─ Tool to call (or done)
   │  └─ Parameters
   ├─ Execute tool
   ├─ Collect result
   └─ Add to history
   ↓
5. Check Exit Conditions
   - LLM says done? → Exit with answer
   - Max iterations? → Exit with partial
   - Error? → Exit with error
   - Otherwise → Go to step 4
   ↓
6. Format Result
   - Answer text
   - Reasoning trace
   - Tools used
   - Confidence score
```

### 4.2 State Management

```python
class ReActState:
    """Maintains state during ReAct loop"""
    
    original_query: str
    max_iterations: int = 10
    current_iteration: int = 0
    
    # Tool execution history
    tool_history: List[ToolExecution] = []
    
    # Cached data (avoid re-reading logs)
    loaded_logs: Optional[DataFrame] = None
    filtered_logs: Optional[DataFrame] = None
    
    # Results
    answer: Optional[str] = None
    confidence: float = 0.0
    done: bool = False
```

---

## 5. Example Scenarios

### 5.1 Simple Query: "find all cms connected to rpd MAWED07T01"

**LLM Plan**:
1. Search logs for "MAWED07T01"
2. Extract cm_mac entities
3. Answer: Found 2 CMs

**Tool Sequence**:
- `search_logs("MAWED07T01")` → 3 logs
- `extract_entities(logs, ["cm_mac"])` → 2 MACs
- Done

**Iterations**: 2

---

### 5.2 Complex Query: "find mdid for cm 28:7a:ee:c9:66:4a"

**LLM Plan**:
1. Search logs for MAC address
2. Try to extract md_id from those logs
3. If not found, search for RPD in those logs
4. Search RPD logs for md_id

**Tool Sequence**:
- `search_logs("28:7a:ee:c9:66:4a")` → 31 logs
- `extract_entities(logs, ["md_id"])` → Found: 0x6a030000
- Done (found in step 2, no iteration needed!)

**Iterations**: 2

**Alternative** (if not found directly):
- `search_logs("28:7a:ee:c9:66:4a")` → 31 logs
- `extract_entities(logs, ["md_id"])` → Empty
- `extract_entities(logs, ["rpdname"])` → MAWED07T01
- `search_logs("MAWED07T01")` → 3 logs
- `extract_entities(logs, ["md_id"])` → 0x6a030000
- Done

**Iterations**: 5

---

### 5.3 Analytical Query: "which cm had most errors yesterday"

**LLM Plan**:
1. Filter logs by time (yesterday)
2. Filter by severity (ERROR)
3. Extract all cm_mac entities
4. Count errors per cm_mac
5. Return top 1

**Tool Sequence**:
- `filter_by_time(logs, "yesterday", "yesterday")` → subset
- `filter_by_severity(logs, ["ERROR", "CRITICAL"])` → errors only
- `extract_entities(logs, ["cm_mac"])` → list of MACs
- `count_entities(logs, "cm_mac")` → {mac: count}
- Format answer with top MAC

**Iterations**: 4-5

---

### 5.4 Novel Query: "show me timeline of cm x registration"

**LLM Plan** (with smart normalization):
1. Search for cm x
2. Try filter with "registration" 
3. If empty → normalize term and retry
4. Build timeline
5. Format chronologically

**Tool Sequence**:
- `search_logs("x")` → 31 logs
- `filter_by_field(logs, "message", "registration")` → 0 logs ❌
- `normalize_term("registration")` → ["registration", "register", "reg", "registered"]
- `fuzzy_search(logs, ["reg", "register"])` → 5 logs ✅
- `build_timeline(logs)` → chronological events
- Format and return

**Iterations**: 5-6

**Key Intelligence**: 
- Recognizes zero results = try alternatives
- Uses term normalization automatically
- Doesn't give up after first attempt

---

### 5.5 Adaptive Query: "find errors for cm x" (with escalation)

**LLM Plan** (multi-level fallback):
1. Search cm x logs
2. Filter by ERROR severity
3. If none → try WARNING
4. If none → try keyword search ("fail", "timeout")
5. If none → escalate to parent (RPD)

**Tool Sequence**:
- `search_logs("cm_x")` → 20 logs
- `filter_by_severity(logs, ["ERROR"])` → 0 logs
- `filter_by_severity(logs, ["WARNING"])` → 0 logs
- `fuzzy_search(logs, ["fail", "timeout", "retry"])` → 2 logs ✅
- Return: "Found 2 potentially problematic logs (no explicit errors)"

**Alternative** (if still nothing found):
- `extract_entities(cm_logs, ["rpdname"])` → RPD_Y
- `search_logs("RPD_Y")` → 50 logs
- `filter_by_severity(logs, ["ERROR"])` → 3 logs
- Return: "No direct CM errors, but RPD RPD_Y has 3 errors that may affect this CM"

**Iterations**: 6-8

**Key Intelligence**:
- Multiple fallback strategies
- Understands entity hierarchy (CM → RPD)
- Knows when to escalate to parent entity
- Provides context even when no exact match

---

## 6. Implementation Phases

### Phase 1: Foundation (Week 1) ✅ COMPLETE
**Goal**: Build ReAct infrastructure

- [x] Create `ReActOrchestrator` class
- [x] Create `ToolRegistry` and `Tool` base class
- [x] Design ReAct prompt templates
- [x] Implement state management
- [x] Build tool execution framework
- [x] Add logging and tracing

**Deliverable**: Working ReAct loop (even with 1 dummy tool) ✅

**Status**: Completed December 2, 2025. See `PHASE1_COMPLETE.md` for details.

---

### Phase 2: Core Tools (Week 1-2)
**Goal**: Implement primitive tools

- [ ] Log search tools (5 tools)
  - search_logs, filter_by_time, filter_by_severity, filter_by_field, get_log_count
- [ ] Entity tools (4 tools)
  - extract_entities, count_entities, aggregate_entities, find_entity_relationships
- [ ] Basic analysis tools (2 tools)
  - detect_errors, calculate_statistics
- [ ] Smart search tools (2 tools)
  - normalize_term, fuzzy_search

**Deliverable**: 13 working primitive tools

---

### Phase 3: Advanced Tools (Week 2)
**Goal**: Add analytical capabilities

- [ ] Timeline tool
- [ ] Pattern detection (LLM-assisted)
- [ ] Utility tools (sample, format)
- [ ] Tool documentation generator

**Deliverable**: Complete tool library

---

### Phase 4: Integration & Testing (Week 2-3)
**Goal**: End-to-end functionality

- [ ] Remove old components
- [ ] Update CLI to use ReActOrchestrator
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Error handling

**Deliverable**: Production-ready system

---

### Phase 5: Refinement (Week 3)
**Goal**: Polish and optimize

- [ ] Prompt engineering for better LLM decisions
- [ ] Add tool result caching
- [ ] Improve error messages
- [ ] Add examples/documentation
- [ ] Performance benchmarking

**Deliverable**: Polished, documented system

---

## 7. Key Design Principles

### 7.0 Intelligence Through Adaptability

**Principle**: LLM should adapt strategy when direct approach fails

#### **7.0.1 Term Normalization & Fuzzy Matching**

**Problem**: User says "registration" but logs have "reg", "register", "registered", etc.

**Solution**: Smart term expansion

```python
# Tool: normalize_term
Input: "registration"
Output: ["registration", "register", "registered", "reg", "registering"]

# Tool: fuzzy_search
# Automatically tries variants until finds matches
```

**Examples**:
- "error" → ["error", "err", "failure", "fail", "exception", "critical"]
- "offline" → ["offline", "down", "disconnected", "unreachable"]
- "CM" → ["cm", "cable modem", "modem", "cm_mac", "cablemodem"]

**Implementation Options**:
1. **Hardcoded mappings** (config file) - Simple, fast
2. **Fuzzy string matching** (Levenshtein distance) - More flexible
3. **Vector DB semantic search** (future) - Most intelligent

**For v2.0**: Start with config-based mappings, LLM can choose variants

---

#### **7.0.2 Smart Fallback & Escalation Strategy**

**Principle**: If first approach fails, LLM tries alternatives

**Scenario 1**: User asks "find errors for cm x"

```
LLM Strategy (Multi-level fallback):

Attempt 1: Direct error search
→ search_logs("cm_x") 
→ filter_by_severity(["ERROR", "CRITICAL"])
→ Result: 0 logs found

Attempt 2: Broaden to warnings
→ filter_by_severity(["ERROR", "CRITICAL", "WARNING"])
→ Result: 0 logs found

Attempt 3: Semantic error detection
→ Search for problematic keywords: ["fail", "timeout", "retry", "reject"]
→ Result: 2 logs found with "timeout"

Attempt 4: Escalate to parent (RPD)
→ extract_entities(cm_logs, ["rpdname"]) → RPD_Y
→ search_logs("RPD_Y")
→ filter_by_severity(["ERROR"])
→ Result: Found RPD errors affecting this CM
```

**Key Intelligence**:
- LLM recognizes zero results = try different approach
- Gradually broaden scope (error → warning → keyword → parent entity)
- Knows entity hierarchy: CM ← RPD ← MD_ID
- Stops when finds something meaningful

---

**Scenario 2**: User asks "show timeline of cm x registration"

```
LLM Strategy (Term normalization + fallback):

Attempt 1: Exact match
→ search_logs("cm_x")
→ filter_by_field("message", "registration")
→ Result: 0 logs

Attempt 2: Normalized terms
→ normalize_term("registration") → ["registration", "register", "reg", "registered"]
→ Search with all variants
→ Result: 5 logs found with "reg"

Attempt 3: Semantic search (if still empty)
→ Search for related terms: ["online", "init", "provisioning"]
→ Result: More context
```

---

**Scenario 3**: Entity not found - Escalate hierarchy

```
Query: "find errors for cm x"

Strategy:
1. Try direct CM logs → No errors
2. Extract RPD from CM logs
3. Search RPD logs → Found errors
4. Answer: "No direct CM errors, but RPD Y has errors affecting this CM"

Entity Hierarchy:
CPE → CM → RPD → MD_ID → CMTS
 ↑                         ↑
downstream              upstream
```

**Escalation Rules (LLM knows)**:
- **Go UP** (to parent): When no direct issues found, check if parent has problems
- **Go DOWN** (to children): When parent has issues, check which children affected
- **Go SIDEWAYS**: Check related entities (same RPD, same MD_ID)

---

#### **7.0.3 Adaptive Search Strategies**

**Matrix of Strategies**:

| User Intent | Found Direct Results? | LLM Action |
|-------------|----------------------|------------|
| Find errors for X | Yes | Return errors |
| Find errors for X | No, but warnings | Return warnings with explanation |
| Find errors for X | No results | 1. Try keywords<br>2. Check parent entity<br>3. Report "no issues found" |
| Timeline of X event | No exact match | Normalize terms, retry |
| Find Y for X | Y in X logs | Return directly |
| Find Y for X | Y not in X logs | Bridge search via related entities |
| All X with errors | Some found | Return found entities |
| All X with errors | None found | Explain "no X has errors in this dataset" |

---

## 7. Key Design Decisions

### 7.1 Why ReAct Pattern?

**Alternatives Considered**:
1. **Chain-of-Thought**: LLM plans everything upfront
   - ❌ Can't adapt if plan fails
   - ❌ No intermediate feedback
   
2. **Function Calling**: LLM calls multiple functions
   - ❌ Still limited to predefined functions
   - ❌ Less flexible
   
3. **ReAct (Chosen)**: Reason → Act → Observe loop
   - ✅ Adapts based on observations
   - ✅ Can try different approaches
   - ✅ Self-correcting
   - ✅ Handles novel situations

### 7.2 Single Query Focus

**Why**: Simplicity and clarity for v2.0

**Future**: Multi-query conversation with context management
- Session memory
- Reference previous queries
- Build on previous findings

### 7.3 Tool Granularity

**Principle**: Tools should be atomic but meaningful

**Too Fine-Grained**: `read_log_line()`, `extract_one_entity()`
- ❌ Too many LLM calls
- ❌ Expensive and slow

**Too Coarse-Grained**: `analyze_everything()`
- ❌ Not composable
- ❌ Back to rigid methods

**Just Right**: `search_logs()`, `extract_entities()`
- ✅ Atomic operations
- ✅ Composable
- ✅ Reusable

### 7.4 Safety Mechanisms

**Max Iterations**: 10 (configurable)
- Prevent infinite loops
- Reasonable for most queries

**Tool Timeout**: 30s per tool
- Prevent hanging

**Result Size Limits**: 
- Max logs per result: 1000
- Max entities: 500
- Prevents memory issues

**Cost Control**:
- Track LLM token usage
- Warn if exceeding budget
- Suggest optimization

---

## 8. Benefits & Trade-offs

### 8.1 Benefits

| Aspect | Improvement |
|--------|-------------|
| **Flexibility** | Can handle any query pattern, not just predefined ones |
| **Adaptability** | Adjusts strategy if first approach fails |
| **Maintainability** | Add tools, not complex workflows |
| **Transparency** | Full reasoning trace for every decision |
| **Intelligence** | LLM truly thinks, not just picks from menu |
| **Extensibility** | New tools = new capabilities automatically |

### 8.2 Trade-offs

| Concern | Mitigation |
|---------|------------|
| **LLM Latency** | Cache tool descriptions, optimize prompts |
| **Cost per Query** | More LLM calls → higher cost | Monitor and set budgets |
| **Unpredictability** | LLM might take unexpected path | Add guardrails, validate tool params |
| **Error Handling** | LLM might call wrong tool | Tool parameter validation, clear errors |
| **Debugging** | Complex reasoning chain | Comprehensive logging and trace visualization |

### 8.3 Performance Expectations

| Metric | Current | Target |
|--------|---------|--------|
| Simple Query (find X) | 5-10s | 3-5s |
| Complex Query (relationships) | 10-30s | 8-15s |
| Analytical Query | 20-60s | 15-30s |
| LLM Calls per Query | 3-8 | 2-5 |
| Success Rate | 70% | 90% |

---

## 9. Migration Strategy

### 9.1 Backward Compatibility

**Not Maintained**: This is a breaking architectural change

**Why**: Clean break allows clean design without legacy baggage

### 9.2 Migration Path

**Week 1**: Build new system in parallel
- Keep old code intact
- New code in separate modules

**Week 2**: Switch CLI to new system
- Update `src/cli/main.py` to use `ReActOrchestrator`
- Run tests on both systems

**Week 3**: Remove old code
- Delete deprecated methods
- Clean up imports
- Update documentation

### 9.3 Rollback Plan

Keep old code in `src/core/legacy/` until new system proven stable (2-3 weeks)

---

## 10. Success Metrics

### 10.1 Functional Metrics

- [ ] Can handle 20 different query patterns
- [ ] 90%+ success rate on test queries
- [ ] Adapts when first strategy fails
- [ ] Provides reasoning for all decisions

### 10.2 Performance Metrics

- [ ] Average query time < 15s
- [ ] 95th percentile < 30s
- [ ] Max 5 LLM calls per query average

### 10.3 Quality Metrics

- [ ] LLM chooses appropriate tools 95% of time
- [ ] Stops at right time (not too early/late)
- [ ] Answers are accurate and complete
- [ ] Error messages are clear and actionable

---

## 11. Risks & Mitigations

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| LLM makes poor tool choices | Medium | High | Better prompts, examples, domain knowledge |
| Infinite loops | Low | High | Max iterations, cycle detection |
| High latency | Medium | Medium | Prompt optimization, caching |
| Unpredictable behavior | Medium | Medium | Comprehensive testing, guardrails |

### 11.2 Implementation Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Underestimate complexity | Medium | High | Phased approach, MVP first |
| Breaking existing functionality | Low | High | Parallel development, testing |
| Tool design too fine/coarse | Medium | Medium | Iterate based on testing |

---

## 12. Future Enhancements (Out of Scope for v2.0)

### 12.1 Vector Database for Domain Knowledge
**Priority**: High (Phase 2 enhancement)

- Store DOCSIS domain knowledge in vector DB
- Semantic search for entity relationships
- Abbreviation/alias mappings (reg→registration, CM→cable modem)
- Common troubleshooting patterns
- Historical query patterns and solutions
- Auto-expand search terms using semantic similarity

**Benefits**:
- LLM can query knowledge base for context
- Better term normalization
- Learn from past queries
- Scalable knowledge management

### 12.2 Multi-Query Conversations
- Session memory across queries
- Reference previous findings
- Build on earlier analysis

### 12.3 Advanced Context Management
- Smart log chunking for large datasets
- Intelligent caching strategies

### 12.3 Learning & Optimization
- Learn from successful query patterns
- Optimize tool selection over time
- User feedback incorporation

### 12.4 Collaborative Analysis
- Multi-agent collaboration (specialized LLMs)
- Parallel tool execution
- Consensus building

### 12.5 Visualization
- Interactive timeline visualization
- Entity relationship graphs
- Real-time query progress

---

## 13. Open Questions for Discussion

1. **Tool Granularity**: Are the proposed tools at the right level? Too fine/coarse?
   - ✅ **Resolved**: Added normalize_term and fuzzy_search tools

2. **Max Iterations**: Is 10 iterations enough? Too many?
   - ✅ **Resolved**: 10 is good, with adaptive strategies might use 6-8 average

3. **Term Normalization Approach**: Config-based or Vector DB?
   - **Recommendation**: Start with config file (v2.0), migrate to Vector DB (v2.1)
   - Config: `term_mappings.yaml` with common variants
   - Vector DB: Semantic similarity search (future)

4. **Escalation Boundaries**: When should LLM stop escalating?
   - **Recommendation**: Max 2 levels up in hierarchy
   - Example: CM → RPD ✓, CM → RPD → MD_ID → CMTS ✗ (too far)

5. **Error Handling**: How should LLM handle tool errors? Retry? Skip? Alternative approach?
   - **Recommendation**: LLM decides based on error type
   - Tool timeout → Retry with smaller scope
   - Invalid parameter → Try alternative tool
   - No results → Adapt strategy (as designed)

6. **Caching Strategy**: Should tools cache results within a query? Across queries?
   - **Recommendation**: 
     - Within query: Yes (cache loaded logs)
     - Across queries: No (for v2.0 - single query focus)

7. **Zero Results Threshold**: How many empty results before declaring "not found"?
   - **Recommendation**: After 3 different approaches, explain why not found
   - Don't exhaust all possibilities, be efficient

8. **Confidence Scoring**: How to calculate confidence for adaptive answers?
   - **Recommendation**: 
     - Direct match: 0.9-1.0
     - Normalized term match: 0.7-0.9
     - Escalated/related entity: 0.5-0.7
     - Partial/inconclusive: 0.3-0.5

---

## 14. Appendix

### 14.1 File Structure (New)

```
src/
├── core/
│   ├── react_orchestrator.py       # NEW: Main ReAct engine
│   ├── tool_registry.py            # NEW: Tool management
│   ├── react_state.py              # NEW: State management
│   ├── tools/                      # NEW: Tool library
│   │   ├── __init__.py
│   │   ├── base_tool.py           # NEW: Tool base class
│   │   ├── search_tools.py        # NEW: Log search/filter
│   │   ├── entity_tools.py        # NEW: Entity operations
│   │   ├── analysis_tools.py      # NEW: Analysis operations
│   │   └── utility_tools.py       # NEW: Helpers
│   ├── log_processor.py           # KEEP: Core log operations
│   ├── entity_manager.py          # KEEP: Entity extraction
│   ├── chunker.py                 # KEEP: Chunking utility
│   └── legacy/                    # OLD CODE (temporary)
│       ├── workflow_orchestrator.py
│       ├── decision_agent.py
│       └── methods/
├── llm/
│   ├── ollama_client.py           # KEEP: LLM interface
│   ├── react_prompts.py           # NEW: ReAct prompt builder
│   └── prompts.py                 # UPDATE: Legacy prompts
├── cli/
│   └── main.py                    # UPDATE: Use ReActOrchestrator
└── utils/
    ├── config.py                  # KEEP
    ├── logger.py                  # KEEP
    └── validators.py              # KEEP
```

### 14.2 Configuration Loading

**How LLM Learns Relationships**:

```python
# 1. Python loads YAML
import yaml
with open('config/entity_mappings.yaml') as f:
    config = yaml.safe_load(f)
    relationships = config['relationships']

# 2. Format as text for LLM
def format_relationships_for_llm(relationships: dict) -> str:
    text = "ENTITY RELATIONSHIPS:\n"
    for entity, related in relationships.items():
        text += f"  - {entity} → {', '.join(related)}\n"
    return text

# 3. Inject into system prompt
system_prompt = base_prompt + format_relationships_for_llm(relationships)

# 4. LLM sees it as text (~300 tokens, 0.2% of context)
```

**Why This Works**:
- ✅ Config is source of truth (version controlled)
- ✅ LLM gets fresh data on every query
- ✅ Tiny token overhead (~300 tokens)
- ✅ Easy to update (just edit YAML)
- ✅ Deployment-specific customization

### 14.3 Dependencies

**New Dependencies**: None (use existing)
- Existing: requests, pandas, pyyaml, click, rich
- LLM: Ollama (already integrated)

### 14.4 Configuration

**New Config Section** (`config/react_config.yaml`):
```yaml
react:
  max_iterations: 10
  tool_timeout_seconds: 30
  max_logs_per_result: 1000
  max_entities_per_result: 500
  enable_caching: true
  verbose_reasoning: true
  max_escalation_levels: 2  # How far up entity hierarchy
  
llm:
  temperature: 0.3  # Lower for consistent tool selection
  max_tokens: 1000
  model: llama3.2

# Term normalization mappings
term_normalization:
  registration:
    - registration
    - register
    - registered
    - registering
    - reg
  
  error:
    - error
    - err
    - fail
    - failure
    - exception
    - critical
    - fatal
  
  offline:
    - offline
    - down
    - disconnected
    - unreachable
    - unavailable
  
  timeout:
    - timeout
    - timed out
    - time-out
    - timedout
  
  cm:
    - cm
    - cable modem
    - modem
    - cablemodem
  
  rpd:
    - rpd
    - remote phy device
    - remote-phy

# Entity hierarchy for smart escalation
entity_hierarchy:
  cpe:
    parent: cm
    related: [cpe_mac, cpe_ip]
  
  cm:
    parent: rpdname
    children: [cpe]
    related: [cm_mac, md_id]
  
  rpdname:
    parent: md_id
    children: [cm]
    related: [ip_address]
  
  md_id:
    parent: cmts
    children: [rpdname, cm]
    related: [package, sf_id]
```

**Future**: Replace term_normalization with Vector DB semantic search

---

## 15. Approval & Next Steps

### Required Approvals
- [ ] Architecture review
- [ ] Design decisions confirmed
- [ ] Tool list finalized
- [ ] Timeline approved

### Post-Approval Actions
1. Create GitHub issue for implementation
2. Set up feature branch
3. Begin Phase 1 implementation
4. Schedule weekly review meetings

---

**Document Status**: DRAFT  
**Next Review Date**: TBD  
**Owner**: Development Team  
**Reviewers**: TBD

---

*End of Document*

