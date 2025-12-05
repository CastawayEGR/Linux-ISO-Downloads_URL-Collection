"""Tests for proxmox.py"""
import pytest
from unittest.mock import patch, MagicMock, call
from proxmox import ProxmoxTarget, detect_file_type


class TestDetectFileType:
    """Test suite for detect_file_type function."""
    
    def test_detect_qcow2(self):
        """Test detection of qcow2 files."""
        assert detect_file_type("fedora-cloud.qcow2") == "qcow2"
        assert detect_file_type("/path/to/debian.qcow2") == "qcow2"
    
    def test_detect_iso(self):
        """Test detection of ISO files."""
        assert detect_file_type("ubuntu-22.04.iso") == "iso"
        assert detect_file_type("/path/to/debian-12.0.0.iso") == "iso"
    
    def test_detect_img(self):
        """Test detection of img files."""
        assert detect_file_type("cloud-image.img") == "img"
    
    def test_unknown_type(self):
        """Test fallback to vztmpl for unknown types."""
        assert detect_file_type("unknown.bin") == "vztmpl"
        assert detect_file_type("archive.tar.gz") == "vztmpl"


class TestProxmoxTarget:
    """Test suite for ProxmoxTarget class."""
    
    def test_init(self):
        """Test ProxmoxTarget initialization."""
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        assert target.host == "192.168.1.100"
        assert target.user == "root"
        assert target.storage == "local"
    
    @patch('subprocess.run')
    def test_check_ssh_keys_success(self, mock_run):
        """Test SSH key detection when keys are available."""
        mock_run.return_value = MagicMock(returncode=0)
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        assert target.check_ssh_keys() is True
        
        # Verify SSH command with BatchMode
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "BatchMode=yes" in " ".join(call_args)
    
    @patch('subprocess.run')
    def test_check_ssh_keys_failure(self, mock_run):
        """Test SSH key detection when keys are not available."""
        mock_run.return_value = MagicMock(returncode=1)
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        assert target.check_ssh_keys() is False
    
    @patch('getpass.getpass')
    def test_prompt_password(self, mock_getpass):
        """Test password prompting."""
        mock_getpass.return_value = "test_password"
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        password = target.prompt_password()
        
        assert password == "test_password"
        mock_getpass.assert_called_once()
    
    @patch('subprocess.run')
    def test_test_connection_with_keys(self, mock_run):
        """Test connection testing with SSH keys."""
        mock_run.return_value = MagicMock(returncode=0, stdout="test")
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        result = target.test_connection(interactive=False)
        
        assert result is True
    
    @patch('subprocess.run')
    @patch.object(ProxmoxTarget, 'check_ssh_keys')
    @patch.object(ProxmoxTarget, 'prompt_password')
    def test_test_connection_with_password(self, mock_prompt, mock_check_keys, mock_run):
        """Test connection testing with password authentication."""
        mock_check_keys.return_value = False
        mock_prompt.return_value = "password123"
        mock_run.return_value = MagicMock(returncode=0, stdout="test")
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        result = target.test_connection(interactive=True)
        
        assert result is True
        mock_prompt.assert_called_once()
    
    @patch('subprocess.run')
    def test_test_connection_failure(self, mock_run):
        """Test connection testing when connection fails."""
        mock_run.return_value = MagicMock(returncode=1)
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        result = target.test_connection(interactive=False)
        
        assert result is False
    
    @patch('subprocess.run')
    def test_discover_storages(self, mock_run):
        """Test storage discovery."""
        mock_output = """local            dir      /var/lib/vz                            active  yes
local-lvm        lvmthin  data                                   active  yes
nfs-storage      nfs      10.0.0.5:/export/proxmox               active  yes"""
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        storages = target.discover_storages()
        
        assert "local" in storages
        assert "local-lvm" in storages
        assert "nfs-storage" in storages
        assert len(storages) == 3
    
    @patch('subprocess.run')
    def test_discover_storages_empty(self, mock_run):
        """Test storage discovery with no results."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        storages = target.discover_storages()
        
        assert storages == []
    
    @patch('subprocess.run')
    def test_get_storage_details(self, mock_run):
        """Test getting storage details."""
        mock_output = """dir: local
        path /var/lib/vz
        content backup,iso,vztmpl"""
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        details = target.get_storage_details("local")
        
        assert "dir: local" in details
        assert "path /var/lib/vz" in details
    
    @patch('subprocess.run')
    @patch('os.path.getsize')
    def test_upload_file_iso(self, mock_getsize, mock_run):
        """Test ISO file upload."""
        mock_getsize.return_value = 1024 * 1024 * 100  # 100MB
        mock_run.return_value = MagicMock(returncode=0)
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        result = target.upload_file("/tmp/test.iso")
        
        assert result is True
        mock_run.assert_called()
    
    @patch('subprocess.run')
    @patch('os.path.getsize')
    def test_upload_file_qcow2(self, mock_getsize, mock_run):
        """Test qcow2 file upload."""
        mock_getsize.return_value = 1024 * 1024 * 50  # 50MB
        mock_run.return_value = MagicMock(returncode=0)
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        result = target.upload_file("/tmp/fedora.qcow2")
        
        assert result is True
    
    @patch('subprocess.run')
    @patch('os.path.getsize')
    def test_upload_file_failure(self, mock_getsize, mock_run):
        """Test file upload failure."""
        mock_getsize.return_value = 1024 * 1024
        mock_run.return_value = MagicMock(returncode=1)
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        result = target.upload_file("/tmp/test.iso")
        
        assert result is False
    
    @patch('subprocess.run')
    @patch('os.path.getsize')
    def test_upload_file_with_progress_callback(self, mock_getsize, mock_run):
        """Test file upload with progress callback."""
        mock_getsize.return_value = 1024 * 1024
        mock_run.return_value = MagicMock(returncode=0)
        
        progress_calls = []
        def progress_callback(percent):
            progress_calls.append(percent)
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        result = target.upload_file("/tmp/test.iso", progress_callback=progress_callback)
        
        assert result is True
        # Progress callback should be called at least once for completion
        assert len(progress_calls) >= 1
    
    @patch('subprocess.run')
    def test_list_files_iso(self, mock_run):
        """Test listing ISO files."""
        mock_output = "ubuntu-22.04.iso\ndebian-12.0.iso"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        files = target.list_files("iso")
        
        assert "ubuntu-22.04.iso" in files
        assert "debian-12.0.iso" in files
    
    @patch('subprocess.run')
    def test_list_files_empty(self, mock_run):
        """Test listing files when none exist."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root", "local")
        files = target.list_files("iso")
        
        assert files == []
    
    def test_invalid_host(self):
        """Test initialization with invalid host."""
        # Should not raise exception, but connection will fail later
        target = ProxmoxTarget("", "root", "local")
        assert target.host == ""
    
    def test_invalid_user(self):
        """Test initialization with invalid user."""
        target = ProxmoxTarget("192.168.1.100", "", "local")
        assert target.user == ""
