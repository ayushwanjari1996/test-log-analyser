"""Test log processor functionality."""

import pytest
import pandas as pd
from pathlib import Path

from src.core.log_processor import LogProcessor
from src.utils.exceptions import LogFileError


# Sample log file path
SAMPLE_LOG = "tests/sample_logs/system.csv"


def test_log_processor_initialization():
    """Test LogProcessor initialization with valid file."""
    processor = LogProcessor(SAMPLE_LOG)
    assert processor.log_file_path.exists()
    assert processor.schema_name == "default"


def test_log_processor_invalid_file():
    """Test LogProcessor with non-existent file."""
    with pytest.raises(LogFileError):
        LogProcessor("nonexistent.csv")


def test_read_all_logs():
    """Test reading entire log file."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    assert isinstance(logs, pd.DataFrame)
    assert len(logs) > 0
    assert "timestamp" in logs.columns
    assert "severity" in logs.columns
    assert "message" in logs.columns


def test_read_csv_stream():
    """Test streaming log file in chunks."""
    processor = LogProcessor(SAMPLE_LOG)
    chunks = list(processor.read_csv_stream(chunk_size=10))
    
    assert len(chunks) > 0
    assert all(isinstance(chunk, pd.DataFrame) for chunk in chunks)


def test_filter_by_entity():
    """Test filtering logs by entity value."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Filter for CM12345
    filtered = processor.filter_by_entity(logs, "entity_id", "CM12345")
    
    assert len(filtered) > 0
    assert all("CM12345" in str(row) for _, row in filtered.iterrows())


def test_filter_by_entity_substring():
    """Test substring matching in entity filter."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Filter for any CM entity
    filtered = processor.filter_by_entity(logs, "message", "CM", exact_match=False)
    
    assert len(filtered) > 0


def test_filter_by_timerange():
    """Test filtering logs by time range."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Filter for specific time range
    filtered = processor.filter_by_timerange(
        logs,
        "timestamp",
        start_time="2024-11-28 10:05:00",
        end_time="2024-11-28 10:10:00"
    )
    
    assert len(filtered) > 0
    assert len(filtered) < len(logs)


def test_extract_entities():
    """Test entity extraction from logs."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Extract CM entities
    entities = processor.extract_entities(logs, "cm")
    
    assert isinstance(entities, dict)
    assert len(entities) > 0
    
    # Check that CM12345 is found
    assert any("12345" in entity for entity in entities.keys())


def test_get_context_around_line():
    """Test getting context lines around a specific entry."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Get context around line 10
    context = processor.get_context_around_line(logs, 10, before_lines=5, after_lines=5)
    
    assert len(context) > 0
    assert len(context) <= 11  # 5 before + 1 target + 5 after


def test_search_text():
    """Test text search across logs."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Search for "error" in logs
    results = processor.search_text(logs, "error", case_sensitive=False)
    
    assert len(results) > 0
    # Verify each result contains "error" (case-insensitive)
    for _, row in results.iterrows():
        row_text = " ".join(str(val) for val in row.values).lower()
        assert "error" in row_text


def test_filter_by_severity():
    """Test filtering logs by severity level."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Filter for ERROR and above
    filtered = processor.filter_by_severity(logs, min_severity="ERROR")
    
    assert len(filtered) > 0
    assert len(filtered) < len(logs)
    
    # All entries should be ERROR or CRITICAL
    for _, row in filtered.iterrows():
        severity = str(row.get("severity", "")).upper()
        assert severity in ["ERROR", "CRITICAL", "FATAL"]


def test_get_statistics():
    """Test getting log statistics."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    stats = processor.get_statistics(logs)
    
    assert "total_entries" in stats
    assert "columns" in stats
    assert "memory_usage_mb" in stats
    assert stats["total_entries"] == len(logs)
    assert "severity_counts" in stats


def test_multiple_filters():
    """Test combining multiple filters."""
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    
    # Filter by entity
    filtered = processor.filter_by_entity(logs, "entity_id", "CM12345")
    
    # Then filter by severity
    filtered = processor.filter_by_severity(filtered, min_severity="WARN")
    
    assert len(filtered) >= 0
    # All entries should have CM12345 and severity >= WARN
    for _, row in filtered.iterrows():
        assert "CM12345" in str(row)
        severity = str(row.get("severity", "")).upper()
        assert severity in ["WARN", "WARNING", "ERROR", "CRITICAL", "FATAL"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

