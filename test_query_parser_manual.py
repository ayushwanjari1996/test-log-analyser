#!/usr/bin/env python
"""Quick test script for QueryParser."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.query_parser import QueryParser
from rich.console import Console
from rich.table import Table

console = Console()

# Test queries
test_queries = [
    "find cm CM12345",
    "find cm x",
    "find all cms",
    "find mdid for cm x",
    "find all cms with errors",
    "why did cm x fail",
    "trace cm x",
    "show rpdname connected to cm CM12345",
    "find ip address for modem x",
    "list all modems with timeouts"
]

parser = QueryParser()

console.print("\n[bold cyan]Testing QueryParser[/bold cyan]\n")

table = Table(show_header=True, header_style="bold magenta")
table.add_column("Query", style="cyan", width=35)
table.add_column("Type", style="yellow", width=15)
table.add_column("Primary Entity", style="green", width=20)
table.add_column("Secondary Entity", style="blue", width=20)

for query in test_queries:
    parsed = parser.parse_query(query)
    
    primary = f"{parsed['primary_entity']['type']}:{parsed['primary_entity']['value']}"
    secondary = "None"
    if parsed["secondary_entity"]:
        secondary = f"{parsed['secondary_entity']['type']}:{parsed['secondary_entity']['value']}"
    
    table.add_row(
        query,
        parsed["query_type"],
        primary,
        secondary
    )

console.print(table)

console.print("\n[bold green]✓ QueryParser working![/bold green]")
console.print("\nTest specific query:")
result = parser.parse_query("find mdid for cm x")
console.print(f"  Query type: {result['query_type']}")
console.print(f"  Target (what we want): {result['primary_entity']['type']}")
console.print(f"  Source (what we search): {result['secondary_entity']['type']}:{result['secondary_entity']['value']}")
console.print(f"  Strategy: {parser.get_search_strategy(result)}")

