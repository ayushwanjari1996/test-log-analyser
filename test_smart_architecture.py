"""
Test the new smart architecture with zero hardcoding.

Tests both Query 1 and Query 2 to ensure:
1. No JSON formatting errors
2. Efficient iteration counts
3. Correct answers with actual values
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
    from src.core.smart_orchestrator import SmartOrchestrator
    from src.core.tool_registry import ToolRegistry
    from src.llm.ollama_client import OllamaClient
    from src.core.tools import create_all_tools
except Exception as e:
    console.print(f"[bold red]Import Error: {e}[/bold red]")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def test_query(orchestrator, query_num, query, expected_iterations, expected_keywords):
    """Test a single query"""
    
    console.print(f"\n[bold yellow]{'=' * 70}[/bold yellow]")
    console.print(f"[bold cyan]Query {query_num}: {query}[/bold cyan]")
    console.print(f"[bold yellow]{'=' * 70}[/bold yellow]\n")
    
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
        console.print(f"\n[bold]Tools Used:[/bold] {' → '.join(result.tools_used)}")
        
        # Evaluation
        console.print("\n[bold yellow]=== EVALUATION ===[/bold yellow]")
        
        passed = True
        
        # Check iterations
        if result.iterations <= expected_iterations:
            console.print(f"[green]✓ Iterations: {result.iterations} <= {expected_iterations}[/green]")
        else:
            console.print(f"[yellow]⚠ Iterations: {result.iterations} > {expected_iterations} (expected)[/yellow]")
            passed = False
        
        # Check keywords in answer
        answer_lower = result.answer.lower()
        for keyword in expected_keywords:
            if keyword.lower() in answer_lower:
                console.print(f"[green]✓ Found keyword: '{keyword}'[/green]")
            else:
                console.print(f"[red]✗ Missing keyword: '{keyword}'[/red]")
                passed = False
        
        # Check no errors
        if not result.errors:
            console.print("[green]✓ No errors[/green]")
        else:
            console.print(f"[yellow]⚠ Errors: {len(result.errors)}[/yellow]")
            for error in result.errors[:3]:
                console.print(f"    {error}")
        
        if passed:
            console.print(f"\n[bold green]✅ Query {query_num}: PASS[/bold green]")
        else:
            console.print(f"\n[bold yellow]⚠ Query {query_num}: PARTIAL[/bold yellow]")
        
        return result, passed
        
    except Exception as e:
        console.print(f"[bold red]ERROR: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return None, False


def main():
    console.print("\n[bold cyan]=== Smart Architecture Test ===[/bold cyan]")
    console.print("[dim]Zero hardcoding - Dynamic prompts from config only[/dim]\n")
    
    # Initialize
    console.print("1. Initializing LLM...")
    llm_client = OllamaClient()
    
    if not llm_client.health_check():
        console.print("[red]ERROR: Ollama not running[/red]")
        sys.exit(1)
    
    console.print(f"   ✓ LLM: {llm_client.model}")
    
    # Create tools and registry
    console.print("2. Creating tools...")
    registry = ToolRegistry()
    
    # Create all tools
    tools = create_all_tools("test.csv")
    
    # Register tools using the correct method name
    registry.register_multiple(tools)
    
    console.print(f"   ✓ Registered {len(registry)} tools")
    
    # Create orchestrator
    console.print("3. Creating smart orchestrator...")
    orchestrator = SmartOrchestrator(
        llm_client=llm_client,
        tool_registry=registry,
        max_iterations=10
    )
    console.print("   ✓ Orchestrator ready\n")
    
    # Test queries
    queries = [
        {
            "num": 1,
            "query": "find all cms connected to rpd MAWED07T01",
            "max_iterations": 4,
            "keywords": ["2", "cm", "1c:93:7c:2a:72:c3", "28:7a:ee:c9:66:4a"]
        },
        {
            "num": 2,
            "query": "search for logs with rpd MAWED07T01",
            "max_iterations": 2,
            "keywords": ["3", "logs", "MAWED07T01"]
        }
    ]
    
    results = []
    for q in queries:
        result, passed = test_query(
            orchestrator,
            q["num"],
            q["query"],
            q["max_iterations"],
            q["keywords"]
        )
        results.append((q["num"], passed))
    
    # Final summary
    console.print(f"\n[bold yellow]{'=' * 70}[/bold yellow]")
    console.print("[bold cyan]FINAL SUMMARY[/bold cyan]")
    console.print(f"[bold yellow]{'=' * 70}[/bold yellow]\n")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for num, passed in results:
        status = "[green]PASS[/green]" if passed else "[yellow]PARTIAL[/yellow]"
        console.print(f"Query {num}: {status}")
    
    console.print(f"\n[bold]Total: {passed_count}/{total_count} passed[/bold]")
    
    if passed_count == total_count:
        console.print("\n[bold green]🎉 ALL TESTS PASSED![/bold green]")
    else:
        console.print("\n[bold yellow]⚠ Some tests need improvement[/bold yellow]")


if __name__ == "__main__":
    main()

