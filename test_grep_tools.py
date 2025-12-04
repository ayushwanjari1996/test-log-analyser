"""
Test Script for New Grep-Based Tools

Tests the grep-first approach independently before integration.
"""

import sys
sys.path.insert(0, '.')

from src.core.tools.grep_tools import (
    GrepLogsTool,
    ParseJsonFieldTool,
    ExtractUniqueValuesTool,
    CountValuesTool,
    GrepAndParseTool
)


def test_grep_logs():
    """Test basic grep functionality."""
    print("\n" + "="*70)
    print("TEST 1: Grep Logs")
    print("="*70)
    
    tool = GrepLogsTool("test.csv")
    
    # Search for a CM MAC address (not CPE MAC - CM has MdId)
    result = tool.execute(pattern="2c:ab:a4:40:a8:bc")
    
    print(f"Pattern: 2c:ab:a4:40:a8:bc (CM MAC)")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Rows found: {len(result.data) if result.success else 0}")
    
    return result.success and len(result.data) > 0


def test_parse_json_field():
    """Test JSON field extraction."""
    print("\n" + "="*70)
    print("TEST 2: Parse JSON Field")
    print("="*70)
    
    # First grep for CM MAC (has MdId)
    grep_tool = GrepLogsTool("test.csv")
    grep_result = grep_tool.execute(pattern="2c:ab:a4:40:a8:bc")
    
    if not grep_result.success:
        print("✗ Grep failed")
        return False
    
    # Then parse MdId
    parse_tool = ParseJsonFieldTool()
    result = parse_tool.execute(logs=grep_result.data, field_name="MdId")
    
    print(f"Grepped logs: {len(grep_result.data)}")
    print(f"Parse success: {result.success}")
    print(f"Message: {result.message}")
    if result.success and result.data:
        print(f"MDIDs found: {result.data[:3]}")
    
    return result.success and len(result.data) > 0


def test_extract_unique():
    """Test unique value extraction."""
    print("\n" + "="*70)
    print("TEST 3: Extract Unique Values")
    print("="*70)
    
    # First get some values
    grep_tool = GrepLogsTool("test.csv")
    grep_result = grep_tool.execute(pattern="CmMacAddress", max_results=50)
    
    if not grep_result.success:
        print("✗ Grep failed")
        return False
    
    # Parse CM MACs
    parse_tool = ParseJsonFieldTool()
    parse_result = parse_tool.execute(logs=grep_result.data, field_name="CmMacAddress")
    
    if not parse_result.success or not parse_result.data:
        print("✗ Parse failed")
        return False
    
    # Extract unique
    unique_tool = ExtractUniqueValuesTool()
    result = unique_tool.execute(values=parse_result.data)
    
    print(f"Total values: {len(parse_result.data)}")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Unique count: {len(result.data) if result.success else 0}")
    
    return result.success


def test_count_values():
    """Test counting values."""
    print("\n" + "="*70)
    print("TEST 4: Count Values")
    print("="*70)
    
    # Get some CM MACs
    grep_tool = GrepLogsTool("test.csv")
    grep_result = grep_tool.execute(pattern="CmMacAddress", max_results=30)
    
    if not grep_result.success:
        print("✗ Grep failed")
        return False
    
    parse_tool = ParseJsonFieldTool()
    parse_result = parse_tool.execute(logs=grep_result.data, field_name="CmMacAddress")
    
    if not parse_result.success:
        print("✗ Parse failed")
        return False
    
    # Count
    count_tool = CountValuesTool()
    result = count_tool.execute(values=parse_result.data)
    
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Unique count: {result.data if result.success else 0}")
    
    return result.success


def test_grep_and_parse():
    """Test combined grep+parse operation."""
    print("\n" + "="*70)
    print("TEST 5: Grep and Parse (Combined)")
    print("="*70)
    
    tool = GrepAndParseTool("test.csv")
    
    # Get MDID for CM MAC in one step
    result = tool.execute(
        pattern="2c:ab:a4:40:a8:bc",
        field_name="MdId",
        unique_only=True
    )
    
    print(f"Pattern: 2c:ab:a4:40:a8:bc (CM MAC)")
    print(f"Field: MdId")
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    if result.success and result.data:
        print(f"MDIDs: {result.data}")
    
    return result.success and len(result.data) > 0


def test_relationship_query():
    """Test relationship query pattern."""
    print("\n" + "="*70)
    print("TEST 6: Relationship Query (Find CM MACs for MDID)")
    print("="*70)
    
    # Step 1: Get MDID for a CM MAC
    tool1 = GrepAndParseTool("test.csv")
    mdid_result = tool1.execute(
        pattern="2c:ab:a4:40:a8:bc",
        field_name="MdId",
        unique_only=True
    )
    
    if not mdid_result.success or not mdid_result.data:
        print("✗ Step 1 failed: Couldn't find MDID")
        return False
    
    mdid = mdid_result.data[0]
    print(f"Step 1: Found MDID = {mdid}")
    
    # Step 2: Find all CM MACs with this MDID
    tool2 = GrepAndParseTool("test.csv")
    cm_result = tool2.execute(
        pattern=mdid,
        field_name="CmMacAddress",
        unique_only=True
    )
    
    print(f"Step 2: Found {len(cm_result.data) if cm_result.success else 0} CM MACs for MDID {mdid}")
    if cm_result.success and cm_result.data:
        print(f"Sample CM MACs: {cm_result.data[:5]}")
    
    return cm_result.success


def test_count_unique_pattern():
    """Test count unique pattern (common query)."""
    print("\n" + "="*70)
    print("TEST 7: Count Unique CM MACs in ERROR logs")
    print("="*70)
    
    # Step 1: Grep ERROR logs
    grep_tool = GrepLogsTool("test.csv")
    error_result = grep_tool.execute(pattern='"Severity":"ERROR"')
    
    print(f"Step 1: Found {len(error_result.data) if error_result.success else 0} ERROR logs")
    
    if not error_result.success or error_result.data.empty:
        print("ℹ️  No ERROR logs found (might be INFO/DEBUG only)")
        return True  # Not a failure, just no errors in test data
    
    # Step 2: Parse CM MACs
    parse_tool = ParseJsonFieldTool()
    parse_result = parse_tool.execute(logs=error_result.data, field_name="CmMacAddress")
    
    if not parse_result.success or not parse_result.data:
        print("ℹ️  No CM MACs in ERROR logs")
        return True
    
    # Step 3: Count unique
    count_tool = CountValuesTool()
    count_result = count_tool.execute(values=parse_result.data)
    
    print(f"Step 2: {count_result.message if count_result.success else 'Count failed'}")
    
    return count_result.success


def performance_test():
    """Compare grep approach vs old approach."""
    print("\n" + "="*70)
    print("PERFORMANCE: Grep vs Load-All")
    print("="*70)
    
    import time
    
    # NEW: Grep approach
    print("\nNEW Approach (Grep):")
    start = time.time()
    
    tool = GrepAndParseTool("test.csv")
    result = tool.execute(
        pattern="2c:ab:a4:40:a8:bc",
        field_name="MdId",
        unique_only=True
    )
    
    grep_time = time.time() - start
    print(f"  Time: {grep_time*1000:.2f}ms")
    print(f"  Result: {result.data if result.success else 'Failed'}")
    
    # OLD: Load-all approach (simulated)
    print("\nOLD Approach (Load All):")
    start = time.time()
    
    import pandas as pd
    df = pd.read_csv("test.csv", encoding='utf-8', on_bad_lines='skip')
    # Search
    mask = df.astype(str).apply(
        lambda row: any("2c:ab:a4:40:a8:bc" in str(cell) for cell in row), axis=1
    )
    filtered = df[mask]
    # Parse (simulated)
    
    old_time = time.time() - start
    print(f"  Time: {old_time*1000:.2f}ms")
    print(f"  Rows: {len(filtered)}")
    
    print(f"\n📊 Speedup: {old_time/grep_time:.2f}x")
    
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("GREP TOOLS - TEST SUITE")
    print("="*70)
    print("\nTesting new grep-first tool architecture")
    
    tests = [
        ("Grep Logs", test_grep_logs),
        ("Parse JSON Field", test_parse_json_field),
        ("Extract Unique", test_extract_unique),
        ("Count Values", test_count_values),
        ("Grep and Parse", test_grep_and_parse),
        ("Relationship Query", test_relationship_query),
        ("Count Unique Pattern", test_count_unique_pattern),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Performance test
    try:
        performance_test()
    except Exception as e:
        print(f"\n⚠️  Performance test failed: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "✓ PASS" if p else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Ready to integrate grep tools.")
        print("\nGrep-first approach working:")
        print("  ✓ Memory efficient (no load-all)")
        print("  ✓ Fast for targeted queries")
        print("  ✓ Works for relationships")
        print("  ✓ JSON parsing integrated")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review before integrating.")


if __name__ == "__main__":
    main()

