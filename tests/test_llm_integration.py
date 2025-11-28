#!/usr/bin/env python
"""Test script for Phase 3 LLM integration."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.llm import OllamaClient, PromptBuilder, ResponseParser
from src.core.log_processor import LogProcessor
from src.core.chunker import LogChunker

console = Console()


def test_ollama_connection():
    """Test Ollama server connection."""
    console.print("\n[bold cyan]═══ Testing Ollama Connection ═══[/bold cyan]\n")
    
    console.print("[yellow]→ Initializing Ollama client...[/yellow]")
    client = OllamaClient()
    
    console.print("[yellow]→ Checking server health...[/yellow]")
    is_healthy = client.health_check()
    
    if is_healthy:
        console.print("[green]✓[/green] Ollama server is running")
        
        console.print("[yellow]→ Listing available models...[/yellow]")
        models = client.list_models()
        
        if models:
            console.print(f"[green]✓[/green] Found {len(models)} models:")
            for model in models[:5]:  # Show first 5
                console.print(f"  - {model}")
        else:
            console.print("[yellow]⚠[/yellow] No models found")
        
        return client
    else:
        console.print("[red]✗[/red] Ollama server is not accessible")
        console.print("[yellow]Make sure Ollama is running: ollama serve[/yellow]")
        return None


def test_prompt_builder():
    """Test prompt building."""
    console.print("\n[bold cyan]═══ Testing Prompt Builder ═══[/bold cyan]\n")
    
    console.print("[yellow]→ Initializing PromptBuilder...[/yellow]")
    builder = PromptBuilder()
    console.print("[green]✓[/green] PromptBuilder initialized")
    
    # Test FIND mode prompt
    console.print("\n[yellow]Testing FIND mode prompt:[/yellow]")
    sample_logs = "2024-01-01 10:00:00 | INFO | CM12345 registered\n2024-01-01 10:00:15 | ERROR | CM12345 timeout"
    
    system_prompt, user_prompt = builder.build_find_prompt(
        entity="CM12345",
        log_chunk=sample_logs
    )
    
    console.print(f"  System prompt length: {len(system_prompt)} chars")
    console.print(f"  User prompt length: {len(user_prompt)} chars")
    console.print(f"  Estimated tokens: {builder.estimate_prompt_tokens(user_prompt)}")
    
    # Test ANALYZE mode prompt
    console.print("\n[yellow]Testing ANALYZE mode prompt:[/yellow]")
    system_prompt, user_prompt = builder.build_analyze_prompt(
        user_query="Why did CM12345 fail?",
        log_chunk=sample_logs,
        focus_entities=["CM12345"]
    )
    
    console.print(f"  System prompt length: {len(system_prompt)} chars")
    console.print(f"  User prompt length: {len(user_prompt)} chars")
    
    # Test log formatting
    console.print("\n[yellow]Testing log formatting:[/yellow]")
    logs_list = [
        {"timestamp": "2024-01-01 10:00:00", "severity": "INFO", "message": "Test 1"},
        {"timestamp": "2024-01-01 10:00:15", "severity": "ERROR", "message": "Test 2"}
    ]
    formatted = builder.format_log_chunk(logs_list)
    console.print(f"  Formatted {len(logs_list)} log entries")
    
    # Show available modes
    modes = builder.get_available_modes()
    console.print(f"\n[green]✓[/green] Available modes: {', '.join(modes)}")
    
    return builder


def test_response_parser():
    """Test response parsing."""
    console.print("\n[bold cyan]═══ Testing Response Parser ═══[/bold cyan]\n")
    
    console.print("[yellow]→ Initializing ResponseParser...[/yellow]")
    parser = ResponseParser()
    console.print("[green]✓[/green] ResponseParser initialized")
    
    # Test FIND response parsing
    console.print("\n[yellow]Testing FIND response parsing:[/yellow]")
    find_response = {
        "entities_found": ["CM12345", "CM12346"],
        "next_entities": ["MdId:98765"],
        "relevant_logs": ["line 1", "line 2"],
        "mode_suggestion": "analyze"
    }
    
    parsed = parser.parse_find_response(find_response)
    console.print(f"[green]✓[/green] Parsed {len(parsed['entities_found'])} entities found")
    console.print(f"  Next entities: {parsed['next_entities']}")
    console.print(f"  Mode suggestion: {parsed['mode_suggestion']}")
    
    # Test ANALYZE response parsing
    console.print("\n[yellow]Testing ANALYZE response parsing:[/yellow]")
    analyze_response = {
        "observations": ["High error rate", "Network issues"],
        "patterns": ["Timeouts at 10:00"],
        "correlations": ["CM12345 → MdId:98765"],
        "next_entities": ["MdId:98765"],
        "confidence": 0.85,
        "mode_suggestion": "find"
    }
    
    parsed = parser.parse_analyze_response(analyze_response)
    console.print(f"[green]✓[/green] Parsed {len(parsed['observations'])} observations")
    console.print(f"  Patterns: {len(parsed['patterns'])}")
    console.print(f"  Confidence: {parsed['confidence']:.2f}")
    
    # Test merging responses
    console.print("\n[yellow]Testing response merging:[/yellow]")
    responses = [
        {"entities_found": ["CM1", "CM2"], "next_entities": ["MD1"], "relevant_logs": [], "mode_suggestion": "find"},
        {"entities_found": ["CM3"], "next_entities": ["MD1", "MD2"], "relevant_logs": [], "mode_suggestion": "find"}
    ]
    
    merged = parser.merge_responses(responses, mode="find")
    console.print(f"[green]✓[/green] Merged 2 responses")
    console.print(f"  Total entities found: {len(merged['entities_found'])}")
    console.print(f"  Unique next entities: {len(merged['next_entities'])}")
    
    return parser


def test_llm_generation(client: OllamaClient, builder: PromptBuilder, parser: ResponseParser):
    """Test actual LLM generation (if Ollama is available)."""
    console.print("\n[bold cyan]═══ Testing LLM Generation ═══[/bold cyan]\n")
    
    if not client:
        console.print("[yellow]⚠ Skipping LLM generation test (Ollama not available)[/yellow]")
        return
    
    # Simple test prompt
    console.print("[yellow]→ Testing simple text generation...[/yellow]")
    try:
        response = client.generate(
            prompt="Say 'Hello, I am working!' and nothing else.",
            temperature=0.1,
            max_tokens=50
        )
        console.print(f"[green]✓[/green] Generated response: {response[:100]}")
    except Exception as e:
        console.print(f"[red]✗[/red] Generation failed: {e}")
        return
    
    # Test JSON generation
    console.print("\n[yellow]→ Testing JSON generation...[/yellow]")
    try:
        json_prompt = """Generate a simple JSON object with these fields:
- status: "ok"
- message: "test successful"
- count: 42

Return ONLY the JSON, no other text."""
        
        json_response = client.generate_json(
            prompt=json_prompt,
            temperature=0.1
        )
        console.print(f"[green]✓[/green] Generated JSON with {len(json_response)} keys")
        console.print(f"  Keys: {list(json_response.keys())}")
    except Exception as e:
        console.print(f"[red]✗[/red] JSON generation failed: {e}")
        return
    
    # Test with actual log data
    console.print("\n[yellow]→ Testing with sample log data...[/yellow]")
    try:
        # Load sample logs
        processor = LogProcessor("tests/sample_logs/system.csv")
        logs = processor.read_all_logs()
        
        # Get CM12345 logs
        cm_logs = processor.filter_by_entity(logs, "entity_id", "CM12345")
        
        # Format for LLM
        log_dicts = cm_logs.to_dict('records')[:5]  # First 5 entries
        log_chunk = builder.format_log_chunk(log_dicts)
        
        # Build prompt
        system_prompt, user_prompt = builder.build_find_prompt(
            entity="CM12345",
            log_chunk=log_chunk
        )
        
        console.print(f"  Sending {len(log_chunk)} chars to LLM...")
        
        # Generate response
        llm_response = client.generate_json(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        # Parse response
        parsed = parser.parse_find_response(llm_response)
        
        console.print(f"[green]✓[/green] LLM analysis complete!")
        console.print(f"  Entities found: {parsed['entities_found']}")
        console.print(f"  Next entities: {parsed['next_entities']}")
        console.print(f"  Mode suggestion: {parsed['mode_suggestion']}")
        
        # Show relevant logs if any
        if parsed['relevant_logs']:
            console.print(f"\n[yellow]Relevant log insights:[/yellow]")
            for i, log in enumerate(parsed['relevant_logs'][:3], 1):
                console.print(f"  {i}. {log}")
    
    except Exception as e:
        console.print(f"[red]✗[/red] Log analysis failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all LLM integration tests."""
    console.print(Panel.fit(
        "[bold white]Phase 3: LLM Integration Tests[/bold white]\n"
        "[cyan]Testing Ollama Client, Prompts, and Response Parsing[/cyan]",
        border_style="blue"
    ))
    
    try:
        # Test Ollama connection
        client = test_ollama_connection()
        
        # Test prompt builder
        builder = test_prompt_builder()
        
        # Test response parser
        parser = test_response_parser()
        
        # Test LLM generation (if available)
        test_llm_generation(client, builder, parser)
        
        console.print("\n[bold green]═══ All Phase 3 Tests Completed! ═══[/bold green]\n")
        
        if not client:
            console.print("[yellow]Note: Start Ollama server to test LLM generation[/yellow]")
            console.print("[yellow]  Run: ollama serve[/yellow]")
        
        return 0
        
    except Exception as e:
        console.print(f"\n[bold red]Error during testing:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

