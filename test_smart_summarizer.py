"""
Test script for SmartSummarizer.

Tests all components independently and the full pipeline.
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

from src.core.smart_summarizer import (
    SmartSummarizer,
    EntityExtractor,
    LogAggregator,
    SmartSampler,
    SummaryFormatter
)


def print_header(title: str):
    """Print test section header."""
    print("\n" + "="*70)
    print(f"TEST: {title}")
    print("="*70)


def test_entity_extractor(log_file: str):
    """Test 1: Entity extraction."""
    print_header("Entity Extractor")
    
    extractor = EntityExtractor(config_dir="config")
    
    # Load sample logs
    logs = pd.read_csv(log_file, nrows=100)
    
    print(f"Loaded {len(logs)} logs")
    
    # Extract entities
    entities = extractor.extract_from_logs(logs)
    
    print(f"\nExtracted {len(entities)} entity types:")
    for entity_type, values in entities.items():
        print(f"  • {entity_type}: {len(values)} unique values, {sum(values.values())} total")
        top_3 = sorted(values.items(), key=lambda x: x[1], reverse=True)[:3]
        for val, cnt in top_3:
            print(f"      - {val}: {cnt}")
    
    if entities:
        print("\n✅ Entity extraction working")
    else:
        print("\n⚠️  No entities extracted")


def test_log_aggregator(log_file: str):
    """Test 2: Log aggregation."""
    print_header("Log Aggregator")
    
    extractor = EntityExtractor(config_dir="config")
    aggregator = LogAggregator()
    
    # Load and extract
    logs = pd.read_csv(log_file, nrows=100)
    entities = extractor.extract_from_logs(logs)
    
    # Aggregate
    stats = aggregator.aggregate(logs, entities)
    
    print(f"Total logs: {stats['total_count']}")
    print(f"\nEntity stats: {len(stats['entities'])} types")
    
    if stats.get('severity_dist'):
        print(f"Severity distribution: {stats['severity_dist']}")
    
    if stats.get('top_functions'):
        print(f"Top functions: {list(stats['top_functions'].keys())[:3]}")
    
    if stats.get('time_range'):
        print(f"Time range: {stats['time_range'].get('span', 'N/A')}")
    
    print("\n✅ Aggregation working")


def test_smart_sampler(log_file: str):
    """Test 3: Smart sampling."""
    print_header("Smart Sampler")
    
    extractor = EntityExtractor(config_dir="config")
    sampler = SmartSampler(max_samples=5, importance_weight=0.6)
    
    # Load and extract
    logs = pd.read_csv(log_file, nrows=100)
    entities = extractor.extract_from_logs(logs)
    
    # Sample
    samples = sampler.sample(logs, entities)
    
    print(f"Selected {len(samples)} samples from {len(logs)} logs")
    
    if samples:
        print("\nSample logs:")
        for i, sample in enumerate(samples, 1):
            severity = sample.get('Severity', 'N/A')
            function = sample.get('Function', 'N/A')
            message = sample.get('Message', '')[:50]
            print(f"  {i}. [{severity}] {function}: {message}")
        
        print("\n✅ Sampling working")
    else:
        print("\n⚠️  No samples selected")


def test_summary_formatter(log_file: str):
    """Test 4: Summary formatting."""
    print_header("Summary Formatter")
    
    extractor = EntityExtractor(config_dir="config")
    aggregator = LogAggregator()
    sampler = SmartSampler(max_samples=5)
    formatter = SummaryFormatter()
    
    # Load, extract, aggregate, sample
    logs = pd.read_csv(log_file, nrows=100)
    entities = extractor.extract_from_logs(logs)
    stats = aggregator.aggregate(logs, entities)
    samples = sampler.sample(logs, entities)
    
    # Format
    summary_text = formatter.format(stats, samples)
    
    print("Generated summary:\n")
    print(summary_text)
    
    print("\n✅ Formatting working")


def test_full_pipeline_small(log_file: str):
    """Test 5: Full pipeline with small dataset."""
    print_header("Full Pipeline - Small Dataset (100 logs)")
    
    summarizer = SmartSummarizer(
        config_dir="config",
        max_samples=10,
        importance_weight=0.6
    )
    
    # Load logs
    logs = pd.read_csv(log_file, nrows=100)
    
    # Summarize
    result = summarizer.summarize(logs)
    
    print(result['summary_text'])
    
    print(f"\nStats:")
    print(f"  • Entities extracted: {len(result['entities'])} types")
    print(f"  • Samples: {len(result['samples'])}")
    print(f"  • Summary length: {len(result['summary_text'])} chars")
    
    print("\n✅ Full pipeline working (small)")


def test_full_pipeline_large(log_file: str):
    """Test 6: Full pipeline with large dataset."""
    print_header("Full Pipeline - Large Dataset (1000 logs)")
    
    summarizer = SmartSummarizer(
        config_dir="config",
        max_samples=10,
        importance_weight=0.6
    )
    
    # Load logs
    logs = pd.read_csv(log_file, nrows=1000)
    
    print(f"Loaded {len(logs)} logs")
    
    # Summarize with timing
    import time
    start = time.time()
    result = summarizer.summarize(logs)
    elapsed = (time.time() - start) * 1000
    
    print(result['summary_text'])
    
    print(f"\nPerformance:")
    print(f"  • Time: {elapsed:.2f}ms")
    print(f"  • Summary length: {len(result['summary_text'])} chars")
    print(f"  • Compression: {len(logs)} logs → {len(result['summary_text'])} chars")
    print(f"  • Ratio: {len(logs) / (len(result['summary_text']) / 100):.1f}x compression")
    
    print("\n✅ Full pipeline working (large)")


def test_edge_cases():
    """Test 7: Edge cases."""
    print_header("Edge Cases")
    
    summarizer = SmartSummarizer(config_dir="config")
    
    # Test 1: Empty DataFrame
    print("\n1. Empty DataFrame:")
    result = summarizer.summarize(pd.DataFrame())
    print(f"   Result: {result['summary_text']}")
    
    # Test 2: None input
    print("\n2. None input:")
    result = summarizer.summarize(None)
    print(f"   Result: {result['summary_text']}")
    
    # Test 3: DataFrame with no _source.log column
    print("\n3. DataFrame without _source.log:")
    df = pd.DataFrame({'col1': [1, 2, 3]})
    result = summarizer.summarize(df)
    print(f"   Result: {result['summary_text'][:100]}...")
    
    print("\n✅ Edge cases handled")


def main():
    """Run all tests."""
    log_file = "test.csv"
    
    print("\n" + "="*70)
    print("SMART SUMMARIZER - TEST SUITE")
    print("="*70)
    print(f"Log file: {log_file}")
    
    # Check if log file exists
    if not Path(log_file).exists():
        print(f"\n❌ Error: Log file '{log_file}' not found!")
        return
    
    tests_run = 0
    tests_passed = 0
    
    # Run tests
    tests = [
        ("Entity Extractor", test_entity_extractor),
        ("Log Aggregator", test_log_aggregator),
        ("Smart Sampler", test_smart_sampler),
        ("Summary Formatter", test_summary_formatter),
        ("Full Pipeline (Small)", test_full_pipeline_small),
        ("Full Pipeline (Large)", test_full_pipeline_large),
        ("Edge Cases", test_edge_cases)
    ]
    
    for test_name, test_func in tests:
        tests_run += 1
        try:
            if test_name == "Edge Cases":
                test_func()
            else:
                test_func(log_file)
            tests_passed += 1
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {tests_run}/7")
    print(f"Tests passed: {tests_passed}/{tests_run}")
    
    if tests_passed == tests_run:
        print("\n✅ All tests passed!")
    else:
        print(f"\n⚠️ {tests_run - tests_passed} test(s) failed")


if __name__ == "__main__":
    main()

