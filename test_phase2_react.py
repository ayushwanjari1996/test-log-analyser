"""
Test script for Phase 2 - Real tools with test.csv

Tests the complete ReAct system with real log analysis tools:
- Search and filter tools
- Entity extraction tools  
- Smart search with normalization
- Real queries on actual log data
"""

import sys
import logging
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)
console = Console()

# Import components
try:
    from src.core.react_orchestrator import ReActOrchestrator
    from src.core.tool_registry import ToolRegistry
    from src.llm.ollama_client import OllamaClient
    from src.core.tools import create_all_tools
except (SyntaxError, ImportError) as e:
    console = Console()
    console.print(f"\n[bold red]FATAL: Syntax or Import Error![/bold red]")
    console.print(f"[red]{type(e).__name__}: {e}[/red]\n")
    traceback.print_exc()
    console.print("\n[yellow]Please fix the syntax errors before running tests.[/yellow]\n")
    sys.exit(1)


def display_result(result, query_num: int):
    """Display analysis result in a nice format"""
    
    console.print(f"\n[bold green]Query {query_num} Complete![/bold green]")
    
    # Answer panel
    console.print(Panel(
        result.answer,
        title="[bold cyan]Answer[/bold cyan]",
        border_style="cyan"
    ))
    
    # Metadata table
    table = Table(title="Execution Details", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Iterations", str(result.iterations))
    table.add_row("Confidence", f"{result.confidence:.2f}")
    table.add_row("Duration", f"{result.duration_seconds:.2f}s")
    table.add_row("Tools Used", " → ".join(result.tools_used) if result.tools_used else "None")
    table.add_row("Success", "YES" if result.success else "NO")
    
    console.print(table)
    
    # Reasoning trace
    if result.reasoning_trace:
        console.print("\n[bold cyan]Reasoning Trace:[/bold cyan]")
        for i, step in enumerate(result.reasoning_trace, 1):
            reasoning_preview = step['reasoning'][:120] + "..." if len(step['reasoning']) > 120 else step['reasoning']
            console.print(f"  {i}. {reasoning_preview}")
            if step['tool']:
                console.print(f"     > [dim]Called: {step['tool']}[/dim]")


def test_real_queries():
    """Test Phase 2 with real queries on test.csv"""
    
    console.print("\n[bold cyan]Phase 2 Test: Real Tools + Real Data[/bold cyan]\n")
    
    # Check if test.csv exists
    import os
    if not os.path.exists("test.csv"):
        console.print("[red]ERROR: test.csv not found. Please ensure it exists in the current directory.[/red]")
        sys.exit(1)
    
    console.print("[green]Found test.csv[/green]\n")
    
    # Initialize components
    console.print("1. Initializing LLM client...")
    llm_client = OllamaClient()
    
    # Check health
    if not llm_client.health_check():
        console.print("[red]ERROR: Ollama is not running. Please start Ollama first.[/red]")
        sys.exit(1)
    
    console.print(f"   [green]LLM ready: {llm_client.model}[/green]")
    
    # Create all real tools
    console.print("\n2. Creating real tools...")
    try:
        tools = create_all_tools(log_file_path="test.csv")
        console.print(f"   [green]Created {len(tools)} tools[/green]")
    except Exception as e:
        console.print(f"[red]ERROR: Failed to create tools: {e}[/red]")
        traceback.print_exc()
        sys.exit(1)
    
    # Register tools
    console.print("\n3. Registering tools...")
    try:
        registry = ToolRegistry()
        registry.register_multiple(tools)
        
        tool_names = registry.list_tools()
        console.print(f"   [green]Registered tools:[/green]")
        for tool_name in tool_names:
            console.print(f"      • {tool_name}")
    except Exception as e:
        console.print(f"[red]ERROR: Failed to register tools: {e}[/red]")
        traceback.print_exc()
        sys.exit(1)
    
    # Create orchestrator
    console.print("\n4. Creating ReAct orchestrator...")
    try:
        orchestrator = ReActOrchestrator(
            llm_client=llm_client,
            tool_registry=registry,
            max_iterations=10
        )
        console.print("   [green]Orchestrator ready[/green]\n")
    except Exception as e:
        console.print(f"[red]ERROR: Failed to create orchestrator: {e}[/red]")
        traceback.print_exc()
        sys.exit(1)
    
    # Test queries - based on the original issue
    test_queries = [
        # Query 1: The original problematic query
        "find all cms connected to rpd MAWED07T01",
        
        # Query 2: Simple search
        "search for logs with rpd MAWED07T01",
        
        # Query 3: Entity extraction
        "what cm mac addresses are in logs with rpd MAWED07T01",
        
        # Query 4: Error search with fallback
        "find errors for cm mac 28:7a:ee:c9:66:4a",
        
        # Query 5: Fuzzy search test
        "find logs with registration for cm mac 1c:93:7c:2a:72:c3",
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        console.print(f"\n[bold]{'='*70}[/bold]")
        console.print(f"[bold yellow]Query {i}/{len(test_queries)}: {query}[/bold yellow]")
        console.print(f"[bold]{'='*70}[/bold]\n")
        
        try:
            result = orchestrator.execute(query)
            display_result(result, i)
            results.append((query, result, None))
            
        except Exception as e:
            console.print(f"[red]ERROR: Query {i} failed: {e}[/red]")
            traceback.print_exc()
            results.append((query, None, str(e)))
    
    # Summary
    console.print(f"\n[bold]{'='*70}[/bold]")
    console.print("[bold cyan]Test Summary[/bold cyan]")
    console.print(f"[bold]{'='*70}[/bold]\n")
    
    successful = sum(1 for _, result, error in results if result and result.success)
    failed = len(results) - successful
    
    summary_table = Table(show_header=True)
    summary_table.add_column("Query", style="cyan", width=50)
    summary_table.add_column("Status", style="green")
    summary_table.add_column("Iterations", justify="right")
    
    for query, result, error in results:
        if result:
            status = "[green]Success[/green]" if result.success else "[yellow]Partial[/yellow]"
            iterations = str(result.iterations)
        else:
            status = "[red]Failed[/red]"
            iterations = "N/A"
        
        summary_table.add_row(
            query[:47] + "..." if len(query) > 50 else query,
            status,
            iterations
        )
    
    console.print(summary_table)
    
    console.print(f"\n[bold green]Successful:[/bold green] {successful}/{len(results)}")
    if failed > 0:
        console.print(f"[bold red]Failed:[/bold red] {failed}/{len(results)}")
    
    console.print(f"\n[bold green]Phase 2 testing complete![/bold green]\n")
    
    return results


if __name__ == "__main__":
    try:
        results = test_real_queries()
    except KeyboardInterrupt:
        console.print("\n[yellow]WARNING: Test interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]FATAL ERROR: {e}[/red]")
        traceback.print_exc()
        sys.exit(1)

