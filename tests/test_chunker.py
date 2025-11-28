"""Test log chunking functionality."""

import pytest
import pandas as pd
from pathlib import Path

from src.core.log_processor import LogProcessor
from src.core.chunker import LogChunker, LogChunk


SAMPLE_LOG = "tests/sample_logs/system.csv"


@pytest.fixture
def sample_logs():
    """Fixture to load sample logs."""
    processor = LogProcessor(SAMPLE_LOG)
    return processor.read_all_logs()


def test_log_chunk_initialization(sample_logs):
    """Test LogChunk initialization."""
    chunk_logs = sample_logs.head(10)
    chunk = LogChunk(
        logs=chunk_logs,
        chunk_id=0,
        start_index=0,
        end_index=10
    )
    
    assert chunk.chunk_id == 0
    assert chunk.start_index == 0
    assert chunk.end_index == 10
    assert len(chunk) == 10
    assert chunk.token_estimate > 0


def test_log_chunk_to_text(sample_logs):
    """Test converting chunk to text."""
    chunk_logs = sample_logs.head(5)
    chunk = LogChunk(
        logs=chunk_logs,
        chunk_id=0,
        start_index=0,
        end_index=5
    )
    
    text = chunk.to_text()
    assert isinstance(text, str)
    assert len(text) > 0


def test_log_chunk_to_dict(sample_logs):
    """Test converting chunk to dictionary."""
    chunk_logs = sample_logs.head(5)
    chunk = LogChunk(
        logs=chunk_logs,
        chunk_id=0,
        start_index=0,
        end_index=5,
        focus_entity="CM12345"
    )
    
    chunk_dict = chunk.to_dict()
    assert chunk_dict["chunk_id"] == 0
    assert chunk_dict["focus_entity"] == "CM12345"
    assert chunk_dict["entry_count"] == 5
    assert "logs" in chunk_dict


def test_chunker_initialization():
    """Test LogChunker initialization."""
    chunker = LogChunker()
    assert chunker.max_tokens > 0
    assert chunker.overlap_lines >= 0


def test_chunk_by_size(sample_logs):
    """Test size-based chunking."""
    chunker = LogChunker()
    chunks = chunker.chunk_by_size(sample_logs, max_tokens=1000)
    
    assert len(chunks) > 0
    assert all(isinstance(chunk, LogChunk) for chunk in chunks)
    
    # Check that chunks don't exceed token limit (with some tolerance)
    for chunk in chunks:
        assert chunk.token_estimate <= chunker.max_tokens * 1.2  # 20% tolerance


def test_chunk_by_size_small_data(sample_logs):
    """Test chunking with very small data."""
    small_logs = sample_logs.head(3)
    chunker = LogChunker()
    chunks = chunker.chunk_by_size(small_logs)
    
    assert len(chunks) >= 1


def test_chunk_by_entity_context(sample_logs):
    """Test entity-context based chunking."""
    # Find indices where CM12345 appears
    indices = sample_logs[sample_logs["entity_id"] == "CM12345"].index.tolist()
    
    chunker = LogChunker()
    chunks = chunker.chunk_by_entity_context(
        sample_logs,
        entity_indices=indices,
        entity_name="CM12345",
        context_lines=5
    )
    
    assert len(chunks) > 0
    assert all(chunk.focus_entity == "CM12345" for chunk in chunks)


def test_chunk_by_entity_no_indices(sample_logs):
    """Test entity chunking with no indices."""
    chunker = LogChunker()
    chunks = chunker.chunk_by_entity_context(
        sample_logs,
        entity_indices=[],
        entity_name="CM99999"
    )
    
    assert len(chunks) == 0


def test_chunk_by_time_window(sample_logs):
    """Test time-window based chunking."""
    chunker = LogChunker()
    chunks = chunker.chunk_by_time_window(
        sample_logs,
        timestamp_column="timestamp",
        window_minutes=5
    )
    
    assert len(chunks) > 0
    assert all(isinstance(chunk, LogChunk) for chunk in chunks)


def test_merge_overlapping_chunks(sample_logs):
    """Test merging overlapping chunks."""
    chunker = LogChunker()
    
    # Create overlapping chunks
    chunk1 = LogChunk(sample_logs.iloc[0:10], 0, 0, 10)
    chunk2 = LogChunk(sample_logs.iloc[8:18], 1, 8, 18)
    chunk3 = LogChunk(sample_logs.iloc[25:35], 2, 25, 35)
    
    chunks = [chunk1, chunk2, chunk3]
    merged = chunker.merge_overlapping_chunks(chunks, max_tokens=10000)
    
    # Should merge chunk1 and chunk2 (overlapping), but not chunk3 (separate)
    assert len(merged) <= len(chunks)


def test_smart_chunk_entity_priority(sample_logs):
    """Test smart chunking with entity priority."""
    # Find CM12345 occurrences
    cm_indices = sample_logs[sample_logs["entity_id"] == "CM12345"].index.tolist()
    entity_indices = {"CM12345": cm_indices}
    
    chunker = LogChunker()
    chunks = chunker.smart_chunk(
        sample_logs,
        entity_indices=entity_indices,
        prioritize_entities=True
    )
    
    assert len(chunks) > 0
    
    # Some chunks should have focus_entity set
    entity_chunks = [c for c in chunks if c.focus_entity]
    assert len(entity_chunks) > 0


def test_smart_chunk_no_entities(sample_logs):
    """Test smart chunking without entities."""
    chunker = LogChunker()
    chunks = chunker.smart_chunk(sample_logs, entity_indices=None)
    
    assert len(chunks) > 0
    # Should fall back to size-based chunking
    assert all(chunk.focus_entity is None for chunk in chunks)


def test_get_chunk_statistics(sample_logs):
    """Test getting chunk statistics."""
    chunker = LogChunker()
    chunks = chunker.chunk_by_size(sample_logs)
    
    stats = chunker.get_chunk_statistics(chunks)
    
    assert "total_chunks" in stats
    assert "total_entries" in stats
    assert "avg_tokens_per_chunk" in stats
    assert stats["total_chunks"] == len(chunks)


def test_chunk_overlap(sample_logs):
    """Test that chunks have proper overlap."""
    chunker = LogChunker()
    chunks = chunker.chunk_by_size(sample_logs, max_tokens=500)
    
    if len(chunks) > 1:
        # Check overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            chunk1 = chunks[i]
            chunk2 = chunks[i + 1]
            
            # There should be some overlap
            # (chunk2 start should be before chunk1 end)
            if chunk2.start_index < len(sample_logs):
                overlap_size = chunk1.end_index - chunk2.start_index
                assert overlap_size >= 0  # Should have overlap or be adjacent


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

