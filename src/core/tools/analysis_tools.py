"""
Analysis and aggregation tools.

Statistics, summaries, grouping, and deep analysis.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from collections import Counter
import pandas as pd

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from ...llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class SummarizeLogsTool(Tool):
    """
    Generate statistical summary of log collection.
    Provides overview without showing raw data.
    """
    
    def __init__(self):
        super().__init__(
            name="summarize_logs",
            description="Generate statistical summary of logs",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="Logs to summarize (auto-injected)",
                    required=True
                ),
                ToolParameter(
                    name="detail_level",
                    param_type=ParameterType.STRING,
                    description="Detail level: 'basic' or 'full' (default: basic)",
                    required=False
                )
            ]
        )
        self.requires_logs = True
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        detail_level = kwargs.get("detail_level", "basic")
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to summarize"
            )
        
        try:
            summary = self._generate_summary(logs, detail_level)
            
            # Format human-readable message
            msg = self._format_summary_message(summary)
            
            return ToolResult(
                success=True,
                data=summary,
                message=msg,
                metadata=summary
            )
            
        except Exception as e:
            logger.error(f"Summarize failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Summarize failed: {str(e)}"
            )
    
    def _generate_summary(self, logs: pd.DataFrame, detail_level: str) -> Dict[str, Any]:
        """Generate summary statistics."""
        summary = {
            "total_count": len(logs),
            "columns": list(logs.columns)
        }
        
        # Time range
        time_col = self._find_time_column(logs)
        if time_col:
            try:
                # Try custom format first: "Nov 5, 2025 @ 15:30:51.495"
                times = pd.to_datetime(logs[time_col], format="%b %d, %Y @ %H:%M:%S.%f", errors='coerce')
                # If many NaT, fallback to auto-detection
                if times.isna().sum() > len(times) * 0.5:
                    times = pd.to_datetime(logs[time_col], errors='coerce')
                
                summary["time_range"] = {
                    "earliest": str(times.min()),
                    "latest": str(times.max()),
                    "span": str(times.max() - times.min())
                }
            except:
                pass
        
        # Parse JSON and get field distributions
        if '_source.log' in logs.columns:
            severities = []
            functions = []
            messages = []
            
            for log_entry in logs['_source.log'].head(100):  # Sample first 100
                try:
                    # Extract JSON (after prefix like "stdout F ")
                    json_start = log_entry.find('{')
                    if json_start == -1:
                        continue
                    json_str = log_entry[json_start:].replace('""', '"')
                    log_json = json.loads(json_str)
                    
                    if 'Severity' in log_json:
                        severities.append(log_json['Severity'])
                    if 'Function' in log_json:
                        functions.append(log_json['Function'])
                    if 'Message' in log_json:
                        messages.append(log_json['Message'])
                        
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Severity distribution
            if severities:
                severity_counts = Counter(severities)
                summary["severity_distribution"] = dict(severity_counts)
            
            # Top functions (if detail_level=full)
            if detail_level == "full" and functions:
                function_counts = Counter(functions)
                summary["top_functions"] = dict(function_counts.most_common(10))
            
            # Top messages (if detail_level=full)
            if detail_level == "full" and messages:
                message_counts = Counter(messages)
                summary["top_messages"] = dict(message_counts.most_common(10))
        
        return summary
    
    def _find_time_column(self, logs: pd.DataFrame) -> Optional[str]:
        """Find timestamp column."""
        candidates = ['_source.@timestamp', '_source.date', '@timestamp', 'timestamp', 'date']
        for col in candidates:
            if col in logs.columns:
                return col
        return None
    
    def _format_summary_message(self, summary: Dict[str, Any]) -> str:
        """Format summary as human-readable message."""
        msg = f"Summary: {summary['total_count']} logs"
        
        if "time_range" in summary:
            tr = summary["time_range"]
            msg += f" | Time range: {tr.get('span', 'N/A')}"
        
        if "severity_distribution" in summary:
            sev = summary["severity_distribution"]
            sev_str = ", ".join(f"{k}:{v}" for k, v in sev.items())
            msg += f" | Severities: {sev_str}"
        
        return msg


class AggregateByFieldTool(Tool):
    """
    Group logs by field and count occurrences.
    Like SQL GROUP BY.
    """
    
    def __init__(self):
        super().__init__(
            name="aggregate_by_field",
            description="Group logs by field value and count (like SQL GROUP BY)",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="Logs to aggregate (auto-injected)",
                    required=True
                ),
                ToolParameter(
                    name="field_name",
                    param_type=ParameterType.STRING,
                    description="JSON field to group by",
                    required=True
                ),
                ToolParameter(
                    name="top_n",
                    param_type=ParameterType.INTEGER,
                    description="Return top N results (default: 10)",
                    required=False
                )
            ]
        )
        self.requires_logs = True
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        field_name = kwargs.get("field_name", "")
        top_n = kwargs.get("top_n", 10)
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to aggregate"
            )
        
        if not field_name:
            return ToolResult(
                success=False,
                data=None,
                error="field_name required"
            )
        
        try:
            # Extract field values from JSON
            values = []
            
            if '_source.log' in logs.columns:
                for log_entry in logs['_source.log']:
                    try:
                        # Extract JSON (after prefix)
                        json_start = log_entry.find('{')
                        if json_start == -1:
                            continue
                        json_str = log_entry[json_start:].replace('""', '"')
                        log_json = json.loads(json_str)
                        if field_name in log_json:
                            value = log_json[field_name]
                            if value and value not in ['<null>', 'null', '']:
                                values.append(value)
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            if not values:
                return ToolResult(
                    success=True,
                    data={},
                    message=f"Field '{field_name}' not found in logs"
                )
            
            # Count occurrences
            counts = Counter(values)
            top_items = dict(counts.most_common(top_n))
            
            # Format message
            total_unique = len(counts)
            total_occurrences = sum(counts.values())
            
            top_str = ", ".join(f"{k}:{v}" for k, v in list(top_items.items())[:3])
            if len(top_items) > 3:
                top_str += f" (and {len(top_items)-3} more)"
            
            msg = f"Grouped by '{field_name}': {total_unique} unique values, {total_occurrences} total occurrences. Top: {top_str}"
            
            return ToolResult(
                success=True,
                data=top_items,
                message=msg,
                metadata={
                    "field": field_name,
                    "unique_count": total_unique,
                    "total_count": total_occurrences,
                    "top_n": top_n
                }
            )
            
        except Exception as e:
            logger.error(f"Aggregate failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Aggregate failed: {str(e)}"
            )


class AnalyzeLogsTool(Tool):
    """
    Deep analysis using LLM.
    Detects patterns, correlations, root causes.
    """
    
    def __init__(self, model: str = "qwen3-loganalyzer"):
        super().__init__(
            name="analyze_logs",
            description="Deep analysis of logs using LLM (patterns, root cause, timeline)",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="Logs to analyze (auto-injected, max 50)",
                    required=True
                ),
                ToolParameter(
                    name="focus",
                    param_type=ParameterType.STRING,
                    description="Analysis focus: 'errors', 'patterns', 'timeline', or 'all'",
                    required=False
                ),
                ToolParameter(
                    name="query_context",
                    param_type=ParameterType.STRING,
                    description="Original user question for context",
                    required=False
                )
            ]
        )
        self.requires_logs = True
        self.llm = OllamaClient(model=model)
        self.model = model
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        focus = kwargs.get("focus", "all")
        query_context = kwargs.get("query_context", "")
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to analyze"
            )
        
        try:
            # Sample if too many logs (max 50 for context limit)
            if len(logs) > 50:
                logger.info(f"Sampling 50 logs from {len(logs)} for analysis")
                sampled = logs.sample(n=50)
            else:
                sampled = logs
            
            # Build analysis prompt
            prompt = self._build_analysis_prompt(sampled, focus, query_context)
            
            # Call LLM
            logger.info(f"Calling LLM for analysis (focus: {focus})")
            response = self.llm.generate(prompt, temperature=0.7)
            
            # Parse response (could be JSON or text)
            analysis = {
                "raw_analysis": response,
                "log_count": len(sampled),
                "focus": focus
            }
            
            return ToolResult(
                success=True,
                data=analysis,
                message=f"Analysis complete: {response[:200]}...",
                metadata={"log_count": len(sampled), "focus": focus}
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Analysis failed: {str(e)}"
            )
    
    def _build_analysis_prompt(
        self,
        logs: pd.DataFrame,
        focus: str,
        query_context: str
    ) -> str:
        """Build prompt for LLM analysis."""
        prompt = "Analyze these logs and identify patterns, correlations, and issues.\n\n"
        
        if query_context:
            prompt += f"User Question: {query_context}\n\n"
        
        prompt += f"Focus: {focus}\n\n"
        prompt += f"Logs ({len(logs)} entries):\n\n"
        
        # Add log samples
        for i, row in logs.head(50).iterrows():
            if '_source.log' in row:
                try:
                    # Extract JSON
                    log_str = row['_source.log']
                    json_start = log_str.find('{')
                    if json_start == -1:
                        continue
                    json_str = log_str[json_start:].replace('""', '"')
                    log_json = json.loads(json_str)
                    severity = log_json.get('Severity', 'N/A')
                    message = log_json.get('Message', '')
                    function = log_json.get('Function', '')
                    
                    prompt += f"{i+1}. [{severity}] {function}: {message}\n"
                except:
                    prompt += f"{i+1}. {row.get('_source.log', '')[:100]}\n"
        
        prompt += "\nProvide analysis with:\n"
        prompt += "1. Patterns detected\n"
        prompt += "2. Likely root cause (if error-related)\n"
        prompt += "3. Timeline/sequence (if applicable)\n"
        prompt += "4. Recommendations\n"
        
        return prompt

