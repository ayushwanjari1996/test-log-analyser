"""
Answer Formatter - Format execution results into human-readable answers
"""

from typing import Dict, Any, List
import pandas as pd
from ..utils.logger import setup_logger

logger = setup_logger()


class AnswerFormatter:
    """
    Format tool execution results into human-readable answers.
    
    Prioritizes results based on what's most useful for the query type.
    """
    
    def format(self, results: Dict[str, Any], original_query: str) -> str:
        """
        Format results into a human-readable answer.
        
        Args:
            results: Dict of tool_name → ToolResult
            original_query: Original user query
            
        Returns:
            Human-readable answer string
        """
        # Check for errors first
        for tool_name, result in results.items():
            if hasattr(result, 'success') and not result.success:
                if "not found" in str(result.message).lower() or "no logs" in str(result.message).lower():
                    continue  # Not a fatal error
                logger.warning(f"Tool {tool_name} had issues: {result.message}")
        
        # Priority order for formatting
        answer = None
        
        # 1. If extract_entities was called, show entities
        if "extract_entities" in results:
            answer = self._format_entities(results["extract_entities"])
        
        # 2. If count_entities was called, show count
        elif "count_entities" in results:
            answer = self._format_entity_count(results["count_entities"])
        
        # 3. If aggregate_entities was called, show aggregation
        elif "aggregate_entities" in results:
            answer = self._format_aggregation(results["aggregate_entities"])
        
        # 4. If return_logs was called, use its formatted output
        elif "return_logs" in results:
            answer = self._format_return_logs(results["return_logs"])
        
        # 5. If get_log_count was called, show count
        elif "get_log_count" in results:
            answer = self._format_log_count(results["get_log_count"])
        
        # 6. If filter was applied, show filter results
        elif any(k.startswith("filter_") for k in results):
            for k, v in results.items():
                if k.startswith("filter_") and hasattr(v, 'data'):
                    answer = self._format_filter_result(k, v)
                    break
        
        # 7. Fallback: show search results
        if answer is None and "search_logs" in results:
            answer = self._format_search_result(results["search_logs"])
        
        # Final fallback
        if answer is None:
            answer = "No results found."
        
        return answer
    
    def _format_entities(self, result) -> str:
        """Format extract_entities result."""
        if not result.success:
            return f"Entity extraction failed: {result.message}"
        
        if not result.data:
            return "No entities found."
        
        parts = []
        for entity_type, values in result.data.items():
            if values:
                # Limit to first 10 values
                display_values = values[:10]
                suffix = f" (and {len(values) - 10} more)" if len(values) > 10 else ""
                parts.append(f"{len(values)} {entity_type}: {', '.join(str(v) for v in display_values)}{suffix}")
        
        if parts:
            return "Found " + "; ".join(parts)
        return "No entities found."
    
    def _format_entity_count(self, result) -> str:
        """Format count_entities result."""
        if not result.success:
            return f"Entity counting failed: {result.message}"
        
        return result.message or f"Count: {result.data}"
    
    def _format_aggregation(self, result) -> str:
        """Format aggregate_entities result."""
        if not result.success:
            return f"Aggregation failed: {result.message}"
        
        if not result.data:
            return "No entities to aggregate."
        
        parts = []
        for entity_type, values in result.data.items():
            if values:
                display_values = values[:10]
                suffix = f" (+{len(values) - 10} more)" if len(values) > 10 else ""
                parts.append(f"{entity_type}: {', '.join(str(v) for v in display_values)}{suffix}")
        
        if parts:
            return "Unique values:\n" + "\n".join(parts)
        return "No unique values found."
    
    def _format_return_logs(self, result) -> str:
        """Format return_logs result."""
        if not result.success:
            return f"Log display failed: {result.message}"
        
        return result.message or "Logs displayed."
    
    def _format_log_count(self, result) -> str:
        """Format get_log_count result."""
        if not result.success:
            return f"Count failed: {result.message}"
        
        count = result.data.get("count", 0) if isinstance(result.data, dict) else result.data
        return f"Total: {count} logs"
    
    def _format_filter_result(self, filter_name: str, result) -> str:
        """Format filter result."""
        if not result.success:
            return f"Filter failed: {result.message}"
        
        if isinstance(result.data, pd.DataFrame):
            count = len(result.data)
            return f"After {filter_name}: {count} logs match"
        
        return result.message or "Filter applied."
    
    def _format_search_result(self, result) -> str:
        """Format search_logs result."""
        if not result.success:
            return f"Search failed: {result.message}"
        
        if isinstance(result.data, pd.DataFrame):
            count = len(result.data)
            if count == 0:
                return "No logs found matching the search."
            return f"Found {count} logs."
        
        return result.message or "Search completed."
    
    def format_with_context(self, results: Dict[str, Any], query: str, 
                           normalized_query: str, search_value: str) -> str:
        """
        Format with additional context for debugging/verbose mode.
        
        Returns formatted answer with execution details.
        """
        answer = self.format(results, query)
        
        # Build execution trace
        trace = []
        for tool_name, result in results.items():
            status = "✓" if result.success else "✗"
            trace.append(f"  {status} {tool_name}")
        
        context = [
            f"Query: {query}",
            f"Normalized: {normalized_query}",
            f"Search value: {search_value or '(all logs)'}",
            f"Execution:",
            *trace,
            f"",
            f"Answer: {answer}"
        ]
        
        return "\n".join(context)

