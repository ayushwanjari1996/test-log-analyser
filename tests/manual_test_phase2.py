#!/usr/bin/env python
"""
Manual testing script for Phase 2 components.
Demonstrates usage of log processor, chunker, and entity manager.

Usage:
    python tests/manual_test_phase2.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

from src.core.log_processor import LogProcessor
from src.core.chunker import LogChunker
from src.core.entity_manager import EntityManager, Entity


console = Console()
SAMPLE_LOG = "tests/sample_logs/system.csv"


def test_log_processor():
    """Test LogProcessor functionality."""
    console.print("\n[bold cyan]═══ Testing LogProcessor ═══[/bold cyan]\n")
    
    # Initialize
    console.print("[yellow]→ Initializing LogProcessor...[/yellow]")
    processor = LogProcessor(SAMPLE_LOG)
    console.print(f"[green]✓[/green] Initialized LogProcessor for {SAMPLE_LOG}")
    
    # Read all logs
    console.print("[yellow]→ Reading all logs...[/yellow]")
    logs = processor.read_all_logs()
    console.print(f"[green]✓[/green] Loaded {len(logs)} log entries")
    
    # Get statistics
    stats = processor.get_statistics(logs)
    console.print(f"\n[yellow]Log Statistics:[/yellow]")
    console.print(f"  Total entries: {stats['total_entries']}")
    console.print(f"  Columns: {', '.join(stats['columns'])}")
    console.print(f"  Memory usage: {stats['memory_usage_mb']:.2f} MB")
    
    if "severity_counts" in stats:
        console.print(f"\n[yellow]Severity Distribution:[/yellow]")
        for severity, count in stats["severity_counts"].items():
            console.print(f"  {severity}: {count}")
    
    # Filter by entity
    console.print(f"\n[yellow]Testing Entity Filter (CM12345):[/yellow]")
    filtered = processor.filter_by_entity(logs, "entity_id", "CM12345")
    console.print(f"  Found {len(filtered)} entries for CM12345")
    
    # Filter by severity
    console.print(f"\n[yellow]Testing Severity Filter (ERROR+):[/yellow]")
    errors = processor.filter_by_severity(logs, min_severity="ERROR")
    console.print(f"  Found {len(errors)} error entries")
    
    # Search text
    console.print(f"\n[yellow]Testing Text Search ('network'):[/yellow]")
    network_logs = processor.search_text(logs, "network")
    console.print(f"  Found {len(network_logs)} entries containing 'network'")
    
    # Extract entities
    console.print(f"\n[yellow]Testing Entity Extraction (CM):[/yellow]")
    console.print("[yellow]→ Extracting CM entities...[/yellow]")
    cm_entities = processor.extract_entities(logs, "cm")
    console.print(f"[green]✓[/green] Extracted {len(cm_entities)} unique CM entities:")
    for entity, indices in list(cm_entities.items())[:5]:
        console.print(f"    {entity}: {len(indices)} occurrences")
    
    return logs


def test_chunker(logs):
    """Test LogChunker functionality."""
    console.print("\n[bold cyan]═══ Testing LogChunker ═══[/bold cyan]\n")
    
    # Initialize
    console.print("[yellow]→ Initializing LogChunker...[/yellow]")
    chunker = LogChunker()
    console.print(f"[green]✓[/green] Initialized LogChunker (max_tokens={chunker.max_tokens})")
    
    # Size-based chunking
    console.print(f"\n[yellow]Testing Size-Based Chunking:[/yellow]")
    console.print("[yellow]→ Creating size-based chunks (max_tokens=1000)...[/yellow]")
    size_chunks = chunker.chunk_by_size(logs, max_tokens=1000)
    console.print(f"[green]✓[/green] Created {len(size_chunks)} chunks")
    
    # Display chunk info
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Chunk ID", style="yellow")
    table.add_column("Entries", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Range")
    
    for chunk in size_chunks[:5]:  # Show first 5
        table.add_row(
            str(chunk.chunk_id),
            str(len(chunk)),
            str(chunk.token_estimate),
            f"{chunk.start_index}-{chunk.end_index}"
        )
    
    console.print(table)
    
    # Entity-context chunking
    console.print(f"\n[yellow]Testing Entity-Context Chunking:[/yellow]")
    console.print("[yellow]→ Getting CM12345 indices...[/yellow]")
    cm_indices = logs[logs["entity_id"] == "CM12345"].index.tolist()
    console.print(f"[yellow]→ Found {len(cm_indices)} CM12345 occurrences, creating entity chunks...[/yellow]")
    entity_chunks = chunker.chunk_by_entity_context(
        logs,
        entity_indices=cm_indices,
        entity_name="CM12345",
        context_lines=5
    )
    console.print(f"[green]✓[/green] Created {len(entity_chunks)} entity-focused chunks for CM12345")
    
    # Time-window chunking
    console.print(f"\n[yellow]Testing Time-Window Chunking:[/yellow]")
    console.print("[yellow]→ Creating time-window chunks...[/yellow]")
    time_chunks = chunker.chunk_by_time_window(
        logs,
        timestamp_column="timestamp",
        window_minutes=5
    )
    console.print(f"[green]✓[/green] Created {len(time_chunks)} time-window chunks (5 min windows)")
    
    # Get statistics
    stats = chunker.get_chunk_statistics(size_chunks)
    console.print(f"\n[yellow]Chunk Statistics:[/yellow]")
    console.print(f"  Total chunks: {stats['total_chunks']}")
    console.print(f"  Avg tokens/chunk: {stats['avg_tokens_per_chunk']:.1f}")
    console.print(f"  Avg entries/chunk: {stats['avg_entries_per_chunk']:.1f}")
    
    return size_chunks


def test_entity_manager(logs):
    """Test EntityManager functionality."""
    console.print("\n[bold cyan]═══ Testing EntityManager ═══[/bold cyan]\n")
    
    # Initialize
    console.print("[yellow]→ Initializing EntityManager...[/yellow]")
    manager = EntityManager()
    console.print(f"[green]✓[/green] Initialized EntityManager")
    
    # Normalize entity terms
    console.print(f"\n[yellow]Testing Entity Normalization:[/yellow]")
    test_terms = ["cable modem", "CM", "modem", "MdId"]
    for term in test_terms:
        console.print(f"[yellow]→ Normalizing '{term}'...[/yellow]")
        entity_type, normalized = manager.normalize_entity(term)
        console.print(f"  '{term}' → type: {entity_type}")
    
    # Extract all entities
    console.print(f"\n[yellow]Testing Entity Extraction:[/yellow]")
    console.print(f"[yellow]→ Extracting entities (cm, md_id) from {len(logs)} logs...[/yellow]")
    entities = manager.extract_all_entities_from_logs(
        logs,
        entity_types=["cm", "md_id"]
    )
    console.print(f"[green]✓[/green] Extracted {len(entities)} unique entities")
    
    # Get entity summary
    summary = manager.get_entity_summary()
    console.print(f"\n[yellow]Entity Summary:[/yellow]")
    console.print(f"  Total entities: {summary['total_entities']}")
    console.print(f"  Total occurrences: {summary['total_occurrences']}")
    console.print(f"  By type:")
    for entity_type, count in summary.get("by_type", {}).items():
        console.print(f"    {entity_type}: {count}")
    
    # Get top entities
    console.print(f"\n[yellow]Top Entities by Occurrence:[/yellow]")
    top_entities = manager.get_top_entities(limit=5)
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Entity Type", style="yellow")
    table.add_column("Entity Value", style="green")
    table.add_column("Occurrences", justify="right")
    
    for entity in top_entities:
        table.add_row(
            entity.entity_type,
            entity.entity_value,
            str(len(entity.occurrences))
        )
    
    console.print(table)
    
    # Find specific entity
    console.print(f"\n[yellow]Testing Specific Entity Search (CM12345):[/yellow]")
    console.print("[yellow]→ Searching for CM12345 in logs...[/yellow]")
    cm_entity = manager.find_entity_in_logs(logs, "CM12345")
    console.print(f"[green]✓[/green] Found CM12345 in {len(cm_entity.occurrences)} locations")
    console.print(f"  Indices: {cm_entity.occurrences[:10]}...")  # Show first 10
    
    # Test entity queue
    console.print(f"\n[yellow]Testing Entity Queue:[/yellow]")
    console.print("[yellow]→ Building entity queue...[/yellow]")
    initial_entities = [cm_entity]
    queue = manager.build_entity_queue(initial_entities, max_depth=3)
    console.print(f"[green]✓[/green] Built queue with {len(initial_entities)} initial entities")
    
    queue_stats = queue.get_statistics()
    console.print(f"  Queue stats: {queue_stats}")
    
    return manager


def test_integration():
    """Test integration of all components."""
    console.print("\n[bold cyan]═══ Testing Component Integration ═══[/bold cyan]\n")
    
    # Load logs
    console.print("[yellow]→ Loading logs...[/yellow]")
    processor = LogProcessor(SAMPLE_LOG)
    logs = processor.read_all_logs()
    console.print(f"[green]✓[/green] Loaded {len(logs)} log entries")
    
    # Extract entities
    console.print("[yellow]→ Extracting entities...[/yellow]")
    manager = EntityManager()
    entities = manager.extract_all_entities_from_logs(logs, entity_types=["cm"])
    console.print(f"[green]✓[/green] Extracted {len(entities)} entities")
    
    # Create entity-focused chunks
    console.print("[yellow]→ Initializing chunker...[/yellow]")
    chunker = LogChunker()
    
    # Build entity indices dict
    console.print("[yellow]→ Building entity indices dict...[/yellow]")
    entity_indices = {}
    for (entity_type, entity_value), entity in entities.items():
        entity_indices[entity_value] = entity.occurrences
    console.print(f"[green]✓[/green] Built indices for {len(entity_indices)} entities")
    
    # Smart chunking
    console.print(f"[yellow]→ Creating smart chunks with entity priority...[/yellow]")
    chunks = chunker.smart_chunk(
        logs,
        entity_indices=entity_indices,
        prioritize_entities=True
    )
    
    console.print(f"[green]✓[/green] Created {len(chunks)} smart chunks")
    
    # Show chunk distribution
    entity_chunks = sum(1 for c in chunks if c.focus_entity)
    console.print(f"  Entity-focused chunks: {entity_chunks}")
    console.print(f"  General chunks: {len(chunks) - entity_chunks}")
    
    # Show sample chunk
    if chunks:
        sample_chunk = chunks[0]
        console.print(f"\n[yellow]Sample Chunk (Chunk {sample_chunk.chunk_id}):[/yellow]")
        console.print(f"  Entries: {len(sample_chunk)}")
        console.print(f"  Tokens: ~{sample_chunk.token_estimate}")
        console.print(f"  Focus entity: {sample_chunk.focus_entity or 'None'}")
        console.print(f"  Range: {sample_chunk.start_index}-{sample_chunk.end_index}")


def main():
    """Run all manual tests."""
    console.print(Panel.fit(
        "[bold white]Phase 2: Log Processing Engine[/bold white]\n"
        "[cyan]Manual Testing Suite[/cyan]",
        border_style="blue"
    ))
    
    try:
        # Test individual components
        logs = test_log_processor()
        chunks = test_chunker(logs)
        manager = test_entity_manager(logs)
        
        # Test integration
        test_integration()
        
        console.print("\n[bold green]═══ All Manual Tests Completed Successfully! ═══[/bold green]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]Error during testing:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

