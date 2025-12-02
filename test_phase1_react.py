"""
Test script for Phase 1 - ReAct infrastructure.

Tests the basic ReAct loop with dummy tools to ensure:
- Tool registration works
- LLM can call tools
- State management works
- Conversation history is maintained
- Loop terminates correctly
"""

import sys
import logging
from rich.console import Console
from rich.logging import RichHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)
console = Console()

# Import Phase 1 components
from src.core.react_orchestrator import ReActOrchestrator, AnalysisResult
from src.core.tool_registry import ToolRegistry
from src.llm.ollama_client import OllamaClient
from src.core.tools.dummy_tool import EchoTool, CountTool


def test_basic_loop():
    """Test basic ReAct loop with dummy tools"""
    
    console.print("\n[bold cyan]🧪 Phase 1 Test: Basic ReAct Loop[/bold cyan]\n")
    
    # Initialize components
    console.print("1. Initializing LLM client...")
    llm_client = OllamaClient()
    
    # Check health
    if not llm_client.health_check():
        console.print("[red]❌ Ollama is not running. Please start Ollama first.[/red]")
        sys.exit(1)
    
    console.print(f"   ✓ LLM ready: {llm_client.model}")
    
    # Setup tool registry
    console.print("\n2. Setting up tools...")
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(CountTool())
    console.print(f"   ✓ Registered {len(registry)} tools: {registry.get_tool_names_summary()}")
    
    # Create orchestrator
    console.print("\n3. Creating ReAct orchestrator...")
    orchestrator = ReActOrchestrator(
        llm_client=llm_client,
        tool_registry=registry,
        max_iterations=5
    )
    console.print("   ✓ Orchestrator ready")
    
    # Test queries
    test_queries = [
        "echo back the message 'Hello Phase 1!'",
        "count from 1 to 10",
    ]
    
    for i, query in enumerate(test_queries, 1):
        console.print(f"\n[bold]{'='*70}[/bold]")
        console.print(f"[bold yellow]Test {i}: {query}[/bold yellow]")
        console.print(f"[bold]{'='*70}[/bold]\n")
        
        try:
            result = orchestrator.execute(query)
            
            # Display results
            console.print(f"\n[bold green]✅ Test {i} Complete![/bold green]")
            console.print(f"[bold]Answer:[/bold] {result.answer}")
            console.print(f"[bold]Confidence:[/bold] {result.confidence:.2f}")
            console.print(f"[bold]Iterations:[/bold] {result.iterations}")
            console.print(f"[bold]Tools Used:[/bold] {' → '.join(result.tools_used)}")
            console.print(f"[bold]Duration:[/bold] {result.duration_seconds:.2f}s")
            
            # Show reasoning trace
            if result.reasoning_trace:
                console.print(f"\n[bold cyan]🧠 Reasoning Trace:[/bold cyan]")
                for step in result.reasoning_trace:
                    console.print(f"  [Iteration {step['iteration']}] {step['reasoning'][:80]}...")
                    if step['tool']:
                        console.print(f"    → Called: {step['tool']}")
            
        except Exception as e:
            console.print(f"[red]❌ Test {i} failed: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    console.print(f"\n[bold green]✅ Phase 1 tests complete![/bold green]\n")


if __name__ == "__main__":
    test_basic_loop()

