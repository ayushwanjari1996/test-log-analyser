"""
Simple test script for debugging - tests ONE query at a time.

Usage: python test_single_query.py
"""

import sys
import logging
from rich.console import Console
from rich.logging import RichHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

logger = logging.getLogger(__name__)
console = Console()

# Import components with error handling
try:
    from src.core.react_orchestrator import ReActOrchestrator
    from src.core.tool_registry import ToolRegistry
    from src.llm.ollama_client import OllamaClient
    from src.core.tools import create_all_tools
except Exception as e:
    console.print(f"[bold red]Import Error: {e}[/bold red]")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_single():
    """Test a single query"""
    
    console.print("\n[bold cyan]=== Single Query Test ===[/bold cyan]\n")
    
    # Check file
    import os
    if not os.path.exists("test.csv"):
        console.print("[red]ERROR: test.csv not found[/red]")
        sys.exit(1)
    
    # Initialize
    console.print("1. Initializing...")
    llm_client = OllamaClient()
    
    if not llm_client.health_check():
        console.print("[red]ERROR: Ollama not running[/red]")
        sys.exit(1)
    
    console.print(f"   LLM: {llm_client.model}")
    
    # Create tools
    console.print("2. Creating tools...")
    tools = create_all_tools("test.csv")
    registry = ToolRegistry()
    registry.register_multiple(tools)
    console.print(f"   Registered: {len(registry)} tools")
    
    # Create orchestrator
    console.print("3. Creating orchestrator...")
    orchestrator = ReActOrchestrator(
        llm_client=llm_client,
        tool_registry=registry,
        max_iterations=10
    )
    
    # The test query
    query = "find all cms connected to rpd MAWED07T01"
    
    console.print(f"\n[bold yellow]Query:[/bold yellow] {query}\n")
    console.print("[dim]Expected: Should find 2 CM MACs in 3-4 iterations[/dim]\n")
    
    # Execute
    try:
        result = orchestrator.execute(query)
        
        # Display result
        console.print("\n[bold green]=== RESULT ===[/bold green]")
        console.print(f"[bold]Success:[/bold] {result.success}")
        console.print(f"[bold]Iterations:[/bold] {result.iterations}")
        console.print(f"[bold]Confidence:[/bold] {result.confidence:.2f}")
        console.print(f"[bold]Duration:[/bold] {result.duration_seconds:.2f}s")
        console.print(f"\n[bold cyan]Answer:[/bold cyan]")
        console.print(result.answer)
        
        # Show tool sequence
        console.print(f"\n[bold]Tools Used:[/bold] {' -> '.join(result.tools_used)}")
        
        # Show reasoning trace
        console.print("\n[bold cyan]Reasoning Trace:[/bold cyan]")
        for i, step in enumerate(result.reasoning_trace, 1):
            console.print(f"\n[bold]Iteration {i}:[/bold]")
            console.print(f"  Reasoning: {step['reasoning'][:150]}...")
            if step['tool']:
                console.print(f"  Tool: {step['tool']}")
            if step.get('done'):
                console.print(f"  [green]DONE - Provided answer[/green]")
        
        # Evaluation
        console.print("\n[bold yellow]=== EVALUATION ===[/bold yellow]")
        if result.iterations <= 4 and result.success and "1c:93:7c:2a:72:c3" in result.answer:
            console.print("[bold green]PASS: Found correct CMs in reasonable iterations[/bold green]")
        elif result.success and "1c:93:7c:2a:72:c3" in result.answer:
            console.print("[yellow]PARTIAL: Found correct answer but took too many iterations[/yellow]")
        else:
            console.print("[red]FAIL: Did not find correct answer[/red]")
        
    except Exception as e:
        console.print(f"[bold red]ERROR: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_single()

