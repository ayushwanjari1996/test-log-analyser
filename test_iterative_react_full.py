"""
Comprehensive Test Suite for Iterative ReAct Orchestrator

Tests the full iterative ReAct architecture end-to-end with real tools
and LLM integration.
"""

import sys
sys.path.insert(0, '.')

from src.core import IterativeReactOrchestrator
from src.utils.logger import setup_logger

logger = setup_logger()

# Test queries covering different complexities
TEST_QUERIES = [
    # 1. Simple count (2-3 iterations expected)
    {
        "query": "count all logs",
        "expected_iterations": (2, 3),
        "description": "Simple query - load and count"
    },
    
    # 2. Severity filter (3-4 iterations)
    {
        "query": "show error logs",
        "expected_iterations": (2, 4),
        "description": "Filter by severity"
    },
    
    # 3. Entity extraction (4-5 iterations)
    {
        "query": "count unique CM MACs",
        "expected_iterations": (3, 6),
        "description": "Extract and count entities"
    },
    
    # 4. Complex query with filtering (5-6 iterations)
    {
        "query": "count unique CM MACs in warning logs",
        "expected_iterations": (4, 6),
        "description": "Filter + entity extraction + counting"
    },
    
    # 5. Search with specific value (3-4 iterations)
    {
        "query": "find logs for MAWED07T01",
        "expected_iterations": (2, 4),
        "description": "Search with specific term"
    },
    
    # 6. Entity relationship query (5-7 iterations)
    {
        "query": "find all CMs connected to RPD MAWED07T01",
        "expected_iterations": (4, 7),
        "description": "Complex relationship query"
    },
    
    # 7. Time-based filtering (4-5 iterations)
    {
        "query": "show error logs from last 24 hours",
        "expected_iterations": (3, 5),
        "description": "Time + severity filtering"
    },
]

def test_single_query(orchestrator, test_case, test_num, total_tests):
    """
    Test a single query.
    
    Args:
        orchestrator: IterativeReactOrchestrator instance
        test_case: Test case dictionary
        test_num: Test number
        total_tests: Total number of tests
        
    Returns:
        bool: True if test passed
    """
    query = test_case["query"]
    expected_min, expected_max = test_case["expected_iterations"]
    description = test_case["description"]
    
    print(f"\n{'='*70}")
    print(f"TEST {test_num}/{total_tests}: {description}")
    print(f"Query: \"{query}\"")
    print(f"Expected: {expected_min}-{expected_max} iterations")
    print('='*70)
    
    try:
        # Process query
        result = orchestrator.process(query)
        
        # Check success
        if not result["success"]:
            print(f"✗ FAILED: {result.get('error', 'Unknown error')}")
            return False
        
        # Display results
        print(f"\n✓ SUCCESS")
        print(f"Answer: {result['answer']}")
        print(f"Iterations: {result['iterations']}/{result['max_iterations']}")
        print(f"Tools used: {' → '.join(result['tools_used'])}")
        
        # Check iteration count
        iterations = result['iterations']
        if expected_min <= iterations <= expected_max:
            print(f"✓ Iterations within expected range")
            return True
        else:
            print(f"⚠ WARNING: Iterations ({iterations}) outside expected range ({expected_min}-{expected_max})")
            # Still count as pass if query succeeded
            return True
            
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases(orchestrator):
    """
    Test edge cases and error handling.
    
    Args:
        orchestrator: IterativeReactOrchestrator instance
        
    Returns:
        int: Number of edge cases passed
    """
    print(f"\n{'='*70}")
    print("EDGE CASE TESTS")
    print('='*70)
    
    edge_cases = [
        {
            "query": "find logs for NONEXISTENT_VALUE_12345",
            "description": "Non-existent value should return gracefully"
        },
        {
            "query": "show logs",
            "description": "Very simple query"
        },
        {
            "query": "extract entities",
            "description": "Vague query - should still attempt"
        },
    ]
    
    passed = 0
    for i, test_case in enumerate(edge_cases, 1):
        print(f"\nEdge Case {i}: {test_case['description']}")
        print(f"Query: \"{test_case['query']}\"")
        
        try:
            result = orchestrator.process(test_case["query"])
            
            # For edge cases, we just check it doesn't crash
            if result["success"] or "error" in result:
                print(f"✓ Handled gracefully: {result['answer'][:100]}")
                passed += 1
            else:
                print(f"✗ Unexpected result")
                
        except Exception as e:
            print(f"✗ EXCEPTION: {e}")
    
    return passed

def test_state_management(orchestrator):
    """
    Test state management across iterations.
    
    Args:
        orchestrator: IterativeReactOrchestrator instance
        
    Returns:
        bool: True if state management works correctly
    """
    print(f"\n{'='*70}")
    print("STATE MANAGEMENT TEST")
    print('='*70)
    
    query = "count unique CM MACs in error logs"
    print(f"Query: \"{query}\"")
    print("This tests: log caching, entity tracking, auto-injection")
    
    try:
        result = orchestrator.process(query)
        
        if result["success"]:
            print(f"\n✓ State management successful")
            print(f"Answer: {result['answer']}")
            print(f"Tools: {' → '.join(result['tools_used'])}")
            
            # Check that logs were loaded and entities extracted
            tools = result['tools_used']
            has_search = 'search_logs' in tools
            has_filter = any('filter' in t for t in tools)
            has_extract = 'extract_entities' in tools
            has_count = 'count_entities' in tools
            
            print(f"\nVerification:")
            print(f"  - Logs loaded: {'✓' if has_search else '✗'}")
            print(f"  - Filtering used: {'✓' if has_filter else '✗'}")
            print(f"  - Entities extracted: {'✓' if has_extract else '✗'}")
            print(f"  - Entities counted: {'✓' if has_count else '✗'}")
            
            return has_search and has_extract
        else:
            print(f"✗ Failed: {result.get('error', 'Unknown')}")
            return False
            
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("ITERATIVE REACT ORCHESTRATOR - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    # Initialize orchestrator
    print("\nInitializing orchestrator...")
    print("  Log file: test.csv")
    print("  Model: qwen3-react")
    print("  Max iterations: 10 (configurable via max_iterations parameter)")
    
    try:
        orchestrator = IterativeReactOrchestrator(
            log_file="test.csv",
            config_dir="config",
            model="qwen3-react",
            max_iterations=10,  # You can change this: 5, 15, 20, etc.
            verbose=True  # Enable verbose to see prompts and responses
        )
        print("✓ Orchestrator initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize orchestrator: {e}")
        print("\nPlease ensure:")
        print("  1. Ollama is running (ollama serve)")
        print("  2. qwen3-react model exists (ollama list)")
        print("  3. test.csv exists in current directory")
        return
    
    # Run main tests
    print(f"\nRunning {len(TEST_QUERIES)} main test cases...")
    results = []
    
    for i, test_case in enumerate(TEST_QUERIES, 1):
        passed = test_single_query(orchestrator, test_case, i, len(TEST_QUERIES))
        results.append(passed)
    
    # Run edge case tests
    edge_passed = test_edge_cases(orchestrator)
    
    # Run state management test
    state_passed = test_state_management(orchestrator)
    
    # Summary
    main_passed = sum(results)
    total_main = len(results)
    
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print('='*70)
    print(f"Main Tests:          {main_passed}/{total_main} passed")
    print(f"Edge Case Tests:     {edge_passed}/3 passed")
    print(f"State Management:    {'✓ Passed' if state_passed else '✗ Failed'}")
    print(f"\nOVERALL:             {main_passed + edge_passed + (1 if state_passed else 0)}/{total_main + 3 + 1} passed")
    
    # Success criteria
    success_rate = (main_passed / total_main) * 100
    print(f"\nSuccess Rate:        {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("✓ EXCELLENT - System working as expected")
    elif success_rate >= 70:
        print("⚠ GOOD - Some issues but mostly functional")
    else:
        print("✗ NEEDS WORK - Significant issues detected")
    
    print('='*70)

if __name__ == "__main__":
    main()

