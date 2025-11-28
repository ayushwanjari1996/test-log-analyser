# Phase 4: Intelligent Query Parsing & Entity Resolution

## Problem Statement

The system needs to understand the difference between:
1. **Entity Type** (e.g., "cm", "modem", "rpdname") - search for the pattern
2. **Entity Value** (e.g., "CM12345", "x", "192.168.1.1") - search for specific instance
3. **Aggregation Requests** (e.g., "all cms", "list modems") - collect all instances

## Query Types & Examples

### Type 1: Specific Entity Value Search
**Pattern:** "find {entity_type} {specific_value}"

```
Examples:
- "find cm CM12345"
- "find rpdname connected to cm x"  ← Search for value "x", not pattern "cm"
- "show logs for modem CM12346"
- "trace IP 192.168.1.100"

Logic:
1. Detect entity type keyword (cm, modem, rpdname, ip)
2. Extract specific value after it
3. Search logs for that VALUE, not the pattern
4. If "connected to X": first find X, then find related entities
```

### Type 2: Entity Type Pattern Search
**Pattern:** "find all {entity_type}"

```
Examples:
- "find all cms"
- "list all modems"
- "show all IP addresses"
- "get all rpdnames"

Logic:
1. Detect "all" + entity type
2. Use regex patterns to extract ALL instances
3. Aggregate and deduplicate
4. Return list with counts
```

### Type 3: Relationship Queries
**Pattern:** "find {entity_type_1} connected to {entity_type_2} {value}"

```
Examples:
- "find rpdname connected to cm x"
  → First find logs with "x"
  → Then extract rpdname from those logs
  
- "find all cms connected to rpdname RPD123"
  → First find logs with "RPD123"
  → Then extract all cm values from those logs
  
- "show modems connected to IP 192.168.1.1"
  → First find logs with IP
  → Then extract modem IDs

Logic:
1. Parse: find A connected to B value
2. Search for B value first (primary search)
3. Extract A from those filtered logs
4. Return relationship mapping
```

### Type 4: Pattern Analysis
**Pattern:** "why", "what caused", "analyze"

```
Examples:
- "why did cm x fail"
  → Search for value "x"
  → Root cause analysis

- "what caused errors for modem CM12345"
  → Search for value "CM12345"
  → Analyze error patterns

Logic:
1. Extract entity value (not type)
2. Perform root cause analysis on that value
```

### Type 5: Aggregation with Attributes
**Pattern:** "find all {entity_type} {with_attribute}"

```
Examples:
- "find all cms with errors"
  → Extract all CM values
  → Filter to only those with ERROR severity
  
- "list modems with timeouts"
  → Extract all modem values
  → Filter logs containing "timeout"
  
- "show all IPs with high latency"
  → Extract all IP values
  → Filter logs containing "latency"

Logic:
1. Extract all instances of entity type
2. Apply filter condition
3. Return filtered list
```

## Query Parser Implementation

```python
class QueryParser:
    """
    Intelligently parse user queries to determine:
    1. Query type (specific value, pattern, relationship, analysis)
    2. Entity types vs entity values
    3. Primary vs secondary entities
    4. Filter conditions
    """
    
    def __init__(self):
        self.entity_keywords = {
            "cm": ["cm", "cable modem", "modem"],
            "md_id": ["mdid", "modem_id", "modemid"],
            "rpdname": ["rpd", "rpdname", "rpd name"],
            "ip_address": ["ip", "ip address"],
            "mac_address": ["mac", "mac address"]
        }
        
        self.relationship_keywords = [
            "connected to", "related to", "associated with", 
            "linked to", "for", "with"
        ]
        
        self.aggregation_keywords = [
            "all", "list", "show all", "get all", "find all"
        ]
        
        self.analysis_keywords = [
            "why", "cause", "reason", "analyze", "investigate"
        ]
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse query and return structured information.
        
        Returns:
            {
                "query_type": "specific_value" | "pattern_search" | "relationship" | "analysis" | "aggregation",
                "primary_entity": {"type": "cm", "value": "CM12345"},
                "secondary_entity": {"type": "rpdname", "value": None},
                "filter_conditions": ["errors", "timeout"],
                "mode": "find" | "analyze" | "trace"
            }
        """
        query_lower = query.lower().strip()
        
        # Detect query type
        if any(keyword in query_lower for keyword in self.analysis_keywords):
            return self._parse_analysis_query(query_lower)
        
        if any(keyword in query_lower for keyword in self.relationship_keywords):
            return self._parse_relationship_query(query_lower)
        
        if any(keyword in query_lower for keyword in self.aggregation_keywords):
            return self._parse_aggregation_query(query_lower)
        
        # Default: specific value search
        return self._parse_specific_query(query_lower)
    
    def _parse_specific_query(self, query: str) -> Dict[str, Any]:
        """
        Parse: "find cm CM12345"
        Parse: "show logs for modem x"
        """
        entity_type, entity_value = self._extract_entity_and_value(query)
        
        return {
            "query_type": "specific_value",
            "primary_entity": {
                "type": entity_type,
                "value": entity_value
            },
            "secondary_entity": None,
            "filter_conditions": [],
            "mode": "find"
        }
    
    def _parse_aggregation_query(self, query: str) -> Dict[str, Any]:
        """
        Parse: "find all cms"
        Parse: "list all modems with errors"
        """
        # Extract entity type
        entity_type = None
        for etype, keywords in self.entity_keywords.items():
            if any(kw in query for kw in keywords):
                entity_type = etype
                break
        
        # Extract filter conditions
        filters = []
        filter_keywords = ["error", "timeout", "fail", "warning", "critical"]
        for keyword in filter_keywords:
            if keyword in query:
                filters.append(keyword)
        
        return {
            "query_type": "aggregation",
            "primary_entity": {
                "type": entity_type,
                "value": None  # None means search for ALL instances
            },
            "secondary_entity": None,
            "filter_conditions": filters,
            "mode": "find"
        }
    
    def _parse_relationship_query(self, query: str) -> Dict[str, Any]:
        """
        Parse: "find rpdname connected to cm x"
        Parse: "show all cms related to rpdname RPD123"
        
        Logic:
        1. Split on relationship keyword
        2. Left side = what we want to find (target entity type)
        3. Right side = what we search for (source entity value)
        """
        # Find relationship keyword
        rel_keyword = None
        for kw in self.relationship_keywords:
            if kw in query:
                rel_keyword = kw
                break
        
        if not rel_keyword:
            return self._parse_specific_query(query)
        
        # Split query
        parts = query.split(rel_keyword)
        target_part = parts[0].strip()  # "find rpdname"
        source_part = parts[1].strip()  # "cm x"
        
        # Extract target entity type (what we want to find)
        target_type = None
        for etype, keywords in self.entity_keywords.items():
            if any(kw in target_part for kw in keywords):
                target_type = etype
                break
        
        # Extract source entity type and value (what we search for)
        source_type, source_value = self._extract_entity_and_value(source_part)
        
        return {
            "query_type": "relationship",
            "primary_entity": {
                "type": target_type,
                "value": None  # We'll extract this after finding source
            },
            "secondary_entity": {
                "type": source_type,
                "value": source_value  # This is what we search for FIRST
            },
            "filter_conditions": [],
            "mode": "find"
        }
    
    def _parse_analysis_query(self, query: str) -> Dict[str, Any]:
        """
        Parse: "why did cm x fail"
        Parse: "what caused errors for modem CM12345"
        """
        # Extract entity value (not type)
        entity_type, entity_value = self._extract_entity_and_value(query)
        
        return {
            "query_type": "analysis",
            "primary_entity": {
                "type": entity_type,
                "value": entity_value  # Specific value for analysis
            },
            "secondary_entity": None,
            "filter_conditions": [],
            "mode": "analyze"
        }
    
    def _extract_entity_and_value(self, text: str) -> Tuple[str, str]:
        """
        Extract entity type and value from text.
        
        Examples:
        - "cm CM12345" → ("cm", "CM12345")
        - "modem x" → ("cm", "x")
        - "ip 192.168.1.1" → ("ip_address", "192.168.1.1")
        - "CM12345" → ("cm", "CM12345")  # Detect from pattern
        
        Logic:
        1. Check if text contains entity keyword + value
        2. If yes, extract both
        3. If no keyword, try to match value against patterns
        """
        import re
        
        # Method 1: Keyword + Value
        for etype, keywords in self.entity_keywords.items():
            for keyword in keywords:
                # Look for pattern: "keyword value"
                pattern = rf'\b{re.escape(keyword)}\s+(\S+)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    return etype, value
        
        # Method 2: Pattern matching (no keyword)
        # Try to identify entity type from value pattern
        from ..utils.config import config
        
        for etype in self.entity_keywords.keys():
            patterns = config.get_entity_pattern(etype)
            for pattern in patterns:
                regex = re.compile(pattern, re.IGNORECASE)
                matches = regex.findall(text)
                if matches:
                    value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    return etype, value
        
        # Method 3: Last word might be the value
        words = text.split()
        if words:
            return "unknown", words[-1]
        
        return "unknown", None
    
    def should_search_value(self, parsed: Dict[str, Any]) -> bool:
        """
        Determine if we should search for specific value or pattern.
        
        Returns True if we should search for the VALUE
        Returns False if we should search for the PATTERN
        """
        if parsed["query_type"] == "aggregation":
            return False  # Search pattern to find all instances
        
        if parsed["primary_entity"]["value"] is not None:
            return True  # Have specific value, search for it
        
        return False  # No value specified, search pattern
```

## Execution Strategy Based on Query Type

### Strategy 1: Specific Value Search
```python
def execute_specific_value_search(self, parsed: Dict) -> Dict:
    """
    Execute: "find cm CM12345"
    
    Steps:
    1. Load logs
    2. Search for EXACT VALUE "CM12345" in all columns
    3. Don't use regex patterns, use direct string search
    4. Chunk and analyze
    """
    entity_value = parsed["primary_entity"]["value"]
    
    # Direct value search, NOT pattern search
    logs = self.processor.read_all_logs()
    
    # Search in all text columns
    filtered = self.processor.search_text(logs, entity_value)
    
    # Process with LLM
    return self._process_entity_lookup(entity_value, filtered)
```

### Strategy 2: Aggregation Search
```python
def execute_aggregation_search(self, parsed: Dict) -> Dict:
    """
    Execute: "find all cms"
    
    Steps:
    1. Load logs
    2. Use REGEX PATTERN to extract all CM values
    3. Aggregate and count
    4. Optionally apply filters
    """
    entity_type = parsed["primary_entity"]["type"]
    filters = parsed["filter_conditions"]
    
    logs = self.processor.read_all_logs()
    
    # Use pattern extraction
    entities = self.processor.extract_entities(logs, entity_type)
    
    # Apply filters if specified
    if filters:
        filtered_entities = {}
        for entity_value, indices in entities.items():
            entity_logs = logs.iloc[indices]
            # Check if any log matches filter
            has_filter = any(
                entity_logs.astype(str).apply(
                    lambda row: any(f in str(row).lower() for f in filters)
                ).any()
            )
            if has_filter:
                filtered_entities[entity_value] = indices
        entities = filtered_entities
    
    return {
        "query_type": "aggregation",
        "entity_type": entity_type,
        "total_found": len(entities),
        "entities": list(entities.keys()),
        "entity_counts": {k: len(v) for k, v in entities.items()},
        "filters_applied": filters
    }
```

### Strategy 3: Relationship Search
```python
def execute_relationship_search(self, parsed: Dict) -> Dict:
    """
    Execute: "find rpdname connected to cm x"
    
    Steps:
    1. Search for SOURCE entity value FIRST (cm x)
    2. Filter logs to only those containing source value
    3. Extract TARGET entity from filtered logs (rpdname)
    4. Return relationship mapping
    """
    target_type = parsed["primary_entity"]["type"]  # rpdname
    source_type = parsed["secondary_entity"]["type"]  # cm
    source_value = parsed["secondary_entity"]["value"]  # x
    
    logs = self.processor.read_all_logs()
    
    # Step 1: Find logs containing source value
    source_logs = self.processor.search_text(logs, source_value)
    
    if len(source_logs) == 0:
        return {
            "error": f"No logs found for {source_type} {source_value}",
            "suggestions": self._suggest_similar_entities(source_value)
        }
    
    # Step 2: Extract target entity from source logs
    target_entities = self.processor.extract_entities(source_logs, target_type)
    
    return {
        "query_type": "relationship",
        "source": {"type": source_type, "value": source_value},
        "target": {"type": target_type, "values": list(target_entities.keys())},
        "total_connections": len(target_entities),
        "log_count": len(source_logs),
        "relationship": {
            f"{source_value}": list(target_entities.keys())
        }
    }
```

### Strategy 4: Analysis Query
```python
def execute_analysis_query(self, parsed: Dict) -> Dict:
    """
    Execute: "why did cm x fail"
    
    Steps:
    1. Search for SPECIFIC VALUE (x)
    2. Perform root cause analysis on those logs
    3. Use iterative exploration
    """
    entity_value = parsed["primary_entity"]["value"]
    
    # Search for the value, not the pattern
    logs = self.processor.read_all_logs()
    filtered = self.processor.search_text(logs, entity_value)
    
    # Root cause analysis
    return self.root_cause_analysis(
        query=f"Why did {entity_value} fail?",
        logs=filtered
    )
```

## Complete Query Handling Flow

```python
class LogAnalyzer:
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Main entry point - intelligently handles any query.
        """
        # 1. Parse query
        parser = QueryParser()
        parsed = parser.parse_query(query)
        
        logger.info(f"Parsed query: {parsed}")
        
        # 2. Route to appropriate handler
        if parsed["query_type"] == "specific_value":
            return self.execute_specific_value_search(parsed)
        
        elif parsed["query_type"] == "aggregation":
            return self.execute_aggregation_search(parsed)
        
        elif parsed["query_type"] == "relationship":
            return self.execute_relationship_search(parsed)
        
        elif parsed["query_type"] == "analysis":
            return self.execute_analysis_query(parsed)
        
        else:
            # Fallback: treat as specific value search
            return self.execute_specific_value_search(parsed)
```

## Test Cases

```python
# Test Case 1: Specific Value
query = "find cm CM12345"
parsed = parser.parse_query(query)
assert parsed["query_type"] == "specific_value"
assert parsed["primary_entity"]["value"] == "CM12345"
# Should search for VALUE "CM12345", not pattern

# Test Case 2: Value with single letter
query = "find cm x"
parsed = parser.parse_query(query)
assert parsed["primary_entity"]["value"] == "x"
# Should search for VALUE "x", not pattern "cm"

# Test Case 3: Aggregation
query = "find all cms"
parsed = parser.parse_query(query)
assert parsed["query_type"] == "aggregation"
assert parsed["primary_entity"]["value"] is None
# Should use PATTERN to extract all CMs

# Test Case 4: Relationship
query = "find rpdname connected to cm x"
parsed = parser.parse_query(query)
assert parsed["query_type"] == "relationship"
assert parsed["secondary_entity"]["value"] == "x"  # Search for THIS first
assert parsed["primary_entity"]["type"] == "rpdname"  # Extract THIS from results

# Test Case 5: Aggregation with Filter
query = "find all cms with errors"
parsed = parser.parse_query(query)
assert parsed["query_type"] == "aggregation"
assert "error" in parsed["filter_conditions"]

# Test Case 6: Analysis
query = "why did cm x fail"
parsed = parser.parse_query(query)
assert parsed["query_type"] == "analysis"
assert parsed["primary_entity"]["value"] == "x"
# Should search for VALUE "x" and analyze

# Test Case 7: Relationship with Full Value
query = "find rpdname connected to cm CM12345"
parsed = parser.parse_query(query)
assert parsed["secondary_entity"]["value"] == "CM12345"
# Should search for "CM12345" not pattern
```

## Edge Cases Handled

1. **Ambiguous Queries**
   - "find cm" → Treat as aggregation (find all cms)
   - "find CM12345" → Detect from pattern, specific value search

2. **Multiple Entity Types**
   - "find cm and rpdname for x" → Extract both types from logs with x

3. **Typos/Variations**
   - "modem" = "cm" = "cable modem" (use aliases)
   - Case insensitive matching

4. **Complex Relationships**
   - "find all cms connected to rpdname RPD123 with errors"
   - Parse: relationship + aggregation + filter

5. **Missing Values**
   - "find connected to cm" → Error, ask for value
   - Provide helpful error message

## Summary

**Key Principle:** 
- Entity TYPE → Use regex PATTERN to extract
- Entity VALUE → Search for EXACT STRING

**Smart Routing:**
```
Query → Parser → Determine Type → Route to Handler
    ↓
specific_value → Search for VALUE → Entity Lookup
aggregation → Search with PATTERN → Extract All → Aggregate
relationship → Search SOURCE value → Extract TARGET type
analysis → Search VALUE → Root Cause Analysis
```

This ensures queries like "find rpdname connected to cm x" correctly:
1. Search for VALUE "x" (not pattern "cm")
2. Then extract rpdname TYPE from those logs

