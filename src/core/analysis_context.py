"""
Analysis Context - Maintains state during multi-step analysis.

This module provides the memory system for intelligent analysis workflows.
Tracks what we've done, what we found, and what's pending.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Step:
    """Represents one step in the analysis workflow."""
    iteration: int
    method: str
    params: Dict
    result: Dict
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def summary(self) -> str:
        """Generate human-readable summary of this step."""
        return f"[Iter {self.iteration}] {self.method}: {self.reasoning}"


@dataclass
class Entity:
    """Represents an entity to explore."""
    type: str
    value: str
    priority: int = 5
    source_iteration: int = 0
    
    def __hash__(self):
        return hash(f"{self.type}:{self.value}")
    
    def __eq__(self, other):
        if isinstance(other, Entity):
            return self.type == other.type and self.value == other.value
        return False


@dataclass
class AnalysisContext:
    """
    Maintains state during multi-step analysis.
    
    This is the "memory" of the analysis workflow - tracks everything
    we know, what we've tried, and what's pending.
    """
    
    # Query information
    original_query: str
    query_intent: str  # "find", "analyze", "root_cause", etc.
    goal: str  # Human-readable goal
    success_criteria: str  # What defines success
    
    # Target entity
    target_entity: str
    target_entity_type: Optional[str] = None
    
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
        """Record a step taken in the analysis."""
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
        
        logger.debug(f"Step recorded: {step.summary()}")
    
    def add_logs(self, logs: List[Dict]):
        """Add newly found logs to context."""
        new_logs = [log for log in logs if log not in self.all_logs]
        self.all_logs.extend(new_logs)
        self.logs_analyzed += len(new_logs)
        
        logger.debug(f"Added {len(new_logs)} new logs (total: {self.logs_analyzed})")
    
    def add_entity(self, entity_type: str, entity_value: str, priority: int = 5):
        """Add discovered entity to exploration queue."""
        # Don't add if already explored or is target entity
        entity_key = f"{entity_type}:{entity_value}"
        if entity_key in self.explored_entities:
            return
        
        if entity_value == self.target_entity:
            return
        
        # Don't add if already in queue
        for pending in self.pending_entities:
            if pending.type == entity_type and pending.value == entity_value:
                return
        
        entity = Entity(
            type=entity_type, 
            value=entity_value, 
            priority=priority,
            source_iteration=self.iteration
        )
        self.pending_entities.append(entity)
        
        # Sort by priority (highest first)
        self.pending_entities.sort(key=lambda e: e.priority, reverse=True)
        
        # Track in entities dict
        if entity_type not in self.entities:
            self.entities[entity_type] = []
        if entity_value not in self.entities[entity_type]:
            self.entities[entity_type].append(entity_value)
        
        logger.debug(f"Added entity to queue: {entity_type}={entity_value} (priority: {priority})")
    
    def mark_explored(self, entity_value: str, entity_type: Optional[str] = None):
        """Mark entity as explored."""
        if entity_type:
            entity_key = f"{entity_type}:{entity_value}"
        else:
            # Find in pending and mark
            entity_key = entity_value
        
        self.explored_entities.add(entity_key)
        
        # Remove from pending queue
        self.pending_entities = [
            e for e in self.pending_entities 
            if f"{e.type}:{e.value}" != entity_key
        ]
        
        logger.debug(f"Marked explored: {entity_key}")
    
    def has_tried(self, method: str) -> bool:
        """Check if method has been tried."""
        return method in self.methods_tried
    
    def is_going_in_circles(self) -> bool:
        """
        Detect if we're repeating same actions.
        Returns True if stuck in a loop.
        """
        if len(self.step_history) < 3:
            return False
        
        # Check last 3 steps for repetition
        recent_methods = [s.method for s in self.step_history[-3:]]
        
        # All same method = loop
        if len(set(recent_methods)) == 1:
            logger.warning(f"Loop detected: repeating {recent_methods[0]}")
            return True
        
        # Check if exploring same entities repeatedly
        recent_entities = []
        for step in self.step_history[-3:]:
            if "entity_value" in step.params:
                recent_entities.append(step.params["entity_value"])
        
        if len(recent_entities) >= 2 and len(set(recent_entities)) == 1:
            logger.warning(f"Loop detected: repeating entity {recent_entities[0]}")
            return True
        
        return False
    
    def get_error_keywords(self) -> List[str]:
        """Extract error-related keywords from errors found."""
        keywords = set()
        for error in self.errors_found:
            msg = error.get("message", "").lower()
            # Extract meaningful words
            words = [w for w in msg.split() if len(w) > 3]
            keywords.update(words[:5])  # First 5 meaningful words
        return list(keywords)
    
    def summary(self) -> str:
        """Generate human-readable summary of current context."""
        entity_count = sum(len(v) for v in self.entities.values())
        
        summary_parts = [
            f"Target: {self.target_entity_type or 'entity'} '{self.target_entity}'",
            f"Goal: {self.goal}",
            f"Progress: Iteration {self.iteration}, analyzed {self.logs_analyzed} logs",
            f"Entities found: {entity_count} ({', '.join(f'{k}:{len(v)}' for k, v in self.entities.items())})",
            f"Errors found: {len(self.errors_found)}",
            f"Patterns detected: {len(self.patterns)}",
            f"Methods tried: {', '.join(self.methods_tried) if self.methods_tried else 'none'}",
            f"Pending entities: {len(self.pending_entities)}",
            f"Answer found: {self.answer_found}"
        ]
        
        return "\n".join(summary_parts)
    
    def get_recent_logs_summary(self, limit: int = 5) -> str:
        """Get summary of recent logs found."""
        if not self.all_logs:
            return "No logs found yet"
        
        recent = self.all_logs[-limit:]
        summaries = []
        
        for log in recent:
            timestamp = log.get("timestamp", "??:??:??")
            severity = log.get("severity", "INFO")
            msg = log.get("message", "")[:60]  # First 60 chars
            summaries.append(f"  [{timestamp}] {severity}: {msg}...")
        
        return "\n".join(summaries)
    
    def get_step_history_summary(self) -> str:
        """Get summary of steps taken so far."""
        if not self.step_history:
            return "No steps taken yet"
        
        summaries = []
        for step in self.step_history:
            result_info = ""
            if "logs" in step.result:
                result_info = f" → {len(step.result['logs'])} logs"
            if "errors" in step.result and step.result["errors"]:
                result_info += f", {len(step.result['errors'])} errors"
            
            summaries.append(f"  {step.iteration}. {step.method}{result_info}")
        
        return "\n".join(summaries)
    
    def get_entities_detailed(self) -> str:
        """
        Get detailed entity list with actual values (for LLM decision making).
        Shows first few values of each entity type.
        """
        if not self.entities:
            return "No entities discovered yet"
        
        detailed = []
        for entity_type, values in self.entities.items():
            # Show first 3 values, with count if more
            if len(values) <= 3:
                value_str = ", ".join(values)
            else:
                value_str = ", ".join(values[:3]) + f" (and {len(values)-3} more)"
            
            detailed.append(f"  - {entity_type}: {value_str}")
        
        return "\n".join(detailed)

