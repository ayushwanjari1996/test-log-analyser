#!/usr/bin/env python
"""Simple test of the intelligent workflow orchestrator."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Fix Windows console encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.core.workflow_orchestrator import WorkflowOrchestrator
from src.core.llm_query_parser import LLMQueryParser
from src.core.log_processor import LogProcessor
from src.core.entity_manager import EntityManager
from src.llm.ollama_client import OllamaClient
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("="*70)
print("INTELLIGENT WORKFLOW ORCHESTRATOR - SIMPLE TEST")
print("="*70)

# Initialize components
print("\n1. Initializing components...")
processor = LogProcessor("test.csv")
entity_manager = EntityManager()
llm_client = OllamaClient()
query_parser = LLMQueryParser(llm_client)
orchestrator = WorkflowOrchestrator(processor, entity_manager, llm_client)
print("✓ All components initialized\n")

# Test queries
test_queries = [
    "find cm 10:e1:77:08:63:8a",
    "analyse logs for cm 10:e1:77:08:63:8a",
]

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}: {query}")
    print(f"{'='*70}\n")
    
    try:
        # Parse query
        print("→ Parsing query...")
        parsed = query_parser.parse_query(query)
        print(f"  Intent: {parsed.get('intent', 'unknown')}")
        print(f"  Query type: {parsed.get('query_type', 'unknown')}")
        
        # Execute workflow
        print("\n→ Executing intelligent workflow...")
        result = orchestrator.execute(query, parsed)
        
        # Display results
        print(f"\n{'─'*70}")
        print("RESULTS:")
        print(f"{'─'*70}")
        print(f"Success: {result.success}")
        print(f"Iterations: {result.iterations}")
        print(f"Logs analyzed: {result.logs_analyzed}")
        print(f"Methods used: {', '.join(result.methods_used)}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"\nAnswer: {result.answer}")
        
        if result.execution_trace:
            print(f"\nExecution trace:")
            for trace in result.execution_trace:
                print(f"  {trace['iteration']+1}. {trace['method']}: {trace['reasoning'][:60]}...")
        
        print(f"\n✓ Test {i} completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test {i} failed: {e}")
        import traceback
        traceback.print_exc()
    
    if i < len(test_queries):
        print(f"\n{'─'*70}\n")

print(f"\n{'='*70}")
print("ALL TESTS COMPLETED")
print(f"{'='*70}\n")

