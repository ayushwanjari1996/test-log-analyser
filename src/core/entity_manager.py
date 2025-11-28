"""Entity management for extraction, normalization, and queue-based exploration."""

import re
from typing import List, Dict, Set, Optional, Any, Tuple
from collections import deque
import pandas as pd

from ..utils.logger import setup_logger
from ..utils.config import config
from ..utils.validators import sanitize_entity_name

logger = setup_logger()


class Entity:
    """
    Represents an entity extracted from logs.
    """
    
    def __init__(
        self,
        entity_type: str,
        entity_value: str,
        occurrences: Optional[List[int]] = None,
        confidence: float = 1.0,
        related_entities: Optional[List['Entity']] = None
    ):
        """
        Initialize an entity.
        
        Args:
            entity_type: Type of entity (e.g., 'cm', 'md_id')
            entity_value: The actual value (e.g., 'CM12345')
            occurrences: List of log indices where entity appears
            confidence: Confidence score (0-1)
            related_entities: List of related Entity objects
        """
        self.entity_type = entity_type
        self.entity_value = sanitize_entity_name(entity_value)
        self.occurrences = occurrences or []
        self.confidence = confidence
        self.related_entities = related_entities or []
        self.explored = False
    
    def add_occurrence(self, index: int):
        """Add a log index where this entity appears."""
        if index not in self.occurrences:
            self.occurrences.append(index)
    
    def mark_explored(self):
        """Mark this entity as explored."""
        self.explored = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "type": self.entity_type,
            "value": self.entity_value,
            "occurrences_count": len(self.occurrences),
            "confidence": self.confidence,
            "explored": self.explored,
            "related_count": len(self.related_entities)
        }
    
    def __hash__(self):
        return hash((self.entity_type, self.entity_value))
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return (
            self.entity_type == other.entity_type and
            self.entity_value == other.entity_value
        )
    
    def __repr__(self):
        return f"Entity({self.entity_type}={self.entity_value}, occurrences={len(self.occurrences)})"


class EntityQueue:
    """
    Queue-based entity exploration manager.
    Prevents cycles and manages priority-based exploration.
    """
    
    def __init__(self, max_depth: int = 5):
        """
        Initialize entity queue.
        
        Args:
            max_depth: Maximum exploration depth
        """
        self.queue = deque()
        self.processed: Set[Tuple[str, str]] = set()
        self.entities: Dict[Tuple[str, str], Entity] = {}
        self.max_depth = max_depth
        self.current_depth = 0
        
        logger.info(f"Initialized EntityQueue (max_depth={max_depth})")
    
    def add_entity(
        self,
        entity: Entity,
        priority: int = 0,
        depth: int = 0
    ):
        """
        Add entity to exploration queue.
        
        Args:
            entity: Entity to add
            priority: Priority level (higher = processed sooner)
            depth: Current exploration depth
        """
        entity_key = (entity.entity_type, entity.entity_value)
        
        # Skip if already processed
        if entity_key in self.processed:
            return
        
        # Skip if too deep
        if depth >= self.max_depth:
            logger.debug(f"Skipping {entity} - max depth reached")
            return
        
        # Add to queue
        self.queue.append((priority, depth, entity))
        self.entities[entity_key] = entity
        
        logger.debug(f"Added {entity} to queue (priority={priority}, depth={depth})")
    
    def get_next_entity(self) -> Optional[Tuple[int, Entity]]:
        """
        Get next entity from queue.
        
        Returns:
            Tuple of (depth, entity) or None if queue is empty
        """
        if not self.queue:
            return None
        
        # Sort by priority (descending) and depth (ascending)
        self.queue = deque(sorted(self.queue, key=lambda x: (-x[0], x[1])))
        
        priority, depth, entity = self.queue.popleft()
        entity_key = (entity.entity_type, entity.entity_value)
        
        # Mark as processed
        self.processed.add(entity_key)
        entity.mark_explored()
        self.current_depth = depth
        
        logger.debug(f"Processing {entity} (depth={depth})")
        return depth, entity
    
    def has_more(self) -> bool:
        """Check if queue has more entities."""
        return len(self.queue) > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "queued": len(self.queue),
            "processed": len(self.processed),
            "total_entities": len(self.entities),
            "current_depth": self.current_depth,
            "max_depth": self.max_depth
        }


class EntityManager:
    """
    Manages entity extraction, normalization, and relationships.
    """
    
    def __init__(self):
        """Initialize entity manager."""
        self.entities: Dict[Tuple[str, str], Entity] = {}
        logger.info("Initialized EntityManager")
    
    def normalize_entity(self, user_term: str) -> Tuple[str, str]:
        """
        Normalize user term to canonical entity type.
        
        Args:
            user_term: User-provided entity term
            
        Returns:
            Tuple of (entity_type, normalized_term)
        """
        user_term_lower = user_term.lower().strip()
        
        # Check all aliases
        aliases = config.entity_mappings.get("aliases", {})
        
        for entity_type, alias_list in aliases.items():
            if user_term_lower in [a.lower() for a in alias_list]:
                return entity_type, user_term
            
            # Check if the term itself is the entity type
            if user_term_lower == entity_type.lower():
                return entity_type, user_term
        
        # Default: treat as-is
        return "unknown", user_term
    
    def get_related_entities(self, entity_type: str) -> List[str]:
        """
        Get entity types related to the given entity type.
        
        Args:
            entity_type: Source entity type
            
        Returns:
            List of related entity types
        """
        return config.get_entity_relationships(entity_type)
    
    def extract_entities_from_text(
        self,
        text: str,
        entity_type: str
    ) -> List[str]:
        """
        Extract entities of a specific type from text.
        
        Args:
            text: Text to search
            entity_type: Type of entity to extract
            
        Returns:
            List of extracted entity values
        """
        patterns = config.get_entity_pattern(entity_type)
        
        if not patterns:
            return []
        
        found_entities = []
        
        for pattern in patterns:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                matches = regex.findall(text)
                
                for match in matches:
                    # Handle both simple matches and group matches
                    entity_value = match if isinstance(match, str) else match[0]
                    entity_value = sanitize_entity_name(entity_value)
                    
                    if entity_value and entity_value not in found_entities:
                        found_entities.append(entity_value)
                        
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        return found_entities
    
    def extract_all_entities_from_logs(
        self,
        logs: pd.DataFrame,
        entity_types: Optional[List[str]] = None,
        search_columns: Optional[List[str]] = None
    ) -> Dict[str, Entity]:
        """
        Extract all entities from log DataFrame.
        
        Args:
            logs: DataFrame of log entries
            entity_types: List of entity types to extract (None = all)
            search_columns: Columns to search (None = all text columns)
            
        Returns:
            Dictionary mapping (entity_type, entity_value) to Entity objects
        """
        if entity_types is None:
            # Get all entity types from config
            entity_types = list(config.entity_mappings.get("patterns", {}).keys())
        
        if search_columns is None:
            search_columns = logs.select_dtypes(include=['object']).columns.tolist()
        
        extracted_entities: Dict[Tuple[str, str], Entity] = {}
        
        logger.info(f"Extracting {len(entity_types)} entity types from {len(logs)} log entries")
        logger.info(f"Search columns: {search_columns}")
        
        for entity_type in entity_types:
            logger.info(f"Processing entity type: {entity_type}")
            patterns = config.get_entity_pattern(entity_type)
            
            if not patterns:
                continue
            
            for pattern in patterns:
                logger.debug(f"  Using pattern: {pattern}")
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    
                    # Search in specified columns
                    for col in search_columns:
                        if col not in logs.columns:
                            continue
                        
                        logger.debug(f"  Searching column: {col} ({len(logs)} rows)")
                        row_count = 0
                        for idx, value in logs[col].items():
                            row_count += 1
                            if row_count % 1000 == 0:
                                logger.debug(f"    Processed {row_count}/{len(logs)} rows in column {col}")
                            
                            if pd.isna(value):
                                continue
                            
                            matches = regex.findall(str(value))
                            
                            for match in matches:
                                entity_value = match if isinstance(match, str) else match[0]
                                entity_value = sanitize_entity_name(entity_value)
                                
                                if not entity_value:
                                    continue
                                
                                entity_key = (entity_type, entity_value)
                                
                                if entity_key not in extracted_entities:
                                    extracted_entities[entity_key] = Entity(
                                        entity_type=entity_type,
                                        entity_value=entity_value,
                                        occurrences=[idx]
                                    )
                                else:
                                    extracted_entities[entity_key].add_occurrence(idx)
                                
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        
        # Store in manager
        self.entities.update(extracted_entities)
        
        logger.info(f"Extracted {len(extracted_entities)} unique entities")
        return extracted_entities
    
    def find_entity_in_logs(
        self,
        logs: pd.DataFrame,
        entity_value: str,
        entity_type: Optional[str] = None
    ) -> Entity:
        """
        Find all occurrences of a specific entity in logs.
        
        Args:
            logs: DataFrame of log entries
            entity_value: The entity value to search for
            entity_type: Optional entity type
            
        Returns:
            Entity object with occurrence information
        """
        occurrences = []
        
        # Search all text columns
        for col in logs.select_dtypes(include=['object']).columns:
            for idx, value in logs[col].items():
                if pd.isna(value):
                    continue
                
                # Case-insensitive search
                if entity_value.lower() in str(value).lower():
                    occurrences.append(idx)
        
        # Determine entity type if not provided
        if entity_type is None:
            entity_type, _ = self.normalize_entity(entity_value)
        
        entity = Entity(
            entity_type=entity_type,
            entity_value=entity_value,
            occurrences=list(set(occurrences))  # Remove duplicates
        )
        
        entity_key = (entity_type, entity_value)
        self.entities[entity_key] = entity
        
        logger.info(f"Found entity {entity} in {len(entity.occurrences)} locations")
        return entity
    
    def build_entity_queue(
        self,
        initial_entities: List[Entity],
        max_depth: int = 5
    ) -> EntityQueue:
        """
        Build exploration queue from initial entities.
        
        Args:
            initial_entities: Starting entities
            max_depth: Maximum exploration depth
            
        Returns:
            Configured EntityQueue
        """
        queue = EntityQueue(max_depth=max_depth)
        
        # Add initial entities with highest priority
        for entity in initial_entities:
            queue.add_entity(entity, priority=10, depth=0)
        
        logger.info(f"Built entity queue with {len(initial_entities)} initial entities")
        return queue
    
    def expand_entity_relationships(
        self,
        entity: Entity,
        logs: pd.DataFrame,
        max_related: int = 5
    ) -> List[Entity]:
        """
        Find related entities based on co-occurrence in logs.
        
        Args:
            entity: Source entity
            logs: DataFrame of log entries
            max_related: Maximum related entities to return
            
        Returns:
            List of related Entity objects
        """
        related_entity_types = self.get_related_entities(entity.entity_type)
        
        if not related_entity_types:
            return []
        
        related_entities = []
        
        # Get logs where source entity appears
        if not entity.occurrences:
            return []
        
        entity_logs = logs.iloc[entity.occurrences]
        
        # Extract entities of related types from those logs
        for related_type in related_entity_types:
            extracted = self.extract_all_entities_from_logs(
                entity_logs,
                entity_types=[related_type]
            )
            
            for entity_key, related_entity in extracted.items():
                if len(related_entities) >= max_related:
                    break
                related_entities.append(related_entity)
        
        logger.info(f"Found {len(related_entities)} related entities for {entity}")
        return related_entities
    
    def get_entity_summary(self) -> Dict[str, Any]:
        """
        Get summary of all extracted entities.
        
        Returns:
            Dictionary with entity statistics
        """
        if not self.entities:
            return {"total_entities": 0}
        
        # Group by entity type
        by_type: Dict[str, int] = {}
        total_occurrences = 0
        
        for (entity_type, _), entity in self.entities.items():
            by_type[entity_type] = by_type.get(entity_type, 0) + 1
            total_occurrences += len(entity.occurrences)
        
        return {
            "total_entities": len(self.entities),
            "total_occurrences": total_occurrences,
            "by_type": by_type,
            "explored": sum(1 for e in self.entities.values() if e.explored)
        }
    
    def get_top_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Entity]:
        """
        Get top entities by occurrence count.
        
        Args:
            entity_type: Filter by entity type (None = all)
            limit: Maximum number to return
            
        Returns:
            List of Entity objects sorted by occurrence count
        """
        entities = list(self.entities.values())
        
        # Filter by type if specified
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        
        # Sort by occurrence count
        entities.sort(key=lambda e: len(e.occurrences), reverse=True)
        
        return entities[:limit]

