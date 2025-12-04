"""
Context Builder for Iterative ReAct.

Builds curated context for LLM at each iteration, including:
- Query
- Tool history (last N actions)
- Current log state (summary, not full logs)
- Available tools
- Extracted entities
"""

import logging
from typing import Dict, Any, List
from .react_state import ReActState
from .tool_registry import ToolRegistry

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
    
    def __init__(self, registry: ToolRegistry, max_history: int = 5):
        """
        Initialize context builder.
        
        Args:
            registry: Tool registry for available tools
            max_history: Maximum number of historical actions to include
        """
        self.registry = registry
        self.max_history = max_history
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
            "available_tools": self._format_available_tools()
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
    
    def _format_available_tools(self) -> str:
        """
        Format available tools description.
        
        Returns:
            String with tool descriptions
        """
        return self.registry.get_tools_description(format="text")
    
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
        
        # Add current state
        prompt += "CURRENT STATE:\n"
        
        log_state = context['current_state']['logs']
        
        # Handle both string (smart summary) and dict (regular summary)
        if isinstance(log_state, str):
            # Smart summary - show as-is
            prompt += log_state + "\n"
        elif isinstance(log_state, dict):
            # Regular summary - format fields
            if log_state.get('total_count', 0) > 0:
                prompt += f"  Total logs: {log_state['total_count']}\n"
                
                # Show sample logs
                if log_state.get('sample_logs'):
                    prompt += "  Sample logs:\n"
                    for i, log in enumerate(log_state['sample_logs'][:3], 1):
                        # Show key fields only
                        severity = log.get('severity', 'N/A')
                        message = log.get('message', '')[:80]
                        prompt += f"    {i}. [{severity}] {message}...\n"
                
                # Show severity distribution
                if log_state.get('severity_distribution'):
                    prompt += f"  Severity: {log_state['severity_distribution']}\n"
            else:
                prompt += f"  {log_state.get('status', 'No logs loaded')}\n"
        else:
            prompt += "  No logs loaded\n"
        
        # Add last_values if available
        if 'last_values' in context['current_state']:
            prompt += f"  Last result: {context['current_state']['last_values']}\n"
        if 'last_dict' in context['current_state']:
            prompt += f"  Last result: {context['current_state']['last_dict']}\n"
        
        # Add entities
        entities = context['entities']
        if entities.get('status') != "No entities extracted yet":
            prompt += "\n  Entities extracted:\n"
            for entity_type, info in entities.items():
                if isinstance(info, dict):
                    prompt += f"    {entity_type}: {info['count']} unique values\n"
        
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
- Thinking: MAX 1-2 sentences
- Reasoning: MAX 1 sentence
- Return JSON immediately

"""
        
        # Add available tools (condensed)
        prompt += context['available_tools']
        
        return prompt

