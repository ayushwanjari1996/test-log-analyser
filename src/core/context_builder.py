"""
Context Builder for Iterative ReAct.

Builds curated context for LLM at each iteration, including:
- Query
- Tool history (last N actions)
- Current log state (summary, not full logs)
- Extracted entities

Note: Tool definitions are in the Modelfile, NOT in the prompt.
"""

import logging
from typing import Dict, Any, List
from .react_state import ReActState
from .tool_registry import ToolRegistry
from .entity_field_mapper import EntityFieldMapper

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds curated context for LLM prompts in iterative ReAct.
    
    Key principles:
    - Keep context compact (< 2K tokens per iteration)
    - Show summaries, not full data
    - Include last N tool actions (default: 5)
    - Show sample logs (default: 3)
    """
    
    def __init__(self, registry: ToolRegistry, max_history: int = 5, config_dir: str = "config"):
        """
        Initialize context builder.
        
        Args:
            registry: Tool registry for available tools
            max_history: Maximum number of historical actions to include
            config_dir: Directory containing configuration files
        """
        self.registry = registry
        self.max_history = max_history
        self.entity_mapper = EntityFieldMapper(config_dir)
        logger.info(f"ContextBuilder initialized (max_history={max_history})")
    
    def build_context(self, state: ReActState) -> Dict[str, Any]:
        """
        Build curated context for LLM.
        
        Args:
            state: Current ReAct state
            
        Returns:
            Dictionary with all context information
        """
        context = {
            "query": state.original_query,
            "iteration": state.current_iteration,
            "max_iterations": state.max_iterations,
            "tool_history": self._format_tool_history(state),
            "current_state": self._format_current_state(state),
            "entities": self._format_entities(state),
            "state": state  # Include state object for schema-aware formatting
        }
        
        return context
    
    def _format_tool_history(self, state: ReActState) -> List[Dict[str, Any]]:
        """
        Format recent tool history.
        
        Args:
            state: Current ReAct state
            
        Returns:
            List of recent tool executions with summaries
        """
        if not state.tool_history:
            return []
        
        # Get last N tool executions
        recent_tools = state.tool_history[-self.max_history:]
        
        formatted = []
        for execution in recent_tools:
            entry = {
                "step": execution.iteration,
                "tool": execution.tool_name,
                "params": execution.parameters,
                "success": execution.success
            }
            
            if execution.success:
                # Add result summary
                entry["result"] = self._summarize_result(execution.result)
            else:
                entry["error"] = execution.error
            
            formatted.append(entry)
        
        return formatted
    
    def _format_current_state(self, state: ReActState) -> Dict[str, Any]:
        """
        Format current state (log summary + available data).
        
        Args:
            state: Current ReAct state
            
        Returns:
            Dictionary with current state information
        """
        current_state = {}
        
        # Use smart summary if available (for large datasets)
        if state.current_summary:
            current_state["logs"] = state.current_summary
        else:
            # Otherwise use the state's built-in log summary (for small datasets)
            log_summary = state.get_log_summary(max_samples=3)
            current_state["logs"] = log_summary
        
        # Include last_result if available (e.g., list of values from previous tool)
        if state.last_result is not None:
            if isinstance(state.last_result, list):
                count = len(state.last_result)
                sample = state.last_result[:5]
                current_state["last_values"] = f"{count} values available (sample: {sample})"
            elif isinstance(state.last_result, dict):
                current_state["last_dict"] = f"Dict with {len(state.last_result)} keys"
        
        return current_state
    
    def _format_entities(self, state: ReActState) -> Dict[str, Any]:
        """
        Format extracted entities.
        
        Args:
            state: Current ReAct state
            
        Returns:
            Dictionary with entity information
        """
        if not state.extracted_entities:
            return {"status": "No entities extracted yet"}
        
        # Format entities with counts
        formatted = {}
        for entity_type, values in state.extracted_entities.items():
            formatted[entity_type] = {
                "count": len(values),
                "sample": values[:5]  # Show first 5
            }
        
        return formatted
    
    def _format_schema_aware_state(self, state: ReActState, context: Dict[str, Any]) -> str:
        """
        Format current state with schema awareness.
        Shows sample logs, available fields, extracted data, and smart hints.
        
        Args:
            state: Current ReAct state
            context: Context dictionary
            
        Returns:
            Formatted state string
        """
        lines = []
        
        # 1. Logs loaded?
        if state.current_logs is not None and len(state.current_logs) > 0:
            count = len(state.current_logs)
            lines.append(f"  Logs loaded: {count} entries (DataFrame)")
            
            # Show sample logs for structure
            if state.log_samples:
                lines.append(f"\n  Sample log structure (showing {len(state.log_samples)} of {count}):")
                for i, sample in enumerate(state.log_samples, 1):
                    # Indent each line of the JSON
                    indented = "\n    ".join(sample.split("\n"))
                    lines.append(f"    Sample {i}:\n    {indented}")
            
            # Show available fields grouped by entity type
            if state.available_fields:
                grouped = self.entity_mapper.group_fields_by_entity(state.available_fields)
                
                lines.append(f"\n  Available fields (grouped by entity):")
                for entity_type, fields in grouped.items():
                    if entity_type == "other":
                        label = "System/Other"
                    else:
                        label = self.entity_mapper.get_entity_label(entity_type)
                    
                    fields_str = ", ".join(fields[:5])
                    if len(fields) > 5:
                        fields_str += f" (+{len(fields)-5} more)"
                    
                    lines.append(f"    {label}: {fields_str}")
                
                lines.append("  ⚠️ Fields are INSIDE logs - use parse_json_field(logs, 'FieldName') to extract values")
            
            # Show extracted fields status
            if state.extracted_fields:
                lines.append(f"\n  Extracted fields:")
                for field, info in state.extracted_fields.items():
                    status = "UNIQUE" if info.get("unique") else "raw (may have duplicates)"
                    lines.append(f"    - {field}: {info['count']} {status} values (in {info['stored_in']})")
        else:
            lines.append("  No logs loaded yet")
        
        # 2. Last result (non-DataFrame data)
        if state.last_result is not None:
            if isinstance(state.last_result, list):
                count = len(state.last_result)
                sample = state.last_result[:3]
                lines.append(f"\n  Last result: {count} values (sample: {sample})")
            elif isinstance(state.last_result, dict):
                lines.append(f"\n  Last result: Dict with {len(state.last_result)} keys")
        
        # 3. Smart hints based on query + state
        hint = self._generate_smart_hint(state, context)
        if hint:
            lines.append(f"\n  💡 HINT: {hint}")
        
        return "\n".join(lines)
    
    def _generate_smart_hint(self, state: ReActState, context: Dict[str, Any]) -> str:
        """
        Generate context-aware hints based on query intent and current state.
        Uses entity mappings for intelligent field suggestion.
        
        Args:
            state: Current ReAct state
            context: Context dictionary
            
        Returns:
            Hint string or empty string
        """
        query = state.original_query.lower()
        
        # Detect which entities are mentioned in the query
        detected_entities = self.entity_mapper.detect_entities_in_query(query)
        
        # Query asks for unique/count
        if any(word in query for word in ["unique", "count", "how many", "total", "number"]):
            # Have logs but no extracted values?
            if state.current_logs is not None and not state.extracted_fields:
                # If we detected entity types, show relevant fields
                if detected_entities and state.available_fields:
                    relevant_fields = []
                    for entity_type in detected_entities:
                        fields = self.entity_mapper.get_fields_for_entity(entity_type, state.available_fields)
                        relevant_fields.extend(fields)
                    
                    if relevant_fields:
                        entity_labels = [self.entity_mapper.get_entity_label(e) for e in detected_entities]
                        fields_str = ", ".join(relevant_fields)
                        return f"Query asks for unique {'/'.join(entity_labels)} values. Available {'/'.join(entity_labels)} fields: {fields_str}. Parse the field that uniquely identifies the entity."
                
                return "Query needs unique values. Logs loaded but no fields extracted yet. Use parse_json_field to extract the field you need."
            
            # Have raw values but not deduplicated?
            if state.last_result and isinstance(state.last_result, list):
                # Check if it's been deduplicated
                is_unique = any(info.get("unique") for info in state.extracted_fields.values())
                if not is_unique:
                    return "Query needs unique count. Raw values extracted but not deduplicated. Next: count_values(values)"
        
        # Query asks for relationship/connection (e.g., "count X per Y")
        if any(word in query for word in ["per", "for each", "associated", "linked", "by"]):
            if state.current_logs is not None:
                return "Query involves relationships between fields. Consider using count_unique_per_group or count_via_relationship"
        
        return ""
    
    def _summarize_result(self, result: Any) -> str:
        """
        Create compact summary of tool result.
        
        Args:
            result: Tool result object
            
        Returns:
            String summary
        """
        # If result has a message, use it
        if hasattr(result, 'message'):
            return result.message
        
        # If result has data, summarize it
        if hasattr(result, 'data'):
            data = result.data
            
            # DataFrame
            if hasattr(data, '__len__') and hasattr(data, 'columns'):
                return f"DataFrame with {len(data)} rows"
            
            # Dictionary
            elif isinstance(data, dict):
                if all(isinstance(v, list) for v in data.values()):
                    # Entity dict
                    parts = [f"{k}: {len(v)} items" for k, v in data.items()]
                    return "Entities: " + ", ".join(parts)
                else:
                    return f"Dict with {len(data)} keys"
            
            # List
            elif isinstance(data, list):
                return f"List with {len(data)} items"
            
            # Scalar
            else:
                return str(data)
        
        return "No result data"
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build full LLM prompt from context.
        
        Args:
            context: Context dictionary from build_context()
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are analyzing logs to answer a query. Decide the NEXT action.

QUERY: {context['query']}
ITERATION: {context['iteration']}/{context['max_iterations']}

"""
        
        # Add tool history
        if context['tool_history']:
            prompt += "PREVIOUS ACTIONS:\n"
            for entry in context['tool_history']:
                step = entry['step']
                tool = entry['tool']
                params = entry['params']
                
                prompt += f"  Step {step}: {tool}({params})\n"
                
                if entry['success']:
                    prompt += f"    → {entry['result']}\n"
                else:
                    prompt += f"    → ERROR: {entry.get('error', 'Unknown error')}\n"
            
            prompt += "\n"
        else:
            prompt += "PREVIOUS ACTIONS: None (first iteration)\n\n"
        
        # Add current state with schema awareness
        prompt += "CURRENT STATE:\n"
        prompt += self._format_schema_aware_state(context["state"], context)
        prompt += "\n"
        
        # Add decision instructions
        prompt += """DECISION POINT:
- Have enough data? → finalize_answer
- Need more data? → call next tool

FORMAT (KEEP BRIEF):
<think>1-2 sentence max</think>
{
  "reasoning": "one sentence",
  "action": "tool_name",
  "params": {dict}
}

CRITICAL: 
- Return JSON ONLY
"""
        
        return prompt

