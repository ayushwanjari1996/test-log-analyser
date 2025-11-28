#!/usr/bin/env python
"""Test Phase 4 LogAnalyzer with all query types."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.analyzer import LogAnalyzer
from rich.console import Console
from rich.panel import Panel
from rich import print_json
import json

console = Console()

console.print(Panel.fit(
    "[bold white]Phase 4: LogAnalyzer Test[/bold white]\n"
    "[cyan]Testing all query types with real logs[/cyan]",
    border_style="blue"
))

# Initialize analyzer
console.print("\n[yellow]→ Initializing LogAnalyzer...[/yellow]")
analyzer = LogAnalyzer("tests/sample_logs/system.csv", use_llm_parsing=True)
console.print("[green]✓[/green] LogAnalyzer initialized\n")

# Test queries
test_queries = [
    ("Specific Value", "find cm CM12345"),
    ("Aggregation", "find all cms"),
    ("Aggregation with Filter", "find all cms with errors"),
    ("Relationship (Simple)", "find rpdname connected to cm CM12345"),
    ("Relationship (May Need Iteration)", "find mdid for cm CM12345"),
    ("Analysis", "why did cm CM12345 fail"),
    ("Trace", "trace cm CM12345"),
]

for test_name, query in test_queries:
    console.print(f"\n[bold cyan]═══ Test: {test_name} ═══[/bold cyan]")
    console.print(f"[yellow]Query:[/yellow] {query}\n")
    
    try:
        result = analyzer.analyze_query(query)
        
        # Display key results
        console.print(f"[green]✓ Success:[/green] {result.get('success', False)}")
        console.print(f"[yellow]Duration:[/yellow] {result.get('duration_seconds', 0):.2f}s")
        console.print(f"[yellow]Query Type:[/yellow] {result.get('query_type', 'unknown')}")
        
        # Type-specific output
        if result.get("query_type") == "specific_value":
            console.print(f"[cyan]Occurrences:[/cyan] {result.get('total_occurrences', 0)}")
            related = result.get('related_entities', {})
            if related:
                console.print(f"[cyan]Related Entities:[/cyan] {', '.join(related.keys())}")
        
        elif result.get("query_type") == "aggregation":
            console.print(f"[cyan]Total Found:[/cyan] {result.get('total_found', 0)}")
            entities = result.get('entities', [])
            if entities:
                console.print(f"[cyan]Top 3:[/cyan] {[e['value'] for e in entities[:3]]}")
        
        elif result.get("query_type") == "relationship":
            console.print(f"[cyan]Found:[/cyan] {result.get('found', False)}")
            if result.get('found'):
                console.print(f"[cyan]Target Values:[/cyan] {result.get('target', {}).get('values', [])}")
                console.print(f"[cyan]Iterations:[/cyan] {result.get('iterations', 0)}")
                console.print(f"[cyan]Path:[/cyan] {' → '.join(result.get('search_path', []))}")
                console.print(f"[cyan]Confidence:[/cyan] {result.get('confidence', 0):.2f}")
        
        elif result.get("query_type") == "analysis":
            obs = result.get('observations', [])
            pat = result.get('patterns', [])
            console.print(f"[cyan]Observations:[/cyan] {len(obs)}")
            console.print(f"[cyan]Patterns:[/cyan] {len(pat)}")
            if obs:
                console.print(f"  - {obs[0][:80]}...")
        
        elif result.get("query_type") == "trace":
            events = result.get('total_events', 0)
            console.print(f"[cyan]Timeline Events:[/cyan] {events}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        import traceback
        traceback.print_exc()

console.print("\n\n[bold cyan]═══ Detailed Example ═══[/bold cyan]")
console.print("\n[yellow]Testing relationship search with potential iteration:[/yellow]")
console.print("[yellow]Query:[/yellow] 'find mdid for cm CM12345'\n")

result = analyzer.analyze_query("find mdid for cm CM12345")
print_json(data=result)

console.print("\n[bold green]✓ Phase 4 LogAnalyzer Test Complete![/bold green]")
console.print("\n[yellow]Components tested:[/yellow]")
console.print("  ✓ LLM Query Parsing")
console.print("  ✓ Specific Value Search")
console.print("  ✓ Aggregation Search")
console.print("  ✓ Relationship Search (with iterative exploration)")
console.print("  ✓ Root Cause Analysis (LLM)")
console.print("  ✓ Flow Trace")

