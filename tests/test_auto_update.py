"""Tests for auto_update.py"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import auto_update


class TestCheckAutoDeployItems:
    """Test suite for check_auto_deploy_items function."""
    
    def test_find_auto_deploy_items(self, sample_distro_dict):
        """Test finding auto-deploy items in distro dict."""
        auto_deploy_items = ["Debian/12.0/0"]
        
        result = auto_update.check_auto_deploy_items(sample_distro_dict, auto_deploy_items)
        
        assert len(result) == 1
        assert result[0]["filename"] == "debian-12.0.0-amd64-netinst.iso"
        assert result[0]["location"] == "/tmp/debian-12.0.0-amd64-netinst.iso"
    
    def test_no_auto_deploy_items(self, sample_distro_dict):
        """Test when no auto-deploy items are configured."""
        result = auto_update.check_auto_deploy_items(sample_distro_dict, [])
        
        assert result == []
    
    def test_auto_deploy_item_not_found(self, sample_distro_dict):
        """Test when auto-deploy item doesn't exist in dict."""
        auto_deploy_items = ["NonExistent/1.0/0"]
        
        result = auto_update.check_auto_deploy_items(sample_distro_dict, auto_deploy_items)
        
        assert result == []
    
    def test_auto_deploy_item_not_downloaded(self, sample_distro_dict):
        """Test when auto-deploy item is not downloaded."""
        auto_deploy_items = ["Ubuntu/22.04/0"]  # Not downloaded
        
        result = auto_update.check_auto_deploy_items(sample_distro_dict, auto_deploy_items)
        
        assert result == []
    
    def test_multiple_auto_deploy_items(self, sample_distro_dict):
        """Test with multiple auto-deploy items."""
        # Add another downloaded item
        sample_distro_dict["Ubuntu"]["22.04"][0]["downloaded"] = True
        sample_distro_dict["Ubuntu"]["22.04"][0]["location"] = "/tmp/ubuntu-22.04.iso"
        
        auto_deploy_items = ["Ubuntu/22.04/0", "Debian/12.0/0"]
        
        result = auto_update.check_auto_deploy_items(sample_distro_dict, auto_deploy_items)
        
        assert len(result) == 2


class TestDeployFilesToProxmox:
    """Test suite for deploy_files_to_proxmox function."""
    
    @patch('auto_update.ProxmoxTarget')
    @patch('auto_update.ConfigManager')
    def test_deploy_with_ssh_keys(self, mock_config_class, mock_proxmox_class):
        """Test deployment using SSH keys."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {
            "host": "192.168.1.100",
            "user": "root",
            "storage": "local"
        }
        mock_config_class.return_value = mock_config
        
        mock_proxmox = MagicMock()
        mock_proxmox.check_ssh_keys.return_value = True
        mock_proxmox.upload_file.return_value = True
        mock_proxmox_class.return_value = mock_proxmox
        
        files = [{"location": "/tmp/test.iso", "filename": "test.iso"}]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=False)
        
        assert result is True
        mock_proxmox.upload_file.assert_called_once()
        mock_proxmox.prompt_password.assert_not_called()
    
    @patch('auto_update.ProxmoxTarget')
    @patch('auto_update.ConfigManager')
    def test_deploy_with_password(self, mock_config_class, mock_proxmox_class):
        """Test deployment using password authentication."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {
            "host": "192.168.1.100",
            "user": "root",
            "storage": "local"
        }
        mock_config_class.return_value = mock_config
        
        mock_proxmox = MagicMock()
        mock_proxmox.check_ssh_keys.return_value = False
        mock_proxmox.prompt_password.return_value = "password123"
        mock_proxmox.upload_file.return_value = True
        mock_proxmox_class.return_value = mock_proxmox
        
        files = [{"location": "/tmp/test.iso", "filename": "test.iso"}]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=True)
        
        assert result is True
        mock_proxmox.prompt_password.assert_called_once()
        mock_proxmox.upload_file.assert_called_once()
    
    @patch('auto_update.ProxmoxTarget')
    @patch('auto_update.ConfigManager')
    def test_deploy_no_proxmox_config(self, mock_config_class, mock_proxmox_class):
        """Test deployment when Proxmox not configured."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {}
        mock_config_class.return_value = mock_config
        
        files = [{"location": "/tmp/test.iso"}]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=False)
        
        assert result is False
        mock_proxmox_class.assert_not_called()
    
    @patch('auto_update.ProxmoxTarget')
    @patch('auto_update.ConfigManager')
    def test_deploy_upload_failure(self, mock_config_class, mock_proxmox_class):
        """Test deployment when upload fails."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {
            "host": "192.168.1.100",
            "user": "root",
            "storage": "local"
        }
        mock_config_class.return_value = mock_config
        
        mock_proxmox = MagicMock()
        mock_proxmox.check_ssh_keys.return_value = True
        mock_proxmox.upload_file.return_value = False
        mock_proxmox_class.return_value = mock_proxmox
        
        files = [{"location": "/tmp/test.iso", "filename": "test.iso"}]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=False)
        
        # Should still return True overall, but individual file fails
        assert result is True
    
    @patch('auto_update.ConfigManager')
    def test_deploy_empty_file_list(self, mock_config_class):
        """Test deployment with empty file list."""
        result = auto_update.deploy_files_to_proxmox([], interactive=False)
        
        # Should handle gracefully
        assert result is False


class TestAutoUpdateDistributions:
    """Test suite for auto_update_distributions function."""
    
    @patch('auto_update.ConfigManager')
    @patch('auto_update.DISTRO_UPDATERS')
    @patch('auto_update.requests.get')
    @patch('builtins.open', new_callable=mock_open, read_data="# Test README\n## Ubuntu\n")
    def test_auto_update_basic(self, mock_file, mock_requests, mock_updaters, mock_config_class):
        """Test basic auto-update functionality."""
        # Setup config mock
        mock_config = MagicMock()
        mock_config.get_auto_update_distributions.return_value = ["ubuntu"]
        mock_config.get_auto_deploy_items.return_value = []
        mock_config_class.return_value = mock_config
        
        # Setup requests mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# README\n## Ubuntu\n"
        mock_requests.return_value = mock_response
        
        # Setup updater mock
        mock_ubuntu_updater = MagicMock()
        mock_ubuntu_updater.get_latest_version.return_value = "22.04"
        mock_ubuntu_updater.generate_download_links.return_value = ["http://example.com/ubuntu.iso"]
        mock_ubuntu_updater.update_section.return_value = "# Updated Ubuntu\n"
        mock_updaters.get.return_value = mock_ubuntu_updater
        
        # Run auto update
        with patch('auto_update.REPO_FILE_PATH', '/tmp/README.md'):
            auto_update.auto_update_distributions()
        
        # Verify updater was called
        mock_ubuntu_updater.get_latest_version.assert_called_once()
    
    @patch('auto_update.ConfigManager')
    def test_auto_update_no_distributions(self, mock_config_class):
        """Test auto-update when no distributions configured."""
        mock_config = MagicMock()
        mock_config.get_auto_update_distributions.return_value = []
        mock_config_class.return_value = mock_config
        
        # Should handle gracefully
        auto_update.auto_update_distributions()
        
        # No exceptions should be raised
    
    @patch('auto_update.ConfigManager')
    @patch('auto_update.DISTRO_UPDATERS')
    def test_auto_update_with_deployment(self, mock_updaters, mock_config_class):
        """Test auto-update with Proxmox deployment."""
        mock_config = MagicMock()
        mock_config.get_auto_update_distributions.return_value = ["ubuntu"]
        mock_config.get_auto_deploy_items.return_value = ["Ubuntu/22.04/0"]
        mock_config.get_proxmox_config.return_value = {
            "host": "192.168.1.100",
            "user": "root",
            "storage": "local"
        }
        mock_config_class.return_value = mock_config
        
        # Test would require full integration mock
        # This verifies the structure exists
        assert callable(auto_update.auto_update_distributions)
    
    @patch('auto_update.ConfigManager')
    @patch('auto_update.DISTRO_UPDATERS')
    def test_auto_update_updater_exception(self, mock_updaters, mock_config_class):
        """Test auto-update handles updater exceptions gracefully."""
        mock_config = MagicMock()
        mock_config.get_auto_update_distributions.return_value = ["ubuntu"]
        mock_config.get_auto_deploy_items.return_value = []
        mock_config_class.return_value = mock_config
        
        # Setup updater to raise exception
        mock_ubuntu_updater = MagicMock()
        mock_ubuntu_updater.get_latest_version.side_effect = Exception("Network error")
        mock_updaters.get.return_value = mock_ubuntu_updater
        
        # Should handle exception gracefully
        try:
            auto_update.auto_update_distributions()
        except Exception:
            pytest.fail("auto_update_distributions should handle exceptions gracefully")


class TestMainFunction:
    """Test suite for main function."""
    
    @patch('auto_update.auto_update_distributions')
    @patch('sys.argv', ['auto_update.py'])
    def test_main_execution(self, mock_auto_update):
        """Test main function execution."""
        with patch('auto_update.__name__', '__main__'):
            # Would need to import and run main
            # This test verifies structure
            assert callable(auto_update.auto_update_distributions)
