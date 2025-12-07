"""
Advanced aggregation tools.

Count unique values per group, with relationship chaining support.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
import pandas as pd

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from ..stream_searcher import StreamSearcher
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


def case_insensitive_get(json_obj: dict, field_name: str) -> Any:
    """
    Get field from JSON with case-insensitive matching.
    
    Args:
        json_obj: JSON dictionary
        field_name: Field name to find (case-insensitive)
        
    Returns:
        Field value or None if not found
    """
    # Try exact match first (fast path)
    if field_name in json_obj:
        return json_obj[field_name]
    
    # Try case-insensitive match
    field_lower = field_name.lower()
    for key, value in json_obj.items():
        if key.lower() == field_lower:
            return value
    
    return None


class CountUniquePerGroupTool(Tool):
    """
    Count unique values of one field per group of another field.
    
    Example: Count unique CmMacAddress per MdId
    SQL equivalent: SELECT MdId, COUNT(DISTINCT CmMacAddress) GROUP BY MdId
    """
    
    def __init__(self):
        super().__init__(
            name="count_unique_per_group",
            description="Count unique values of one field per group (COUNT DISTINCT)",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="Logs to analyze (auto-injected)",
                    required=True
                ),
                ToolParameter(
                    name="group_by",
                    param_type=ParameterType.STRING,
                    description="Field to group by (e.g., 'MdId', 'RpdName')",
                    required=True
                ),
                ToolParameter(
                    name="count_field",
                    param_type=ParameterType.STRING,
                    description="Field to count unique values of (e.g., 'CmMacAddress')",
                    required=True
                ),
                ToolParameter(
                    name="top_n",
                    param_type=ParameterType.INTEGER,
                    description="Return top N groups (default: 10)",
                    required=False
                )
            ]
        )
        self.requires_logs = True
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        group_by = kwargs.get("group_by", "")
        count_field = kwargs.get("count_field", "")
        top_n = kwargs.get("top_n", 10)
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to analyze"
            )
        
        if not group_by or not count_field:
            return ToolResult(
                success=False,
                data=None,
                error="Both 'group_by' and 'count_field' are required"
            )
        
        try:
            # Build mapping: group_value -> set of unique count_field values
            groups = defaultdict(set)
            
            if '_source.log' in logs.columns:
                for log_entry in logs['_source.log']:
                    try:
                        # Parse JSON
                        json_start = log_entry.find('{')
                        if json_start == -1:
                            continue
                        json_str = log_entry[json_start:].replace('""', '"')
                        log_json = json.loads(json_str)
                        
                        # Case-insensitive field lookup
                        group_value = case_insensitive_get(log_json, group_by)
                        count_value = case_insensitive_get(log_json, count_field)
                        
                        # Only count if both fields exist and have non-empty values
                        if (group_value is not None and 
                            count_value is not None and 
                            group_value not in ['<null>', 'null', ''] and
                            count_value not in ['<null>', 'null', '']):
                            groups[str(group_value)].add(str(count_value))
                            
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            if not groups:
                return ToolResult(
                    success=True,
                    data={},
                    message=f"No logs found with both '{group_by}' and '{count_field}' fields"
                )
            
            # Convert sets to counts
            group_counts = {group: len(values) for group, values in groups.items()}
            
            # Sort by count (descending) and take top N
            sorted_groups = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
            top_groups = dict(sorted_groups[:top_n])
            
            # Format message
            total_groups = len(group_counts)
            total_items = sum(group_counts.values())
            
            # Show all results if ≤ 10, otherwise show first 10 + "X more"
            display_limit = 10
            if len(top_groups) <= display_limit:
                # Show all
                top_str = ", ".join(f"{k}:{v}" for k, v in top_groups.items())
            else:
                # Show first 10 + count
                top_str = ", ".join(f"{k}:{v}" for k, v in list(top_groups.items())[:display_limit])
                top_str += f" (and {len(top_groups)-display_limit} more)"
            
            msg = f"Counted unique '{count_field}' per '{group_by}': {total_groups} groups, {total_items} total unique values. Results: {top_str}"
            
            return ToolResult(
                success=True,
                data=top_groups,
                message=msg,
                metadata={
                    "group_by": group_by,
                    "count_field": count_field,
                    "total_groups": total_groups,
                    "total_unique_values": total_items,
                    "top_n": top_n
                }
            )
            
        except Exception as e:
            logger.error(f"Error in count_unique_per_group: {e}")
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to count unique values: {str(e)}"
            )


class CountViaRelationshipTool(Tool):
    """
    Count values via multi-hop relationship chains.
    
    Example: Count CPEs per MdId when they're not in same log
    - CPE is in log with CM
    - CM is in log with RPD
    - RPD is in log with MdId
    → Chain: CPE → CM → RPD → MdId
    """
    
    def __init__(self, log_file: str, config_dir: str = "config"):
        super().__init__(
            name="count_via_relationship",
            description="Count values via relationship chains (for cross-log aggregation)",
            parameters=[
                ToolParameter(
                    name="source_field",
                    param_type=ParameterType.STRING,
                    description="Field to count (e.g., 'CpeMacAddress')",
                    required=True
                ),
                ToolParameter(
                    name="target_field",
                    param_type=ParameterType.STRING,
                    description="Field to group by (e.g., 'MdId')",
                    required=True
                ),
                ToolParameter(
                    name="max_depth",
                    param_type=ParameterType.INTEGER,
                    description="Maximum chain hops (default: 4)",
                    required=False
                ),
                ToolParameter(
                    name="top_n",
                    param_type=ParameterType.INTEGER,
                    description="Return top N groups (default: 10)",
                    required=False
                )
            ]
        )
        self.requires_logs = False
        self.log_file = log_file
        self.config_dir = config_dir
        
        # Load entity mappings
        config_path = Path(config_dir) / "entity_mappings.yaml"
        with open(config_path, 'r') as f:
            self.entity_config = yaml.safe_load(f)
        
        # Build field -> entity type mapping
        self.field_to_entity = {}
        for entity_type, config in self.entity_config.items():
            for field in config.get('fields', []):
                self.field_to_entity[field.lower()] = entity_type
    
    def execute(self, **kwargs) -> ToolResult:
        source_field = kwargs.get("source_field", "")
        target_field = kwargs.get("target_field", "")
        max_depth = kwargs.get("max_depth", 4)
        top_n = kwargs.get("top_n", 10)
        
        if not source_field or not target_field:
            return ToolResult(
                success=False,
                data=None,
                error="Both 'source_field' and 'target_field' are required"
            )
        
        try:
            # Step 1: Get all unique source values
            logger.info(f"Finding all unique values for '{source_field}'")
            searcher = StreamSearcher(self.log_file)
            
            # Search for logs containing source_field
            source_logs = searcher.search(source_field, case_sensitive=False, regex=False)
            
            source_values = set()
            for log_entry in source_logs['_source.log']:
                try:
                    json_start = log_entry.find('{')
                    if json_start == -1:
                        continue
                    json_str = log_entry[json_start:].replace('""', '"')
                    log_json = json.loads(json_str)
                    
                    value = case_insensitive_get(log_json, source_field)
                    if value and value not in ['<null>', 'null', '']:
                        source_values.add(str(value))
                except (json.JSONDecodeError, TypeError):
                    continue
            
            if not source_values:
                return ToolResult(
                    success=True,
                    data={},
                    message=f"No values found for '{source_field}'"
                )
            
            logger.info(f"Found {len(source_values)} unique values for '{source_field}'")
            
            # Step 2: For each source value, find target value via chaining
            target_counts = defaultdict(set)
            found_count = 0
            
            for source_value in source_values:
                target_value = self._find_target_via_chain(
                    source_value, 
                    target_field, 
                    max_depth
                )
                
                if target_value:
                    target_counts[target_value].add(source_value)
                    found_count += 1
            
            if not target_counts:
                return ToolResult(
                    success=True,
                    data={},
                    message=f"Could not find '{target_field}' for any '{source_field}' values (tried {len(source_values)} values)"
                )
            
            # Convert to counts
            group_counts = {group: len(values) for group, values in target_counts.items()}
            
            # Sort and take top N
            sorted_groups = sorted(group_counts.items(), key=lambda x: x[1], reverse=True)
            top_groups = dict(sorted_groups[:top_n])
            
            # Format message
            total_groups = len(group_counts)
            coverage_pct = (found_count / len(source_values)) * 100
            
            # Show all results if ≤ 10, otherwise show first 10 + "X more"
            display_limit = 10
            if len(top_groups) <= display_limit:
                # Show all
                top_str = ", ".join(f"{k}:{v}" for k, v in top_groups.items())
            else:
                # Show first 10 + count
                top_str = ", ".join(f"{k}:{v}" for k, v in list(top_groups.items())[:display_limit])
                top_str += f" (and {len(top_groups)-display_limit} more)"
            
            msg = f"Counted '{source_field}' per '{target_field}' via relationship chain: {total_groups} groups, {found_count}/{len(source_values)} values mapped ({coverage_pct:.1f}%). Results: {top_str}"
            
            return ToolResult(
                success=True,
                data=top_groups,
                message=msg,
                metadata={
                    "source_field": source_field,
                    "target_field": target_field,
                    "total_groups": total_groups,
                    "values_mapped": found_count,
                    "values_total": len(source_values),
                    "coverage_percent": coverage_pct,
                    "max_depth": max_depth
                }
            )
            
        except Exception as e:
            logger.error(f"Error in count_via_relationship: {e}")
            import traceback
            traceback.print_exc()
            return ToolResult(
                success=False,
                data=None,
                error=f"Failed to count via relationship: {str(e)}"
            )
    
    def _find_target_via_chain(
        self, 
        start_value: str, 
        target_field: str, 
        max_depth: int
    ) -> Optional[str]:
        """
        Find target field value via BFS relationship traversal.
        
        Returns:
            Target field value or None if not found
        """
        from collections import deque
        
        searcher = StreamSearcher(self.log_file)
        visited = set()
        queue = deque([(start_value, 0)])  # (value, depth)
        
        while queue:
            current_value, depth = queue.popleft()
            
            if depth > max_depth:
                continue
            
            if current_value in visited:
                continue
            visited.add(current_value)
            
            # Search for logs containing this value
            try:
                results = searcher.search(current_value, case_sensitive=False, regex=False, max_results=50)
                
                for log_entry in results['_source.log']:
                    try:
                        json_start = log_entry.find('{')
                        if json_start == -1:
                            continue
                        json_str = log_entry[json_start:].replace('""', '"')
                        log_json = json.loads(json_str)
                        
                        # Check if target field is in this log
                        target_value = case_insensitive_get(log_json, target_field)
                        if target_value and target_value not in ['<null>', 'null', '']:
                            return str(target_value)  # Found it!
                        
                        # Extract entity fields to continue BFS
                        for field_name, field_value in log_json.items():
                            if not field_value or field_value in ['<null>', 'null', '']:
                                continue
                            
                            # Check if this is an entity field (skip generic fields)
                            field_entity_type = self.field_to_entity.get(field_name.lower())
                            if field_entity_type and str(field_value) not in visited:
                                queue.append((str(field_value), depth + 1))
                                
                    except (json.JSONDecodeError, TypeError):
                        continue
                        
            except Exception as e:
                logger.debug(f"Search failed for value '{current_value}': {e}")
                continue
        
        return None  # Not found within max_depth

