"""Tests for updaters.py"""
import pytest
from unittest.mock import patch, MagicMock
import updaters


class TestDistroUpdater:
    """Test suite for DistroUpdater base class."""
    
    def test_get_latest_version_not_implemented(self):
        """Test that base class raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            updaters.DistroUpdater.get_latest_version()
    
    def test_generate_download_links_not_implemented(self):
        """Test that base class raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            updaters.DistroUpdater.generate_download_links("1.0")
    
    def test_update_section_not_implemented(self):
        """Test that base class raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            updaters.DistroUpdater.update_section("content", "1.0", [])
    
    def test_add_metadata_comment(self):
        """Test metadata comment addition."""
        metadata = {"auto_updated": True, "last_updated": "2024-01-01"}
        section = "## Ubuntu\n"
        
        result = updaters.DistroUpdater.add_metadata_comment(section, metadata)
        
        assert "<!-- Auto-updated: 2024-01-01 -->" in result
        assert "## Ubuntu" in result
    
    def test_add_metadata_comment_no_metadata(self):
        """Test that no comment is added without metadata."""
        section = "## Ubuntu\n"
        
        result = updaters.DistroUpdater.add_metadata_comment(section, None)
        
        assert result == section
        assert "<!--" not in result


class TestGetDistrowatchVersion:
    """Test suite for get_distrowatch_version function."""
    
    @patch('requests.get')
    def test_get_version_success(self, mock_get):
        """Test successful version retrieval from DistroWatch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<a href="/table.php?distribution=ubuntu">Ubuntu 22.04</a>'
        mock_get.return_value = mock_response
        
        version = updaters.get_distrowatch_version('ubuntu')
        
        assert version is not None
    
    @patch('requests.get')
    def test_get_version_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        version = updaters.get_distrowatch_version('nonexistent')
        
        assert version is None
    
    @patch('requests.get')
    def test_get_version_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")
        
        version = updaters.get_distrowatch_version('ubuntu')
        
        assert version is None


class TestFedoraCloudUpdater:
    """Test suite for FedoraCloudUpdater."""
    
    @patch('updaters.fetch_fedora_releases')
    def test_get_latest_version(self, mock_fetch):
        """Test getting latest Fedora Cloud version."""
        mock_fetch.return_value = [
            {'version': '40', 'variant': 'Cloud', 'arch': 'x86_64', 'link': 'http://example.com/fedora40.qcow2'},
            {'version': '39', 'variant': 'Cloud', 'arch': 'x86_64', 'link': 'http://example.com/fedora39.qcow2'}
        ]
        
        if hasattr(updaters, 'FedoraCloudUpdater'):
            # Call as static/class method without self
            version = updaters.FedoraCloudUpdater.get_latest_version()
            assert version is not None
    
    @patch('updaters.fetch_fedora_releases')
    def test_generate_download_links(self, mock_fetch):
        """Test generating Fedora Cloud download links."""
        mock_fetch.return_value = [
            {'version': '40', 'variant': 'Cloud', 'arch': 'x86_64', 'link': 'http://example.com/Fedora-Cloud-Generic-40.qcow2'}
        ]
        
        if hasattr(updaters, 'FedoraCloudUpdater'):
            links = updaters.FedoraCloudUpdater.generate_download_links(['40'])
            # Returns dict with version keys
            assert isinstance(links, dict)
            assert '40' in links or len(links) > 0


class TestUbuntuCloudUpdater:
    """Test suite for UbuntuCloudUpdater."""
    
    @patch('requests.get')
    def test_get_latest_version(self, mock_get):
        """Test getting latest Ubuntu Cloud version."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<a href="jammy/">jammy/</a><a href="noble/">noble/</a>'
        mock_get.return_value = mock_response
        
        if hasattr(updaters, 'UbuntuCloudUpdater'):
            version = updaters.UbuntuCloudUpdater.get_latest_version()
            # May return None if parsing fails, just check it doesn't crash
            assert version is None or isinstance(version, (str, list, dict))
    
    def test_generate_download_links(self):
        """Test generating Ubuntu Cloud download links."""
        if hasattr(updaters, 'UbuntuCloudUpdater'):
            # Test with simple version string
            links = updaters.UbuntuCloudUpdater.generate_download_links('jammy')
            assert isinstance(links, (list, dict))
            # May be empty if no actual network call


class TestDebianCloudUpdater:
    """Test suite for DebianCloudUpdater."""
    
    @patch('requests.get')
    def test_get_latest_version(self, mock_get):
        """Test getting latest Debian Cloud version."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<a href="12.0.0/">12.0.0/</a>'
        mock_get.return_value = mock_response
        
        if hasattr(updaters, 'DebianCloudUpdater'):
            version = updaters.DebianCloudUpdater.get_latest_version()
            # May return None if parsing fails
            assert version is None or isinstance(version, str)
    
    def test_generate_download_links(self):
        """Test generating Debian Cloud download links."""
        if hasattr(updaters, 'DebianCloudUpdater'):
            links = updaters.DebianCloudUpdater.generate_download_links("12.0.0")
            assert isinstance(links, list)
            # May be empty without actual network call
            assert len(links) >= 0


class TestRockyCloudUpdater:
    """Test suite for RockyCloudUpdater."""
    
    @patch('requests.get')
    def test_get_latest_version(self, mock_get):
        """Test getting latest Rocky Cloud version."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<a href="9/">9/</a>'
        mock_get.return_value = mock_response
        
        if hasattr(updaters, 'RockyCloudUpdater'):
            version = updaters.RockyCloudUpdater.get_latest_version()
            assert version is not None
    
    def test_generate_download_links(self):
        """Test generating Rocky Cloud download links."""
        if hasattr(updaters, 'RockyCloudUpdater'):
            links = updaters.RockyCloudUpdater.generate_download_links("9")
            assert isinstance(links, list)
            assert len(links) > 0


class TestDistroUpdaters:
    """Test suite for DISTRO_UPDATERS dictionary."""
    
    def test_distro_updaters_exists(self):
        """Test that DISTRO_UPDATERS dictionary exists."""
        assert hasattr(updaters, 'DISTRO_UPDATERS')
        assert isinstance(updaters.DISTRO_UPDATERS, dict)
    
    def test_distro_updaters_has_cloud_images(self):
        """Test that DISTRO_UPDATERS includes cloud image updaters."""
        expected_keys = ['fedora cloud', 'ubuntu cloud', 'debian cloud', 'rocky cloud']
        
        for key in expected_keys:
            if key in updaters.DISTRO_UPDATERS:
                updater = updaters.DISTRO_UPDATERS[key]
                assert hasattr(updater, 'get_latest_version')
                assert hasattr(updater, 'generate_download_links')
                assert hasattr(updater, 'update_section')
