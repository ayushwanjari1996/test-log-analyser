"""Test entity manager functionality."""

import pytest
import pandas as pd

from src.core.log_processor import LogProcessor
from src.core.entity_manager import Entity, EntityQueue, EntityManager


SAMPLE_LOG = "tests/sample_logs/system.csv"


@pytest.fixture
def sample_logs():
    """Fixture to load sample logs."""
    processor = LogProcessor(SAMPLE_LOG)
    return processor.read_all_logs()


@pytest.fixture
def entity_manager():
    """Fixture for EntityManager."""
    return EntityManager()


def test_entity_initialization():
    """Test Entity object initialization."""
    entity = Entity(
        entity_type="cm",
        entity_value="CM12345",
        occurrences=[0, 5, 10]
    )
    
    assert entity.entity_type == "cm"
    assert entity.entity_value == "CM12345"
    assert len(entity.occurrences) == 3
    assert not entity.explored


def test_entity_add_occurrence():
    """Test adding occurrences to entity."""
    entity = Entity("cm", "CM12345", [0])
    entity.add_occurrence(5)
    entity.add_occurrence(5)  # Duplicate
    
    assert len(entity.occurrences) == 2
    assert 5 in entity.occurrences


def test_entity_mark_explored():
    """Test marking entity as explored."""
    entity = Entity("cm", "CM12345")
    assert not entity.explored
    
    entity.mark_explored()
    assert entity.explored


def test_entity_to_dict():
    """Test converting entity to dictionary."""
    entity = Entity("cm", "CM12345", [0, 1, 2])
    entity_dict = entity.to_dict()
    
    assert entity_dict["type"] == "cm"
    assert entity_dict["value"] == "CM12345"
    assert entity_dict["occurrences_count"] == 3


def test_entity_equality():
    """Test entity equality comparison."""
    entity1 = Entity("cm", "CM12345")
    entity2 = Entity("cm", "CM12345")
    entity3 = Entity("cm", "CM12346")
    
    assert entity1 == entity2
    assert entity1 != entity3


def test_entity_queue_initialization():
    """Test EntityQueue initialization."""
    queue = EntityQueue(max_depth=5)
    assert queue.max_depth == 5
    assert not queue.has_more()


def test_entity_queue_add_entity():
    """Test adding entity to queue."""
    queue = EntityQueue(max_depth=5)
    entity = Entity("cm", "CM12345")
    
    queue.add_entity(entity, priority=10, depth=0)
    assert queue.has_more()


def test_entity_queue_prevent_duplicates():
    """Test that queue prevents duplicate processing."""
    queue = EntityQueue(max_depth=5)
    entity = Entity("cm", "CM12345")
    
    queue.add_entity(entity, priority=10, depth=0)
    queue.add_entity(entity, priority=5, depth=1)  # Should be ignored
    
    # Should only have one entity
    depth, retrieved = queue.get_next_entity()
    assert retrieved == entity
    assert not queue.has_more()


def test_entity_queue_priority_ordering():
    """Test that queue respects priority ordering."""
    queue = EntityQueue(max_depth=5)
    
    entity1 = Entity("cm", "CM12345")
    entity2 = Entity("cm", "CM12346")
    entity3 = Entity("cm", "CM12347")
    
    # Add with different priorities
    queue.add_entity(entity1, priority=5, depth=0)
    queue.add_entity(entity2, priority=10, depth=0)
    queue.add_entity(entity3, priority=1, depth=0)
    
    # Should get highest priority first
    depth, first = queue.get_next_entity()
    assert first == entity2  # Priority 10


def test_entity_queue_max_depth():
    """Test that queue respects max depth."""
    queue = EntityQueue(max_depth=2)
    entity = Entity("cm", "CM12345")
    
    queue.add_entity(entity, priority=10, depth=3)  # Too deep
    assert not queue.has_more()


def test_entity_queue_get_statistics():
    """Test getting queue statistics."""
    queue = EntityQueue(max_depth=5)
    
    entity1 = Entity("cm", "CM12345")
    entity2 = Entity("cm", "CM12346")
    
    queue.add_entity(entity1, priority=10, depth=0)
    queue.add_entity(entity2, priority=5, depth=1)
    
    stats = queue.get_statistics()
    assert stats["queued"] == 2
    assert stats["processed"] == 0
    assert stats["max_depth"] == 5


def test_entity_manager_initialization(entity_manager):
    """Test EntityManager initialization."""
    assert isinstance(entity_manager, EntityManager)
    assert len(entity_manager.entities) == 0


def test_normalize_entity(entity_manager):
    """Test entity normalization."""
    # Test known entity type
    entity_type, term = entity_manager.normalize_entity("cable modem")
    assert entity_type == "cm"
    
    # Test unknown entity
    entity_type, term = entity_manager.normalize_entity("unknown_entity")
    assert entity_type == "unknown"


def test_get_related_entities(entity_manager):
    """Test getting related entities."""
    related = entity_manager.get_related_entities("cm")
    assert isinstance(related, list)
    # Should have some related entities based on config
    # (md_id, mac_address, ip_address from config)


def test_extract_entities_from_text(entity_manager):
    """Test extracting entities from text."""
    text = "Cable modem CM12345 and CM12346 are active"
    entities = entity_manager.extract_entities_from_text(text, "cm")
    
    assert len(entities) > 0
    # Should find both CM12345 and CM12346


def test_extract_all_entities_from_logs(entity_manager, sample_logs):
    """Test extracting all entities from logs."""
    entities = entity_manager.extract_all_entities_from_logs(
        sample_logs,
        entity_types=["cm"]
    )
    
    assert len(entities) > 0
    assert all(isinstance(entity, Entity) for entity in entities.values())
    
    # Check that entities have occurrences
    for entity in entities.values():
        assert len(entity.occurrences) > 0


def test_find_entity_in_logs(entity_manager, sample_logs):
    """Test finding specific entity in logs."""
    entity = entity_manager.find_entity_in_logs(
        sample_logs,
        entity_value="CM12345"
    )
    
    assert isinstance(entity, Entity)
    assert entity.entity_value == "CM12345"
    assert len(entity.occurrences) > 0


def test_build_entity_queue(entity_manager):
    """Test building entity queue."""
    entity1 = Entity("cm", "CM12345", [0])
    entity2 = Entity("cm", "CM12346", [1])
    
    queue = entity_manager.build_entity_queue([entity1, entity2], max_depth=5)
    
    assert isinstance(queue, EntityQueue)
    assert queue.has_more()


def test_expand_entity_relationships(entity_manager, sample_logs):
    """Test expanding entity relationships."""
    # First find an entity
    entity = entity_manager.find_entity_in_logs(sample_logs, "CM12345")
    
    # Expand relationships
    related = entity_manager.expand_entity_relationships(
        entity,
        sample_logs,
        max_related=5
    )
    
    assert isinstance(related, list)
    # May or may not find related entities depending on config and data


def test_get_entity_summary(entity_manager, sample_logs):
    """Test getting entity summary."""
    # Extract some entities first
    entity_manager.extract_all_entities_from_logs(sample_logs, entity_types=["cm"])
    
    summary = entity_manager.get_entity_summary()
    
    assert "total_entities" in summary
    assert "total_occurrences" in summary
    assert "by_type" in summary
    assert summary["total_entities"] > 0


def test_get_top_entities(entity_manager, sample_logs):
    """Test getting top entities by occurrence."""
    # Extract entities
    entity_manager.extract_all_entities_from_logs(sample_logs, entity_types=["cm"])
    
    top = entity_manager.get_top_entities(entity_type="cm", limit=3)
    
    assert len(top) <= 3
    assert all(isinstance(entity, Entity) for entity in top)
    
    # Should be sorted by occurrence count
    if len(top) > 1:
        assert len(top[0].occurrences) >= len(top[1].occurrences)


def test_entity_manager_multiple_entity_types(entity_manager, sample_logs):
    """Test extracting multiple entity types."""
    entities = entity_manager.extract_all_entities_from_logs(
        sample_logs,
        entity_types=["cm", "md_id"]
    )
    
    # Should find both CM and MdId entities
    entity_types = {entity.entity_type for entity in entities.values()}
    assert len(entity_types) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

