"""
Generate Ollama Modelfile for qwen3:8b with tool knowledge baked in.
Dynamically extracts tools and entity mappings from config.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.tools import create_all_tools
from src.utils.config import config


def generate_modelfile():
    """Generate Modelfile with all tool knowledge"""
    
    print("Generating Modelfile for qwen3:8b with tool knowledge...\n")
    
    # Get all tools
    tools = create_all_tools("test.csv")
    print(f"Found {len(tools)} tools")
    
    # Get entity mappings
    entity_data = config.entity_mappings
    aliases = entity_data.get("aliases", {})
    patterns = entity_data.get("patterns", {})
    
    # Build system prompt
    system_prompt = """You are an intelligent log analysis assistant.

Your job: Help users analyze logs by understanding their queries and suggesting which operations to perform.

"""
    
    # Add entity knowledge
    system_prompt += "ENTITY TYPES AND MAPPINGS:\n\n"
    
    if aliases:
        for entity_type, alias_list in aliases.items():
            user_terms = [a for a in alias_list if a.lower() != entity_type.lower()]
            if user_terms:
                system_prompt += f"• When user says '{', '.join(user_terms)}' → use entity type '{entity_type}'\n"
    
    system_prompt += f"\nAvailable entity types: {', '.join(patterns.keys())}\n\n"
    
    # Add tool knowledge
    system_prompt += "AVAILABLE TOOLS (operations you can suggest):\n\n"
    
    for tool in tools:
        system_prompt += f"**{tool.name}**\n"
        system_prompt += f"Purpose: {tool.description}\n"
        
        # List parameters (exclude 'logs' - auto-injected)
        params = [p for p in tool.parameters if p.name != 'logs']
        if params:
            system_prompt += "Parameters:\n"
            for param in params:
                req = "required" if param.required else "optional"
                system_prompt += f"  - {param.name} ({param.param_type.value}, {req})\n"
        system_prompt += "\n"
    
    system_prompt += """
OPERATION WORKFLOW RULES:

1. search_logs ALWAYS comes first (gets logs from file)
2. Filters work on searched logs (filter_by_time, filter_by_severity, filter_by_field)
3. Entity operations work on logs (extract_entities, count_entities, etc.)
4. Display operations show results (return_logs, finalize_answer)

IMPORTANT:
- 'logs' parameter is automatic - never mention it
- Use exact entity type names (cm_mac, not cm)
- Output valid JSON only
"""
    
    # Build Modelfile
    modelfile = f"""FROM qwen3:8b

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 8192

SYSTEM \"\"\"
{system_prompt}
\"\"\"
"""
    
    # Write to file
    output_file = "Modelfile.qwen3-loganalyzer"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(modelfile)
    
    print(f"\n✓ Generated: {output_file}")
    print(f"\nTo create custom model, run:")
    print(f"  ollama create qwen3-loganalyzer -f {output_file}")
    print(f"\nThen chat with it:")
    print(f"  ollama run qwen3-loganalyzer")
    
    return output_file


if __name__ == "__main__":
    generate_modelfile()

