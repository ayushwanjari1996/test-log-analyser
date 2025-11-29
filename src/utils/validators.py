"""Input validation utilities."""

import re
from typing import List, Optional
from pathlib import Path


def validate_log_file(file_path: str) -> bool:
    """Validate that log file exists and is readable."""
    path = Path(file_path)
    return path.exists() and path.is_file() and path.suffix.lower() == '.csv'


def validate_entity_query(query: str) -> bool:
    """Validate entity query format."""
    if not query or len(query.strip()) < 2:
        return False
    
    # Check for basic query patterns
    return bool(re.match(r'^[a-zA-Z0-9\s\-_.:]+$', query.strip()))


def validate_json_response(response: dict, required_fields: List[str]) -> bool:
    """Validate LLM JSON response structure."""
    if not isinstance(response, dict):
        return False
    
    return all(field in response for field in required_fields)


def sanitize_entity_name(entity: str) -> str:
    """Sanitize entity name for safe processing."""
    # Remove special characters, keep alphanumeric and common separators
    # Include : for MAC/IPv6 addresses
    sanitized = re.sub(r'[^\w\-_.:.]', '', entity.strip())
    return sanitized[:100]  # Limit length (increased for IPv6)
