"""
Test iterative ReAct with qwen3-loganalyzer
Just send query + history, no extra prompts
"""

import json
from src.llm.ollama_client import OllamaClient

queries = [
    "Find error logs for MAWED07T01 from last 24 hours",
    "Count unique CM MACs in warning logs"
]

def simulate_result(action: str) -> str:
    """Simulate tool result"""
    results = {
        "search_logs": "Found 150 logs",
        "filter_by_time": "Filtered to 80 logs",
        "filter_by_severity": "Filtered to 25 logs",
        "filter_by_field": "Filtered to 40 logs",
        "extract_entities": "Extracted 15 entities",
        "count_entities": "Count: 15 unique",
        "aggregate_entities": "Found 15 unique values",
        "find_entity_relationships": "Found 5 related entities",
        "normalize_term": "Normalized to: cm_mac",
        "fuzzy_search": "Found 8 matching logs",
        "get_log_count": "Total: 150 logs",
        "return_logs": "Displayed 5 sample logs",
        "finalize_answer": "DONE"
    }
    return results.get(action, "Executed")

def test_iterative():
    client = OllamaClient(model="qwen3-react")
    
    for idx, query in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {idx}: {query}")
        print('='*60)
        
        history = []
        
        for iteration in range(1, 5):  # max 4 iterations
            print(f"\n--- Iteration {iteration} ---")
            
            # Build simple message
            if history:
                msg = f"Query: {query}\n\nPrevious: {history}\n\nNext action?"
            else:
                msg = query
            
            print(f"Sending: {msg}\n")
            
            # Call LLM
            response = client.generate(msg)
            
            # Extract JSON (skip <think> tags)
            json_str = response
            if "<think>" in response:
                # Remove thinking process
                json_str = response.split("</think>")[-1].strip()
            
            print(f"LLM Response (thinking + JSON):\n{response[:200]}...\n")
            print(f"Extracted JSON: {json_str}\n")
            
            try:
                decision = json.loads(json_str)
                action = decision.get("action", "unknown")
                
                result = simulate_result(action)
                print(f"Simulated: {result}")
                
                history.append(f"{action} → {result}")
                
                if action == "finalize_answer":
                    print(f"\n✓ Done in {iteration} steps")
                    break
                    
            except:
                print("✗ Parse failed")
                break

if __name__ == "__main__":
    test_iterative()

