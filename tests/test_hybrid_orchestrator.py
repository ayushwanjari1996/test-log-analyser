"""
Test Hybrid Orchestrator - End-to-end tests
"""

import sys
sys.path.insert(0, '.')

from src.core import HybridOrchestrator

# Test queries
QUERIES = [
    # 1. Simple count
    "count all logs",
    
    # 2. Entity extraction with relationship
    "find all cms connected to rpd MAWED07T01",
    
    # 3. Severity filter
    "show error logs for MAWED07T01",
    
    # 4. Simple search + display
    "show logs containing 1c:93:7c:2a:72:c3",
    
    # 5. Entity counting
    "how many unique rpd are in the logs",
    
    # 6. Entity aggregation
    "list all unique md_id values",
    
    # 7. Combined query - errors with entity extraction
    "find cm_mac in error logs for rpd MAWED07T01",
]

def main():
    print("=" * 60)
    print("Testing Hybrid Orchestrator")
    print("=" * 60)
    
    # Initialize orchestrator
    print("\nInitializing orchestrator...")
    try:
        orchestrator = HybridOrchestrator(
            log_file="test.csv",
            model="qwen3-loganalyzer",
            verbose=False
        )
        print("✓ Orchestrator ready\n")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return
    
    # Run tests
    results = []
    for i, query in enumerate(QUERIES, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(QUERIES)}] {query}")
        print("=" * 60)
        
        try:
            result = orchestrator.process(query)
            
            print(f"\nNormalized: {result.get('normalized_query', 'N/A')}")
            print(f"Search value: {result.get('search_value', 'N/A')}")
            print(f"Plan: {result.get('plan', {})}")
            print(f"\nAnswer: {result['answer']}")
            print(f"Success: {result['success']}")
            
            results.append(result['success'])
            
        except Exception as e:
            print(f"✗ Error: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{len(QUERIES)} passed")
    print("=" * 60)

if __name__ == "__main__":
    main()

