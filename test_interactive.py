#!/usr/bin/env python
"""Interactive CLI for testing Phase 4 LogAnalyzer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging FIRST with emoji=False before any imports
import logging
from rich.console import Console
from rich.logging import RichHandler

# Reconfigure root logger to use emoji=False
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(
        console=Console(stderr=True, emoji=False),
        show_time=True,
        show_path=False,
        markup=True
    )],
    force=True  # Force reconfiguration
)

# Now import our modules (they will use the reconfigured logger)
from src.core.analyzer import LogAnalyzer
from src.core.workflow_orchestrator import WorkflowOrchestrator
from src.core.llm_query_parser import LLMQueryParser
from src.core.log_processor import LogProcessor
from src.core.entity_manager import EntityManager
from src.llm.ollama_client import OllamaClient
from rich.panel import Panel
from rich import print_json
from rich.table import Table

# Disable emoji parsing to prevent :ab: in MAC addresses from being converted to emojis
console = Console(emoji=False)

console.print(Panel.fit(
    "[bold white]Phase 4: Interactive Log Analyzer[/bold white]\n"
    "[cyan]Ask questions in natural language[/cyan]\n"
    "[dim yellow]Note: If you see emojis in logs (e.g., 🆎), restart Python to reload logger[/dim yellow]",
    border_style="blue"
))

# Ask for mode
console.print("\n[bold cyan]Select Mode:[/bold cyan]")
console.print("  1. [green]Prod Mode[/green] - Clean output with reasoning (default)")
console.print("  2. [yellow]Verbose Mode[/yellow] - Full debug logs")
console.print("  3. [magenta]Intelligent Mode[/magenta] - New self-orchestrating workflow")
mode_input = console.input("\n[cyan]Enter mode (1, 2, or 3):[/cyan] ").strip()

if mode_input == "2":
    mode = "verbose"
    logging.getLogger().setLevel(logging.DEBUG)
    console.print("[yellow]✓[/yellow] Verbose mode enabled - showing all logs\n")
elif mode_input == "3":
    mode = "intelligent"
    logging.getLogger().setLevel(logging.INFO)  # Show workflow decisions
    console.print("[magenta]✓[/magenta] Intelligent mode enabled - LLM-orchestrated workflow\n")
else:
    mode = "prod"
    logging.getLogger().setLevel(logging.WARNING)  # Hide INFO/DEBUG
    console.print("[green]✓[/green] Prod mode enabled - clean output with reasoning\n")

# Initialize analyzer
if mode == "verbose":
    console.print("\n[yellow]→ Initializing LogAnalyzer...[/yellow]")

if mode == "intelligent":
    console.print("\n[magenta]→ Initializing Intelligent Workflow Orchestrator...[/magenta]")
    # Initialize components for intelligent mode
    processor = LogProcessor("test.csv")
    entity_manager = EntityManager()
    llm_client = OllamaClient()
    query_parser = LLMQueryParser(llm_client)
    orchestrator = WorkflowOrchestrator(processor, entity_manager, llm_client)
    console.print("[green]✓[/green] Orchestrator ready!\n")
    analyzer = None  # Not using old analyzer
else:
    analyzer = LogAnalyzer("test.csv", use_llm_parsing=True)
    query_parser = None
    orchestrator = None
    if mode == "verbose":
        console.print("[green]✓[/green] LogAnalyzer ready!\n")
    else:
        console.print("[dim]LogAnalyzer ready![/dim]\n")

console.print("[yellow]Example queries:[/yellow]")
console.print("  - find cm CM12345")
console.print("  - find all cms")
console.print("  - find rpdname for cm 10:e1:77:08:63:8a")
console.print("  - why did cm CM12345 fail")
console.print("  - trace cm CM12345")
console.print("\n[dim]Type 'quit', 'exit', or 'mode' to change mode[/dim]\n")

def print_prod_mode_result(result):
    """Print clean, user-friendly result with reasoning."""
    console.print("\n" + "="*60)
    
    # Header
    query_type = result.get("query_type", "unknown")
    success = result.get("success", False)
    
    if success:
        console.print(f"[bold green]✓ Query Successful[/bold green] ({query_type})")
    else:
        console.print(f"[bold red]✗ Query Failed[/bold red] ({query_type})")
    
    # Show LLM reasoning if available
    parsed = result.get("parsed_query", {})
    if parsed.get("llm_parsed"):
        console.print(f"\n[cyan]Intent:[/cyan] {parsed.get('intent', 'N/A')}")
        console.print(f"[cyan]Confidence:[/cyan] {parsed.get('confidence', 0):.0%}")
        
        # Show reasoning for primary entity
        primary = parsed.get("primary_entity", {})
        if primary.get("reasoning"):
            console.print(f"[cyan]Primary Entity Reasoning:[/cyan] {primary['reasoning']}")
        
        # Show reasoning for secondary entity
        secondary = parsed.get("secondary_entity")
        if secondary and secondary.get("reasoning"):
            console.print(f"[cyan]Secondary Entity Reasoning:[/cyan] {secondary['reasoning']}")
    
    # Result details based on type
    if query_type == "relationship":
        console.print(f"\n[bold]Search Process:[/bold]")
        iterations = result.get("iterations", 0)
        found = result.get("found", False)
        
        console.print(f"  • Iterations: {iterations}")
        
        if found:
            path = result.get("search_path", [])
            console.print(f"  • Path taken:")
            for i, step in enumerate(path):
                if i == 0:
                    console.print(f"    [yellow]Start:[/yellow] {step}")
                elif i == len(path) - 1:
                    console.print(f"    [green]Found:[/green] {step}")
                else:
                    console.print(f"    [cyan]Bridge:[/cyan] {step}")
            
            # Show bridge reasoning
            bridges = result.get("bridge_entities", [])
            if bridges:
                console.print(f"\n[bold]Bridge Entities Used:[/bold]")
                for bridge in bridges:
                    console.print(f"  • {bridge['type']}:{bridge['value']} (score: {bridge['score']})")
            
            target = result.get("target", {})
            console.print(f"\n[bold green]Answer:[/bold green] {', '.join(target.get('values', []))}")
            console.print(f"[dim]Confidence: {result.get('confidence', 0):.0%}[/dim]")
        else:
            console.print(f"  • [yellow]Could not find target entity after {iterations} iterations[/yellow]")
            console.print(f"  • Searched {result.get('logs_searched', 0)} log entries")
    
    elif query_type == "specific_value":
        occurrences = result.get("total_occurrences", 0)
        console.print(f"\n[bold]Found:[/bold] {occurrences} occurrences")
        
        related = result.get("related_entities", {})
        if related:
            console.print(f"\n[bold]Related Entities Found:[/bold]")
            for etype, values in related.items():
                console.print(f"  • {etype}: {len(values)} unique ({', '.join(values[:3])}{'...' if len(values) > 3 else ''})")
    
    elif query_type == "aggregation":
        total = result.get("total_found", 0)
        console.print(f"\n[bold]Total Found:[/bold] {total} unique entities")
        
        entities = result.get("entities", [])
        if entities:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Value", style="yellow")
            table.add_column("Occurrences", justify="right", style="green")
            
            for entity in entities[:10]:  # Show top 10
                table.add_row(entity['value'], str(entity['occurrences']))
            
            console.print(table)
            
            if len(entities) > 10:
                console.print(f"[dim]... and {len(entities) - 10} more[/dim]")
    
    elif query_type == "analysis":
        observations = result.get("observations", [])
        patterns = result.get("patterns", [])
        
        console.print(f"\n[bold]Analysis Results:[/bold]")
        console.print(f"  • Chunks analyzed: {result.get('chunks_analyzed', 0)}")
        console.print(f"  • Total logs: {result.get('total_logs', 0)}")
        
        if observations:
            console.print(f"\n[bold cyan]Key Observations:[/bold cyan]")
            for i, obs in enumerate(observations[:5], 1):
                console.print(f"  {i}. {obs}")
        else:
            console.print(f"\n[dim]No specific observations extracted by LLM[/dim]")
        
        if patterns:
            console.print(f"\n[bold cyan]Patterns Detected:[/bold cyan]")
            for i, pat in enumerate(patterns[:5], 1):
                console.print(f"  {i}. {pat}")
        else:
            console.print(f"[dim]No patterns detected[/dim]")
        
        # Show summary if no observations
        if not observations and not patterns and success:
            console.print(f"\n[yellow]ℹ️  Analysis completed but no specific issues found.[/yellow]")
            console.print(f"[dim]The entity appears in {result.get('total_logs', 0)} logs without obvious errors.[/dim]")
    
    elif query_type == "trace":
        events = result.get("total_events", 0)
        console.print(f"\n[bold]Timeline:[/bold] {events} events")
        
        timeline = result.get("timeline", [])
        if timeline:
            console.print(f"\n[cyan]Event Sequence:[/cyan]")
            for i, event in enumerate(timeline[:10], 1):
                ts = event.get('timestamp', 'N/A')
                severity = event.get('severity', 'INFO')
                msg = event.get('message', '')[:60]
                console.print(f"  {i}. [{severity}] {ts} - {msg}...")
            
            if len(timeline) > 10:
                console.print(f"[dim]... and {len(timeline) - 10} more events[/dim]")
    
    # Duration
    duration = result.get("duration_seconds", 0)
    console.print(f"\n[dim]Completed in {duration:.2f}s[/dim]")
    console.print("="*60 + "\n")


def print_intelligent_mode_result(result):
    """Print intelligent workflow orchestrator result."""
    console.print("\n" + "="*70)
    
    # Header
    success = result.success
    if success:
        console.print(f"[bold green]✅ ANALYSIS COMPLETE[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️  ANALYSIS COMPLETED (LIMITED RESULTS)[/bold yellow]")
    
    # Execution summary
    console.print(f"\n[bold cyan]Workflow Summary:[/bold cyan]")
    console.print(f"  • Iterations: {result.iterations}")
    console.print(f"  • Logs analyzed: {result.logs_analyzed}")
    console.print(f"  • Methods used: {', '.join(result.methods_used)}")
    console.print(f"  • Confidence: {result.confidence:.0%}")
    
    # Show execution trace (LLM reasoning at each step)
    if result.execution_trace:
        console.print(f"\n[bold magenta]🧠 Decision Path:[/bold magenta]")
        for trace in result.execution_trace:
            iter_num = trace['iteration'] + 1
            method = trace['method']
            reasoning = trace['reasoning']
            logs = trace['logs_found']
            entities = trace['entities_found']
            errors = trace['errors_found']
            
            console.print(f"\n  [cyan]Step {iter_num}:[/cyan] {method}")
            console.print(f"    [dim]Reasoning:[/dim] {reasoning}")
            console.print(f"    [dim]Results:[/dim] {logs} logs, {entities} entities, {errors} errors")
    
    # Main answer
    console.print(f"\n[bold green]📊 Answer:[/bold green]")
    console.print(f"  {result.answer}")
    
    # Summary details
    summary = result.summary
    if summary:
        # Timeline
        if summary.get("timeline"):
            console.print(f"\n[bold cyan]⏱️  Timeline:[/bold cyan]")
            for event in summary["timeline"][:5]:
                time = event.get("time", event.get("timestamp", "??:??:??"))
                evt = event.get("event", event.get("description", ""))
                console.print(f"  • [{time}] {evt}")
            if len(summary["timeline"]) > 5:
                console.print(f"  [dim]... and {len(summary['timeline'])-5} more events[/dim]")
        
        # Causal chain
        if summary.get("causal_chain"):
            console.print(f"\n[bold yellow]🔗 Causal Chain:[/bold yellow]")
            for i, step in enumerate(summary["causal_chain"], 1):
                if isinstance(step, dict):
                    entity = step.get("entity", "")
                    event = step.get("event", "")
                    console.print(f"  {i}. {entity} → {event}")
                else:
                    console.print(f"  {i}. {step}")
        
        # Key findings
        if summary.get("key_findings"):
            console.print(f"\n[bold cyan]🔍 Key Findings:[/bold cyan]")
            for finding in summary["key_findings"][:5]:
                console.print(f"  • {finding}")
        
        # Observations
        if summary.get("observations"):
            console.print(f"\n[bold cyan]💡 Observations:[/bold cyan]")
            for obs in summary["observations"][:5]:
                console.print(f"  • {obs}")
        
        # Recommendations
        if summary.get("recommendations"):
            console.print(f"\n[bold green]✨ Recommendations:[/bold green]")
            for rec in summary["recommendations"][:3]:
                console.print(f"  • {rec}")
        
        # Status
        status = summary.get("status", "unknown")
        if status == "healthy":
            console.print(f"\n[bold green]Status:[/bold green] ✓ Healthy - No issues detected")
        elif status == "warning":
            console.print(f"\n[bold yellow]Status:[/bold yellow] ⚠ Warnings detected")
        elif status in ["error", "critical"]:
            console.print(f"\n[bold red]Status:[/bold red] ✗ Errors detected")
    
    # Entities found
    if result.entities_found:
        console.print(f"\n[bold cyan]🔗 Related Entities:[/bold cyan]")
        for etype, values in list(result.entities_found.items())[:3]:
            console.print(f"  • {etype}: {', '.join(values[:3])}{'...' if len(values) > 3 else ''}")
    
    console.print(f"\n[dim]Total execution time: {result.iterations} iterations[/dim]")
    console.print("="*70 + "\n")


while True:
    try:
        query = console.input("[bold cyan]❯[/bold cyan] ")
        
        if query.lower() in ["quit", "exit", "q"]:
            console.print("[yellow]Goodbye![/yellow]")
            break
        
        if query.lower() == "mode":
            console.print("\n[bold cyan]Switch Mode:[/bold cyan]")
            console.print("  1. [green]Prod Mode[/green] - Clean output")
            console.print("  2. [yellow]Verbose Mode[/yellow] - Full debug logs")
            console.print("  3. [magenta]Intelligent Mode[/magenta] - Self-orchestrating workflow")
            mode_input = console.input("[cyan]Enter mode (1, 2, or 3):[/cyan] ").strip()
            
            if mode_input == "2":
                mode = "verbose"
                logging.getLogger().setLevel(logging.DEBUG)
                console.print("[yellow]✓[/yellow] Switched to verbose mode\n")
            elif mode_input == "3":
                mode = "intelligent"
                logging.getLogger().setLevel(logging.INFO)
                console.print("[magenta]✓[/magenta] Switched to intelligent mode\n")
            else:
                mode = "prod"
                logging.getLogger().setLevel(logging.WARNING)
                console.print("[green]✓[/green] Switched to prod mode\n")
            continue
        
        if not query.strip():
            continue
        
        if mode == "verbose":
            console.print(f"\n[yellow]Processing:[/yellow] {query}")
        elif mode == "intelligent":
            console.print(f"\n[magenta]🧠 Analyzing:[/magenta] {query}")
        
        # Process query based on mode
        if mode == "intelligent":
            # Use new intelligent workflow orchestrator
            parsed_query = query_parser.parse_query(query)
            result = orchestrator.execute(query, parsed_query)
            print_intelligent_mode_result(result)
        else:
            # Use old analyzer
            result = analyzer.analyze_query(query)
            
            if mode == "prod":
                print_prod_mode_result(result)
            else:
                # Verbose mode - show full JSON
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

