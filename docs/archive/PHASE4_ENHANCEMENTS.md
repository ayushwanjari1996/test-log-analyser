# Phase 4 Enhancements - Advanced Analysis & Root Cause

## 🧠 Core Vision: Intelligent Self-Orchestrating Analysis Engine

### The Problem with Current Design
- Methods are **isolated** - each does one thing, doesn't collaborate
- **Hard-coded routing** - if-else decides what to call
- **Single-shot execution** - runs once and stops
- **No adaptability** - can't change strategy based on findings

### The New Vision: LLM-Orchestrated Workflow
An intelligent system where:
1. **Methods call each other** dynamically based on findings
2. **LLM decides** what to do next at each step (with regex fallback)
3. **Iterates until satisfied** - keeps investigating until answer found
4. **Explainable** - shows reasoning at each decision point
5. **Foolproof** - exhausts all strategies before giving up

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                               │
│              "why is cm x offline"                          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Query Understanding (LLM)                       │
│  • Parse intent: ROOT_CAUSE_ANALYSIS                        │
│  • Extract entities: cm=x                                   │
│  • Identify goal: "Find why entity is offline"              │
│  • Set success criteria: "Found error explaining offline"   │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│           🧠 LLM Decision Agent (Orchestrator)              │
│                                                             │
│  Input:                                                     │
│    - Query intent                                           │
│    - Current context (what we know so far)                  │
│    - Available methods                                      │
│    - Success criteria                                       │
│                                                             │
│  Output:                                                    │
│    - Next method to call                                    │
│    - Parameters for that method                             │
│    - Reasoning for this choice                              │
│    - Confidence in this decision                            │
│                                                             │
│  Fallback: Regex-based decision if LLM fails                │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                 Method Executor                             │
│                                                             │
│  Available Methods:                                         │
│    1. DirectSearch (find entity in logs)                    │
│    2. IterativeSearch (find through entity chains)          │
│    3. PatternAnalysis (analyze log patterns)                │
│    4. TimelineAnalysis (build event timeline)               │
│    5. RootCauseAnalysis (find causal chains)                │
│    6. Summarization (create summary of findings)            │
│    7. RelationshipMapping (map entity connections)          │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Feedback Loop (After Each Step)                │
│                                                             │
│  Questions LLM asks itself:                                 │
│    ✓ Did we answer the query?                               │
│    ✓ Did we find new interesting information?               │
│    ✓ Should we investigate further?                         │
│    ✓ Which entity/method is most promising next?            │
│    ✓ Are we going in circles?                               │
│    ✓ Should we try a different strategy?                    │
│    ✓ Have we exhausted all options?                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
              ┌──────────┴──────────┐
              │                     │
         Answer Found          Continue Search
              │                     │
              ↓                     ↓
      Final Summarization    Loop Back to Decision Agent
```

---

## 📋 Core Components

### Component 1: LLM Decision Agent (The Brain)

**File**: `src/core/decision_agent.py`

**Purpose**: Decides what to do next at each step of analysis

```python
class LLMDecisionAgent:
    """
    The intelligent orchestrator that decides analysis flow.
    
    At each step, it:
    1. Reviews current context (what we know)
    2. Evaluates available methods
    3. Decides the best next action
    4. Provides reasoning for the decision
    5. Falls back to regex rules if LLM fails
    """
    
    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config
        self.max_iterations = 10  # Prevent infinite loops
        
    def decide_next_step(
        self, 
        query_intent: str,
        current_context: AnalysisContext,
        available_methods: List[str],
        iteration: int
    ) -> Decision:
        """
        Decide what to do next.
        
        Args:
            query_intent: What user wants (e.g., "find_root_cause")
            current_context: Everything we know so far
            available_methods: Methods we can call
            iteration: Current iteration number
            
        Returns:
            Decision object with:
                - method: Which method to call
                - params: Parameters for that method
                - reasoning: Why this choice
                - confidence: 0.0-1.0
                - should_stop: Whether to stop after this
        """
        
        # Safety: Prevent infinite loops
        if iteration >= self.max_iterations:
            return Decision(
                method="summarize",
                reasoning="Max iterations reached",
                should_stop=True
            )
        
        # Build decision prompt for LLM
        prompt = self._build_decision_prompt(
            query_intent, current_context, available_methods
        )
        
        try:
            # Ask LLM to decide
            llm_response = self.llm.generate_json(prompt)
            decision = self._parse_decision(llm_response)
            
            # Validate decision makes sense
            if self._validate_decision(decision, current_context):
                return decision
            else:
                # LLM made invalid decision, use fallback
                logger.warning("LLM decision invalid, using fallback")
                return self._fallback_decision(query_intent, current_context)
                
        except Exception as e:
            logger.error(f"LLM decision failed: {e}, using fallback")
            return self._fallback_decision(query_intent, current_context)
    
    def _build_decision_prompt(self, intent, context, methods):
        """Build prompt asking LLM what to do next."""
        return f"""
You are an intelligent log analysis orchestrator. Decide the next step.

QUERY INTENT: {intent}
GOAL: {context.goal}
SUCCESS CRITERIA: {context.success_criteria}

CURRENT ITERATION: {context.iteration}
WHAT WE KNOW SO FAR:
{context.summary()}

FINDINGS SO FAR:
- Entities found: {context.entities}
- Logs analyzed: {context.logs_analyzed} 
- Errors found: {context.errors_found}
- Patterns detected: {context.patterns}

AVAILABLE METHODS:
1. direct_search - Search for specific entity in logs
2. iterative_search - Find entity through related entities
3. pattern_analysis - Analyze patterns in found logs
4. timeline_analysis - Build timeline of events
5. root_cause_analysis - Find causal chains
6. summarization - Summarize findings
7. relationship_mapping - Map entity relationships

PREVIOUS STEPS:
{context.step_history}

Based on this, decide the BEST next action.

DECISION RULES:
- If query answered satisfactorily → choose 'summarization' and stop
- If direct search failed → try 'iterative_search'
- If found errors → do 'root_cause_analysis' or 'timeline_analysis'
- If no errors but entity active → do 'pattern_analysis'
- If interesting entities found → do 'direct_search' on them
- If going in circles → try different method or stop
- If exhausted options → 'summarization' and stop

Return JSON:
{{
  "method": "method_name",
  "params": {{
    "entity_value": "value to search",
    "entity_type": "type if known",
    "search_scope": "focused|broad",
    "max_depth": 2
  }},
  "reasoning": "Why this method is best next step (2-3 sentences)",
  "confidence": 0.85,
  "should_stop": false,
  "expected_outcome": "What we hope to find"
}}
"""
    
    def _fallback_decision(self, intent, context):
        """
        Regex-based fallback decision making.
        Used when LLM fails or gives invalid response.
        """
        
        # Rule 1: No logs found yet → try direct search
        if context.logs_analyzed == 0:
            return Decision(
                method="direct_search",
                params={"entity_value": context.target_entity},
                reasoning="Fallback: Start with direct search",
                confidence=0.9
            )
        
        # Rule 2: Logs found but no errors → try iterative search
        if context.logs_analyzed > 0 and len(context.errors_found) == 0:
            if not context.has_tried("iterative_search"):
                return Decision(
                    method="iterative_search",
                    params={"start_entity": context.target_entity},
                    reasoning="Fallback: No direct errors, trying related entities",
                    confidence=0.7
                )
        
        # Rule 3: Errors found → analyze them
        if len(context.errors_found) > 0:
            if not context.has_tried("root_cause_analysis"):
                return Decision(
                    method="root_cause_analysis",
                    params={"error_logs": context.errors_found},
                    reasoning="Fallback: Found errors, analyzing root cause",
                    confidence=0.85
                )
        
        # Rule 4: New entities found → search them
        if len(context.pending_entities) > 0:
            next_entity = context.pending_entities[0]
            return Decision(
                method="direct_search",
                params={"entity_value": next_entity.value},
                reasoning=f"Fallback: Exploring entity {next_entity.value}",
                confidence=0.75
            )
        
        # Rule 5: Nothing else to try → summarize
        return Decision(
            method="summarization",
            params={},
            reasoning="Fallback: Exhausted all strategies, summarizing findings",
            confidence=1.0,
            should_stop=True
        )
```

---

### Component 2: Analysis Context (Memory)

**File**: `src/core/analysis_context.py`

**Purpose**: Tracks everything we know during analysis

```python
@dataclass
class AnalysisContext:
    """
    Maintains state during multi-step analysis.
    Tracks what we've done, what we found, what's pending.
    """
    
    # Query info
    original_query: str
    query_intent: str  # "find", "analyze", "root_cause", etc.
    goal: str  # "Find why cm x is offline"
    success_criteria: str  # "Found error explaining offline status"
    
    # Target
    target_entity: str
    target_entity_type: str
    
    # Progress tracking
    iteration: int = 0
    step_history: List[Step] = field(default_factory=list)
    methods_tried: Set[str] = field(default_factory=set)
    
    # Findings
    logs_analyzed: int = 0
    all_logs: List[Dict] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)  # type -> values
    errors_found: List[Dict] = field(default_factory=list)
    patterns: List[Dict] = field(default_factory=list)
    relationships: List[Tuple] = field(default_factory=list)
    
    # Entity exploration queue
    pending_entities: List[Entity] = field(default_factory=list)
    explored_entities: Set[str] = field(default_factory=set)
    
    # Results
    answer_found: bool = False
    answer: str = ""
    confidence: float = 0.0
    
    def add_step(self, method: str, params: Dict, result: Dict, reasoning: str):
        """Record a step taken."""
        step = Step(
            iteration=self.iteration,
            method=method,
            params=params,
            result=result,
            reasoning=reasoning,
            timestamp=datetime.now()
        )
        self.step_history.append(step)
        self.methods_tried.add(method)
        self.iteration += 1
    
    def add_logs(self, logs: List[Dict]):
        """Add newly found logs."""
        self.all_logs.extend(logs)
        self.logs_analyzed += len(logs)
    
    def add_entity(self, entity_type: str, entity_value: str, priority: int = 5):
        """Add discovered entity to exploration queue."""
        if entity_value not in self.explored_entities:
            entity = Entity(type=entity_type, value=entity_value, priority=priority)
            self.pending_entities.append(entity)
            self.pending_entities.sort(key=lambda e: e.priority, reverse=True)
    
    def mark_explored(self, entity_value: str):
        """Mark entity as explored."""
        self.explored_entities.add(entity_value)
        self.pending_entities = [e for e in self.pending_entities if e.value != entity_value]
    
    def has_tried(self, method: str) -> bool:
        """Check if method has been tried."""
        return method in self.methods_tried
    
    def is_going_in_circles(self) -> bool:
        """Detect if we're repeating same actions."""
        if len(self.step_history) < 3:
            return False
        
        # Check last 3 steps for repetition
        recent_methods = [s.method for s in self.step_history[-3:]]
        if len(set(recent_methods)) == 1:  # All same method
            return True
        
        # Check if exploring same entities repeatedly
        recent_entities = []
        for step in self.step_history[-3:]:
            if "entity_value" in step.params:
                recent_entities.append(step.params["entity_value"])
        
        if len(recent_entities) >= 2 and len(set(recent_entities)) == 1:
            return True
        
        return False
    
    def summary(self) -> str:
        """Generate human-readable summary of context."""
        return f"""
Target: {self.target_entity_type} '{self.target_entity}'
Goal: {self.goal}
Progress: Iteration {self.iteration}, analyzed {self.logs_analyzed} logs
Entities found: {sum(len(v) for v in self.entities.values())}
Errors found: {len(self.errors_found)}
Methods tried: {', '.join(self.methods_tried)}
Answer found: {self.answer_found}
"""

@dataclass
class Step:
    """Represents one step in analysis."""
    iteration: int
    method: str
    params: Dict
    result: Dict
    reasoning: str
    timestamp: datetime

@dataclass
class Decision:
    """Represents a decision made by LLM or fallback."""
    method: str
    params: Dict = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0
    should_stop: bool = False
    expected_outcome: str = ""
```

---

### Component 3: Workflow Orchestrator (The Engine)

**File**: `src/core/workflow_orchestrator.py`

**Purpose**: Executes the analysis workflow, calling methods based on LLM decisions

```python
class WorkflowOrchestrator:
    """
    Orchestrates multi-step analysis workflow.
    
    This is the main engine that:
    1. Initializes analysis context
    2. Loops: Ask LLM → Execute method → Update context
    3. Continues until answer found or max iterations
    4. Returns comprehensive results
    """
    
    def __init__(
        self,
        processor: LogProcessor,
        entity_manager: EntityManager,
        llm_client: OllamaClient,
        config: ConfigManager
    ):
        self.processor = processor
        self.entity_manager = entity_manager
        self.llm_client = llm_client
        self.config = config
        
        # Initialize decision agent
        self.decision_agent = LLMDecisionAgent(llm_client, config)
        
        # Initialize all analysis methods
        self.methods = {
            "direct_search": DirectSearchMethod(processor, entity_manager),
            "iterative_search": IterativeSearchMethod(processor, entity_manager, llm_client),
            "pattern_analysis": PatternAnalysisMethod(llm_client),
            "timeline_analysis": TimelineAnalysisMethod(llm_client),
            "root_cause_analysis": RootCauseAnalysisMethod(llm_client),
            "summarization": SummarizationMethod(llm_client),
            "relationship_mapping": RelationshipMappingMethod(entity_manager)
        }
        
    def execute(self, query: str) -> AnalysisResult:
        """
        Execute intelligent analysis workflow.
        
        Args:
            query: User's natural language query
            
        Returns:
            AnalysisResult with findings, reasoning, and execution trace
        """
        
        logger.info(f"Starting intelligent analysis for: {query}")
        
        # Step 1: Understand query
        parsed = self._parse_query(query)
        
        # Step 2: Initialize context
        context = AnalysisContext(
            original_query=query,
            query_intent=parsed["intent"],
            goal=parsed["goal"],
            success_criteria=parsed["success_criteria"],
            target_entity=parsed["entity_value"],
            target_entity_type=parsed["entity_type"]
        )
        
        # Step 3: Iterative execution loop
        while context.iteration < self.decision_agent.max_iterations:
            
            logger.info(f"\n{'='*60}")
            logger.info(f"ITERATION {context.iteration + 1}")
            logger.info(f"{'='*60}")
            
            # Check if we're going in circles
            if context.is_going_in_circles():
                logger.warning("Detected circular reasoning, forcing strategy change")
                # Force a different method
                decision = self._get_alternative_decision(context)
            else:
                # Ask LLM: What should we do next?
                decision = self.decision_agent.decide_next_step(
                    query_intent=context.query_intent,
                    current_context=context,
                    available_methods=list(self.methods.keys()),
                    iteration=context.iteration
                )
            
            logger.info(f"Decision: {decision.method}")
            logger.info(f"Reasoning: {decision.reasoning}")
            logger.info(f"Confidence: {decision.confidence:.2f}")
            
            # Execute the chosen method
            result = self._execute_method(decision.method, decision.params, context)
            
            # Update context with results
            self._update_context(context, decision, result)
            
            # Check success criteria
            if self._check_success(context):
                logger.info("✓ Success criteria met!")
                context.answer_found = True
                decision.should_stop = True
            
            # Should we stop?
            if decision.should_stop:
                logger.info("Stopping: LLM decided we're done")
                break
        
        # Step 4: Final summarization
        final_summary = self._generate_final_summary(context)
        
        # Step 5: Build result
        return AnalysisResult(
            success=context.answer_found,
            answer=context.answer or final_summary["summary"],
            confidence=context.confidence,
            logs_analyzed=context.logs_analyzed,
            entities_found=context.entities,
            errors_found=context.errors_found,
            patterns=context.patterns,
            timeline=final_summary.get("timeline", []),
            causal_chain=final_summary.get("causal_chain", []),
            execution_trace=self._build_execution_trace(context),
            iterations=context.iteration,
            summary=final_summary
        )
    
    def _execute_method(self, method_name: str, params: Dict, context: AnalysisContext) -> Dict:
        """Execute a specific analysis method."""
        
        if method_name not in self.methods:
            logger.error(f"Unknown method: {method_name}")
            return {"error": f"Unknown method: {method_name}"}
        
        method = self.methods[method_name]
        
        try:
            # Execute method with context
            result = method.execute(params, context)
            logger.info(f"Method result: {len(result.get('logs', []))} logs, {len(result.get('entities', []))} entities")
            return result
            
        except Exception as e:
            logger.error(f"Method {method_name} failed: {e}")
            return {"error": str(e)}
    
    def _update_context(self, context: AnalysisContext, decision: Decision, result: Dict):
        """Update context with method results."""
        
        # Record the step
        context.add_step(
            method=decision.method,
            params=decision.params,
            result=result,
            reasoning=decision.reasoning
        )
        
        # Add any new logs found
        if "logs" in result:
            context.add_logs(result["logs"])
        
        # Add any entities discovered
        if "entities" in result:
            for entity_type, values in result["entities"].items():
                for value in values:
                    # Priority based on entity type
                    priority = self._get_entity_priority(entity_type, context.query_intent)
                    context.add_entity(entity_type, value, priority)
        
        # Add errors
        if "errors" in result:
            context.errors_found.extend(result["errors"])
        
        # Add patterns
        if "patterns" in result:
            context.patterns.extend(result["patterns"])
        
        # Add relationships
        if "relationships" in result:
            context.relationships.extend(result["relationships"])
        
        # Update answer if found
        if "answer" in result and result["answer"]:
            context.answer = result["answer"]
            context.confidence = result.get("confidence", 0.8)
    
    def _check_success(self, context: AnalysisContext) -> bool:
        """Check if success criteria met."""
        
        # Intent-specific success checks
        if context.query_intent == "root_cause":
            # Need to find at least one error
            return len(context.errors_found) > 0
        
        elif context.query_intent == "find":
            # Need to find logs for target entity
            return context.logs_analyzed > 0
        
        elif context.query_intent == "analyze":
            # Need logs and some insights (patterns or timeline)
            return context.logs_analyzed > 0 and (
                len(context.patterns) > 0 or 
                len(context.step_history) > 1
            )
        
        # Generic: have we found an answer?
        return context.answer_found or len(context.errors_found) > 0
    
    def _get_entity_priority(self, entity_type: str, intent: str) -> int:
        """
        Determine entity exploration priority based on type and query intent.
        Higher = more important to explore.
        """
        
        # For connectivity/offline issues
        if intent == "root_cause" and any(kw in intent for kw in ["offline", "down", "unreachable"]):
            priorities = {
                "rpdname": 10,  # Critical for connectivity
                "ip_address": 9,
                "interface": 8,
                "cm_mac": 7,
                "md_id": 6,
                "sf_id": 4
            }
        # For performance issues
        elif any(kw in intent for kw in ["slow", "latency", "timeout"]):
            priorities = {
                "sf_id": 10,  # Service flows critical for performance
                "md_id": 9,
                "ip_address": 7,
                "cm_mac": 6,
                "rpdname": 5
            }
        # Default priorities
        else:
            priorities = {
                "cm_mac": 8,
                "rpdname": 7,
                "ip_address": 6,
                "md_id": 6,
                "sf_id": 5,
                "interface": 4
            }
        
        return priorities.get(entity_type, 5)  # Default: medium priority
    
    def _generate_final_summary(self, context: AnalysisContext) -> Dict:
        """Generate comprehensive final summary."""
        
        # Use summarization method
        summarizer = self.methods["summarization"]
        return summarizer.execute(
            params={"context": context},
            context=context
        )
    
    def _build_execution_trace(self, context: AnalysisContext) -> List[Dict]:
        """Build detailed execution trace for debugging/display."""
        
        trace = []
        for step in context.step_history:
            trace.append({
                "iteration": step.iteration,
                "method": step.method,
                "reasoning": step.reasoning,
                "params": step.params,
                "result_summary": {
                    "logs_found": len(step.result.get("logs", [])),
                    "entities_found": len(step.result.get("entities", {})),
                    "errors_found": len(step.result.get("errors", []))
                },
                "timestamp": step.timestamp.isoformat()
            })
        return trace
```

---

## 🔧 Analysis Methods (The Tools)

Each method is a self-contained analysis technique. The orchestrator calls them as needed.

### Method 1: Direct Search

```python
class DirectSearchMethod:
    """Search for specific entity directly in logs."""
    
    def execute(self, params: Dict, context: AnalysisContext) -> Dict:
        entity_value = params["entity_value"]
        
        # Search in processor
        logs = self.processor.search_text(entity_value)
        
        # Extract entities from found logs
        entities = self.entity_manager.extract_entities_from_logs(logs)
        
        # Detect errors
        errors = [log for log in logs if log.get("severity") in ["ERROR", "CRITICAL"]]
        
        return {
            "logs": logs,
            "entities": entities,
            "errors": errors
        }
```

### Method 2: Iterative Search

```python
class IterativeSearchMethod:
    """Find entity through chains of related entities."""
    
    def execute(self, params: Dict, context: AnalysisContext) -> Dict:
        start_entity = params["start_entity"]
        max_depth = params.get("max_depth", 3)
        
        # Use existing IterativeSearchStrategy
        strategy = IterativeSearchStrategy(
            processor=self.processor,
            entity_manager=self.entity_manager,
            llm_client=self.llm_client
        )
        
        result = strategy.search(
            target_entity=start_entity,
            max_iterations=max_depth
        )
        
        return result
```

### Method 3: Pattern Analysis

```python
class PatternAnalysisMethod:
    """Analyze patterns in log data using LLM."""
    
    def execute(self, params: Dict, context: AnalysisContext) -> Dict:
        logs = params.get("logs", context.all_logs[-100:])  # Last 100 logs
        
        # Ask LLM to find patterns
        prompt = f"""
Analyze these logs and identify patterns:

{self._format_logs(logs)}

Find:
1. Repeated event sequences
2. Timing patterns (intervals, bursts)
3. State transitions
4. Common entity combinations
5. Anomalies or unusual behavior

Return JSON with patterns found.
"""
        
        response = self.llm_client.generate_json(prompt)
        
        return {
            "patterns": response.get("patterns", []),
            "anomalies": response.get("anomalies", [])
        }
```

### Method 4: Timeline Analysis

```python
class TimelineAnalysisMethod:
    """Build chronological timeline of events."""
    
    def execute(self, params: Dict, context: AnalysisContext) -> Dict:
        logs = params.get("logs", context.all_logs)
        
        # Sort by timestamp
        sorted_logs = sorted(logs, key=lambda x: x.get("timestamp", ""))
        
        # Build timeline with LLM understanding
        prompt = f"""
Build a timeline of key events from these logs:

{self._format_logs(sorted_logs)}

Create a timeline showing:
1. Timestamp
2. Event description
3. Entities involved
4. Event type (normal/warning/error)
5. Impact

Return JSON with timeline array.
"""
        
        response = self.llm_client.generate_json(prompt)
        
        return {
            "timeline": response.get("timeline", []),
            "duration": self._calculate_duration(sorted_logs),
            "event_distribution": self._analyze_distribution(sorted_logs)
        }
```

### Method 5: Root Cause Analysis

```python
class RootCauseAnalysisMethod:
    """Find root cause of errors/issues."""
    
    def execute(self, params: Dict, context: AnalysisContext) -> Dict:
        error_logs = params.get("error_logs", context.errors_found)
        all_logs = context.all_logs
        
        # Build causal chain with LLM
        prompt = f"""
Given these error logs and context, find the root cause:

ERROR LOGS:
{self._format_logs(error_logs)}

CONTEXT (all logs around the time):
{self._format_logs(all_logs[-50:])}

ENTITY RELATIONSHIPS:
{context.relationships}

Analyze:
1. What failed?
2. When did it start?
3. What was happening before the failure?
4. Which entity caused the issue?
5. What's the causal chain?

Return JSON with:
- root_cause: str
- causal_chain: [step1, step2, ...]
- confidence: float
- supporting_evidence: [log excerpts]
"""
        
        response = self.llm_client.generate_json(prompt)
        
        return {
            "root_cause": response.get("root_cause"),
            "causal_chain": response.get("causal_chain", []),
            "confidence": response.get("confidence", 0.5),
            "evidence": response.get("supporting_evidence", []),
            "answer": response.get("root_cause")  # For context.answer
        }
```

### Method 6: Summarization

```python
class SummarizationMethod:
    """Create comprehensive summary of all findings."""
    
    def execute(self, params: Dict, context: AnalysisContext) -> Dict:
        
        prompt = f"""
Summarize the complete analysis:

QUERY: {context.original_query}
GOAL: {context.goal}

WHAT WE DID:
{self._format_steps(context.step_history)}

FINDINGS:
- Logs analyzed: {context.logs_analyzed}
- Entities found: {context.entities}
- Errors found: {len(context.errors_found)}
- Patterns: {len(context.patterns)}

ERRORS (if any):
{self._format_logs(context.errors_found)}

ALL LOGS:
{self._format_logs(context.all_logs[:100])}  # First 100

Create a comprehensive summary including:
1. What happened (high-level)
2. Key findings
3. Timeline of events
4. Entities involved and their roles
5. Root cause (if error query)
6. Status assessment
7. Recommendations

Return JSON with structured summary.
"""
        
        response = self.llm_client.generate_json(prompt)
        
        return response
```

### Method 7: Relationship Mapping

```python
class RelationshipMappingMethod:
    """Map relationships between entities."""
    
    def execute(self, params: Dict, context: AnalysisContext) -> Dict:
        
        # Use entity manager to build relationship graph
        relationships = self.entity_manager.get_entity_relationships(
            context.all_logs
        )
        
        # Create visual relationship map
        graph = self._build_relationship_graph(relationships)
        
        return {
            "relationships": relationships,
            "graph": graph,
            "entities": context.entities
        }
```

---

## 📊 Example: Complete Workflow Execution

### Query: "why is cm 10:e1:77:08:63:8a offline"

```
============================================================
🔍 INTELLIGENT ANALYSIS WORKFLOW
Query: why is cm 10:e1:77:08:63:8a offline
============================================================

📋 QUERY UNDERSTANDING
   Intent: root_cause
   Goal: Find why CM is offline
   Success Criteria: Found error explaining offline status
   Target: cm_mac = 10:e1:77:08:63:8a

------------------------------------------------------------
ITERATION 1
------------------------------------------------------------
🧠 LLM DECISION:
   Method: direct_search
   Reasoning: "Start by searching for the target CM directly 
               in logs to see if there are any immediate errors"
   Confidence: 0.95
   
⚙️  EXECUTING: direct_search(entity_value="10:e1:77:08:63:8a")
   
✓ RESULT:
   • Found 13 logs
   • All severity: INFO
   • No errors detected
   • Entities discovered:
     - rpdname: MAWED06P01
     - md_id: 0x7a030000
     - ip_address: 172.17.91.21
     - sf_ids: 0xa7a, 0x28d3
   
❌ Success criteria not met (no errors found)

------------------------------------------------------------
ITERATION 2
------------------------------------------------------------
🧠 LLM DECISION:
   Method: iterative_search
   Reasoning: "No direct errors in CM logs. The CM is connected 
               to RPD 'MAWED06P01'. For connectivity issues, the 
               RPD is critical - if RPD is offline, CM goes offline.
               Should search RPD logs for issues."
   Confidence: 0.88
   Params:
     entity_value: "MAWED06P01"
     entity_type: "rpdname"
     search_scope: "broad"
   
⚙️  EXECUTING: iterative_search → direct_search("MAWED06P01")
   
✓ RESULT:
   • Searched entire log file (2113 logs)
   • Found 156 logs with "MAWED06P01"
   • Severity distribution:
     - INFO: 143
     - WARNING: 8
     - ERROR: 5
   • ERRORS DETECTED:
     [15:45:23] ERROR: RPD MAWED06P01 connection timeout
     [15:45:23] ERROR: No response from upstream device
     [15:45:28] ERROR: RPD marked offline
   
✓ Success criteria MET (errors found!)

------------------------------------------------------------
ITERATION 3
------------------------------------------------------------
🧠 LLM DECISION:
   Method: root_cause_analysis
   Reasoning: "Found errors in RPD logs. Now need to analyze 
               the causal relationship between RPD errors and 
               CM offline status. Build timeline to show how 
               RPD failure caused CM offline."
   Confidence: 0.92
   Params:
     error_logs: [5 RPD errors]
     context_logs: [CM logs + RPD logs]
   
⚙️  EXECUTING: root_cause_analysis
   
✓ RESULT:
   Root Cause: "RPD MAWED06P01 lost upstream connection"
   
   Causal Chain:
     1. [15:44:50] CM 10:e1:77:08:63:8a - Last successful DSA callback
     2. [15:45:18] RPD MAWED06P01 - Upstream connection degraded
     3. [15:45:23] RPD MAWED06P01 - Connection timeout (ERROR)
     4. [15:45:28] RPD MAWED06P01 - Marked offline by system
     5. [15:45:30] CM 10:e1:77:08:63:8a - Lost connection (RPD offline)
     6. [15:45:35] CM 10:e1:77:08:63:8a - Marked offline
   
   Confidence: 0.95
   
   Supporting Evidence:
     - RPD error occurred 10s before CM went offline
     - CM's last log shows active connection to RPD
     - Timing correlation is strong
     - RPD is critical path for CM connectivity

✓ Answer found with high confidence!

------------------------------------------------------------
ITERATION 4
------------------------------------------------------------
🧠 LLM DECISION:
   Method: summarization
   Reasoning: "Root cause identified with high confidence. 
               Now summarize all findings into clear answer."
   Confidence: 1.0
   Should Stop: YES
   
⚙️  EXECUTING: summarization
   
✓ RESULT: [Summary generated]

------------------------------------------------------------

============================================================
✅ ANALYSIS COMPLETE
============================================================

🎯 ROOT CAUSE FOUND

Summary:
  CM 10:e1:77:08:63:8a went offline because its parent RPD
  (MAWED06P01) lost upstream connectivity at 15:45:23.

Root Cause:
  RPD "MAWED06P01" experienced upstream connection timeout

Impact Timeline:
  15:44:50 - CM last seen active (processing DSA callbacks)
  15:45:23 - RPD connection error (upstream timeout)
  15:45:28 - RPD marked offline by system
  15:45:30 - CM lost connection (RPD dependency)
  15:45:35 - CM marked offline

Causal Chain:
  Upstream Network Issue
      ↓
  RPD MAWED06P01 timeout
      ↓
  RPD marked offline
      ↓
  CM 10:e1:77:08:63:8a lost connection
      ↓
  CM marked offline

Evidence:
  • 5 ERROR logs from RPD MAWED06P01
  • Strong timing correlation (10s between failures)
  • CM logs show dependency on RPD
  • No errors in CM logs (failure was external)

Related Impact:
  • All CMs connected to RPD MAWED06P01 likely affected
  • Check other CMs: [list of other CMs on same RPD]

Confidence: 95%

Next Steps:
  1. Check RPD MAWED06P01 physical connection
  2. Verify upstream network path
  3. Check for fiber/cable issues
  4. Review other CMs on same RPD

Search Path:
  cm:10:e1:77:08:63:8a (no errors)
    → rpdname:MAWED06P01 (ERROR found)
      → root_cause_analysis
        → ANSWER

Analysis Duration: 12.8s
Iterations: 4
Logs Analyzed: 169
Methods Used: direct_search, iterative_search, root_cause_analysis, summarization

============================================================
```

---

## 🎯 Design Principles

### 1. **Composability**
- Methods can call each other
- Results feed into next decision
- No hard-coded workflows

### 2. **Intelligence**
- LLM decides what to do next
- Adapts based on findings
- Learns from each step

### 3. **Safety**
- Max iteration limit (prevent infinite loops)
- Cycle detection (avoid repetition)
- Regex fallback (works without LLM)
- Validation of LLM decisions

### 4. **Explainability**
- Every decision has reasoning
- Full execution trace
- Shows search path
- Confidence scores

### 5. **Completeness**
- Exhausts all strategies
- Never gives up too early
- Always provides summary
- Shows what was tried

### 6. **Performance**
- Efficient method execution
- Caches results
- Limits search scope when appropriate
- Parallel execution where possible (future)

---

## 🚀 Implementation Phases

### Phase A: Core Infrastructure (Day 1)

**Priority 1: Decision Agent** [4 hours]
- [ ] Create `LLMDecisionAgent` class
- [ ] Implement `decide_next_step()`
- [ ] Build decision prompts
- [ ] Implement fallback logic
- [ ] Test decision making

**Priority 2: Analysis Context** [2 hours]
- [ ] Create `AnalysisContext` dataclass
- [ ] Implement state tracking
- [ ] Add entity queue management
- [ ] Test context updates

**Priority 3: Workflow Orchestrator** [4 hours]
- [ ] Create `WorkflowOrchestrator` class
- [ ] Implement main execution loop
- [ ] Add success criteria checking
- [ ] Implement cycle detection
- [ ] Test end-to-end flow

### Phase B: Analysis Methods (Day 2)

**Priority 4: Refactor Existing Methods** [3 hours]
- [ ] Convert existing code to method classes
- [ ] `DirectSearchMethod` (from current search logic)
- [ ] `IterativeSearchMethod` (from `IterativeSearchStrategy`)
- [ ] Standardize method interface

**Priority 5: New Analysis Methods** [5 hours]
- [ ] `PatternAnalysisMethod`
- [ ] `TimelineAnalysisMethod`
- [ ] `RootCauseAnalysisMethod`
- [ ] `SummarizationMethod`
- [ ] `RelationshipMappingMethod`

### Phase C: Integration & Testing (Day 3)

**Priority 6: Integration** [3 hours]
- [ ] Update `LogAnalyzer` to use `WorkflowOrchestrator`
- [ ] Migrate existing functionality
- [ ] Ensure backward compatibility
- [ ] Update configuration

**Priority 7: Prompts & Response Parsing** [2 hours]
- [ ] Add decision prompts to `prompts.yaml`
- [ ] Update method-specific prompts
- [ ] Enhance response parser for new outputs
- [ ] Test LLM responses

**Priority 8: User Interface** [3 hours]
- [ ] Update `test_interactive.py` for new output
- [ ] Show execution trace in Prod mode
- [ ] Display LLM reasoning at each step
- [ ] Add progress indicators

### Phase D: Testing & Refinement (Day 4)

**Priority 9: Comprehensive Testing** [4 hours]
- [ ] Test various query types
- [ ] Test edge cases (no results, many results)
- [ ] Test error handling
- [ ] Test fallback mechanisms
- [ ] Performance testing

**Priority 10: Documentation** [2 hours]
- [ ] Update README
- [ ] Create architecture diagram
- [ ] Document configuration options
- [ ] Add usage examples

---

## 📁 File Structure

### New Files
```
src/core/decision_agent.py
  - LLMDecisionAgent
  - Decision dataclass
  - Fallback decision logic

src/core/analysis_context.py
  - AnalysisContext dataclass
  - Step dataclass
  - Context management utilities

src/core/workflow_orchestrator.py
  - WorkflowOrchestrator
  - Main execution loop
  - Method coordination

src/core/methods/
  __init__.py
  base_method.py (abstract base class)
  direct_search.py
  iterative_search.py
  pattern_analysis.py
  timeline_analysis.py
  root_cause_analysis.py
  summarization.py
  relationship_mapping.py
```

### Modified Files
```
src/core/analyzer.py
  - Use WorkflowOrchestrator instead of manual routing
  - Backward compatibility layer
  - Simplified interface

config/prompts.yaml
  + decision_agent section
  + method-specific prompts
  ~ Enhanced existing prompts

test_interactive.py
  ~ Show execution trace
  ~ Display LLM reasoning
  ~ Enhanced Prod mode output

src/core/__init__.py
  + Export new components
```

---

## 🎪 Success Metrics

### Before Enhancement:
```
"analyse cm x"           → "No observations" ❌
"why cm x offline"       → "No errors found" ❌
Limited to single method → No adaptation ❌
```

### After Enhancement:
```
"analyse cm x"           → Full summary with timeline ✅
"why cm x offline"       → Root cause with causal chain ✅
"find rpdname for cm x"  → Iterative search with reasoning ✅
Any complex query        → Intelligent multi-step analysis ✅
```

### Quality Metrics:
- **Adaptability**: System tries multiple strategies automatically
- **Completeness**: Never gives "no results" if answer exists in logs
- **Explainability**: Shows why each decision was made
- **Robustness**: Fallback ensures it works even if LLM fails
- **Intelligence**: LLM guides the investigation smartly

---

## 🔮 Future Enhancements (Post-Phase 4)

### 1. Learning from History
- Track which method sequences work best for query types
- Build success statistics
- Optimize decision making over time

### 2. Parallel Execution
- Execute independent methods in parallel
- Faster analysis for complex queries
- Resource-aware scheduling

### 3. Interactive Mode
- Ask user questions during analysis
- "Should I search entity X or Y next?"
- Human-in-the-loop for critical decisions

### 4. Cost Optimization
- Cache LLM responses
- Reuse previous analysis
- Minimize redundant LLM calls

### 5. Advanced Visualizations
- Relationship graphs
- Timeline visualizations
- Decision tree diagrams

---

## 📚 References

### Related Components
- Current analyzer: `src/core/analyzer.py`
- Iterative search: `src/core/iterative_search.py`
- LLM query parser: `src/core/llm_query_parser.py`
- Bridge selector: `src/core/llm_bridge_selector.py`

### Configuration
- Prompts: `config/prompts.yaml`
- Entity mappings: `config/entity_mappings.yaml`
- System config: `config/config.yaml`

### Testing
- Interactive CLI: `test_interactive.py`
- Phase 4 tests: `test_phase4_analyzer.py`

---

**Status**: 📋 Designed - Ready for Implementation
**Date**: November 29, 2025
**Priority**: Critical - Core Architecture Enhancement
**Estimated Time**: 4 days for complete implementation
**Impact**: Transforms system from rule-based to intelligent self-orchestrating analysis engine
