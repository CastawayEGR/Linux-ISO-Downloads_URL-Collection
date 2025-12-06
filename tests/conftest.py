"""Test fixtures and configuration for pytest."""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".config" / "distroget"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def temp_config_file(temp_config_dir):
    """Create a temporary config file with sample data."""
    config_file = temp_config_dir / "config.json"
    sample_config = {
        "location_history": ["/tmp/downloads", "/home/user/isos"],
        "proxmox": {
            "hostname": "192.168.1.100",
            "username": "root",
            "storage_mappings": {
                "iso": "local",
                "vztmpl": "local",
                "snippets": "local"
            }
        },
        "auto_update": {
            "enabled": True,
            "distributions": ["ubuntu", "debian"]
        },
        "auto_deploy_items": []
    }
    config_file.write_text(json.dumps(sample_config, indent=2))
    return config_file


@pytest.fixture
def mock_config_manager(temp_config_file):
    """Mock ConfigManager with temporary config file."""
    with patch('config_manager.CONFIG_FILE', temp_config_file):
        from config_manager import ConfigManager
        yield ConfigManager()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for testing commands without execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="mock output",
            stderr=""
        )
        yield mock_run


@pytest.fixture
def mock_requests():
    """Mock requests for testing HTTP calls."""
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "mock content"
        mock_response.content = b"mock content"
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def sample_distro_dict():
    """Sample distribution dictionary for testing."""
    return {
        "Ubuntu": {
            "22.04": [
                {
                    "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04-desktop-amd64.iso",
                    "filename": "ubuntu-22.04-desktop-amd64.iso",
                    "downloaded": False
                }
            ]
        },
        "Debian": {
            "12.0": [
                {
                    "url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.0.0-amd64-netinst.iso",
                    "filename": "debian-12.0.0-amd64-netinst.iso",
                    "downloaded": True,
                    "location": "/tmp/debian-12.0.0-amd64-netinst.iso"
                }
            ]
        }
    }


@pytest.fixture
def mock_proxmox_target():
    """Mock ProxmoxTarget for testing without actual SSH connections."""
    with patch('proxmox.ProxmoxTarget') as MockTarget:
        mock_instance = MagicMock()
        mock_instance.host = "192.168.1.100"
        mock_instance.user = "root"
        mock_instance.storage = "local"
        mock_instance.test_connection.return_value = True
        mock_instance.discover_storages.return_value = ["local", "local-lvm", "nfs-storage"]
        mock_instance.upload_file.return_value = True
        MockTarget.return_value = mock_instance
        yield mock_instance
