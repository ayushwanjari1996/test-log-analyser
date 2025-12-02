"""
Entity extraction and manipulation tools.

Provides operations for extracting and working with entities from logs.
"""

import pandas as pd
from typing import List, Dict, Any
from .base_tool import Tool, ToolResult, ToolParameter, ParameterType
from ..entity_manager import EntityManager


class ExtractEntitiesTool(Tool):
    """Extract entities from logs"""
    
    def __init__(self, entity_manager: EntityManager):
        super().__init__(
            name="extract_entities",
            description="Extract entities of specific types from logs",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs to extract entities from",
                    required=True
                ),
                ToolParameter(
                    name="entity_types",
                    param_type=ParameterType.LIST,
                    description="List of entity types to extract (e.g., ['cm_mac', 'rpdname', 'md_id'])",
                    required=True,
                    example=["cm_mac", "rpdname"]
                )
            ]
        )
        self.entity_manager = entity_manager
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        entity_types = kwargs.get("entity_types", [])
        
        # Validate logs parameter
        if not isinstance(logs, pd.DataFrame):
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid 'logs' parameter: expected DataFrame, got {type(logs).__name__}. You must call search_logs first!"
            )
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to extract entities from",
                metadata={"count": 0}
            )
        
        if not entity_types:
            return ToolResult(
                success=False,
                data=None,
                error="No entity types specified"
            )
        
        # Extract entities - only from _source.log column
        search_columns = ["_source.log"] if "_source.log" in logs.columns else None
        
        entity_objects = self.entity_manager.extract_all_entities_from_logs(
            logs,
            entity_types=entity_types,
            search_columns=search_columns
        )
        
        # Convert to dict of type -> list of values
        entities_dict = {}
        for (etype, evalue), entity_obj in entity_objects.items():
            if etype not in entities_dict:
                entities_dict[etype] = []
            if evalue not in entities_dict[etype]:
                entities_dict[etype].append(evalue)
        
        # Count total
        total_entities = sum(len(values) for values in entities_dict.values())
        
        if total_entities == 0:
            return ToolResult(
                success=True,
                data=entities_dict,
                message=f"No entities of types {entity_types} found",
                metadata={"count": 0, "entity_types": entity_types}
            )
        
        # Build summary message WITH ACTUAL VALUES
        summary_parts = []
        for k, v in entities_dict.items():
            if v:
                # Show up to 3 values in message
                value_preview = ", ".join(str(x) for x in v[:3])
                if len(v) > 3:
                    value_preview += f" (and {len(v)-3} more)"
                summary_parts.append(f"{k}: [{value_preview}]")
        
        summary = "; ".join(summary_parts)
        
        return ToolResult(
            success=True,
            data=entities_dict,
            message=f"Extracted {total_entities} entities: {summary}",
            metadata={"count": total_entities, "by_type": {k: len(v) for k, v in entities_dict.items()}}
        )


class CountEntitiesTool(Tool):
    """Count occurrences of each entity value"""
    
    def __init__(self, entity_manager: EntityManager):
        super().__init__(
            name="count_entities",
            description="Count how many times each entity value appears in logs",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs",
                    required=True
                ),
                ToolParameter(
                    name="entity_type",
                    param_type=ParameterType.STRING,
                    description="Entity type to count (e.g., 'cm_mac')",
                    required=True,
                    example="cm_mac"
                )
            ]
        )
        self.entity_manager = entity_manager
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        entity_type = kwargs.get("entity_type")
        
        # Validate logs parameter
        if not isinstance(logs, pd.DataFrame):
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid 'logs' parameter: expected DataFrame, got {type(logs).__name__}. You must call search_logs first!"
            )
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to count entities in",
                metadata={"count": 0}
            )
        
        # Extract entities
        search_columns = ["_source.log"] if "_source.log" in logs.columns else None
        entity_objects = self.entity_manager.extract_all_entities_from_logs(
            logs,
            entity_types=[entity_type],
            search_columns=search_columns
        )
        
        # Count occurrences
        counts = {}
        for (etype, evalue), entity_obj in entity_objects.items():
            if etype == entity_type:
                counts[evalue] = len(entity_obj.occurrences)
        
        if not counts:
            return ToolResult(
                success=True,
                data={},
                message=f"No entities of type '{entity_type}' found",
                metadata={"count": 0}
            )
        
        # Sort by count descending
        sorted_counts = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
        
        return ToolResult(
            success=True,
            data=sorted_counts,
            message=f"Counted {len(counts)} unique {entity_type} entities",
            metadata={"count": len(counts), "total_occurrences": sum(counts.values())}
        )


class AggregateEntitiesTool(Tool):
    """Get all unique entity values of specified types"""
    
    def __init__(self, entity_manager: EntityManager):
        super().__init__(
            name="aggregate_entities",
            description="Get list of all unique entity values from logs",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs",
                    required=True
                ),
                ToolParameter(
                    name="entity_types",
                    param_type=ParameterType.LIST,
                    description="Entity types to aggregate",
                    required=True,
                    example=["cm_mac", "rpdname"]
                )
            ]
        )
        self.entity_manager = entity_manager
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        entity_types = kwargs.get("entity_types", [])
        
        # Validate logs parameter
        if not isinstance(logs, pd.DataFrame):
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid 'logs' parameter: expected DataFrame, got {type(logs).__name__}. You must call search_logs first!"
            )
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to aggregate entities from",
                metadata={"count": 0}
            )
        
        # Extract entities
        search_columns = ["_source.log"] if "_source.log" in logs.columns else None
        entity_objects = self.entity_manager.extract_all_entities_from_logs(
            logs,
            entity_types=entity_types,
            search_columns=search_columns
        )
        
        # Aggregate by type
        aggregated = {}
        for (etype, evalue), entity_obj in entity_objects.items():
            if etype not in aggregated:
                aggregated[etype] = []
            if evalue not in aggregated[etype]:
                aggregated[etype].append(evalue)
        
        total = sum(len(values) for values in aggregated.values())
        
        if total == 0:
            return ToolResult(
                success=True,
                data=aggregated,
                message=f"No entities of types {entity_types} found",
                metadata={"count": 0}
            )
        
        # Build summary WITH ACTUAL VALUES
        summary_parts = []
        for k, v in aggregated.items():
            if v:
                value_preview = ", ".join(str(x) for x in v[:3])
                if len(v) > 3:
                    value_preview += f" (and {len(v)-3} more)"
                summary_parts.append(f"{k}: [{value_preview}]")
        
        summary = "; ".join(summary_parts)
        
        return ToolResult(
            success=True,
            data=aggregated,
            message=f"Aggregated {total} unique entities: {summary}",
            metadata={"count": total, "by_type": {k: len(v) for k, v in aggregated.items()}}
        )


class FindEntityRelationshipsTool(Tool):
    """Find entities that co-occur with a target entity"""
    
    def __init__(self, entity_manager: EntityManager):
        super().__init__(
            name="find_entity_relationships",
            description="Find what other entities appear in logs with a target entity",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs",
                    required=True
                ),
                ToolParameter(
                    name="target_value",
                    param_type=ParameterType.STRING,
                    description="Entity value to find relationships for",
                    required=True,
                    example="MAWED07T01"
                ),
                ToolParameter(
                    name="related_types",
                    param_type=ParameterType.LIST,
                    description="Entity types to look for",
                    required=True,
                    example=["cm_mac", "md_id"]
                )
            ]
        )
        self.entity_manager = entity_manager
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        target_value = kwargs.get("target_value")
        related_types = kwargs.get("related_types", [])
        
        # Validate logs parameter
        if not isinstance(logs, pd.DataFrame):
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid 'logs' parameter: expected DataFrame, got {type(logs).__name__}. You must call search_logs first!"
            )
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data={},
                message="No logs to find relationships in",
                metadata={"count": 0}
            )
        
        # Filter logs containing target value
        # Search for target_value in the logs DataFrame
        mask = logs.astype(str).apply(lambda row: row.str.contains(str(target_value), case=False, na=False).any(), axis=1)
        target_logs = logs[mask]
        
        if target_logs.empty:
            return ToolResult(
                success=True,
                data={},
                message=f"No logs found containing '{target_value}'",
                metadata={"count": 0}
            )
        
        # Extract related entities from these logs
        search_columns = ["_source.log"] if "_source.log" in target_logs.columns else None
        entity_objects = self.entity_manager.extract_all_entities_from_logs(
            target_logs,
            entity_types=related_types,
            search_columns=search_columns
        )
        
        # Build relationships
        relationships = {}
        for (etype, evalue), entity_obj in entity_objects.items():
            if etype not in relationships:
                relationships[etype] = []
            if evalue not in relationships[etype]:
                relationships[etype].append(evalue)
        
        total = sum(len(values) for values in relationships.values())
        
        if total == 0:
            return ToolResult(
                success=True,
                data=relationships,
                message=f"No related entities of types {related_types} found for '{target_value}'",
                metadata={"count": 0, "target": target_value}
            )
        
        # Build summary WITH ACTUAL VALUES
        summary_parts = []
        for k, v in relationships.items():
            if v:
                value_preview = ", ".join(str(x) for x in v[:3])
                if len(v) > 3:
                    value_preview += f" (and {len(v)-3} more)"
                summary_parts.append(f"{k}: [{value_preview}]")
        
        summary = "; ".join(summary_parts)
        
        return ToolResult(
            success=True,
            data=relationships,
            message=f"Found {total} related entities for '{target_value}': {summary}",
            metadata={"count": total, "target": target_value, "by_type": {k: len(v) for k, v in relationships.items()}}
        )

