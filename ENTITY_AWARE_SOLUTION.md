# Entity-Aware Field Grouping - Implementation

## Problem Solved

**Before:**
- Hint: "Parse 'Role' field" ❌ (wrong field, not related to CPE)
- LLM confused about which field to use

**After:**
- Fields grouped by entity type (CPE, CM, RPD, etc.)
- Hint: "CPE fields: CpeMacAddress, CpeIpAddress - parse the one that identifies devices" ✓
- LLM sees grouped options + samples → makes correct choice

---

## Implementation

### 1. Created `EntityFieldMapper` (`src/core/entity_field_mapper.py`)

**Purpose:** Load `entity_mappings.yaml` and provide:
- Field name → Entity type mapping
- Query keyword → Entity detection  
- Field grouping by entity category

**Key Methods:**
```python
# Map field to entity type
get_entity_type("CpeMacAddress") → "cpe"

# Group fields by entity
group_fields_by_entity(["CpeMacAddress", "CmMacAddress", "Severity"])
→ {
    "cpe": ["CpeMacAddress"],
    "cm": ["CmMacAddress"],  
    "other": ["Severity"]
  }

# Detect entities in query
detect_entities_in_query("count unique CPE devices") → {"cpe"}
```

---

### 2. Updated `ContextBuilder` (`src/core/context_builder.py`)

#### **Changed: Field Display (Grouped by Entity)**

**Before:**
```
Available fields: CpeMacAddress, Role, CmMacAddress, Severity, ...
```

**After:**
```
Available fields (grouped by entity):
  CPE: CpeMacAddress, CpeIpAddress
  CM: CmMacAddress, MdId
  Rpdname: RpdName, RpdIpAddress
  System/Other: Role, Severity, Package, ...
```

#### **Changed: Smart Hints (Entity-Aware)**

**Before:**
```
💡 HINT: Parse 'Role' field  ❌ Wrong!
```

**After:**
```
💡 HINT: Query asks for unique CPE values.
         Available CPE fields: CpeMacAddress, CpeIpAddress
         Parse the field that uniquely identifies CPE devices.
```

**LLM Decision Process:**
1. Sees query mentions "CPE devices"
2. Sees hint points to CPE fields
3. Sees samples showing `"CpeMacAddress": "2c:ab:a4:47:1a:d2"`
4. Reasons: MAC address uniquely identifies devices
5. Chooses: `parse_json_field(logs, "CpeMacAddress")` ✓

---

## How Entity Mappings Work

### From `entity_mappings.yaml`:

```yaml
aliases:
  cpe:
    - "CPE"
    - "customer premise equipment"  
    - "CpeMacAddress"    ← Field name
    - "CpeIpAddress"     ← Field name
    
  cm:
    - "cable modem"
    - "CM"
    - "CmMacAddress"     ← Field name
    - "MdId"             ← Field name
```

### Mapper Logic:

1. **Load mappings** → build reverse index:
   ```
   "CpeMacAddress" → "cpe"
   "CpeIpAddress" → "cpe"
   "CmMacAddress" → "cm"
   "MdId" → "cm"
   ```

2. **Detect in query** → "CPE devices" matches alias "CPE" → entity type "cpe"

3. **Find available fields** → check which CPE fields exist in logs → ["CpeMacAddress"]

4. **Show grouped** → display by entity category

---

## Generic & Extensible

**Adding new entity:**
```yaml
# In entity_mappings.yaml, just add:
aliases:
  new_entity:
    - "alias1"
    - "FieldName1"
    - "FieldName2"
```

**No code changes needed!** System automatically:
- ✅ Maps field names to entity type
- ✅ Groups fields in display
- ✅ Detects entity in queries
- ✅ Generates appropriate hints

---

## Expected Flow (After Implementation)

**Query:** "count total number of cpe devices"

### Iteration 1: Search
```
LLM: grep_logs("CpeMacAddress")
→ [RAW DATA] Found 39 log entries - may contain duplicates
```

### Iteration 2: LLM Sees
```
CURRENT STATE:
  Logs: 39 entries
  
  Sample:
    {"CpeMacAddress": "2c:ab:a4:47:1a:d2", "MdId": "0x2040000", ...}
  
  Available fields (grouped by entity):
    CPE: CpeMacAddress, CpeIpAddress
    CM: CmMacAddress, MdId
    System/Other: Role, Severity, ...
  
  💡 HINT: Query asks for unique CPE values.
           Available CPE fields: CpeMacAddress, CpeIpAddress
           Parse the field that uniquely identifies CPE devices.
```

**LLM Decision:**
```json
{
  "reasoning": "CPE devices are uniquely identified by MAC address",
  "action": "parse_json_field",
  "params": {"field_name": "CpeMacAddress"}
}
```
✅ **Correct!**

### Iteration 3: Extract
```
→ [RAW DATA] Extracted 39 raw values - may contain duplicates

Extracted fields:
  - CpeMacAddress: 39 raw values (may have duplicates)

💡 HINT: Query needs unique count. Next: count_values(values)
```

### Iteration 4: Count
```
LLM: count_values(values)
→ [FINAL COUNT] 15 unique values
```

### Iteration 5: Answer
```
LLM: finalize_answer("15 unique CPE devices")
```

---

## Files Modified

1. **`src/core/entity_field_mapper.py`** (NEW)
   - ~150 lines
   - Generic entity mapping logic
   
2. **`src/core/context_builder.py`** (UPDATED)
   - Import EntityFieldMapper
   - Update field display to show grouped by entity
   - Update hints to be entity-aware

**Total:** ~180 lines added, 0 breaking changes

---

## Why This Solution is "Truly Smart"

✅ **Generic** - No hardcoded queries or fields  
✅ **Extensible** - Add new entities via YAML only  
✅ **Context-Aware** - Hints adapt to query + available data  
✅ **Self-Documenting** - Grouped display shows relationships  
✅ **LLM-Friendly** - Shows options, lets LLM reason and choose  

**The system understands entity relationships from configuration, not code.**


