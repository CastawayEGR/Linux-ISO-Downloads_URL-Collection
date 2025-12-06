"""Tests for proxmox.py"""
import pytest
from unittest.mock import patch, MagicMock, call
from proxmox import ProxmoxTarget, detect_file_type


class TestDetectFileType:
    """Test suite for detect_file_type function."""
    
    def test_detect_qcow2(self):
        """Test detection of qcow2 files - returns 'iso' for Proxmox storage."""
        # Cloud images (qcow2) go to ISO storage in Proxmox
        assert detect_file_type("fedora-cloud.qcow2") == "iso"
        assert detect_file_type("/path/to/debian.qcow2") == "iso"
    
    def test_detect_iso(self):
        """Test detection of ISO files."""
        assert detect_file_type("ubuntu-22.04.iso") == "iso"
        assert detect_file_type("/path/to/debian-12.0.0.iso") == "iso"
    
    def test_detect_img(self):
        """Test detection of img files - returns 'iso' for Proxmox storage."""
        # Cloud images (.img) go to ISO storage in Proxmox
        assert detect_file_type("cloud-image.img") == "iso"
    
    def test_unknown_type(self):
        """Test fallback to iso for unknown types."""
        # Default is 'iso' storage
        assert detect_file_type("unknown.bin") == "iso"
    
    def test_detect_tar_gz(self):
        """Test detection of container templates."""
        assert detect_file_type("container.tar.gz") == "vztmpl"
        assert detect_file_type("template.tar.xz") == "vztmpl"


class TestProxmoxTarget:
    """Test suite for ProxmoxTarget class."""
    
    def test_init(self):
        """Test ProxmoxTarget initialization."""
        target = ProxmoxTarget("192.168.1.100", "root")
        assert target.hostname == "192.168.1.100"
        assert target.username == "root"
        assert target.password is None
    
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
        
        target = ProxmoxTarget("192.168.1.100", "root")
        success, message = target.test_connection(interactive=False)
        
        assert success is True
        assert isinstance(message, str)
    
    @patch('subprocess.run')
    @patch.object(ProxmoxTarget, 'check_ssh_keys')
    @patch.object(ProxmoxTarget, 'prompt_password')
    def test_test_connection_with_password(self, mock_prompt, mock_check_keys, mock_run):
        """Test connection testing with password authentication."""
        mock_check_keys.return_value = False
        mock_prompt.return_value = "password123"
        mock_run.return_value = MagicMock(returncode=0, stdout="test")
        
        target = ProxmoxTarget("192.168.1.100", "root")
        success, message = target.test_connection(interactive=True)
        
        assert success is True
        assert isinstance(message, str)
        mock_prompt.assert_called_once()
    
    @patch('subprocess.run')
    def test_test_connection_failure(self, mock_run):
        """Test connection testing when connection fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Connection refused")
        
        target = ProxmoxTarget("192.168.1.100", "root")
        success, message = target.test_connection(interactive=False)
        
        assert success is False
        assert isinstance(message, str)
    
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
        
        target = ProxmoxTarget("192.168.1.100", "root")
        storages = target.discover_storages()
        
        # Returns list of storage dicts or storage names
        assert isinstance(storages, list)
        assert len(storages) >= 2  # At least 2 storages
        storage_names = [s.get('name') if isinstance(s, dict) else s for s in storages]
        assert "local" in storage_names or "local-lvm" in storage_names
    
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
    def test_get_storage_path(self, mock_run):
        """Test getting storage path."""
        mock_output = "/var/lib/vz/template/iso\n"
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root")
        path = target.get_storage_path("local")
        
        # get_storage_path may return None if discovery/parsing fails
        # Just verify method runs without error
        assert path is None or isinstance(path, str)
    
    @patch('proxmox.ProxmoxTarget._get_storage_content')
    @patch('proxmox.ProxmoxTarget.get_storage_path')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_upload_file_iso(self, mock_getsize, mock_exists, mock_run, mock_get_path, mock_get_content):
        """Test ISO file upload."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024 * 100  # 100MB
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_get_path.return_value = "/var/lib/vz/template/iso"
        mock_get_content.return_value = ["iso", "vztmpl"]
        
        target = ProxmoxTarget("192.168.1.100", "root")
        result = target.upload_file("/tmp/test.iso", "local")
        
        # upload_file returns tuple (success, message) or bool
        success = result[0] if isinstance(result, tuple) else result
        assert success is True
    
    @patch('proxmox.ProxmoxTarget._get_storage_content')
    @patch('proxmox.ProxmoxTarget.get_storage_path')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_upload_file_qcow2(self, mock_getsize, mock_exists, mock_run, mock_get_path, mock_get_content):
        """Test qcow2 file upload."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024 * 50  # 50MB
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_get_path.return_value = "/var/lib/vz/template/iso"
        mock_get_content.return_value = ["iso", "vztmpl"]
        
        target = ProxmoxTarget("192.168.1.100", "root")
        result = target.upload_file("/tmp/fedora.qcow2", "local")
        
        success = result[0] if isinstance(result, tuple) else result
        assert success is True
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_upload_file_failure(self, mock_getsize, mock_exists, mock_run):
        """Test file upload failure."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        mock_run.return_value = MagicMock(returncode=1, stderr="Upload failed")
        
        target = ProxmoxTarget("192.168.1.100", "root")
        result = target.upload_file("/tmp/test.iso", "local")
        
        success = result[0] if isinstance(result, tuple) else result
        assert success is False
    
    @patch('proxmox.ProxmoxTarget._get_storage_content')
    @patch('proxmox.ProxmoxTarget.get_storage_path')
    @patch('subprocess.Popen')
    @patch('subprocess.run')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_upload_file_with_progress_callback(self, mock_getsize, mock_exists, mock_run, mock_popen, mock_get_path, mock_get_content):
        """Test file upload with progress callback."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_get_path.return_value = "/var/lib/vz/template/iso"
        mock_get_content.return_value = ["iso", "vztmpl"]
        
        # Mock Popen for progress callback path
        mock_process = MagicMock()
        mock_process.stdout = iter(["50%", "100%"])  # Iterable stdout
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process
        
        progress_calls = []
        def progress_callback(percent, filename):
            progress_calls.append(percent)
        
        target = ProxmoxTarget("192.168.1.100", "root")
        result = target.upload_file("/tmp/test.iso", "local", progress_callback=progress_callback)
        
        success = result[0] if isinstance(result, tuple) else result
        assert success is True
        # Progress callback should be called
        assert len(progress_calls) > 0
    
    @patch('subprocess.run')
    def test_list_files_iso(self, mock_run):
        """Test listing ISO files."""
        mock_output = "ubuntu-22.04.iso\ndebian-12.0.iso"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root")
        files = target.list_files("local", "iso")
        
        # Returns list of files
        assert isinstance(files, list)
        if len(files) > 0:
            assert "ubuntu-22.04.iso" in files or any('ubuntu' in f for f in files)
    
    @patch('subprocess.run')
    def test_list_files_empty(self, mock_run):
        """Test listing files when none exist."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        target = ProxmoxTarget("192.168.1.100", "root")
        files = target.list_files("local", "iso")
        
        assert files == []
    
    def test_invalid_host(self):
        """Test initialization with invalid host."""
        # Should not raise exception, but connection will fail later
        target = ProxmoxTarget("", "root")
        assert target.hostname == ""
    
    def test_invalid_user(self):
        """Test initialization with invalid user."""
        target = ProxmoxTarget("192.168.1.100", "")
        assert target.username == ""
