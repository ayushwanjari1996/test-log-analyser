"""
Test Qwen3 Log Analyzer - Plan Generation
Tests if the model can generate valid JSON plans for 10 diverse queries.
"""

import requests
import json

MODEL = "qwen3-loganalyzer"
BASE_URL = "http://localhost:11434"

QUERIES = [
    # 1. Simple count
    "count all logs",
    
    # 2. Entity extraction with relationship
    "find all cm_mac connected to rpdname MAWED07T01",
    
    # 3. Severity filter
    "show error logs for MAWED07T01",
    
    # 4. Simple search + display
    "show logs containing 1c:93:7c:2a:72:c3",
    
    # 5. Entity counting
    "how many unique rpdname are in the logs",
    
    # 6. Time filter
    "show logs from last 1 hour",
    
    # 7. Error analysis
    "analyze issues for cm_mac 28:7a:ee:c9:66:4a",
    
    # 8. Multiple severity filter
    "find warning and error logs",
    
    # 9. Entity aggregation
    "list all unique md_id values",
    
    # 10. Combined query
    "find cm_mac in error logs for rpdname MAWED07T01",
]

def ask_llm(query: str) -> str:
    """Send query to LLM and get response."""
    prompt = f'Query: "{query}"\nOutput JSON plan: {{"operations": [...], "params": {{...}}}}'
    
    response = requests.post(
        f"{BASE_URL}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False}
    )
    
    if response.status_code != 200:
        return f"ERROR: {response.status_code}"
    
    return response.json().get("response", "")

def extract_json(text: str) -> dict:
    """Try to extract JSON from response."""
    # Remove thinking tags if present
    if "<think>" in text:
        text = text.split("</think>")[-1]
    
    text = text.strip()
    
    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass
    
    # Try to find JSON in text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except:
            pass
    
    return None

def validate_plan(plan: dict) -> tuple:
    """Check if plan is valid. Returns (is_valid, issues)."""
    issues = []
    
    if not plan:
        return False, ["Could not parse JSON"]
    
    if "operations" not in plan:
        issues.append("Missing 'operations' key")
    elif not isinstance(plan["operations"], list):
        issues.append("'operations' is not a list")
    elif len(plan["operations"]) == 0:
        issues.append("'operations' is empty")
    elif plan["operations"][0] != "search_logs":
        issues.append(f"First op should be 'search_logs', got '{plan['operations'][0]}'")
    
    if "params" not in plan:
        issues.append("Missing 'params' key")
    
    return len(issues) == 0, issues

def main():
    print("=" * 60)
    print("Testing Qwen3 Log Analyzer Plan Generation")
    print("=" * 60)
    
    results = []
    
    for i, query in enumerate(QUERIES, 1):
        print(f"\n[{i}/10] {query}")
        
        response = ask_llm(query)
        plan = extract_json(response)
        is_valid, issues = validate_plan(plan)
        
        if is_valid:
            print(f"  OK: {json.dumps(plan, separators=(',', ':'))}")
            results.append(True)
        else:
            print(f"  FAIL: {', '.join(issues)}")
            if plan:
                print(f"  Plan: {plan}")
            else:
                print(f"  Raw: {response[:200]}...")
            results.append(False)
    
    # Summary
    passed = sum(results)
    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed}/10 passed")
    print("=" * 60)
    
    if passed < 10:
        print("\nFailed queries:")
        for i, (q, r) in enumerate(zip(QUERIES, results), 1):
            if not r:
                print(f"  {i}. {q}")

if __name__ == "__main__":
    main()

