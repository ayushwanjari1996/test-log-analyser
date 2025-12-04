"""
Independent Test Script for StreamSearcher

Tests the streaming CSV search engine without any tool integration.
"""

import sys
import time
sys.path.insert(0, '.')

from src.core.stream_searcher import StreamSearcher


def test_basic_search():
    """Test basic text search."""
    print("\n" + "="*70)
    print("TEST 1: Basic Search")
    print("="*70)
    
    searcher = StreamSearcher("test.csv")
    
    # Search for a MAC address
    search_term = "2c:ab:a4:47:1a:d2"
    print(f"\nSearching for: {search_term}")
    
    start_time = time.time()
    results = searcher.search(search_term)
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} matches")
    print(f"⏱ Time: {elapsed*1000:.2f}ms")
    
    if not results.empty:
        print(f"\nFirst match preview:")
        first_row = results.iloc[0]
        print(f"  Date: {first_row.get('_source.date', 'N/A')}")
        log_preview = str(first_row.get('_source.log', ''))[:100]
        print(f"  Log: {log_preview}...")
    
    return len(results) > 0


def test_count_only():
    """Test counting without loading data."""
    print("\n" + "="*70)
    print("TEST 2: Count Only (Fast)")
    print("="*70)
    
    searcher = StreamSearcher("test.csv")
    
    search_term = "ERROR"
    print(f"\nCounting: {search_term}")
    
    start_time = time.time()
    count = searcher.count_matches(search_term)
    elapsed = time.time() - start_time
    
    print(f"✓ Found {count} matches")
    print(f"⏱ Time: {elapsed*1000:.2f}ms")
    
    return count > 0


def test_case_sensitive():
    """Test case-sensitive search."""
    print("\n" + "="*70)
    print("TEST 3: Case Sensitive vs Insensitive")
    print("="*70)
    
    searcher = StreamSearcher("test.csv")
    
    search_term = "error"
    
    print(f"\nSearching for: {search_term}")
    
    # Case insensitive
    start_time = time.time()
    results_insensitive = searcher.search(search_term, case_sensitive=False)
    time_insensitive = time.time() - start_time
    
    # Case sensitive
    start_time = time.time()
    results_sensitive = searcher.search(search_term, case_sensitive=True)
    time_sensitive = time.time() - start_time
    
    print(f"✓ Case insensitive: {len(results_insensitive)} matches ({time_insensitive*1000:.2f}ms)")
    print(f"✓ Case sensitive: {len(results_sensitive)} matches ({time_sensitive*1000:.2f}ms)")
    
    return len(results_insensitive) >= len(results_sensitive)


def test_max_results():
    """Test limiting results."""
    print("\n" + "="*70)
    print("TEST 4: Limited Results")
    print("="*70)
    
    searcher = StreamSearcher("test.csv")
    
    search_term = "ulc-mulpi"
    max_results = 10
    
    print(f"\nSearching for: {search_term} (max {max_results} results)")
    
    start_time = time.time()
    results = searcher.search(search_term, max_results=max_results)
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} matches (stopped at limit)")
    print(f"⏱ Time: {elapsed*1000:.2f}ms (faster due to early stop)")
    
    return len(results) == max_results


def test_column_specific():
    """Test searching specific columns."""
    print("\n" + "="*70)
    print("TEST 5: Column-Specific Search")
    print("="*70)
    
    searcher = StreamSearcher("test.csv")
    
    search_term = "Nov 5, 2025"
    columns = ["_source.date"]
    
    print(f"\nSearching for: {search_term}")
    print(f"In columns: {columns}")
    
    start_time = time.time()
    results = searcher.search(search_term, columns=columns)
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} matches")
    print(f"⏱ Time: {elapsed*1000:.2f}ms")
    
    return len(results) > 0


def test_json_field_search():
    """Test searching within JSON fields."""
    print("\n" + "="*70)
    print("TEST 6: JSON Field Search")
    print("="*70)
    
    searcher = StreamSearcher("test.csv")
    
    # Search for MdId which is inside JSON
    search_term = '"MdId":"0x64030000"'
    
    print(f"\nSearching for JSON field: {search_term}")
    
    start_time = time.time()
    results = searcher.search(search_term)
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} matches")
    print(f"⏱ Time: {elapsed*1000:.2f}ms")
    
    if not results.empty:
        print(f"\nJSON search works! Found logs with MdId=0x64030000")
    
    return len(results) > 0


def test_regex_search():
    """Test regex pattern search."""
    print("\n" + "="*70)
    print("TEST 7: Regex Search")
    print("="*70)
    
    searcher = StreamSearcher("test.csv")
    
    # MAC address pattern
    pattern = r"[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}"
    
    print(f"\nSearching with regex: {pattern}")
    print("(Looking for MAC addresses)")
    
    start_time = time.time()
    results = searcher.search(pattern, regex=True, max_results=5)
    elapsed = time.time() - start_time
    
    print(f"✓ Found {len(results)} matches")
    print(f"⏱ Time: {elapsed*1000:.2f}ms")
    
    return len(results) > 0


def performance_comparison():
    """Compare streaming vs full load."""
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON")
    print("="*70)
    
    import pandas as pd
    
    search_term = "2c:ab:a4:47:1a:d2"
    
    # Method 1: Full load (old way)
    print("\nMethod 1: Load all + Search (OLD)")
    start_time = time.time()
    df = pd.read_csv("test.csv", encoding='utf-8', on_bad_lines='skip')
    load_time = time.time() - start_time
    
    start_search = time.time()
    mask = df.astype(str).apply(
        lambda row: any(search_term in str(cell) for cell in row), axis=1
    )
    results_old = df[mask]
    search_time = time.time() - start_search
    total_old = load_time + search_time
    
    print(f"  Load time: {load_time*1000:.2f}ms")
    print(f"  Search time: {search_time*1000:.2f}ms")
    print(f"  Total: {total_old*1000:.2f}ms")
    print(f"  Found: {len(results_old)} matches")
    print(f"  Memory: ~{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    # Method 2: Streaming (new way)
    print("\nMethod 2: Stream + Search (NEW)")
    searcher = StreamSearcher("test.csv")
    
    start_time = time.time()
    results_new = searcher.search(search_term)
    total_new = time.time() - start_time
    
    print(f"  Total: {total_new*1000:.2f}ms")
    print(f"  Found: {len(results_new)} matches")
    print(f"  Memory: Minimal (streaming)")
    
    # Comparison
    print(f"\n📊 SPEEDUP: {total_old/total_new:.2f}x faster")
    print(f"💾 MEMORY SAVED: ~{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    return total_new < total_old


def main():
    """Run all tests."""
    print("="*70)
    print("STREAM SEARCHER - INDEPENDENT TEST SUITE")
    print("="*70)
    print("\nTesting streaming CSV search without tool integration")
    print("Log file: test.csv")
    
    tests = [
        ("Basic Search", test_basic_search),
        ("Count Only", test_count_only),
        ("Case Sensitive", test_case_sensitive),
        ("Max Results", test_max_results),
        ("Column Specific", test_column_specific),
        ("JSON Field Search", test_json_field_search),
        ("Regex Search", test_regex_search),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ {test_name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Performance comparison
    print("\n")
    try:
        perf_passed = performance_comparison()
        results.append(("Performance", perf_passed))
    except Exception as e:
        print(f"\n✗ Performance test FAILED: {e}")
        results.append(("Performance", False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for test_name, passed_flag in results:
        status = "✓ PASS" if passed_flag else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Stream searcher is working perfectly.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed.")


if __name__ == "__main__":
    main()

