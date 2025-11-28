"""Configuration management for log analyzer."""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class ConfigManager:
    """Manages application configuration from YAML files."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._entity_mappings: Optional[Dict[str, Any]] = None
        self._log_schema: Optional[Dict[str, Any]] = None
        self._prompts: Optional[Dict[str, Any]] = None
    
    @property
    def entity_mappings(self) -> Dict[str, Any]:
        """Load and cache entity mappings configuration."""
        if self._entity_mappings is None:
            self._entity_mappings = self._load_yaml("entity_mappings.yaml")
        return self._entity_mappings
    
    @property
    def log_schema(self) -> Dict[str, Any]:
        """Load and cache log schema configuration."""
        if self._log_schema is None:
            self._log_schema = self._load_yaml("log_schema.yaml")
        return self._log_schema
    
    @property
    def prompts(self) -> Dict[str, Any]:
        """Load and cache prompt templates."""
        if self._prompts is None:
            self._prompts = self._load_yaml("prompts.yaml")
        return self._prompts
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {filename}: {e}")
    
    def get_entity_aliases(self, entity_type: str) -> List[str]:
        """Get all aliases for a given entity type."""
        aliases = self.entity_mappings.get("aliases", {})
        return aliases.get(entity_type, [entity_type])
    
    def get_entity_relationships(self, entity_type: str) -> List[str]:
        """Get related entities for a given entity type."""
        relationships = self.entity_mappings.get("relationships", {})
        return relationships.get(entity_type, [])
    
    def get_entity_pattern(self, entity_type: str) -> List[str]:
        """Get regex patterns for entity extraction."""
        patterns = self.entity_mappings.get("patterns", {})
        return patterns.get(entity_type, [])
    
    def get_log_columns(self, schema_name: str = "default") -> List[str]:
        """Get column names for log schema."""
        schema = self.log_schema.get("csv_schema", {})
        return schema.get(schema_name, {}).get("columns", [])
    
    def get_chunking_config(self) -> Dict[str, Any]:
        """Get chunking configuration."""
        return self.log_schema.get("chunking", {})
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.log_schema.get("llm", {})
    
    def get_prompt_template(self, mode: str, template_type: str = "user_template") -> str:
        """Get prompt template for specific mode."""
        mode_prompts = self.prompts.get(f"{mode}_mode", {})
        return mode_prompts.get(template_type, "")


# Global configuration instance
config = ConfigManager()
