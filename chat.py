#!/usr/bin/env python3
"""
Interactive Chat CLI for AI Log Analyzer

Usage:
    python chat.py                           # Use iterative ReAct (default)
    python chat.py --orchestrator hybrid     # Use hybrid planner
    python chat.py --log-file mylog.csv      # Specify log file
    python chat.py --help                    # Show help
"""

import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from datetime import datetime

sys.path.insert(0, '.')

from src.core import IterativeReactOrchestrator, HybridOrchestrator
from src.utils.logger import setup_logger

console = Console()


class ChatSession:
    """Manages a chat session with the log analyzer."""
    
    def __init__(self, orchestrator, orchestrator_type):
        self.orchestrator = orchestrator
        self.orchestrator_type = orchestrator_type
        self.history = []
        self.start_time = datetime.now()
        self.total_queries = 0
        self.successful_queries = 0
    
    def add_query(self, query, result):
        """Add a query to history."""
        self.history.append({
            "query": query,
            "answer": result.get("answer", "No answer"),
            "success": result.get("success", False),
            "timestamp": datetime.now()
        })
        self.total_queries += 1
        if result.get("success", False):
            self.successful_queries += 1
    
    def show_history(self):
        """Display chat history."""
        if not self.history:
            console.print("[yellow]No history yet. Ask a question![/yellow]")
            return
        
        table = Table(title="Chat History", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Query", style="cyan")
        table.add_column("Answer", style="green")
        table.add_column("Status", width=8)
        
        for i, entry in enumerate(self.history[-10:], 1):  # Show last 10
            status = "✓" if entry["success"] else "✗"
            table.add_row(
                str(i),
                entry["query"][:40] + "..." if len(entry["query"]) > 40 else entry["query"],
                entry["answer"][:50] + "..." if len(entry["answer"]) > 50 else entry["answer"],
                status
            )
        
        console.print(table)
    
    def show_stats(self):
        """Display session statistics."""
        duration = (datetime.now() - self.start_time).total_seconds()
        success_rate = (self.successful_queries / self.total_queries * 100) if self.total_queries > 0 else 0
        
        stats = Table(title="Session Statistics", show_header=False)
        stats.add_column("Metric", style="bold")
        stats.add_column("Value", style="cyan")
        
        stats.add_row("Orchestrator", self.orchestrator_type)
        stats.add_row("Total Queries", str(self.total_queries))
        stats.add_row("Successful", f"{self.successful_queries}/{self.total_queries}")
        stats.add_row("Success Rate", f"{success_rate:.1f}%")
        stats.add_row("Session Duration", f"{duration:.0f}s")
        
        console.print(stats)


def show_welcome(orchestrator_type, log_file, max_iterations=None):
    """Display welcome message."""
    welcome = f"""
# 🤖 AI Log Analyzer - Interactive Chat

**Orchestrator**: {orchestrator_type}
**Log File**: {log_file}
"""
    
    if orchestrator_type == "Iterative ReAct":
        welcome += f"**Max Iterations**: {max_iterations}\n"
    
    welcome += """
## Commands:
- Type your question naturally (e.g., "count all error logs")
- `/help` - Show this help
- `/history` - View chat history
- `/stats` - Show session statistics
- `/clear` - Clear screen
- `/exit` or `/quit` - Exit chat

## Example Queries:
- "count all logs"
- "show error logs"
- "count unique CM MACs"
- "find logs for MAWED07T01"
- "list all RPDs in warning logs"

Ready to analyze! 🚀
"""
    
    console.print(Panel(Markdown(welcome), border_style="green"))


def show_help():
    """Show help message."""
    help_text = """
# Available Commands

- `/help` - Show this help message
- `/history` - View your query history (last 10)
- `/stats` - Show session statistics
- `/clear` - Clear the screen
- `/exit` or `/quit` - Exit the chat

# How to Ask Questions

Just type naturally! Examples:

**Simple Queries:**
- "count all logs"
- "show error logs"
- "how many logs are there?"

**Entity Queries:**
- "count unique CM MACs"
- "list all RPD names"
- "find all cable modems"

**Filtered Queries:**
- "count errors for MAWED07T01"
- "show warning logs from last hour"
- "find CM MACs in error logs"

**Relationship Queries:**
- "find all CMs connected to RPD MAWED07T01"
- "what RPDs have errors?"
"""
    
    console.print(Panel(Markdown(help_text), border_style="blue"))


def process_command(command, session):
    """Process special commands."""
    command = command.lower().strip()
    
    if command in ["/exit", "/quit"]:
        return "exit"
    elif command == "/help":
        show_help()
        return "continue"
    elif command == "/history":
        session.show_history()
        return "continue"
    elif command == "/stats":
        session.show_stats()
        return "continue"
    elif command == "/clear":
        console.clear()
        return "continue"
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print("[yellow]Type /help to see available commands[/yellow]")
        return "continue"


@click.command()
@click.option('--log-file', '-f', default='test.csv', 
              help='Path to log CSV file')
@click.option('--orchestrator', '-o', 
              type=click.Choice(['iterative', 'hybrid'], case_sensitive=False),
              default='iterative',
              help='Orchestrator type: iterative (ReAct) or hybrid (planner)')
@click.option('--model', '-m', default='qwen3-react',
              help='LLM model name for iterative orchestrator')
@click.option('--max-iterations', '-i', default=10,
              help='Max iterations for iterative orchestrator')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose logging')
@click.option('--config-dir', '-c', default='config',
              help='Configuration directory')
def main(log_file, orchestrator, model, max_iterations, verbose, config_dir):
    """Interactive chat interface for AI log analysis."""
    
    # Setup logging
    setup_logger(level="DEBUG" if verbose else "INFO")
    
    try:
        # Initialize orchestrator
        console.print("\n[cyan]Initializing orchestrator...[/cyan]")
        
        if orchestrator == 'iterative':
            orch = IterativeReactOrchestrator(
                log_file=log_file,
                config_dir=config_dir,
                model=model,
                max_iterations=max_iterations,
                verbose=verbose
            )
            orch_type = "Iterative ReAct"
        else:
            orch = HybridOrchestrator(
                log_file=log_file,
                config_dir=config_dir,
                model="qwen3-loganalyzer",
                verbose=verbose
            )
            orch_type = "Hybrid Planner"
            max_iterations = None
        
        console.print("[green]✓ Orchestrator initialized[/green]\n")
        
    except Exception as e:
        console.print(f"[red]Failed to initialize orchestrator: {e}[/red]")
        console.print("\n[yellow]Please ensure:[/yellow]")
        console.print("  1. Ollama is running (ollama serve)")
        console.print(f"  2. Model '{model}' exists (ollama list)")
        console.print(f"  3. Log file '{log_file}' exists")
        sys.exit(1)
    
    # Show welcome
    show_welcome(orch_type, log_file, max_iterations)
    
    # Create session
    session = ChatSession(orch, orch_type)
    
    # Main chat loop
    while True:
        try:
            # Get user input
            query = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
            
            if not query:
                continue
            
            # Check for commands
            if query.startswith('/'):
                action = process_command(query, session)
                if action == "exit":
                    break
                continue
            
            # Process query
            console.print("[dim]Thinking...[/dim]")
            
            result = orch.process(query)
            
            # Display result
            if result.get("success"):
                answer = result["answer"]
                console.print(f"\n[bold green]Assistant:[/bold green] {answer}")
                
                # Show metadata if verbose
                if verbose:
                    if "iterations" in result:
                        console.print(f"[dim]  (Iterations: {result['iterations']}, "
                                    f"Tools: {' → '.join(result.get('tools_used', []))})[/dim]")
            else:
                error = result.get("error", "Unknown error")
                console.print(f"\n[bold red]Error:[/bold red] {error}")
            
            # Add to history
            session.add_query(query, result)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
            continue
        except EOFError:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()
    
    # Goodbye message
    console.print("\n[cyan]Session Summary:[/cyan]")
    session.show_stats()
    console.print("\n[green]Thanks for using AI Log Analyzer! Goodbye! 👋[/green]\n")


if __name__ == '__main__':
    main()

