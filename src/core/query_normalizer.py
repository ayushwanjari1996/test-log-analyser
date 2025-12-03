"""
Query Normalizer - Normalize user queries using entity_mappings.yaml
"""

import re
from typing import Dict, List, Optional
from ..utils.config import ConfigManager
from ..utils.logger import setup_logger

logger = setup_logger()


class QueryNormalizer:
    """
    Normalize user queries by:
    1. Replacing entity aliases with canonical types (from entity_mappings.yaml)
    2. Extracting search values (MAC, IP, IDs, names)
    """
    
    def __init__(self, config: ConfigManager = None):
        """Initialize with config (uses global config if not provided)."""
        if config is None:
            from ..utils.config import config as global_config
            config = global_config
        
        self.config = config
        self.alias_to_canonical = self._build_alias_map()
        
        # Extractable entity types (from patterns in entity_mappings.yaml)
        self.extractable_types = list(config.entity_mappings.get('patterns', {}).keys())
        
        logger.info(f"QueryNormalizer initialized with {len(self.alias_to_canonical)} aliases")
    
    def _build_alias_map(self) -> Dict[str, str]:
        """Build reverse mapping: alias → canonical type."""
        alias_map = {}
        aliases = self.config.entity_mappings.get('aliases', {})
        
        for canonical_type, alias_list in aliases.items():
            # Map the canonical type to itself
            alias_map[canonical_type.lower()] = canonical_type
            
            # Map each alias to the canonical type
            for alias in alias_list:
                alias_map[alias.lower()] = canonical_type
        
        return alias_map
    
    def _get_extractable_type(self, canonical: str) -> str:
        """
        Map canonical type to extractable type.
        e.g., 'cm' → 'cm_mac', 'rpdname' stays 'rpdname'
        """
        # Direct mapping for types that need conversion
        type_to_extractable = {
            'cm': 'cm_mac',
            'cpe': 'cpe_mac',
        }
        
        if canonical in type_to_extractable:
            return type_to_extractable[canonical]
        
        # If it's already an extractable type, return as-is
        if canonical in self.extractable_types:
            return canonical
        
        return canonical
    
    def normalize(self, query: str) -> Dict:
        """
        Normalize a query.
        
        Returns:
            {
                "original_query": "find all cms for rpd MAWED07T01",
                "normalized_query": "find all cm_mac for rpdname MAWED07T01",
                "search_value": "MAWED07T01",
                "detected_entities": ["cm_mac", "rpdname"]
            }
        """
        original = query
        normalized = query
        detected_entities = []
        
        # Step 1: Find and replace entity aliases with canonical types
        # Sort by length (longest first) to avoid partial replacements
        sorted_aliases = sorted(self.alias_to_canonical.keys(), key=len, reverse=True)
        
        for alias in sorted_aliases:
            # Word boundary match (case-insensitive)
            pattern = rf'\b{re.escape(alias)}\b'
            if re.search(pattern, normalized, re.IGNORECASE):
                canonical = self.alias_to_canonical[alias]
                extractable = self._get_extractable_type(canonical)
                
                # Replace alias with extractable type
                normalized = re.sub(pattern, extractable, normalized, flags=re.IGNORECASE)
                
                if extractable not in detected_entities:
                    detected_entities.append(extractable)
        
        # Step 2: Extract search value (the thing user is searching FOR)
        search_value = self._extract_search_value(query)
        
        result = {
            "original_query": original,
            "normalized_query": normalized,
            "search_value": search_value,
            "detected_entities": detected_entities
        }
        
        logger.info(f"Normalized: '{original}' → '{normalized}' (search: {search_value})")
        return result
    
    def _extract_search_value(self, query: str) -> str:
        """
        Extract the search value from query.
        Looks for MAC addresses, IPs, hex IDs, or alphanumeric identifiers.
        """
        # Priority order of patterns to try
        patterns = [
            # MAC address (xx:xx:xx:xx:xx:xx or xx-xx-xx-xx-xx-xx)
            r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}',
            # Hex ID (0x...)
            r'0x[0-9a-fA-F]+',
            # IPv4
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            # Alphanumeric ID (like MAWED07T01) - at least 6 chars, has both letters and numbers
            r'\b[A-Za-z]+[0-9]+[A-Za-z0-9]*\b|\b[0-9]+[A-Za-z]+[A-Za-z0-9]*\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(0)
        
        # Fallback: return empty string (will search all logs)
        return ""
    
    def get_extractable_types(self) -> List[str]:
        """Get list of all extractable entity types."""
        return self.extractable_types.copy()

