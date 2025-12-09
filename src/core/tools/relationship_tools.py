"""
Relationship discovery tools.

Find connections between entities across multiple log entries.
"""

import json
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any, Set, Optional, Tuple
import pandas as pd
from collections import deque

from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from ..stream_searcher import StreamSearcher

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


class FindRelationshipChainTool(Tool):
    """
    Find relationship chain between start value and target field.
    
    Uses BFS to traverse log relationships up to max_depth levels.
    Solves the CPE→RPD→MdId problem where data is split across logs.
    """
    
    def __init__(self, log_file: str, config_dir: str = "config"):
        super().__init__(
            name="find_relationship_chain",
            description="Find connection between start entity and target field (tree search)",
            parameters=[
                ToolParameter(
                    name="start_value",
                    param_type=ParameterType.STRING,
                    description="Starting value to search from (MAC, IP, name, etc.)",
                    required=True
                ),
                ToolParameter(
                    name="target_field",
                    param_type=ParameterType.STRING,
                    description="Target field to find (MdId, RpdName, etc.)",
                    required=True
                ),
                ToolParameter(
                    name="max_depth",
                    param_type=ParameterType.INTEGER,
                    description="Maximum traversal depth (default: 4)",
                    required=False
                )
            ]
        )
        self.log_file = log_file
        self.searcher = StreamSearcher(log_file)
        self.requires_logs = False
        
        # Load entity mappings
        mapping_file = Path(config_dir) / "entity_mappings.yaml"
        with open(mapping_file, 'r') as f:
            self.entity_config = yaml.safe_load(f)
        
        # Build reverse lookup: field_name -> entity_type
        self.field_to_entity = {}
        for entity_type, aliases in self.entity_config['aliases'].items():
            for alias in aliases:
                self.field_to_entity[alias.lower()] = entity_type
    
    def execute(self, **kwargs) -> ToolResult:
        start_value = kwargs.get("start_value", "")
        target_field = kwargs.get("target_field", "")
        max_depth = kwargs.get("max_depth", 4)
        
        if not start_value or not target_field:
            return ToolResult(
                success=False,
                data=None,
                error="Both start_value and target_field required"
            )
        
        try:
            # BFS to find target field
            result = self._bfs_search(start_value, target_field, max_depth)
            
            if result["found"]:
                path_str = " → ".join(result["path"])
                return ToolResult(
                    success=True,
                    data={
                        "value": result["value"],
                        "path": result["path"],
                        "depth": result["depth"]
                    },
                    message=f"[FINAL] Found {target_field}='{result['value']}' via path: {path_str}",
                    metadata={
                        "target_field": target_field,
                        "value": result["value"],
                        "depth": result["depth"],
                        "path": result["path"],
                        "data_type": "final_value"
                    }
                )
            else:
                return ToolResult(
                    success=True,
                    data=None,
                    message=f"Could not find '{target_field}' within {max_depth} levels from '{start_value}'",
                    metadata={
                        "target_field": target_field,
                        "explored_depth": result["depth"],
                        "partial_path": result.get("path", [])
                    }
                )
                
        except Exception as e:
            logger.error(f"Relationship chain search failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Search failed: {str(e)}"
            )
    
    def _bfs_search(
        self,
        start_value: str,
        target_field: str,
        max_depth: int
    ) -> Dict[str, Any]:
        """
        BFS search for target field.
        
        Returns:
            {
                "found": bool,
                "value": target value or None,
                "path": list of field:value,
                "depth": levels traversed
            }
        """
        # Queue: (value_to_search, current_path, depth)
        queue = deque([(start_value, [], 0)])
        visited = set([start_value.lower()])
        
        while queue:
            current_value, path, depth = queue.popleft()
            
            # Check depth limit
            if depth > max_depth:
                continue
            
            logger.debug(f"Level {depth}: Searching for '{current_value}'")
            
            # Grep for this value
            results = self.searcher.search(current_value, max_results=10)
            
            if results.empty:
                logger.debug(f"  No logs found for '{current_value}'")
                continue
            
            # Parse entity fields from matching logs
            fields = self._extract_entity_fields(results)
            
            # Check if target field is in these logs (case-insensitive)
            target_lower = target_field.lower()
            for field_name, field_values in fields.items():
                if field_name.lower() == target_lower:
                    # Found it!
                    final_path = path + [f"{field_name}:{field_values[0]}"]
                    logger.debug(f"  ✓ Found target at depth {depth}")
                    return {
                        "found": True,
                        "value": field_values[0],
                        "path": final_path,
                        "depth": depth
                    }
            
            # Get current entity type for relationship filtering
            current_entity_type = self._detect_entity_type(current_value, fields)
            valid_relationships = self._get_valid_relationships(current_entity_type)
            
            # Add discovered fields to queue (only valid entity fields)
            for field_name, field_values in fields.items():
                # Get entity type of this field
                field_entity_type = self.field_to_entity.get(field_name.lower())
                
                # Skip if not a valid relationship
                if field_entity_type and field_entity_type not in valid_relationships:
                    logger.debug(f"  Skipping {field_name} (not in valid relationships)")
                    continue
                
                for value in field_values[:2]:  # Limit to 2 values per field
                    value_str = str(value).lower()
                    
                    # Skip if already visited
                    if value_str in visited:
                        continue
                    
                    visited.add(value_str)
                    new_path = path + [f"{field_name}:{value}"]
                    queue.append((value, new_path, depth + 1))
                    
                    logger.debug(f"  Added to queue: {field_name}={value}")
        
        # Not found
        return {
            "found": False,
            "value": None,
            "path": [],
            "depth": max_depth
        }
    
    def _extract_entity_fields(self, logs: pd.DataFrame) -> Dict[str, List[Any]]:
        """
        Extract ONLY entity fields from logs (skip generic fields).
        
        Args:
            logs: DataFrame with logs
            
        Returns:
            Dict of field_name -> list of unique values
        """
        entity_fields = {}
        
        # Generic fields to skip
        skip_fields = {'role', 'severity', 'package', 'version', 'file', 'logger', 
                      'function', 'message', 'netmasklength', 'cpetype'}
        
        if '_source.log' not in logs.columns:
            return entity_fields
        
        for log_entry in logs['_source.log']:
            try:
                # Extract JSON part (after "stdout F " prefix)
                if isinstance(log_entry, str):
                    # Find the JSON part
                    json_start = log_entry.find('{')
                    if json_start == -1:
                        continue
                    
                    json_str = log_entry[json_start:]
                    
                    # Replace double-escaped quotes
                    json_str = json_str.replace('""', '"')
                    
                    # Parse JSON
                    log_json = json.loads(json_str)
                    
                    # Extract each field
                    for field_name, field_value in log_json.items():
                        # Skip generic fields
                        if field_name.lower() in skip_fields:
                            continue
                        
                        # Skip empty or null
                        if not field_value or field_value in ['<null>', 'null', '']:
                            continue
                        
                        # Skip non-scalar fields
                        if isinstance(field_value, (dict, list)):
                            continue
                        
                        # Add to collection
                        if field_name not in entity_fields:
                            entity_fields[field_name] = []
                        
                        if field_value not in entity_fields[field_name]:
                            entity_fields[field_name].append(field_value)
                        
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Failed to parse log entry: {e}")
                continue
        
        return entity_fields
    
    def _detect_entity_type(self, value: str, fields: Dict[str, List[Any]]) -> Optional[str]:
        """
        Detect entity type from value or field context.
        
        Returns:
            Entity type (e.g., 'cpe', 'cm', 'rpdname') or None
        """
        # Check if value appears in any entity field
        for field_name, field_values in fields.items():
            if value in [str(v) for v in field_values]:
                entity_type = self.field_to_entity.get(field_name.lower())
                if entity_type:
                    return entity_type
        
        # Fallback: try to guess from value format
        if ':' in value and value.count(':') == 5:
            return 'cpe'  # MAC address
        elif value.startswith('0x'):
            return 'md_id'  # Hex ID
        elif 'rpd' in value.lower():
            return 'rpdname'
        
        return None
    
    def _get_valid_relationships(self, entity_type: Optional[str]) -> Set[str]:
        """
        Get valid relationships for an entity type.
        
        Returns:
            Set of entity types this entity can connect to
        """
        if not entity_type or entity_type not in self.entity_config['relationships']:
            # If unknown, allow all entity types
            return set(self.entity_config['aliases'].keys())
        
        return set(self.entity_config['relationships'][entity_type])

