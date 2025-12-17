"""
Entity Field Mapper - Maps log fields to entity types using entity_mappings.yaml

Provides:
- Field name → Entity type mapping
- Entity-aware field grouping
- Query keyword → Entity type detection
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)


class EntityFieldMapper:
    """
    Maps fields to entity types based on entity_mappings.yaml
    
    Builds reverse mapping from field names to entity categories for
    intelligent field grouping and query understanding.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize mapper by loading entity_mappings.yaml
        
        Args:
            config_dir: Directory containing entity_mappings.yaml
        """
        self.config_dir = config_dir
        self.aliases: Dict[str, List[str]] = {}
        self.field_to_entity: Dict[str, str] = {}  # "CpeMacAddress" → "cpe"
        self.entity_labels: Dict[str, str] = {}  # "cpe" → "CPE"
        
        self._load_mappings()
    
    def _load_mappings(self) -> None:
        """Load and parse entity_mappings.yaml"""
        config_path = Path(self.config_dir) / "entity_mappings.yaml"
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.aliases = config.get('aliases', {})
            
            # Build reverse mapping: field name → entity type
            for entity_type, field_list in self.aliases.items():
                # Create display label (capitalize first letter)
                self.entity_labels[entity_type] = entity_type.upper() if len(entity_type) <= 3 else entity_type.replace('_', ' ').title()
                
                for field_name in field_list:
                    # Only map actual field names (PascalCase or contains uppercase)
                    # Skip lowercase aliases (those are for query matching)
                    if any(c.isupper() for c in field_name):
                        # Normalize field name for matching
                        normalized = field_name.strip()
                        self.field_to_entity[normalized] = entity_type
            
            logger.info(f"Loaded entity mappings: {len(self.field_to_entity)} field mappings, {len(self.aliases)} entity types")
            
        except Exception as e:
            logger.warning(f"Failed to load entity mappings: {e}. Using empty mappings.")
            self.aliases = {}
            self.field_to_entity = {}
    
    def get_entity_type(self, field_name: str) -> Optional[str]:
        """
        Get entity type for a field name.
        
        Args:
            field_name: Field name (e.g., "CpeMacAddress")
            
        Returns:
            Entity type (e.g., "cpe") or None if not found
        """
        return self.field_to_entity.get(field_name)
    
    def group_fields_by_entity(self, field_names: List[str]) -> Dict[str, List[str]]:
        """
        Group field names by their entity types.
        
        Args:
            field_names: List of field names from logs
            
        Returns:
            Dictionary: entity_type → list of field names
            Also includes "other" category for unmapped fields
        """
        grouped = {}
        other_fields = []
        
        for field in field_names:
            entity_type = self.get_entity_type(field)
            
            if entity_type:
                if entity_type not in grouped:
                    grouped[entity_type] = []
                grouped[entity_type].append(field)
            else:
                other_fields.append(field)
        
        # Add "other" category if there are unmapped fields
        if other_fields:
            grouped["other"] = other_fields
        
        return grouped
    
    def detect_entities_in_query(self, query: str) -> Set[str]:
        """
        Detect which entity types are mentioned in the query.
        
        Args:
            query: User query string
            
        Returns:
            Set of entity types mentioned (e.g., {"cpe", "cm"})
        """
        query_lower = query.lower()
        detected = set()
        
        for entity_type, alias_list in self.aliases.items():
            for alias in alias_list:
                # Check if alias appears in query (as whole word or part of phrase)
                alias_lower = alias.lower()
                if alias_lower in query_lower:
                    detected.add(entity_type)
                    break  # Found this entity type, move to next
        
        return detected
    
    def get_entity_label(self, entity_type: str) -> str:
        """
        Get display label for entity type.
        
        Args:
            entity_type: Entity type key (e.g., "cpe")
            
        Returns:
            Display label (e.g., "CPE")
        """
        return self.entity_labels.get(entity_type, entity_type.upper())
    
    def get_fields_for_entity(self, entity_type: str, available_fields: List[str]) -> List[str]:
        """
        Get fields that belong to a specific entity type.
        
        Args:
            entity_type: Entity type (e.g., "cpe")
            available_fields: List of available field names
            
        Returns:
            List of field names belonging to that entity type
        """
        return [f for f in available_fields if self.get_entity_type(f) == entity_type]






