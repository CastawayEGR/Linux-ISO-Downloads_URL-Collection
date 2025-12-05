"""Tests for config_manager.py"""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from config_manager import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager class."""
    
    def test_init_creates_config_file(self, temp_config_dir):
        """Test that ConfigManager creates config file on init."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            assert config_file.exists()
            assert manager.config is not None
    
    def test_load_existing_config(self, temp_config_file):
        """Test loading existing configuration."""
        with patch('config_manager.CONFIG_FILE', temp_config_file):
            manager = ConfigManager()
            assert "location_history" in manager.config
            assert "proxmox" in manager.config
            assert manager.config["proxmox"]["host"] == "192.168.1.100"
    
    def test_save_config(self, temp_config_dir):
        """Test saving configuration to file."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            manager.config["test_key"] = "test_value"
            manager.save()
            
            # Reload and verify
            loaded_config = json.loads(config_file.read_text())
            assert loaded_config["test_key"] == "test_value"
    
    def test_add_to_location_history(self, temp_config_file):
        """Test adding location to history."""
        with patch('config_manager.CONFIG_FILE', temp_config_file):
            manager = ConfigManager()
            initial_count = len(manager.config.get("location_history", []))
            
            manager.add_to_location_history("/new/location")
            assert len(manager.config["location_history"]) == initial_count + 1
            assert manager.config["location_history"][0] == "/new/location"
    
    def test_location_history_max_size(self, temp_config_dir):
        """Test that location history respects max size of 10."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            # Add 15 locations
            for i in range(15):
                manager.add_to_location_history(f"/location/{i}")
            
            # Should only keep 10
            assert len(manager.config["location_history"]) == 10
            # Most recent should be first
            assert manager.config["location_history"][0] == "/location/14"
    
    def test_location_history_deduplication(self, temp_config_file):
        """Test that duplicate locations are removed."""
        with patch('config_manager.CONFIG_FILE', temp_config_file):
            manager = ConfigManager()
            location = "/duplicate/path"
            
            manager.add_to_location_history(location)
            initial_count = len(manager.config["location_history"])
            
            manager.add_to_location_history(location)
            # Should not increase count, just move to front
            assert len(manager.config["location_history"]) == initial_count
            assert manager.config["location_history"][0] == location
    
    def test_get_proxmox_config(self, temp_config_file):
        """Test getting Proxmox configuration."""
        with patch('config_manager.CONFIG_FILE', temp_config_file):
            manager = ConfigManager()
            proxmox_config = manager.get_proxmox_config()
            
            assert proxmox_config["host"] == "192.168.1.100"
            assert proxmox_config["user"] == "root"
            assert proxmox_config["storage"] == "local"
    
    def test_set_proxmox_config(self, temp_config_dir):
        """Test setting Proxmox configuration."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            manager.set_proxmox_config(
                host="10.0.0.5",
                user="admin",
                storage="nfs-storage"
            )
            
            proxmox_config = manager.get_proxmox_config()
            assert proxmox_config["host"] == "10.0.0.5"
            assert proxmox_config["user"] == "admin"
            assert proxmox_config["storage"] == "nfs-storage"
    
    def test_get_auto_update_distributions(self, temp_config_file):
        """Test getting auto-update distributions list."""
        with patch('config_manager.CONFIG_FILE', temp_config_file):
            manager = ConfigManager()
            distributions = manager.get_auto_update_distributions()
            
            assert "ubuntu" in distributions
            assert "debian" in distributions
    
    def test_set_auto_update_distributions(self, temp_config_dir):
        """Test setting auto-update distributions."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            new_distros = ["fedora", "rocky", "arch"]
            manager.set_auto_update_distributions(new_distros)
            
            saved_distros = manager.get_auto_update_distributions()
            assert saved_distros == new_distros
    
    def test_get_auto_deploy_items_empty(self, temp_config_dir):
        """Test getting auto-deploy items when empty."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            items = manager.get_auto_deploy_items()
            
            assert items == []
    
    def test_add_auto_deploy_item(self, temp_config_dir):
        """Test adding an auto-deploy item."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            item_path = "Ubuntu/22.04/0"
            manager.add_auto_deploy_item(item_path)
            
            items = manager.get_auto_deploy_items()
            assert item_path in items
    
    def test_remove_auto_deploy_item(self, temp_config_dir):
        """Test removing an auto-deploy item."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            item_path = "Ubuntu/22.04/0"
            manager.add_auto_deploy_item(item_path)
            assert item_path in manager.get_auto_deploy_items()
            
            manager.remove_auto_deploy_item(item_path)
            assert item_path not in manager.get_auto_deploy_items()
    
    def test_toggle_auto_deploy_item(self, temp_config_dir):
        """Test toggling auto-deploy item."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            item_path = "Ubuntu/22.04/0"
            
            # Toggle on
            manager.toggle_auto_deploy_item(item_path)
            assert item_path in manager.get_auto_deploy_items()
            
            # Toggle off
            manager.toggle_auto_deploy_item(item_path)
            assert item_path not in manager.get_auto_deploy_items()
    
    def test_config_migration(self, temp_config_dir):
        """Test that old configs without auto_deploy_items are migrated."""
        config_file = temp_config_dir / "config.json"
        old_config = {"proxmox": {"host": "localhost"}}
        config_file.write_text(json.dumps(old_config))
        
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            # Should have auto_deploy_items after migration
            assert "auto_deploy_items" in manager.config
            assert isinstance(manager.config["auto_deploy_items"], list)
    
    def test_no_password_storage(self, temp_config_dir):
        """Test that passwords are never stored in config."""
        config_file = temp_config_dir / "config.json"
        with patch('config_manager.CONFIG_FILE', config_file):
            manager = ConfigManager()
            
            # Try to set config with password
            manager.set_proxmox_config(
                host="10.0.0.5",
                user="root",
                storage="local",
                password="secret123"  # This should not be stored
            )
            
            manager.save()
            
            # Reload and verify no password
            loaded_config = json.loads(config_file.read_text())
            assert "password" not in loaded_config.get("proxmox", {})
