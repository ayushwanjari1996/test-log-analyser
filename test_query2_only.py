"""
Test Query 2 specifically - "search for logs with rpd MAWED07T01"

Expected behavior:
- Iteration 1: search_logs → Found 3 logs
- Iteration 2: DONE (user asked to search, we searched, that's the answer)

Should NOT:
- Try to extract entities
- Call fuzzy_search with wrong parameters
- Keep iterating after finding logs
"""

import sys
import logging
from rich.console import Console
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

logger = logging.getLogger(__name__)
console = Console()

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


def test_query2():
    """Test Query 2: search for logs"""
    
    console.print("\n[bold cyan]=== Query 2 Test ===[/bold cyan]\n")
    
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
    query = "search for logs with rpd MAWED07T01"
    
    console.print(f"\n[bold yellow]Query:[/bold yellow] {query}\n")
    console.print("[dim]Expected: search_logs → DONE in 1-2 iterations[/dim]\n")
    console.print("[dim]Should NOT extract entities or keep searching[/dim]\n")
    
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
                if step.get('parameters'):
                    console.print(f"  Parameters: {step['parameters']}")
            if step.get('done'):
                console.print(f"  [green]DONE[/green]")
        
        # Evaluation
        console.print("\n[bold yellow]=== EVALUATION ===[/bold yellow]")
        if result.iterations <= 2 and result.success and "3 logs" in result.answer.lower():
            console.print("[bold green]✓ PASS: Simple search completed efficiently[/bold green]")
        elif result.success and "3 logs" in result.answer.lower():
            console.print(f"[yellow]⚠ PARTIAL: Found answer but took {result.iterations} iterations (expected 1-2)[/yellow]")
        else:
            console.print("[red]✗ FAIL: Did not answer correctly[/red]")
        
        # Check for issues
        if "extract_entities" in result.tools_used:
            console.print("[yellow]⚠ NOTE: Called extract_entities (not needed for simple search)[/yellow]")
        if result.iterations > 3:
            console.print(f"[yellow]⚠ NOTE: Took {result.iterations} iterations (expected 1-2)[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]ERROR: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_query2()

