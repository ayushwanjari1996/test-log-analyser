"""
Quick test to see what qwen3-react model is outputting.
This helps debug JSON generation issues.
"""

import sys
sys.path.insert(0, '.')

from src.llm.ollama_client import OllamaClient

def test_model_output():
    """Test what the model actually generates."""
    print("=" * 70)
    print("Testing qwen3-react model output")
    print("=" * 70)
    
    client = OllamaClient(model="qwen3-react")
    
    # Simple test prompt matching our actual usage
    prompt = """You are analyzing logs to answer a query. Decide the NEXT action.

QUERY: count all logs
ITERATION: 1/10

PREVIOUS ACTIONS: None (first iteration)

CURRENT STATE:
  No logs loaded

DECISION POINT:
- Have you gathered enough data to answer the query?
  YES → Call finalize_answer with the final answer
  NO → Call the next tool needed

Return JSON in this exact format:
{
  "reasoning": "explain why this action is needed",
  "action": "tool_name",
  "params": {parameter dict}
}

AVAILABLE TOOLS (13 tools):

1. search_logs - Search/filter logs by keyword
   Description: Search/filter logs by keyword or pattern
   Parameters:
     - value (string, required): Search term or keyword
     - field (string, optional): Field to search in (default: message)

2. finalize_answer - Finish and return answer
   Description: Finalize the analysis and return the answer
   Parameters:
     - answer (string, required): Final answer to return
"""
    
    print("\nSending prompt...")
    print("-" * 70)
    print(prompt[:300] + "...")
    print("-" * 70)
    
    try:
        # Test WITHOUT format_json (let Modelfile handle it)
        print("\nTest 1: Without format_json flag (relying on Modelfile system prompt)")
        response = client.generate(
            prompt=prompt,
            format_json=False,
            temperature=0.3
        )
        
        print(f"\nResponse length: {len(response)} chars")
        print("-" * 70)
        print("Full response:")
        print(response)
        print("-" * 70)
        
        # Test WITH format_json
        print("\n\nTest 2: With format_json=True flag")
        response2 = client.generate(
            prompt=prompt,
            format_json=True,
            temperature=0.3
        )
        
        print(f"\nResponse length: {len(response2)} chars")
        print("-" * 70)
        print("Full response:")
        print(response2)
        print("-" * 70)
        
        # Try to parse both
        import json
        
        print("\n\nParsing attempts:")
        for i, resp in enumerate([response, response2], 1):
            print(f"\nTest {i}:")
            try:
                parsed = json.loads(resp)
                print(f"  ✓ Direct parse successful: {list(parsed.keys())}")
            except:
                print(f"  ✗ Direct parse failed")
                
                # Try finding JSON
                import re
                try:
                    start = resp.index('{')
                    end = resp.rindex('}') + 1
                    json_str = resp[start:end]
                    parsed = json.loads(json_str)
                    print(f"  ✓ Extracted parse successful: {list(parsed.keys())}")
                except:
                    print(f"  ✗ Extraction failed")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_model_output()

