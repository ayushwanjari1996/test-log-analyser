#!/usr/bin/env python
"""Test LLM-based query parsing."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.llm_query_parser import LLMQueryParser, HybridQueryParser
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import json

console = Console()

# Test queries - including complex/creative ones
test_queries = [
    "find cm CM12345",
    "find mdid for cm x",
    "show me all modems that had errors",
    "what caused modem x to fail",
    "trace the flow of cm x",
    "which rpdname is connected to modem x",
    "list all cable modems with timeouts in the last hour",
    "find the ip address for cm x",
    "show me everything related to modem x",
    "why are all modems failing"
]

console.print(Panel.fit(
    "[bold white]LLM Query Parser Test[/bold white]\n"
    "[cyan]Testing with Ollama LLM[/cyan]",
    border_style="blue"
))

# Initialize LLM parser
console.print("\n[yellow]→ Initializing LLM Query Parser...[/yellow]")
parser = LLMQueryParser()
console.print("[green]✓[/green] Initialized\n")

# Test each query
for i, query in enumerate(test_queries, 1):
    console.print(f"\n[bold cyan]═══ Test {i}: {query} ═══[/bold cyan]")
    
    try:
        parsed = parser.parse_query(query)
        
        # Display results
        console.print(f"[yellow]Query Type:[/yellow] {parsed['query_type']}")
        console.print(f"[yellow]Intent:[/yellow] {parsed['intent']}")
        console.print(f"[yellow]Confidence:[/yellow] {parsed['confidence']:.2f}")
        
        # Primary entity
        primary = parsed['primary_entity']
        console.print(f"\n[green]Target (what to find):[/green]")
        console.print(f"  Type: {primary['type']}")
        console.print(f"  Value: {primary.get('value', 'None (find all)')}")
        if primary.get('reasoning'):
            console.print(f"  Reasoning: {primary['reasoning']}")
        
        # Secondary entity
        if parsed['secondary_entity']:
            secondary = parsed['secondary_entity']
            console.print(f"\n[blue]Source (where to search):[/blue]")
            console.print(f"  Type: {secondary['type']}")
            console.print(f"  Value: {secondary.get('value', 'None')}")
            console.print(f"  Is Value: {secondary.get('is_value', True)}")
            if secondary.get('reasoning'):
                console.print(f"  Reasoning: {secondary['reasoning']}")
        
        # Filters
        if parsed['filter_conditions']:
            console.print(f"\n[magenta]Filters:[/magenta] {', '.join(parsed['filter_conditions'])}")
        
        console.print(f"\n[yellow]Strategy:[/yellow] {parsed['search_strategy']}")
        console.print(f"[yellow]Mode:[/yellow] {parsed['mode']}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        import traceback
        traceback.print_exc()

console.print("\n\n[bold cyan]═══ Detailed JSON Example ═══[/bold cyan]")
console.print("\nParsing: 'find mdid for cm x'\n")
result = parser.parse_query("find mdid for cm x")
console.print(json.dumps(result, indent=2))

console.print("\n[bold green]✓ LLM Query Parser Test Complete![/bold green]")
console.print("\n[yellow]Note:[/yellow] LLM parsing allows users to ask ANYTHING!")
console.print("The system will intelligently understand intent and extract entities.")

