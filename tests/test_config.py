"""Test configuration management."""

import pytest
from src.utils.config import ConfigManager
from src.utils.exceptions import ConfigurationError


def test_config_manager_initialization():
    """Test ConfigManager initialization."""
    config_manager = ConfigManager("config")
    assert config_manager.config_dir.name == "config"


def test_entity_aliases():
    """Test entity alias retrieval."""
    config_manager = ConfigManager("config")
    aliases = config_manager.get_entity_aliases('cm')
    assert isinstance(aliases, list)
    assert len(aliases) > 0


def test_invalid_config_file():
    """Test handling of missing config files."""
    config_manager = ConfigManager("nonexistent")
    with pytest.raises(FileNotFoundError):
        _ = config_manager.entity_mappings
