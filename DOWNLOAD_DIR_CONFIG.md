# Auto-Update Download Directory Configuration

## Overview

The auto-update download directory is now fully configurable and persistent across runs.

## Configuration Methods

### 1. Interactive Configuration Menu

```bash
python3 distroget.py --configure
```

Then select:
- **Option 3**: Configure auto-update download directory

You'll be prompted for a directory path. The default is `~/Downloads/distroget-auto`.

### 2. Command Line Override

```bash
python3 distroget.py --auto-update --download-dir /custom/path
```

This overrides the configured directory for a single run.

### 3. Configuration File

The download directory is stored in `~/.config/distroget/config.json`:

```json
{
  "auto_update": {
    "enabled": true,
    "distributions": ["ubuntu", "debian"],
    "download_dir": "/path/to/downloads"
  }
}
```

## Auto-Enable Behavior

**New in this version**: Auto-update now automatically enables itself when:
- Distributions are configured, AND
- You run `--auto-update`

This means you no longer need to manually enable auto-update if you've configured distributions.

### Status Indicators

In the configure menu, you'll see:
- `✓ Enabled (3 distros)` - Auto-update is enabled with 3 distributions configured
- `⚠ Configured but disabled (3 distros)` - Distributions configured but flag is disabled (will auto-enable on run)
- `✗ Not configured` - No distributions configured

### Manual Toggle

You can manually toggle auto-update enabled/disabled in the configure menu:
- **Option 4**: Toggle auto-update enabled/disabled

## Usage Examples

### Set custom download directory and run auto-update:
```bash
python3 distroget.py --configure
# Select option 3, enter: /mnt/isos/auto-downloads
# Exit menu

python3 distroget.py --auto-update
# Uses /mnt/isos/auto-downloads
```

### One-time override:
```bash
python3 distroget.py --auto-update --download-dir /tmp/test-downloads
# Uses /tmp/test-downloads (doesn't save to config)
```

### For cron jobs:
```bash
# Uses configured directory from config
0 2 * * * /usr/bin/python3 /path/to/distroget.py --auto-update

# Or specify directory explicitly
0 2 * * * /usr/bin/python3 /path/to/distroget.py --auto-update --download-dir /data/isos
```

## Directory Creation

The directory will be created automatically:
- During configuration if you confirm the setting
- On first download if it doesn't exist

## Benefits

1. **Persistent Configuration**: No need to specify `--download-dir` every time
2. **Per-Environment Setup**: Different directories for dev/prod/staging
3. **Cron-Friendly**: Set once, runs automatically
4. **Auto-Enable**: No confusion about why auto-update "isn't working"
5. **Clear Status**: Configuration menu shows exactly what's configured

