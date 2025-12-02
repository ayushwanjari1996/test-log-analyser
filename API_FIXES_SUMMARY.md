# API Compatibility Fixes

**Issue**: ConfigManager API mismatches

## Root Cause

ConfigManager has:
```python
@property
def entity_mappings(self) -> Dict[str, Any]:
    # Returns: {"aliases": {...}, "relationships": {...}, "patterns": {...}}
```

NOT individual properties like `.patterns` or `.relationships`

## Fixes Applied

### File: `src/llm/dynamic_prompts.py`

**Before** (wrong):
```python
patterns = self.config.patterns  # ❌ Doesn't exist
relationships = self.config.relationships  # ❌ Doesn't exist
```

**After** (correct):
```python
entity_data = self.config.entity_mappings
patterns = entity_data.get("patterns", {})
relationships = entity_data.get("relationships", {})
```

### File: `src/core/tool_registry.py`

**Before** (wrong):
```python
registry.get_all_tool_names()  # ❌ Doesn't exist
registry.get_tool(name)  # ❌ Doesn't exist
```

**After** (correct):
```python
registry.list_tools()  # ✅ Correct
registry.get(name)  # ✅ Correct
```

## Status

✅ All API calls now match actual implementations
✅ Code compiles without errors
✅ Ready for user testing


