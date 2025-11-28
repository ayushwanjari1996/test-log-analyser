#!/usr/bin/env python
"""Interactive CLI for testing Phase 4 LogAnalyzer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.analyzer import LogAnalyzer
from rich.console import Console
from rich.panel import Panel
from rich import print_json

console = Console()

console.print(Panel.fit(
    "[bold white]Phase 4: Interactive Log Analyzer[/bold white]\n"
    "[cyan]Ask questions in natural language[/cyan]",
    border_style="blue"
))

# Initialize analyzer
console.print("\n[yellow]→ Initializing LogAnalyzer...[/yellow]")
analyzer = LogAnalyzer("test.csv", use_llm_parsing=True)
console.print("[green]✓[/green] LogAnalyzer ready!\n")

console.print("[yellow]Example queries:[/yellow]")
console.print("  - find cm CM12345")
console.print("  - find all cms")
console.print("  - find rpdname for cm CM12345")
console.print("  - why did cm CM12345 fail")
console.print("  - trace cm CM12345")
console.print("\n[dim]Type 'quit' or 'exit' to stop[/dim]\n")

while True:
    try:
        query = console.input("[bold cyan]❯[/bold cyan] ")
        
        if query.lower() in ["quit", "exit", "q"]:
            console.print("[yellow]Goodbye![/yellow]")
            break
        
        if not query.strip():
            continue
        
        console.print(f"\n[yellow]Processing:[/yellow] {query}")
        result = analyzer.analyze_query(query)
        
        console.print("\n[bold cyan]Result:[/bold cyan]")
        print_json(data=result)
        console.print()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        break
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback
        traceback.print_exc()

