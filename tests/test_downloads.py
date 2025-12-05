"""Tests for downloads.py"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import downloads


class TestDownloadManager:
    """Test suite for DownloadManager class."""
    
    def test_init(self, tmp_path):
        """Test DownloadManager initialization."""
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir)
        
        assert manager.target_dir == target_dir
        assert manager.max_workers == 3
        assert manager.running is True
    
    def test_get_status_includes_is_remote(self, tmp_path):
        """Test that get_status() includes 'is_remote' key.
        
        This test catches the bug where DownloadManager.get_status()
        was missing the 'is_remote' key, causing KeyError in UI code.
        """
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir)
        
        status = manager.get_status()
        
        # Critical: Must have 'is_remote' key
        assert 'is_remote' in status
        assert status['is_remote'] is False
    
    def test_get_status_structure(self, tmp_path):
        """Test that get_status() returns all expected keys."""
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir)
        
        status = manager.get_status()
        
        # Verify all expected keys are present
        expected_keys = [
            'active',
            'completed',
            'completed_urls',
            'failed',
            'retry_counts',
            'queued',
            'downloaded_files',
            'is_remote'
        ]
        
        for key in expected_keys:
            assert key in status, f"Missing key '{key}' in status dict"
    
    def test_get_status_types(self, tmp_path):
        """Test that get_status() returns correct data types."""
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir)
        
        status = manager.get_status()
        
        assert isinstance(status['active'], dict)
        assert isinstance(status['completed'], int)
        assert isinstance(status['completed_urls'], set)
        assert isinstance(status['failed'], int)
        assert isinstance(status['retry_counts'], dict)
        assert isinstance(status['queued'], int)
        assert isinstance(status['downloaded_files'], list)
        assert isinstance(status['is_remote'], bool)
    
    @patch('requests.get')
    def test_download_file_success(self, mock_get, tmp_path):
        """Test successful file download."""
        target_dir = tmp_path / "downloads"
        target_dir.mkdir()
        
        # Mock successful download
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content = lambda chunk_size: [b'test' * 256]
        mock_get.return_value = mock_response
        
        manager = downloads.DownloadManager(str(target_dir))
        manager._download_file('http://example.com/test.iso', 'test.iso')
        
        # Verify file was created
        downloaded_file = target_dir / 'test.iso'
        assert downloaded_file.exists()
    
    def test_start_creates_workers(self, tmp_path):
        """Test that start() creates worker threads."""
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir, max_workers=2)
        
        manager.start()
        
        assert len(manager.workers) == 2
        assert all(worker.is_alive() for worker in manager.workers)
        
        # Cleanup
        manager.stop()
    
    def test_add_download(self, tmp_path):
        """Test adding URL to download queue."""
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir)
        
        url = "http://example.com/test.iso"
        manager.add_download(url)
        
        assert manager.download_queue.qsize() == 1
    
    def test_stop(self, tmp_path):
        """Test stopping download manager."""
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir)
        manager.start()
        
        assert manager.running is True
        
        manager.stop()
        
        assert manager.running is False


class TestDownloadManagerIntegration:
    """Integration tests for DownloadManager with UI expectations."""
    
    def test_status_compatible_with_ui_code(self, tmp_path):
        """Test that status dict works with UI code pattern.
        
        This simulates the code in distroget.py line 812:
        if status['is_remote']:
        """
        target_dir = str(tmp_path / "downloads")
        manager = downloads.DownloadManager(target_dir)
        
        status = manager.get_status()
        
        # This should not raise KeyError
        try:
            if status['is_remote']:
                pass  # Remote handling
            else:
                pass  # Local handling
        except KeyError as e:
            pytest.fail(f"KeyError accessing status dict: {e}")
    
    def test_status_consistency_with_combined_manager(self, tmp_path):
        """Test that status keys match CombinedDownloadTransferManager.
        
        Both managers should return compatible status dicts.
        """
        from transfers import CombinedDownloadTransferManager
        
        # Create both managers
        local_dir = str(tmp_path / "downloads")
        local_manager = downloads.DownloadManager(local_dir)
        
        remote_manager = CombinedDownloadTransferManager(
            "192.168.1.100", "/tmp/uploads"
        )
        
        local_status = local_manager.get_status()
        remote_status = remote_manager.get_status()
        
        # Both should have 'is_remote' key
        assert 'is_remote' in local_status
        assert 'is_remote' in remote_status
        
        # Values should differ appropriately
        assert local_status['is_remote'] is False
        assert remote_status['is_remote'] is True
