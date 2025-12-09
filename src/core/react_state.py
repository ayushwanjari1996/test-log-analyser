"""
State management for ReAct loop.

Tracks the conversation history, tool executions, and results
during the reasoning loop.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ToolExecution:
    """Record of a single tool execution"""
    iteration: int
    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "iteration": self.iteration,
            "tool": self.tool_name,
            "parameters": self.parameters,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class LLMDecision:
    """Record of LLM reasoning and decision"""
    iteration: int
    reasoning: str
    tool_name: Optional[str]
    parameters: Dict[str, Any]
    answer: Optional[str] = None
    confidence: float = 0.0
    done: bool = False
    adaptation_needed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "iteration": self.iteration,
            "reasoning": self.reasoning,
            "tool": self.tool_name,
            "parameters": self.parameters,
            "answer": self.answer,
            "confidence": self.confidence,
            "done": self.done,
            "timestamp": self.timestamp.isoformat()
        }


class ReActState:
    """
    State management for ReAct loop.
    
    Maintains:
    - Original query
    - Tool execution history
    - LLM decision history
    - Cached data (loaded logs, etc.)
    - Current iteration count
    - Final answer
    """
    
    def __init__(
        self,
        original_query: str,
        max_iterations: int = 10
    ):
        self.original_query = original_query
        self.max_iterations = max_iterations
        self.current_iteration = 0
        
        # History
        self.tool_history: List[ToolExecution] = []
        self.llm_decisions: List[LLMDecision] = []
        
        # Cached data
        self.loaded_logs: Optional[pd.DataFrame] = None
        self.filtered_logs: Optional[pd.DataFrame] = None
        self.current_logs: Optional[pd.DataFrame] = None  # Current working dataset
        self.current_summary: Optional[str] = None  # Smart summary of current logs
        self.last_result: Optional[Any] = None  # Last tool result (list, dict, etc.)
        self.extracted_entities: Dict[str, List[Any]] = {}
        
        # Schema awareness
        self.log_samples: List[str] = []  # Sample logs to show structure
        self.available_fields: List[str] = []  # Fields available in logs
        self.extracted_fields: Dict[str, Dict[str, Any]] = {}  # Track what's been extracted
        
        # Results
        self.answer: Optional[str] = None
        self.confidence: float = 0.0
        self.done: bool = False
        
        # Timestamps
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        
        logger.info(f"ReActState initialized for query: '{original_query[:50]}...'")
    
    def add_tool_execution(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Record a tool execution"""
        execution = ToolExecution(
            iteration=self.current_iteration,
            tool_name=tool_name,
            parameters=parameters,
            result=result,
            success=success,
            error=error
        )
        self.tool_history.append(execution)
        logger.debug(f"Recorded tool execution: {tool_name} (success={success})")
    
    def add_llm_decision(
        self,
        reasoning: str,
        tool_name: Optional[str],
        parameters: Dict[str, Any],
        answer: Optional[str] = None,
        confidence: float = 0.0,
        done: bool = False
    ) -> None:
        """Record an LLM decision"""
        decision = LLMDecision(
            iteration=self.current_iteration,
            reasoning=reasoning,
            tool_name=tool_name,
            parameters=parameters,
            answer=answer,
            confidence=confidence,
            done=done
        )
        self.llm_decisions.append(decision)
        logger.debug(f"Recorded LLM decision: tool={tool_name}, done={done}")
        
        # Update state if done
        if done:
            self.done = True
            self.answer = answer
            self.confidence = confidence
    
    def increment_iteration(self) -> None:
        """Move to next iteration"""
        self.current_iteration += 1
        logger.debug(f"Iteration {self.current_iteration}/{self.max_iterations}")
    
    def is_max_iterations_reached(self) -> bool:
        """Check if max iterations reached"""
        return self.current_iteration >= self.max_iterations
    
    def get_conversation_history(self) -> str:
        """
        Get formatted conversation history for LLM context.
        
        Returns string with all previous decisions and tool results.
        """
        if not self.llm_decisions:
            return "No history yet."
        
        history = "CONVERSATION HISTORY:\n\n"
        
        for decision in self.llm_decisions:
            history += f"[Iteration {decision.iteration + 1}]\n"
            history += f"REASONING: {decision.reasoning}\n"
            
            if decision.tool_name:
                history += f"ACTION: Called tool '{decision.tool_name}'\n"
                
                # Find corresponding tool execution
                execution = next(
                    (e for e in self.tool_history 
                     if e.iteration == decision.iteration and e.tool_name == decision.tool_name),
                    None
                )
                
                if execution:
                    if execution.success:
                        # Show the tool message (which now includes actual values)
                        if hasattr(execution.result, 'message'):
                            history += f"OBSERVATION: {execution.result.message}\n"
                            
                            # For search_logs, remind about auto-injection
                            if decision.tool_name == "search_logs":
                                history += f"NOTE: These logs are cached - other tools will automatically use them\n"
                            
                            # For entity extraction, show the actual data clearly
                            if decision.tool_name in ["extract_entities", "aggregate_entities"] and hasattr(execution.result, 'data'):
                                data = execution.result.data
                                if isinstance(data, dict) and data:
                                    history += f"ENTITIES FOUND: {data}\n"
                        else:
                            result_summary = self._format_result_summary(execution.result.data)
                            history += f"OBSERVATION: {result_summary}\n"
                    else:
                        history += f"OBSERVATION: Tool failed - {execution.error}\n"
            
            if decision.done:
                history += f"FINAL ANSWER: {decision.answer}\n"
            
            history += "\n"
        
        return history
    
    def _format_result_summary(self, data: Any) -> str:
        """Format tool result data for history"""
        if data is None:
            return "No data returned"
        elif isinstance(data, pd.DataFrame):
            return f"Found {len(data)} logs (stored as DataFrame - use this in next tool calls)"
        elif isinstance(data, dict):
            if all(isinstance(v, list) for v in data.values()):
                # Entity dictionary - SHOW THE ACTUAL VALUES!
                summary_parts = []
                for k, v in data.items():
                    if v:
                        # Show up to 5 values
                        value_preview = ", ".join(str(x) for x in v[:5])
                        if len(v) > 5:
                            value_preview += f" (and {len(v)-5} more)"
                        summary_parts.append(f"{k}: [{value_preview}]")
                
                if summary_parts:
                    return "Extracted entities: " + "; ".join(summary_parts)
                else:
                    return "No entities extracted"
            else:
                return f"Dict with {len(data)} keys"
        elif isinstance(data, list):
            return f"List with {len(data)} items"
        else:
            return str(data)[:100]
    
    def finalize(self, answer: Optional[str] = None, confidence: float = 0.0) -> None:
        """Mark state as done and record end time"""
        self.done = True
        if answer:
            self.answer = answer
        if confidence > 0:
            self.confidence = confidence
        self.end_time = datetime.now()
        
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"ReAct loop completed in {duration:.2f}s after {self.current_iteration} iterations")
    
    def get_log_summary(self, max_samples: int = 3) -> Dict[str, Any]:
        """
        Generate compact log summary for LLM context.
        
        Args:
            max_samples: Number of sample logs to include
            
        Returns:
            Dictionary with log statistics and samples
        """
        if self.current_logs is None or len(self.current_logs) == 0:
            return {
                "status": "No logs loaded",
                "total_count": 0,
                "sample_logs": []
            }
        
        total = len(self.current_logs)
        
        # Get sample logs
        sample = self.current_logs.head(max_samples)
        sample_records = sample.to_dict('records')
        
        # Get severity distribution
        severity_dist = {}
        if 'severity' in self.current_logs.columns:
            severity_dist = self.current_logs['severity'].value_counts().to_dict()
        
        # Get time range
        time_range = {}
        if 'timestamp' in self.current_logs.columns:
            try:
                time_range = {
                    "earliest": str(self.current_logs['timestamp'].min()),
                    "latest": str(self.current_logs['timestamp'].max())
                }
            except:
                pass
        
        return {
            "status": "Logs loaded",
            "total_count": total,
            "sample_logs": sample_records,
            "severity_distribution": severity_dist,
            "time_range": time_range
        }
    
    def update_current_logs(self, logs: Optional[pd.DataFrame], summary: Optional[str] = None) -> None:
        """
        Update the current working dataset.
        
        Args:
            logs: New logs DataFrame
            summary: Optional smart summary of logs (for large datasets)
        """
        self.current_logs = logs
        self.current_summary = summary
        if logs is not None:
            # Auto-extract schema
            self._extract_schema(logs)
            logger.debug(f"Updated current_logs: {len(logs)} logs" + 
                        (f" with smart summary ({len(summary)} chars)" if summary else ""))
    
    def _extract_schema(self, logs: pd.DataFrame, max_samples: int = 2) -> None:
        """
        Extract schema information from logs: sample logs and available fields.
        
        Args:
            logs: DataFrame to extract schema from
            max_samples: Number of sample logs to extract
        """
        import json
        
        # Extract sample logs
        self.log_samples = []
        if '_source.log' in logs.columns:
            samples = logs['_source.log'].head(max_samples)
            for log_entry in samples:
                try:
                    # Extract JSON part
                    json_start = log_entry.find('{')
                    if json_start != -1:
                        json_str = log_entry[json_start:].replace('""', '"')
                        log_json = json.loads(json_str)
                        # Store formatted JSON for readability
                        self.log_samples.append(json.dumps(log_json, indent=2))
                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue
        
        # Extract available fields from samples
        self.available_fields = []
        if self.log_samples:
            try:
                # Get fields from first sample
                first_sample = json.loads(self.log_samples[0])
                self.available_fields = list(first_sample.keys())
            except:
                pass
        
        logger.debug(f"Extracted schema: {len(self.log_samples)} samples, {len(self.available_fields)} fields")
    
    def update_last_result(self, result: Any) -> None:
        """
        Update last tool result (for list/dict/other non-DataFrame results).
        
        Args:
            result: Last tool result data
        """
        self.last_result = result
        logger.debug(f"Updated last_result: {type(result).__name__} ({len(result) if hasattr(result, '__len__') else 'N/A'})")
    
    def mark_field_extracted(self, field_name: str, value_count: int, is_unique: bool = False) -> None:
        """
        Mark a field as extracted from logs.
        
        Args:
            field_name: Name of the field extracted
            value_count: Number of values extracted
            is_unique: Whether values have been deduplicated
        """
        self.extracted_fields[field_name] = {
            "count": value_count,
            "unique": is_unique,
            "stored_in": "last_result"
        }
        logger.debug(f"Marked field '{field_name}' as extracted ({value_count} values, unique={is_unique})")
    
    def update_entities(self, entities: Dict[str, List[Any]]) -> None:
        """
        Update extracted entities.
        
        Args:
            entities: Dictionary of entity_type -> list of values
        """
        for entity_type, values in entities.items():
            if entity_type in self.extracted_entities:
                # Merge with existing
                existing = set(self.extracted_entities[entity_type])
                existing.update(values)
                self.extracted_entities[entity_type] = list(existing)
            else:
                self.extracted_entities[entity_type] = values
        
        logger.debug(f"Updated entities: {list(self.extracted_entities.keys())}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of execution"""
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            "query": self.original_query,
            "iterations": self.current_iteration,
            "max_iterations": self.max_iterations,
            "tools_used": len(self.tool_history),
            "success": self.done,
            "answer": self.answer,
            "confidence": self.confidence,
            "duration_seconds": duration,
            "tool_sequence": [e.tool_name for e in self.tool_history]
        }

