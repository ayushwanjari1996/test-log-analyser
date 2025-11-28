"""Intelligent query parsing for natural language log queries."""

import re
from typing import Dict, Any, Tuple, List, Optional
from ..utils.logger import setup_logger
from ..utils.config import config

logger = setup_logger()


class QueryParser:
    """
    Parse natural language queries to understand user intent.
    
    Distinguishes between:
    - Entity types (patterns) vs entity values (specific instances)
    - Different query types (specific, aggregation, relationship, analysis)
    - Primary vs secondary entities
    """
    
    def __init__(self):
        """Initialize query parser with entity mappings."""
        self.entity_keywords = {
            "cm": ["cm", "cable modem", "modem", "cablemodem"],
            "md_id": ["mdid", "modem_id", "modemid", "md-id", "md id"],
            "rpdname": ["rpd", "rpdname", "rpd name", "remote phy"],
            "ip_address": ["ip", "ip address", "ipaddress"],
            "mac_address": ["mac", "mac address", "macaddress"],
            "dc_id": ["dc", "dc_id", "downstream channel"],
            "sf_id": ["sf", "sf_id", "service flow"]
        }
        
        self.relationship_keywords = [
            "connected to", "related to", "associated with", 
            "linked to", " for ", " with "  # Add spaces to avoid false matches
        ]
        
        self.aggregation_keywords = [
            "all", "list", "show all", "get all", "find all", "every"
        ]
        
        self.analysis_keywords = [
            "why", "cause", "reason", "analyze", "investigate", 
            "what caused", "root cause", "explain"
        ]
        
        self.trace_keywords = [
            "trace", "flow", "timeline", "sequence", "track", "follow"
        ]
        
        logger.info("Initialized QueryParser")
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse user query into structured format.
        
        Args:
            query: Natural language query string
            
        Returns:
            Parsed query dictionary with type, entities, mode, etc.
        """
        query_lower = query.lower().strip()
        
        logger.info(f"Parsing query: '{query}'")
        
        # Detect query type (order matters!)
        # 1. Trace queries
        if any(kw in query_lower for kw in self.trace_keywords):
            result = self._parse_trace_query(query_lower)
        
        # 2. Analysis queries
        elif any(kw in query_lower for kw in self.analysis_keywords):
            result = self._parse_analysis_query(query_lower)
        
        # 3. Aggregation queries (must check before relationship)
        elif any(kw in query_lower for kw in self.aggregation_keywords):
            result = self._parse_aggregation_query(query_lower)
        
        # 4. Relationship queries (but check if it's really a relationship)
        elif any(kw in query_lower for kw in self.relationship_keywords):
            # Check if it's actually a relationship or just "find X"
            result = self._parse_relationship_query(query_lower)
            
            # If secondary entity looks invalid, it's probably specific
            if result["secondary_entity"] and result["secondary_entity"]["type"] == "unknown":
                result = self._parse_specific_query(query_lower)
        
        # 5. Default: specific value search
        else:
            result = self._parse_specific_query(query_lower)
        
        # Add original query
        result["original_query"] = query
        
        logger.info(f"Parsed as: {result['query_type']}")
        logger.debug(f"Full parse result: {result}")
        
        return result
    
    def _parse_specific_query(self, query: str) -> Dict[str, Any]:
        """
        Parse specific value query.
        Example: "find cm CM12345", "show logs for modem x"
        """
        entity_type, entity_value = self._extract_entity_and_value(query)
        
        return {
            "query_type": "specific_value",
            "primary_entity": {
                "type": entity_type,
                "value": entity_value
            },
            "secondary_entity": None,
            "filter_conditions": self._extract_filter_conditions(query),
            "mode": "find"
        }
    
    def _parse_aggregation_query(self, query: str) -> Dict[str, Any]:
        """
        Parse aggregation query.
        Example: "find all cms", "list all modems with errors"
        """
        # Extract entity type
        entity_type = self._extract_entity_type(query)
        
        # Extract filter conditions
        filters = self._extract_filter_conditions(query)
        
        return {
            "query_type": "aggregation",
            "primary_entity": {
                "type": entity_type,
                "value": None  # None means ALL instances
            },
            "secondary_entity": None,
            "filter_conditions": filters,
            "mode": "find"
        }
    
    def _parse_relationship_query(self, query: str) -> Dict[str, Any]:
        """
        Parse relationship query.
        Example: "find rpdname connected to cm x"
                 "show mdid for modem CM12345"
        """
        # Find relationship keyword
        rel_keyword = None
        for kw in self.relationship_keywords:
            if kw in query:
                rel_keyword = kw
                break
        
        if not rel_keyword:
            return self._parse_specific_query(query)
        
        # Split query on relationship keyword
        parts = query.split(rel_keyword, 1)
        target_part = parts[0].strip()  # What we want to find
        source_part = parts[1].strip()  # What we search for
        
        # Extract target entity type (what we want)
        target_type = self._extract_entity_type(target_part)
        
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
            "filter_conditions": self._extract_filter_conditions(query),
            "mode": "find"
        }
    
    def _parse_analysis_query(self, query: str) -> Dict[str, Any]:
        """
        Parse analysis query.
        Example: "why did cm x fail", "what caused errors for modem CM12345"
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
            "filter_conditions": self._extract_filter_conditions(query),
            "mode": "analyze"
        }
    
    def _parse_trace_query(self, query: str) -> Dict[str, Any]:
        """
        Parse trace/flow query.
        Example: "trace cm x", "show flow for modem CM12345"
        """
        entity_type, entity_value = self._extract_entity_and_value(query)
        
        return {
            "query_type": "trace",
            "primary_entity": {
                "type": entity_type,
                "value": entity_value
            },
            "secondary_entity": None,
            "filter_conditions": [],
            "mode": "trace"
        }
    
    def _extract_entity_type(self, text: str) -> str:
        """
        Extract entity type from text.
        Example: "find all cms" → "cm"
        """
        for entity_type, keywords in self.entity_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return entity_type
        
        return "unknown"
    
    def _extract_entity_and_value(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Extract entity type and value from text.
        
        Examples:
        - "cm CM12345" → ("cm", "CM12345")
        - "modem x" → ("cm", "x")
        - "ip 192.168.1.1" → ("ip_address", "192.168.1.1")
        - "CM12345" → ("cm", "CM12345")  # Detect from pattern
        """
        # Method 1: Keyword + Value pattern
        for entity_type, keywords in self.entity_keywords.items():
            for keyword in keywords:
                # Look for: "keyword value"
                pattern = rf'\b{re.escape(keyword)}\s+(\S+)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    return entity_type, value
        
        # Method 2: Pattern matching (no keyword, detect from value)
        patterns = config.entity_mappings.get("patterns", {})
        for entity_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    matches = regex.findall(text)
                    if matches:
                        value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                        return entity_type, value
                except:
                    continue
        
        # Method 3: Last word might be the value
        words = text.split()
        if words:
            # Filter out common words
            stop_words = {'the', 'a', 'an', 'for', 'to', 'in', 'on', 'with', 'by'}
            value_words = [w for w in words if w.lower() not in stop_words]
            if value_words:
                return "unknown", value_words[-1]
        
        return "unknown", None
    
    def _extract_filter_conditions(self, query: str) -> List[str]:
        """
        Extract filter conditions from query.
        Example: "with errors" → ["error"]
        """
        filters = []
        
        filter_keywords = {
            "error": ["error", "errors", "failed", "failure"],
            "timeout": ["timeout", "timeouts", "timed out"],
            "warning": ["warning", "warnings", "warn"],
            "critical": ["critical", "severe"],
            "high": ["high", "elevated"]
        }
        
        query_lower = query.lower()
        for filter_name, keywords in filter_keywords.items():
            if any(kw in query_lower for kw in keywords):
                filters.append(filter_name)
        
        return filters
    
    def should_search_value(self, parsed: Dict[str, Any]) -> bool:
        """
        Determine if we should search for specific value or pattern.
        
        Returns:
            True: Search for specific VALUE
            False: Search for PATTERN (to find all instances)
        """
        if parsed["query_type"] == "aggregation":
            return False  # Use pattern to find all
        
        if parsed["primary_entity"]["value"] is not None:
            return True  # Have specific value
        
        return False  # No value, use pattern
    
    def get_search_strategy(self, parsed: Dict[str, Any]) -> str:
        """
        Determine search strategy based on parsed query.
        
        Returns:
            "direct" | "aggregation" | "iterative" | "analysis" | "trace"
        """
        query_type = parsed["query_type"]
        
        if query_type == "specific_value":
            return "direct"
        elif query_type == "aggregation":
            return "aggregation"
        elif query_type == "relationship":
            return "iterative"  # May need multiple iterations
        elif query_type == "analysis":
            return "analysis"
        elif query_type == "trace":
            return "trace"
        else:
            return "direct"
