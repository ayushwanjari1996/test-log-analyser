#!/usr/bin/env python
"""
Test runner for Phase 2 components with detailed output.

Usage:
    python tests/run_phase2_tests.py
    python tests/run_phase2_tests.py --verbose
    python tests/run_phase2_tests.py --module log_processor
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import pytest


console = Console()


def run_all_tests(verbose=False):
    """Run all Phase 2 tests."""
    console.print("\n[bold blue]═══ Phase 2: Log Processing Engine Tests ═══[/bold blue]\n")
    
    test_files = [
        "tests/test_log_processor.py",
        "tests/test_chunker.py",
        "tests/test_entity_manager.py"
    ]
    
    # Verify test files exist
    missing = []
    for test_file in test_files:
        if not Path(test_file).exists():
            missing.append(test_file)
    
    if missing:
        console.print(f"[red]Missing test files:[/red]")
        for file in missing:
            console.print(f"  - {file}")
        return False
    
    # Run pytest
    args = ["-v"] if verbose else []
    args.extend(test_files)
    
    result = pytest.main(args)
    
    if result == 0:
        console.print("\n[bold green]✓ All Phase 2 tests passed![/bold green]\n")
        return True
    else:
        console.print("\n[bold red]✗ Some tests failed[/bold red]\n")
        return False


def run_module_tests(module_name, verbose=False):
    """Run tests for a specific module."""
    console.print(f"\n[bold blue]Testing {module_name}...[/bold blue]\n")
    
    test_file = f"tests/test_{module_name}.py"
    
    if not Path(test_file).exists():
        console.print(f"[red]Test file not found: {test_file}[/red]")
        return False
    
    args = [test_file]
    if verbose:
        args.append("-v")
    
    result = pytest.main(args)
    return result == 0


def show_component_info():
    """Display information about Phase 2 components."""
    console.print("\n[bold blue]Phase 2: Log Processing Engine Components[/bold blue]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Component", style="yellow")
    table.add_column("File", style="green")
    table.add_column("Description")
    
    components = [
        (
            "LogProcessor",
            "src/core/log_processor.py",
            "CSV reading, filtering, entity extraction"
        ),
        (
            "LogChunker",
            "src/core/chunker.py",
            "Log chunking for LLM context windows"
        ),
        (
            "EntityManager",
            "src/core/entity_manager.py",
            "Entity extraction and relationship management"
        )
    ]
    
    for name, file, desc in components:
        table.add_row(name, file, desc)
    
    console.print(table)
    console.print()


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="Test runner for Phase 2 components"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose test output"
    )
    parser.add_argument(
        "--module", "-m",
        choices=["log_processor", "chunker", "entity_manager"],
        help="Test specific module only"
    )
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="Show component information"
    )
    
    args = parser.parse_args()
    
    if args.info:
        show_component_info()
        return 0
    
    # Show component info first
    show_component_info()
    
    # Run tests
    if args.module:
        success = run_module_tests(args.module, verbose=args.verbose)
    else:
        success = run_all_tests(verbose=args.verbose)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

