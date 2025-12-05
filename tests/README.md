# Test Suite

This directory contains the test suite for distroget.

## Structure

- `conftest.py` - Pytest fixtures and test configuration
- `test_config_manager.py` - Tests for configuration management
- `test_proxmox.py` - Tests for Proxmox integration
- `test_auto_update.py` - Tests for auto-update functionality
- `test_updaters.py` - Tests for distribution updaters
- `test_configure.py` - Tests for configuration menus
- `test_downloads.py` - Tests for download manager (catches KeyError bugs)
- `test_integration.py` - Integration tests for UI and download workflows

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_config_manager.py
```

### Run specific test
```bash
pytest tests/test_config_manager.py::TestConfigManager::test_save_config
```

## Test Coverage

Current test coverage focuses on:
- Configuration management (ConfigManager class)
- Proxmox integration (ProxmoxTarget class)
- Auto-update functionality
- Distribution updaters
- Configuration menus
- Download manager (DownloadManager and status dict structure)
- Integration tests for UI workflows and user feedback

### Bug Prevention Tests

The test suite includes specific tests to prevent regression of known bugs:
- **KeyError on 'is_remote'**: Tests ensure `DownloadManager.get_status()` includes all required keys
- **Missing user feedback**: Tests verify local downloads show summary with target directory
- **Status dict compatibility**: Tests ensure local and remote managers have compatible status structures

## CI/CD

Tests automatically run on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Python versions: 3.8, 3.9, 3.10, 3.11, 3.12

See `.github/workflows/tests.yml` for details.
