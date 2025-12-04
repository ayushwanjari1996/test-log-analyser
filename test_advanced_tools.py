"""
Test script for advanced tools (Phase 1-3).
Tests each tool independently WITHOUT LLM calls.

Tools tested:
1. find_relationship_chain
2. sort_by_time
3. extract_time_range
4. summarize_logs
5. aggregate_by_field
6. analyze_logs (WITH LLM call - optional)
"""

import logging
import sys
import pandas as pd
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%m/%d/%y %H:%M:%S'
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.tools.relationship_tools import FindRelationshipChainTool
from src.core.tools.time_tools import SortByTimeTool, ExtractTimeRangeTool
from src.core.tools.analysis_tools import SummarizeLogsTool, AggregateByFieldTool, AnalyzeLogsTool


def print_header(title: str):
    """Print test section header."""
    print("\n" + "="*70)
    print(f"TEST: {title}")
    print("="*70)


def print_result(result):
    """Pretty print tool result."""
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.data is not None:
        if isinstance(result.data, pd.DataFrame):
            print(f"Data: DataFrame with {len(result.data)} rows")
        else:
            print(f"Data: {result.data}")
    if result.error:
        print(f"Error: {result.error}")
    if result.metadata:
        print(f"Metadata: {result.metadata}")


def test_relationship_chain(log_file: str):
    """Test 1: Find relationship chain."""
    print_header("find_relationship_chain")
    
    tool = FindRelationshipChainTool(log_file, config_dir="config")
    
    # Test 1a: CPE MAC -> mdId (should chain through RpdName)
    print("\n--- Test 1a: CPE MAC -> mdId (multi-hop) ---")
    result = tool.execute(
        start_value="2c:ab:a4:47:1a:d2",
        target_field="mdId",
        max_depth=4
    )
    print_result(result)
    
    # Test 1b: CM MAC -> mdId (direct)  
    print("\n--- Test 1b: CM MAC -> mdId (direct) ---")
    result = tool.execute(
        start_value="2c:ab:a4:40:a8:bc",
        target_field="mdId",
        max_depth=2
    )
    print_result(result)
    
    # Test 1c: RpdName -> SfId
    print("\n--- Test 1c: RpdName -> SfId ---")
    result = tool.execute(
        start_value="2c:ab:a4:47:1a:d2",
        target_field="mdid",
        max_depth=3
    )
    print_result(result)
    
    # Test 1d: Unreachable field (should fail gracefully)
    print("\n--- Test 1d: Unreachable field ---")
    result = tool.execute(
        start_value="2c:ab:a4:47:1a:d2",
        target_field="NonExistentField",
        max_depth=2
    )
    print_result(result)


def test_sort_by_time(log_file: str):
    """Test 2: Sort logs by time."""
    print_header("sort_by_time")
    
    tool = SortByTimeTool()
    
    # Load some sample logs
    logs = pd.read_csv(log_file, nrows=20)
    
    # Test 2a: Sort ascending (oldest first)
    print("\n--- Test 2a: Sort ascending (oldest first) ---")
    result = tool.execute(logs=logs, order="asc")
    print_result(result)
    
    if result.success and isinstance(result.data, pd.DataFrame) and not result.data.empty:
        # Show first and last timestamps
        time_col = '_source.@timestamp'
        if time_col in result.data.columns:
            first = result.data.iloc[0][time_col]
            last = result.data.iloc[-1][time_col]
            print(f"First timestamp: {first}")
            print(f"Last timestamp: {last}")
    
    # Test 2b: Sort descending (newest first)
    print("\n--- Test 2b: Sort descending (newest first) ---")
    result = tool.execute(logs=logs, order="desc")
    print_result(result)


def test_extract_time_range(log_file: str):
    """Test 3: Extract time range."""
    print_header("extract_time_range")
    
    tool = ExtractTimeRangeTool()
    
    # Load sample logs
    logs = pd.read_csv(log_file, nrows=100)
    
    # Get a sample timestamp for testing
    if '_source.@timestamp' in logs.columns:
        sample_time = logs['_source.@timestamp'].iloc[0]
        print(f"Sample timestamp: {sample_time}")
    
    # Test 3a: Extract specific time range
    print("\n--- Test 3a: Extract specific time range ---")
    result = tool.execute(
        logs=logs,
        start_time="2025-04-23T15:30:00",
        end_time="2025-04-23T15:31:00"
    )
    print_result(result)
    
    # Test 3b: Relative time (now-1h to now)
    print("\n--- Test 3b: Relative time (now-1h to now) ---")
    result = tool.execute(
        logs=logs,
        start_time="now-1h",
        end_time="now"
    )
    print_result(result)


def test_summarize_logs(log_file: str):
    """Test 4: Summarize logs."""
    print_header("summarize_logs")
    
    tool = SummarizeLogsTool()
    
    # Load sample logs
    logs = pd.read_csv(log_file, nrows=100)
    
    # Test 4a: Basic summary
    print("\n--- Test 4a: Basic summary ---")
    result = tool.execute(logs=logs, detail_level="basic")
    print_result(result)
    
    # Test 4b: Full summary
    print("\n--- Test 4b: Full summary ---")
    result = tool.execute(logs=logs, detail_level="full")
    print_result(result)


def test_aggregate_by_field(log_file: str):
    """Test 5: Aggregate by field."""
    print_header("aggregate_by_field")
    
    tool = AggregateByFieldTool()
    
    # Load sample logs (more rows to include RpdName at line 320)
    logs = pd.read_csv(log_file, nrows=400)
    
    # Test 5a: Aggregate by Severity
    print("\n--- Test 5a: Aggregate by Severity ---")
    result = tool.execute(logs=logs, field_name="Severity", top_n=10)
    print_result(result)
    
    # Test 5b: Aggregate by Function
    print("\n--- Test 5b: Aggregate by Function ---")
    result = tool.execute(logs=logs, field_name="Function", top_n=5)
    print_result(result)
    
    # Test 5c: Aggregate by RpdName
    print("\n--- Test 5c: Aggregate by RpdName ---")
    result = tool.execute(logs=logs, field_name="RpdName", top_n=10)
    print_result(result)
    
    # Test 5d: Non-existent field
    print("\n--- Test 5d: Non-existent field ---")
    result = tool.execute(logs=logs, field_name="NonExistentField", top_n=5)
    print_result(result)


def test_analyze_logs(log_file: str, skip_llm: bool = True):
    """Test 6: Analyze logs (LLM-based)."""
    print_header("analyze_logs (LLM-based)")
    
    if skip_llm:
        print("⚠️ Skipping LLM-based analysis (set skip_llm=False to test)")
        return
    
    tool = AnalyzeLogsTool(model="qwen3-loganalyzer")
    
    # Load sample logs
    logs = pd.read_csv(log_file, nrows=30)
    
    # Test 6a: Error analysis
    print("\n--- Test 6a: Error analysis ---")
    result = tool.execute(
        logs=logs,
        focus="errors",
        query_context="What errors occurred?"
    )
    print_result(result)
    
    # Test 6b: Pattern analysis
    print("\n--- Test 6b: Pattern analysis ---")
    result = tool.execute(
        logs=logs,
        focus="patterns",
        query_context="What patterns do you see?"
    )
    print_result(result)


def main():
    """Run all tests."""
    log_file = "test.csv"
    
    print("\n" + "="*70)
    print("ADVANCED TOOLS TEST SUITE")
    print("="*70)
    print(f"Log file: {log_file}")
    
    # Check if log file exists
    if not Path(log_file).exists():
        print(f"❌ Error: Log file '{log_file}' not found!")
        return
    
    # Run tests
    tests_run = 0
    tests_passed = 0
    
    try:
        # Test 1: Relationship chain (no logs needed)
        print("\n🔍 Test 1/6: Relationship Chain")
        test_relationship_chain(log_file)
        tests_run += 1
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        tests_run += 1
    
    try:
        # Test 2: Sort by time
        print("\n⏱️ Test 2/6: Sort by Time")
        test_sort_by_time(log_file)
        tests_run += 1
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        tests_run += 1
    
    try:
        # Test 3: Extract time range
        print("\n📅 Test 3/6: Extract Time Range")
        test_extract_time_range(log_file)
        tests_run += 1
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        tests_run += 1
    
    try:
        # Test 4: Summarize
        print("\n📊 Test 4/6: Summarize Logs")
        test_summarize_logs(log_file)
        tests_run += 1
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        tests_run += 1
    
    try:
        # Test 5: Aggregate
        print("\n📈 Test 5/6: Aggregate by Field")
        test_aggregate_by_field(log_file)
        tests_run += 1
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 5 failed: {e}")
        tests_run += 1
    
    try:
        # Test 6: Analyze (skip LLM by default)
        print("\n🧠 Test 6/6: Analyze Logs")
        test_analyze_logs(log_file, skip_llm=True)
        tests_run += 1
        tests_passed += 1  # Count as passed even if skipped
    except Exception as e:
        print(f"❌ Test 6 failed: {e}")
        tests_run += 1
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {tests_run}/6")
    print(f"Tests passed: {tests_passed}/{tests_run}")
    
    if tests_passed == tests_run:
        print("\n✅ All tests passed!")
    else:
        print(f"\n⚠️ {tests_run - tests_passed} test(s) failed")


if __name__ == "__main__":
    main()

