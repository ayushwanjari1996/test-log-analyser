"""
Unit tests for each individual tool.
Tests tools in isolation before orchestration.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import create_all_tools
from src.utils.logger import setup_logger

console = Console(force_terminal=True, force_jupyter=False)
logger = setup_logger()


class ToolTester:
    """Helper class for testing tools"""
    
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.tools = create_all_tools(log_file)
        self.tool_dict = {tool.name: tool for tool in self.tools}
        self.results = []
    
    def get_tool(self, name: str):
        """Get tool by name"""
        return self.tool_dict.get(name)
    
    def test_tool(self, tool_name: str, test_name: str, params: dict, expected_success: bool = True):
        """Test a tool with given parameters"""
        console.print(f"\n[yellow]Testing {tool_name}: {test_name}[/yellow]")
        
        tool = self.get_tool(tool_name)
        if not tool:
            console.print(f"[red]✗ Tool '{tool_name}' not found[/red]")
            self.results.append({
                "tool": tool_name,
                "test": test_name,
                "status": "FAIL",
                "error": "Tool not found"
            })
            return None
        
        try:
            # Execute tool
            result = tool.execute(**params)
            
            # Check success matches expected
            success_match = result.success == expected_success
            
            if success_match:
                console.print(f"[green]✓ {result.message}[/green]")
                if result.data is not None:
                    if isinstance(result.data, pd.DataFrame):
                        console.print(f"  Data: DataFrame with {len(result.data)} rows")
                    elif isinstance(result.data, dict):
                        console.print(f"  Data: {result.data}")
                    else:
                        console.print(f"  Data: {type(result.data).__name__}")
                
                self.results.append({
                    "tool": tool_name,
                    "test": test_name,
                    "status": "PASS",
                    "message": result.message
                })
                return result
            else:
                console.print(f"[red]✗ Expected success={expected_success}, got {result.success}[/red]")
                console.print(f"  Error: {result.error}")
                self.results.append({
                    "tool": tool_name,
                    "test": test_name,
                    "status": "FAIL",
                    "error": f"Success mismatch: expected {expected_success}, got {result.success}"
                })
                return result
                
        except Exception as e:
            console.print(f"[red]✗ Exception: {e}[/red]")
            import traceback
            traceback.print_exc()
            self.results.append({
                "tool": tool_name,
                "test": test_name,
                "status": "ERROR",
                "error": str(e)
            })
            return None
    
    def print_summary(self):
        """Print test summary"""
        console.print("\n" + "=" * 70)
        console.print("[bold]TEST SUMMARY[/bold]")
        console.print("=" * 70)
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Tool", style="cyan", width=25)
        table.add_column("Test", style="white", width=30)
        table.add_column("Status", justify="center", width=10)
        
        passed = 0
        failed = 0
        errors = 0
        
        for r in self.results:
            status_color = {
                "PASS": "green",
                "FAIL": "red",
                "ERROR": "red"
            }.get(r['status'], "white")
            
            table.add_row(
                r['tool'],
                r['test'],
                f"[{status_color}]{r['status']}[/{status_color}]"
            )
            
            if r['status'] == "PASS":
                passed += 1
            elif r['status'] == "FAIL":
                failed += 1
            else:
                errors += 1
        
        console.print(table)
        console.print(f"\n[bold]Results: {passed} passed, {failed} failed, {errors} errors[/bold]")
        console.print(f"[bold]Total: {passed}/{len(self.results)} tests passed[/bold]")


def main():
    """Run all tool tests"""
    console.print(Panel.fit(
        "[bold green]Individual Tool Unit Tests[/bold green]",
        border_style="green"
    ))
    
    # Check test file
    if not Path("test.csv").exists():
        console.print("[red]✗ test.csv not found![/red]")
        return
    
    console.print(f"[green]✓ Found test.csv[/green]")
    
    # Initialize tester
    tester = ToolTester("test.csv")
    console.print(f"[green]✓ Loaded {len(tester.tools)} tools[/green]\n")
    
    # List all tools
    console.print("[bold]Available Tools:[/bold]")
    for idx, tool in enumerate(tester.tools, 1):
        console.print(f"  {idx}. {tool.name}")
    
    # ================================================================
    # TEST 1: SEARCH_LOGS
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 1: SEARCH_LOGS[/bold cyan]")
    console.print("=" * 70)
    
    # Test 1.1: Basic search
    result = tester.test_tool(
        "search_logs",
        "Basic search with value",
        {"value": "MAWED07T01"},
        expected_success=True
    )
    search_result_df = result.data if result else None
    
    # Test 1.2: Search with column filter
    tester.test_tool(
        "search_logs",
        "Search with specific columns",
        {"value": "error", "columns": ["_source.log"]},
        expected_success=True
    )
    
    # Test 1.3: Search no results
    tester.test_tool(
        "search_logs",
        "Search with no results",
        {"value": "NONEXISTENT_VALUE_12345"},
        expected_success=True
    )
    
    # ================================================================
    # TEST 2: FILTER_BY_TIME
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 2: FILTER_BY_TIME[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        tester.test_tool(
            "filter_by_time",
            "Filter by time range",
            {
                "logs": search_result_df,
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2025-12-31T23:59:59"
            },
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping filter_by_time (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 3: FILTER_BY_SEVERITY
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 3: FILTER_BY_SEVERITY[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        # Test 3.1: Filter errors
        tester.test_tool(
            "filter_by_severity",
            "Filter ERROR logs",
            {"logs": search_result_df, "severities": ["ERROR"]},
            expected_success=True
        )
        
        # Test 3.2: Filter multiple severities
        tester.test_tool(
            "filter_by_severity",
            "Filter ERROR and WARNING logs",
            {"logs": search_result_df, "severities": ["ERROR", "WARNING"]},
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping filter_by_severity (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 4: FILTER_BY_FIELD
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 4: FILTER_BY_FIELD[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        tester.test_tool(
            "filter_by_field",
            "Filter by field value",
            {"logs": search_result_df, "field": "_source.log", "value": "MAWED07T01"},
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping filter_by_field (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 5: GET_LOG_COUNT
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 5: GET_LOG_COUNT[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None:
        tester.test_tool(
            "get_log_count",
            "Count logs",
            {"logs": search_result_df},
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping get_log_count (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 6: EXTRACT_ENTITIES
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 6: EXTRACT_ENTITIES[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        # Test 6.1: Extract single entity type
        result = tester.test_tool(
            "extract_entities",
            "Extract single entity type",
            {"logs": search_result_df, "entity_types": ["cm_mac"]},
            expected_success=True
        )
        entities_result = result.data if result else {}
        
        # Test 6.2: Extract multiple entity types
        tester.test_tool(
            "extract_entities",
            "Extract multiple entity types",
            {"logs": search_result_df, "entity_types": ["cm_mac", "rpdname", "md_id"]},
            expected_success=True
        )
        
        # Test 6.3: Extract all entity types
        tester.test_tool(
            "extract_entities",
            "Extract all entity types (empty list)",
            {"logs": search_result_df, "entity_types": []},
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping extract_entities (no logs available)[/yellow]")
        entities_result = {}
    
    # ================================================================
    # TEST 7: COUNT_ENTITIES
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 7: COUNT_ENTITIES[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        tester.test_tool(
            "count_entities",
            "Count entities of specific type",
            {"logs": search_result_df, "entity_type": "cm_mac"},
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping count_entities (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 8: AGGREGATE_ENTITIES
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 8: AGGREGATE_ENTITIES[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        tester.test_tool(
            "aggregate_entities",
            "Aggregate entity statistics",
            {"logs": search_result_df, "entity_types": ["cm_mac", "rpdname"]},
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping aggregate_entities (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 9: FIND_ENTITY_RELATIONSHIPS
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 9: FIND_ENTITY_RELATIONSHIPS[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        tester.test_tool(
            "find_entity_relationships",
            "Find entity relationships",
            {"logs": search_result_df, "target_value": "MAWED07T01", "related_types": ["cm_mac"]},
            expected_success=True
        )
    else:
        console.print("[yellow]⚠ Skipping find_entity_relationships (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 10: NORMALIZE_TERM
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 10: NORMALIZE_TERM[/bold cyan]")
    console.print("=" * 70)
    
    tester.test_tool(
        "normalize_term",
        "Normalize search term",
        {"term": "reg"},
        expected_success=True
    )
    
    # ================================================================
    # TEST 11: FUZZY_SEARCH
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 11: FUZZY_SEARCH[/bold cyan]")
    console.print("=" * 70)
    
    tester.test_tool(
        "fuzzy_search",
        "Fuzzy search with normalized term",
        {"logs": search_result_df if search_result_df is not None else pd.DataFrame(), "term": "error"},
        expected_success=True
    )
    
    # ================================================================
    # TEST 12: RETURN_LOGS
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 12: RETURN_LOGS[/bold cyan]")
    console.print("=" * 70)
    
    if search_result_df is not None and not search_result_df.empty:
        result = tester.test_tool(
            "return_logs",
            "Format logs for display",
            {"logs": search_result_df, "max_samples": 3},
            expected_success=True
        )
        
        if result and result.success:
            console.print("\n[cyan]Formatted Output:[/cyan]")
            console.print(Panel(result.data.get('formatted', 'No output'), border_style="cyan"))
    else:
        console.print("[yellow]⚠ Skipping return_logs (no logs available)[/yellow]")
    
    # ================================================================
    # TEST 13: FINALIZE_ANSWER
    # ================================================================
    console.print("\n" + "=" * 70)
    console.print("[bold cyan]TEST GROUP 13: FINALIZE_ANSWER[/bold cyan]")
    console.print("=" * 70)
    
    tester.test_tool(
        "finalize_answer",
        "Finalize with answer",
        {"answer": "Test answer", "confidence": 0.95},
        expected_success=True
    )
    
    # Print summary
    tester.print_summary()
    
    # Check if all passed
    all_passed = all(r['status'] == 'PASS' for r in tester.results)
    if all_passed:
        console.print("\n[bold green]✓ ALL TOOLS WORKING CORRECTLY[/bold green]")
    else:
        console.print("\n[bold red]✗ SOME TOOLS HAVE ISSUES - FIX BEFORE ORCHESTRATION[/bold red]")


if __name__ == "__main__":
    main()

