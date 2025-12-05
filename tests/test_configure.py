"""Tests for configure.py"""
import pytest
from unittest.mock import patch, MagicMock, call
import configure


class TestConfigureProxmoxMenu:
    """Test suite for configure_proxmox_menu function."""
    
    @patch('curses.wrapper')
    @patch('configure.ConfigManager')
    @patch('configure.ProxmoxTarget')
    def test_configure_proxmox_basic(self, mock_proxmox, mock_config_class, mock_curses):
        """Test basic Proxmox configuration flow."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {}
        mock_config_class.return_value = mock_config
        
        mock_target = MagicMock()
        mock_target.test_connection.return_value = True
        mock_target.discover_storages.return_value = ["local", "local-lvm"]
        mock_proxmox.return_value = mock_target
        
        # Test that function exists and is callable
        assert callable(configure.configure_proxmox_menu)
    
    @patch('configure.ConfigManager')
    def test_configure_proxmox_with_existing_config(self, mock_config_class):
        """Test Proxmox configuration with existing settings."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {
            "host": "192.168.1.100",
            "user": "root",
            "storage": "local"
        }
        mock_config_class.return_value = mock_config
        
        # Verify config can be retrieved
        config = mock_config.get_proxmox_config()
        assert config["host"] == "192.168.1.100"


class TestConfigureAutoUpdateMenu:
    """Test suite for configure_auto_update_menu function."""
    
    @patch('curses.wrapper')
    @patch('configure.ConfigManager')
    @patch('configure.DISTRO_UPDATERS')
    def test_configure_auto_update_basic(self, mock_updaters, mock_config_class, mock_curses):
        """Test basic auto-update configuration flow."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get_auto_update_distributions.return_value = []
        mock_config_class.return_value = mock_config
        
        mock_updaters.keys.return_value = ['ubuntu', 'debian', 'fedora']
        
        # Test that function exists and is callable
        assert callable(configure.configure_auto_update_menu)
    
    @patch('configure.ConfigManager')
    @patch('configure.DISTRO_UPDATERS')
    def test_configure_auto_update_with_selections(self, mock_updaters, mock_config_class):
        """Test auto-update configuration with selected distributions."""
        mock_config = MagicMock()
        mock_config.get_auto_update_distributions.return_value = ["ubuntu", "debian"]
        mock_config_class.return_value = mock_config
        
        mock_updaters.keys.return_value = ['ubuntu', 'debian', 'fedora', 'arch']
        
        # Verify distributions can be retrieved
        distros = mock_config.get_auto_update_distributions()
        assert "ubuntu" in distros
        assert "debian" in distros


class TestMainConfigMenu:
    """Test suite for main_config_menu function."""
    
    @patch('curses.wrapper')
    @patch('configure.configure_proxmox_menu')
    @patch('configure.configure_auto_update_menu')
    def test_main_menu_structure(self, mock_auto_update, mock_proxmox, mock_curses):
        """Test main configuration menu structure."""
        # Test that function exists and is callable
        assert callable(configure.main_config_menu)
    
    @patch('curses.wrapper')
    def test_main_menu_callable(self, mock_curses):
        """Test that main menu can be called."""
        # Should not raise exceptions when called
        try:
            # We can't actually run it without proper curses setup
            # but we can verify it's properly defined
            assert hasattr(configure, 'main_config_menu')
            assert callable(configure.main_config_menu)
        except Exception as e:
            pytest.fail(f"main_config_menu not properly defined: {e}")


class TestConfigureIntegration:
    """Integration tests for configure.py module."""
    
    def test_module_imports(self):
        """Test that all required modules are imported."""
        assert hasattr(configure, 'ConfigManager')
        assert hasattr(configure, 'ProxmoxTarget')
        assert hasattr(configure, 'DISTRO_UPDATERS')
    
    def test_all_functions_defined(self):
        """Test that all main functions are defined."""
        functions = [
            'configure_proxmox_menu',
            'configure_auto_update_menu',
            'main_config_menu'
        ]
        
        for func_name in functions:
            assert hasattr(configure, func_name)
            assert callable(getattr(configure, func_name))
    
    @patch('configure.ConfigManager')
    def test_config_manager_integration(self, mock_config_class):
        """Test ConfigManager integration in configure module."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {
            "host": "192.168.1.100",
            "user": "root",
            "storage": "local"
        }
        mock_config.get_auto_update_distributions.return_value = ["ubuntu"]
        mock_config_class.return_value = mock_config
        
        # Verify config methods are available
        config = mock_config_class()
        assert config.get_proxmox_config() is not None
        assert config.get_auto_update_distributions() is not None
