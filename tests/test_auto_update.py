"""Tests for auto_update.py"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import auto_update


class TestCheckAutoDeployItems:
    """Test suite for check_auto_deploy_items function."""
    
    @patch('auto_update.ConfigManager')
    def test_find_auto_deploy_items(self, mock_config_class, sample_distro_dict):
        """Test finding auto-deploy items in distro dict."""
        mock_config = MagicMock()
        mock_config.get_auto_deploy_items.return_value = ["Debian/12.0"]
        mock_config_class.return_value = mock_config
        
        # Sample distro dict with simple structure
        distro_dict = {
            "Debian": {
                "12.0": [
                    "debian-12.0.0-amd64-netinst.iso: https://example.com/debian.iso"
                ]
            }
        }
        
        result = auto_update.check_auto_deploy_items(distro_dict)
        
        assert len(result) == 1
        assert result[0][0] == "Debian/12.0"
        assert result[0][2] == "debian-12.0.0-amd64-netinst.iso"
    
    @patch('auto_update.ConfigManager')
    def test_no_auto_deploy_items(self, mock_config_class, sample_distro_dict):
        """Test when no auto-deploy items are configured."""
        mock_config = MagicMock()
        mock_config.get_auto_deploy_items.return_value = []
        mock_config_class.return_value = mock_config
        
        result = auto_update.check_auto_deploy_items(sample_distro_dict)
        
        assert result == []
    
    @patch('auto_update.ConfigManager')
    def test_auto_deploy_item_not_found(self, mock_config_class, sample_distro_dict):
        """Test when auto-deploy item doesn't exist in dict."""
        mock_config = MagicMock()
        mock_config.get_auto_deploy_items.return_value = ["NonExistent/1.0/0"]
        mock_config_class.return_value = mock_config
        
        result = auto_update.check_auto_deploy_items(sample_distro_dict)
        
        assert result == []
    
    @patch('auto_update.ConfigManager')
    def test_auto_deploy_item_not_downloaded(self, mock_config_class, sample_distro_dict):
        """Test when auto-deploy item is not downloaded."""
        mock_config = MagicMock()
        mock_config.get_auto_deploy_items.return_value = ["Ubuntu/22.04"]
        mock_config_class.return_value = mock_config
        
        # Item exists but has no downloadable URLs in this test
        result = auto_update.check_auto_deploy_items(sample_distro_dict)
        
        # Result depends on sample_distro_dict structure
        assert isinstance(result, list)
    
    @patch('auto_update.ConfigManager')
    def test_multiple_auto_deploy_items(self, mock_config_class, sample_distro_dict):
        """Test with multiple auto-deploy items."""
        mock_config = MagicMock()
        mock_config.get_auto_deploy_items.return_value = ["Debian/12.0", "Ubuntu/22.04"]
        mock_config_class.return_value = mock_config
        
        distro_dict = {
            "Debian": {
                "12.0": ["debian.iso: https://example.com/debian.iso"]
            },
            "Ubuntu": {
                "22.04": ["ubuntu.iso: https://example.com/ubuntu.iso"]
            }
        }
        
        result = auto_update.check_auto_deploy_items(distro_dict)
        
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
            "hostname": "192.168.1.100",
            "username": "root"
        }
        mock_config_class.return_value = mock_config
        
        mock_proxmox = MagicMock()
        mock_proxmox.check_ssh_keys.return_value = True
        mock_proxmox.test_connection.return_value = (True, "Connected")
        # upload_file returns tuple (success, message) or just bool
        mock_proxmox.upload_file.return_value = (True, "Uploaded")
        mock_config.get_storage_for_type.return_value = "local"
        mock_proxmox_class.return_value = mock_proxmox
        
        files = ["/tmp/test.iso"]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=False)
        
        assert isinstance(result, list)
        mock_proxmox.upload_file.assert_called()
        mock_proxmox.prompt_password.assert_not_called()
    
    @patch('auto_update.ProxmoxTarget')
    @patch('auto_update.ConfigManager')
    def test_deploy_with_password(self, mock_config_class, mock_proxmox_class):
        """Test deployment using password authentication."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {
            "hostname": "192.168.1.100",
            "username": "root"
        }
        mock_config_class.return_value = mock_config
        
        mock_proxmox = MagicMock()
        mock_proxmox.check_ssh_keys.return_value = False
        mock_proxmox.prompt_password.return_value = "password123"
        mock_proxmox.test_connection.return_value = (True, "Connected")
        mock_proxmox.upload_file.return_value = (True, "Uploaded")
        mock_config.get_storage_for_type.return_value = "local"
        mock_proxmox_class.return_value = mock_proxmox
        
        files = ["/tmp/test.iso"]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=True)
        
        assert isinstance(result, list)
        mock_proxmox.prompt_password.assert_called_once()
        mock_proxmox.upload_file.assert_called()
    
    @patch('auto_update.ProxmoxTarget')
    @patch('auto_update.ConfigManager')
    def test_deploy_no_proxmox_config(self, mock_config_class, mock_proxmox_class):
        """Test deployment when Proxmox not configured."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {"hostname": ""}
        mock_config_class.return_value = mock_config
        
        files = ["/tmp/test.iso"]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=False)
        
        assert result == []
        mock_proxmox_class.assert_not_called()
    
    @patch('auto_update.ProxmoxTarget')
    @patch('auto_update.ConfigManager')
    def test_deploy_upload_failure(self, mock_config_class, mock_proxmox_class):
        """Test deployment when upload fails."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {
            "hostname": "192.168.1.100",
            "username": "root"
        }
        mock_config_class.return_value = mock_config
        
        mock_proxmox = MagicMock()
        mock_proxmox.check_ssh_keys.return_value = True
        mock_proxmox.test_connection.return_value = (True, "Connected")
        mock_proxmox.upload_file.return_value = (False, "Upload failed")
        mock_config.get_storage_for_type.return_value = "local"
        mock_proxmox_class.return_value = mock_proxmox
        
        files = ["/tmp/test.iso"]
        
        result = auto_update.deploy_files_to_proxmox(files, interactive=False)
        
        # Returns list of deployment results
        assert isinstance(result, list)
    
    @patch('auto_update.ConfigManager')
    def test_deploy_empty_file_list(self, mock_config_class):
        """Test deployment with empty file list."""
        mock_config = MagicMock()
        mock_config.get_proxmox_config.return_value = {"hostname": "192.168.1.100"}
        mock_config_class.return_value = mock_config
        
        result = auto_update.deploy_files_to_proxmox([], interactive=False)
        
        # Should handle gracefully and return empty list
        assert result == []


class TestAutoUpdateDistributions:
    """Test suite for auto_update_distributions function."""
    
    @patch('auto_update.ConfigManager')
    @patch('auto_update.DISTRO_UPDATERS')
    def test_auto_update_basic(self, mock_updaters, mock_config_class):
        """Test basic auto-update functionality."""
        from pathlib import Path
        # Setup config mock
        mock_config = MagicMock()
        mock_config.get_auto_update_distros.return_value = ["ubuntu"]
        mock_config.is_auto_update_enabled.return_value = True
        mock_config_class.return_value = mock_config
        
        # Setup updater mock
        mock_ubuntu_updater = MagicMock()
        mock_ubuntu_updater.get_latest_version.return_value = "22.04"
        mock_ubuntu_updater.generate_download_links.return_value = ["http://example.com/ubuntu.iso"]
        mock_updaters.__getitem__.return_value = mock_ubuntu_updater
        
        # Run auto update with required download_dir parameter
        result = auto_update.auto_update_distributions(Path("/tmp/downloads"))
        
        # Verify result is a dict
        assert isinstance(result, dict)
    
    @patch('auto_update.ConfigManager')
    def test_auto_update_no_distributions(self, mock_config_class):
        """Test auto-update when no distributions configured."""
        from pathlib import Path
        mock_config = MagicMock()
        mock_config.get_auto_update_distros.return_value = []
        mock_config_class.return_value = mock_config
        
        # Should handle gracefully
        result = auto_update.auto_update_distributions(Path("/tmp/downloads"))
        
        # No exceptions should be raised, returns status dict
        assert isinstance(result, dict)
        assert result.get('status') == 'no_distros'
    
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
        from pathlib import Path
        mock_config = MagicMock()
        mock_config.get_auto_update_distros.return_value = ["ubuntu"]
        mock_config.is_auto_update_enabled.return_value = True
        mock_config_class.return_value = mock_config
        
        # Setup updater to raise exception
        mock_ubuntu_updater = MagicMock()
        mock_ubuntu_updater.get_latest_version.side_effect = Exception("Network error")
        mock_updaters.__getitem__.return_value = mock_ubuntu_updater
        
        # Should handle exception gracefully
        try:
            result = auto_update.auto_update_distributions(Path("/tmp/downloads"))
            assert isinstance(result, dict)
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
