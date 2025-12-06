# Test Specification Document

Complete specification of all 100 tests in the Linux ISO Downloads URL Collection project.

## Table of Contents
- [auto_update.py Tests](#auto_updatepy-tests)
- [config_manager.py Tests](#config_managerpy-tests)
- [configure.py Tests](#configurepy-tests)
- [downloads.py Tests](#downloadspy-tests)
- [integration Tests](#integration-tests)
- [proxmox.py Tests](#proxmoxpy-tests)
- [updaters.py Tests](#updaterspy-tests)

---

## auto_update.py Tests

### TestCheckAutoDeployItems (5 tests)

#### test_find_auto_deploy_items
**Purpose**: Verify the function can find and extract auto-deploy items from the distro dictionary.

**Test Setup**:
- Mocks ConfigManager to return configured auto-deploy paths
- Creates a sample distro dictionary with downloadable items
- Paths follow format: "Distro/Version"

**Success Criteria**:
- Returns list with exactly 1 item
- Item tuple contains correct path ("Debian/12.0")
- Item tuple contains correct filename

**Failure Conditions**:
- Empty list returned when items exist
- Wrong path or filename extracted
- Exception raised during processing

---

#### test_no_auto_deploy_items
**Purpose**: Verify graceful handling when no auto-deploy items are configured.

**Test Setup**:
- ConfigManager mocked to return empty list
- Sample distro dictionary provided

**Success Criteria**:
- Returns empty list `[]`
- No exceptions raised
- No attempts to process non-existent items

**Failure Conditions**:
- Non-empty list returned
- Exception raised
- Unexpected behavior

---

#### test_auto_deploy_item_not_found
**Purpose**: Verify handling when configured item doesn't exist in distro dictionary.

**Test Setup**:
- ConfigManager returns path "NonExistent/1.0/0"
- Distro dictionary doesn't contain this path

**Success Criteria**:
- Returns empty list `[]`
- Logs/prints that item not found
- No exceptions raised

**Failure Conditions**:
- Crashes with KeyError
- Returns non-empty list
- Doesn't handle missing path gracefully

---

#### test_auto_deploy_item_not_downloaded
**Purpose**: Verify handling of items that exist but haven't been downloaded.

**Test Setup**:
- ConfigManager returns valid path
- Item exists in distro dict but has no downloadable URLs

**Success Criteria**:
- Returns list (may be empty)
- No exceptions raised
- Handles missing download data gracefully

**Failure Conditions**:
- Exception raised
- Incorrect data structure returned

---

#### test_multiple_auto_deploy_items
**Purpose**: Verify processing of multiple auto-deploy items simultaneously.

**Test Setup**:
- ConfigManager returns 2+ paths
- Distro dictionary contains all paths with download URLs

**Success Criteria**:
- Returns list with correct number of items (2)
- All items properly extracted
- Order preserved or documented

**Failure Conditions**:
- Wrong number of items
- Duplicate items
- Missing items

---

### TestDeployFilesToProxmox (5 tests)

#### test_deploy_with_ssh_keys
**Purpose**: Verify deployment works using SSH key authentication (passwordless).

**Test Setup**:
- Proxmox configured with hostname and username
- SSH keys available (check_ssh_keys returns True)
- Mock file upload succeeds

**Success Criteria**:
- Returns list of deployment results
- upload_file called for each file
- prompt_password NOT called (using keys)
- No password requested

**Failure Conditions**:
- Password prompted when keys available
- Upload not attempted
- Exception raised

---

#### test_deploy_with_password
**Purpose**: Verify deployment works using password authentication when SSH keys unavailable.

**Test Setup**:
- Proxmox configured
- SSH keys NOT available (check_ssh_keys returns False)
- Interactive mode enabled
- Password prompt returns "password123"

**Success Criteria**:
- Returns list of results
- prompt_password called exactly once
- upload_file called after password entered
- Deployment succeeds

**Failure Conditions**:
- Password not prompted in interactive mode
- Upload attempted without authentication
- Multiple password prompts

---

#### test_deploy_no_proxmox_config
**Purpose**: Verify graceful handling when Proxmox is not configured.

**Test Setup**:
- ConfigManager returns empty hostname
- Files provided for deployment

**Success Criteria**:
- Returns empty list `[]`
- Error message displayed to user
- ProxmoxTarget NOT instantiated
- No deployment attempted

**Failure Conditions**:
- Attempts connection without config
- Exception raised
- Unclear error message

---

#### test_deploy_upload_failure
**Purpose**: Verify handling when file upload fails.

**Test Setup**:
- Proxmox properly configured
- Connection succeeds
- upload_file returns (False, "Upload failed")

**Success Criteria**:
- Returns list of results (including failure)
- Failure properly recorded
- Continues processing (doesn't crash)
- User informed of failure

**Failure Conditions**:
- Exception raised on failure
- Partial upload not handled
- User not informed

---

#### test_deploy_empty_file_list
**Purpose**: Verify handling of empty file list.

**Test Setup**:
- Proxmox configured
- Empty list passed as files parameter

**Success Criteria**:
- Returns empty list `[]`
- No upload attempts
- No exceptions
- Handles gracefully

**Failure Conditions**:
- Exception raised
- Unnecessary operations performed

---

### TestAutoUpdateDistributions (4 tests)

#### test_auto_update_basic
**Purpose**: Verify basic auto-update workflow for a single distribution.

**Test Setup**:
- ConfigManager returns ["ubuntu"] for auto-update list
- Mock updater returns version "22.04"
- Mock download links generated
- download_dir parameter provided

**Success Criteria**:
- Returns dict with status information
- No exceptions raised
- Version check performed
- Links generated

**Failure Conditions**:
- Exception raised
- Wrong data type returned
- Download not initiated

---

#### test_auto_update_no_distributions
**Purpose**: Verify handling when no distributions configured for auto-update.

**Test Setup**:
- ConfigManager returns empty list
- download_dir provided

**Success Criteria**:
- Returns dict with status='no_distros'
- Helpful message displayed
- No exceptions raised
- Suggests configuration command

**Failure Conditions**:
- Exception raised
- Attempts update anyway
- Unclear error message

---

#### test_auto_update_with_deployment
**Purpose**: Verify auto-update can trigger Proxmox deployment.

**Test Setup**:
- Auto-update configured
- Auto-deploy items configured
- Proxmox configured

**Success Criteria**:
- Update proceeds
- Deployment triggered after download
- Returns success status

**Failure Conditions**:
- Update and deploy not coordinated
- Exception raised

---

#### test_auto_update_updater_exception
**Purpose**: Verify graceful handling of updater exceptions.

**Test Setup**:
- Configured distribution
- Updater raises exception during processing

**Success Criteria**:
- Exception caught and handled
- Error logged
- Other distributions still processed
- Returns result dict

**Failure Conditions**:
- Unhandled exception propagates
- All updates stopped
- Silent failure

---

### TestMainFunction (1 test)

#### test_main_execution
**Purpose**: Verify the main() function can be called without errors.

**Success Criteria**:
- main() function exists
- Can be called
- No immediate exceptions

**Failure Conditions**:
- Function doesn't exist
- Immediate crash

---

## config_manager.py Tests

### TestConfigManager (16 tests)

#### test_init_creates_config_file
**Purpose**: Verify ConfigManager initializes properly with new config file.

**Test Setup**:
- Temporary directory with no existing config
- Create ConfigManager instance with custom path

**Success Criteria**:
- config attribute is not None (dict loaded)
- config_path set correctly to provided path
- No exceptions during init

**Failure Conditions**:
- config is None
- config_path not set
- Exception raised

---

#### test_load_existing_config
**Purpose**: Verify ConfigManager loads existing configuration file.

**Test Setup**:
- Temporary config file with predefined values
- Create ConfigManager pointing to that file

**Success Criteria**:
- Config loaded correctly
- Contains "location_history" key
- Contains "proxmox" key
- proxmox.hostname == "192.168.1.100"

**Failure Conditions**:
- Config not loaded
- Data corrupted
- Wrong values returned

---

#### test_save_config
**Purpose**: Verify configuration can be saved to disk.

**Test Setup**:
- Create ConfigManager
- Add test data to config
- Call save()
- Read file directly and verify

**Success Criteria**:
- File created on disk
- Contains saved data
- JSON properly formatted
- Data persists after reload

**Failure Conditions**:
- File not created
- Data not written
- JSON malformed

---

#### test_add_to_location_history
**Purpose**: Verify adding download locations to history.

**Test Setup**:
- Load existing config
- Record initial history count
- Add new location

**Success Criteria**:
- History count increases by 1
- New location at index 0 (front)
- Order: newest first

**Failure Conditions**:
- Count doesn't increase
- Wrong position
- Duplicate entry created

---

#### test_location_history_max_size
**Purpose**: Verify location history limited to 10 entries.

**Test Setup**:
- Create new ConfigManager
- Add 15 different locations

**Success Criteria**:
- History length exactly 10
- Newest entry (14) at index 0
- Oldest entries dropped (0-4)

**Failure Conditions**:
- More than 10 entries stored
- Wrong entries dropped
- Order incorrect

---

#### test_location_history_deduplication
**Purpose**: Verify duplicate locations removed/moved to front.

**Test Setup**:
- Add location A
- Add other locations
- Add location A again

**Success Criteria**:
- Count doesn't increase on duplicate
- Location A moved to front (index 0)
- Only one instance of location A

**Failure Conditions**:
- Duplicate entries exist
- Count increased
- Wrong location at front

---

#### test_get_proxmox_config
**Purpose**: Verify retrieving Proxmox configuration.

**Test Setup**:
- Load config with Proxmox settings

**Success Criteria**:
- Returns dict
- Contains hostname == "192.168.1.100"
- Contains username == "root"
- No password field

**Failure Conditions**:
- Wrong or missing data
- Password field present
- Exception raised

---

#### test_set_proxmox_config
**Purpose**: Verify setting Proxmox configuration.

**Test Setup**:
- Create new ConfigManager
- Call set_proxmox_config() with values
- Retrieve config

**Success Criteria**:
- hostname set to "10.0.0.5"
- username set to "admin"
- Config saved correctly
- Can be retrieved

**Failure Conditions**:
- Values not set
- Not persisted
- Wrong values

---

#### test_get_auto_update_distributions
**Purpose**: Verify retrieving list of distributions for auto-update.

**Test Setup**:
- Load config with auto-update distros

**Success Criteria**:
- Returns list
- Contains "ubuntu"
- Contains "debian"

**Failure Conditions**:
- Wrong type returned
- Missing distributions
- Extra unexpected items

---

#### test_set_auto_update_distributions
**Purpose**: Verify setting auto-update distribution list.

**Test Setup**:
- Create ConfigManager
- Set distros ["fedora", "rocky", "arch"]
- Retrieve distros

**Success Criteria**:
- Returns exactly ["fedora", "rocky", "arch"]
- Order preserved
- Old values replaced

**Failure Conditions**:
- Wrong values
- Merged with old values
- Not saved

---

#### test_get_auto_deploy_items_empty
**Purpose**: Verify getting auto-deploy items when none configured.

**Test Setup**:
- Create new ConfigManager (empty config)

**Success Criteria**:
- Returns empty list `[]`
- No exceptions

**Failure Conditions**:
- Returns None
- Exception raised
- Wrong type

---

#### test_add_auto_deploy_item
**Purpose**: Verify adding item to auto-deploy list.

**Test Setup**:
- Create ConfigManager
- Toggle item "Ubuntu/22.04/0" (adds it)
- Retrieve list

**Success Criteria**:
- Item present in list
- Can be retrieved

**Failure Conditions**:
- Item not added
- Duplicate created
- Wrong item added

---

#### test_remove_auto_deploy_item
**Purpose**: Verify removing item from auto-deploy list.

**Test Setup**:
- Add item "Ubuntu/22.04/0"
- Verify it's present
- Toggle again (removes it)
- Verify absent

**Success Criteria**:
- Item present after first toggle
- Item absent after second toggle
- No exceptions

**Failure Conditions**:
- Item not removed
- Exception on removal
- List corruption

---

#### test_toggle_auto_deploy_item
**Purpose**: Verify toggle functionality adds/removes items.

**Test Setup**:
- Start with empty list
- Toggle item (should add)
- Toggle same item (should remove)

**Success Criteria**:
- First toggle adds item
- Second toggle removes item
- Idempotent behavior

**Failure Conditions**:
- Toggle doesn't work
- State inconsistent
- Exception raised

---

#### test_config_migration
**Purpose**: Verify old config format loads without errors.

**Test Setup**:
- Create old-style config file (missing new fields)
- Load with ConfigManager

**Success Criteria**:
- Loads without exception
- Config not None
- Contains proxmox section
- Missing fields handled gracefully

**Failure Conditions**:
- Exception on load
- Data lost
- Crash on missing fields

---

#### test_no_password_storage
**Purpose**: CRITICAL - Verify passwords never stored in config file.

**Test Setup**:
- Set Proxmox config (password intentionally not in API)
- Save config
- Read file directly from disk
- Parse JSON

**Success Criteria**:
- No "password" field in proxmox config
- File doesn't contain password string
- Security maintained

**Failure Conditions**:
- Password found in file
- Security violation
- Password leaked

---

## configure.py Tests

### TestConfigureProxmoxMenu (2 tests)

#### test_configure_proxmox_basic
**Purpose**: Verify Proxmox configuration menu structure exists.

**Test Setup**:
- Mock curses
- Mock ConfigManager
- Mock ProxmoxTarget

**Success Criteria**:
- Function configure_proxmox_menu exists
- Is callable
- Returns without error in test

**Failure Conditions**:
- Function doesn't exist
- Not callable
- Immediate exception

---

#### test_configure_proxmox_with_existing_config
**Purpose**: Verify menu can load existing Proxmox configuration.

**Test Setup**:
- Mock ConfigManager with existing config

**Success Criteria**:
- Can retrieve config with host="192.168.1.100"
- Config accessible to menu

**Failure Conditions**:
- Can't access config
- Wrong values

---

### TestConfigureAutoUpdateMenu (2 tests)

#### test_configure_auto_update_basic
**Purpose**: Verify auto-update configuration menu exists.

**Test Setup**:
- Mock curses and ConfigManager
- Mock DISTRO_UPDATERS

**Success Criteria**:
- Function exists and is callable
- No immediate errors

**Failure Conditions**:
- Function missing
- Crashes on call

---

#### test_configure_auto_update_with_selections
**Purpose**: Verify menu can handle existing distribution selections.

**Test Setup**:
- Mock with pre-selected ["ubuntu", "debian"]
- Mock available updaters

**Success Criteria**:
- Can retrieve selected distributions
- Contains "ubuntu" and "debian"

**Failure Conditions**:
- Can't access selections
- Wrong distributions

---

### TestMainConfigMenu (2 tests)

#### test_main_menu_structure
**Purpose**: Verify main configuration menu structure.

**Test Setup**:
- Mock all sub-menus

**Success Criteria**:
- main_config_menu function exists
- Is callable

**Failure Conditions**:
- Function doesn't exist
- Not callable

---

#### test_main_menu_callable
**Purpose**: Verify main menu can be invoked.

**Test Setup**:
- Mock curses

**Success Criteria**:
- Function defined in module
- Callable without immediate crash

**Failure Conditions**:
- Not defined
- Immediate exception

---

### TestConfigureIntegration (3 tests)

#### test_module_imports
**Purpose**: Verify all required modules imported.

**Success Criteria**:
- configure.ConfigManager exists
- configure.ProxmoxTarget exists
- configure.DISTRO_UPDATERS exists

**Failure Conditions**:
- Import missing
- Module not accessible

---

#### test_all_functions_defined
**Purpose**: Verify all main menu functions exist.

**Success Criteria**:
- configure_proxmox_menu defined
- configure_auto_update_menu defined
- main_config_menu defined
- All are callable

**Failure Conditions**:
- Function missing
- Not callable

---

#### test_config_manager_integration
**Purpose**: Verify ConfigManager integrates with configure module.

**Test Setup**:
- Mock ConfigManager with methods

**Success Criteria**:
- Can access get_proxmox_config()
- Can access get_auto_update_distributions()
- Methods return data

**Failure Conditions**:
- Methods not accessible
- Integration broken

---

## downloads.py Tests

### TestDownloadManager (8 tests)

#### test_init
**Purpose**: Verify DownloadManager initializes correctly.

**Test Setup**:
- Create with tmp_path directory

**Success Criteria**:
- target_dir set correctly
- max_workers == 3 (default)
- running == True

**Failure Conditions**:
- Attributes not set
- Wrong default values
- Exception raised

---

#### test_get_status_includes_is_remote
**Purpose**: CRITICAL - Verify status dict includes 'is_remote' key.
**Bug Prevention**: This catches KeyError in distroget.py line 812.

**Test Setup**:
- Create DownloadManager
- Call get_status()

**Success Criteria**:
- Returns dict with 'is_remote' key
- is_remote == False (local downloads)

**Failure Conditions**:
- KeyError: 'is_remote'
- Key missing from dict
- Wrong value

---

#### test_get_status_structure
**Purpose**: Verify get_status() returns all required keys.

**Test Setup**:
- Create DownloadManager
- Get status dict

**Success Criteria**:
- Contains all 8 required keys:
  - active, completed, completed_urls
  - failed, retry_counts, queued
  - downloaded_files, is_remote

**Failure Conditions**:
- Any key missing
- Extra unexpected keys
- Wrong structure

---

#### test_get_status_types
**Purpose**: Verify get_status() returns correct data types.

**Test Setup**:
- Create DownloadManager
- Get status and check types

**Success Criteria**:
- active: dict
- completed: int
- completed_urls: set
- failed: int
- retry_counts: dict
- queued: int
- downloaded_files: list
- is_remote: bool

**Failure Conditions**:
- Wrong type for any field
- None values
- Inconsistent types

---

#### test_download_file_success
**Purpose**: Verify successful file download.

**Test Setup**:
- Mock requests.get with 200 response
- Mock file content
- Call _download_file()

**Success Criteria**:
- File created in target directory
- File exists on disk
- Content written

**Failure Conditions**:
- File not created
- Empty file
- Wrong location

---

#### test_start_creates_workers
**Purpose**: Verify start() creates worker threads.

**Test Setup**:
- Create with max_workers=2
- Call start()

**Success Criteria**:
- workers list has 2 threads
- All threads are alive
- Threads started properly

**Failure Conditions**:
- Wrong number of workers
- Threads not started
- Threads dead

---

#### test_add_download
**Purpose**: Verify adding URL to download queue.

**Test Setup**:
- Create DownloadManager
- Add URL via add_download()

**Success Criteria**:
- Queue size increased to 1
- URL in queue

**Failure Conditions**:
- Queue empty
- URL not added
- Duplicate entries

---

#### test_stop
**Purpose**: Verify stopping download manager.

**Test Setup**:
- Start manager
- Verify running == True
- Call stop()

**Success Criteria**:
- running == False after stop
- Workers joined
- Clean shutdown

**Failure Conditions**:
- Still running after stop
- Hanging threads
- Exception raised

---

### TestDownloadManagerIntegration (2 tests)

#### test_status_compatible_with_ui_code
**Purpose**: CRITICAL - Verify status dict works with UI code pattern.
**Bug Context**: Simulates distroget.py line 812: `if status['is_remote']:`

**Test Setup**:
- Create DownloadManager
- Get status
- Access status['is_remote'] (as UI does)

**Success Criteria**:
- No KeyError raised
- Can check `if status['is_remote']:`
- Boolean value returned

**Failure Conditions**:
- KeyError on access
- Wrong type (not bool)
- Exception raised

---

#### test_status_consistency_with_combined_manager
**Purpose**: Verify local and remote managers have compatible status dicts.

**Test Setup**:
- Create DownloadManager (local)
- Create CombinedDownloadTransferManager (remote)
- Get status from both

**Success Criteria**:
- Both have 'is_remote' key
- Local: is_remote == False
- Remote: is_remote == True
- Same structure/keys

**Failure Conditions**:
- Different keys
- Wrong boolean values
- Incompatible structures

---

## integration Tests

### TestLocalDownloadFeedback (4 tests)

#### test_local_download_shows_summary
**Purpose**: CRITICAL - Verify local downloads show summary to user.
**Bug Context**: Original bug had silent downloads with no location shown.

**Test Setup**:
- Mock DownloadManager with completed downloads
- Mock is_remote == False

**Success Criteria**:
- Status accessible
- is_remote key present
- Value is False

**Failure Conditions**:
- Silent completion
- No feedback
- Missing is_remote

---

#### test_local_download_summary_includes_location
**Purpose**: Verify users are told WHERE files were downloaded.

**Test Setup**:
- Mock completed download
- Check downloaded_files list

**Success Criteria**:
- downloaded_files list populated
- Contains file paths
- completed count > 0

**Failure Conditions**:
- Empty files list
- No location info
- Count zero

---

#### test_local_download_lists_files
**Purpose**: Verify summary lists individual files, not just count.

**Test Setup**:
- Mock 3 completed files
- Check downloaded_files contains all

**Success Criteria**:
- downloaded_files length == 3
- All 3 files present in list
- Correct paths

**Failure Conditions**:
- Missing files
- Wrong count
- Empty list

---

#### test_remote_vs_local_status_keys
**Purpose**: Prevent KeyError when UI checks status['is_remote'].

**Test Setup**:
- Create both manager types
- Get status from each

**Success Criteria**:
- Both have 'is_remote' key
- Both are boolean type
- Local: False, Remote: True

**Failure Conditions**:
- Missing key in either
- Wrong type
- Wrong values

---

### TestDownloadCompletionFlow (3 tests)

#### test_completion_shows_file_sizes
**Purpose**: Verify completion shows human-readable file sizes.

**Test Setup**:
- Mock downloaded file
- Mock os.path.getsize returns 100MB
- Check display

**Success Criteria**:
- File sizes retrieved
- Sizes displayed to user

**Failure Conditions**:
- No size information
- Wrong sizes
- Size not readable

---

#### test_completion_handles_no_downloads
**Purpose**: Verify graceful handling when no files downloaded.

**Test Setup**:
- Complete with zero downloads

**Success Criteria**:
- No exceptions
- Appropriate message
- Clean completion

**Failure Conditions**:
- Exception raised
- Crash
- Unclear state

---

#### test_completion_shows_failures
**Purpose**: Verify failed downloads reported to user.

**Test Setup**:
- Mock some failed downloads

**Success Criteria**:
- Failures counted
- Failures reported
- User informed

**Failure Conditions**:
- Failures hidden
- Silent failure
- No error info

---

### TestUIStatusCompatibility (2 tests)

#### test_status_dict_has_required_keys_for_ui
**Purpose**: Verify status dict has all keys UI expects.

**Test Setup**:
- Create manager
- Get status

**Success Criteria**:
- Has is_remote
- Has active
- Has completed
- Has other required keys

**Failure Conditions**:
- Missing any key
- Wrong structure

---

#### test_status_active_is_dict
**Purpose**: Verify 'active' field is dict (UI iterates over it).

**Test Setup**:
- Get status
- Check type of active field

**Success Criteria**:
- active is dict type
- Can iterate over it
- Compatible with UI code

**Failure Conditions**:
- Wrong type (list, None, etc.)
- Not iterable
- UI crashes

---

## proxmox.py Tests

### TestDetectFileType (5 tests)

#### test_detect_qcow2
**Purpose**: Verify qcow2 files detected as 'iso' storage type.
**Design Note**: In Proxmox, cloud images go to ISO storage.

**Test Setup**:
- Test "fedora-cloud.qcow2"
- Test "/path/to/debian.qcow2"

**Success Criteria**:
- Both return "iso"
- Correct Proxmox storage mapping

**Failure Conditions**:
- Returns "qcow2" (wrong for Proxmox)
- Returns wrong type
- Exception raised

---

#### test_detect_iso
**Purpose**: Verify ISO files correctly detected.

**Test Setup**:
- Test "ubuntu-22.04.iso"
- Test "/path/to/debian-12.0.0.iso"

**Success Criteria**:
- Both return "iso"
- Path handling correct

**Failure Conditions**:
- Wrong type returned
- Path not handled

---

#### test_detect_img
**Purpose**: Verify .img files detected as 'iso' storage.
**Design Note**: Like qcow2, .img goes to ISO storage.

**Test Setup**:
- Test "cloud-image.img"

**Success Criteria**:
- Returns "iso"

**Failure Conditions**:
- Returns "img"
- Wrong type

---

#### test_unknown_type
**Purpose**: Verify unknown files default to 'iso'.

**Test Setup**:
- Test "unknown.bin"

**Success Criteria**:
- Returns "iso" (safe default)

**Failure Conditions**:
- Returns "vztmpl"
- Throws exception

---

#### test_detect_tar_gz
**Purpose**: Verify container templates detected.

**Test Setup**:
- Test .tar.gz and .tar.xz files

**Success Criteria**:
- Return "vztmpl"
- Correct container template mapping

**Failure Conditions**:
- Wrong type
- Not recognized

---

### TestProxmoxTarget (18 tests)

#### test_init
**Purpose**: Verify ProxmoxTarget initialization.

**Success Criteria**:
- hostname set to "192.168.1.100"
- username set to "root"
- password is None (not provided)

**Failure Conditions**:
- Attributes wrong or missing
- Exception raised

---

#### test_check_ssh_keys_success
**Purpose**: Verify SSH key detection when keys available.

**Test Setup**:
- Mock subprocess.run returns 0 (success)

**Success Criteria**:
- Returns True
- BatchMode=yes in SSH command
- No password prompt

**Failure Conditions**:
- Returns False (keys present)
- Prompts for password
- Exception raised

---

#### test_check_ssh_keys_failure
**Purpose**: Verify detection when SSH keys not available.

**Test Setup**:
- Mock subprocess.run returns 1 (failure)

**Success Criteria**:
- Returns False
- Correct detection

**Failure Conditions**:
- Returns True (no keys)
- Wrong detection

---

#### test_prompt_password
**Purpose**: Verify password prompting.

**Test Setup**:
- Mock getpass.getpass

**Success Criteria**:
- Returns entered password
- getpass called once
- Password not echoed

**Failure Conditions**:
- Wrong password
- Not called
- Exception

---

#### test_test_connection_with_keys
**Purpose**: Verify connection test with SSH keys.

**Test Setup**:
- Mock successful SSH connection

**Success Criteria**:
- Returns tuple (True, message)
- success is True
- message is string

**Failure Conditions**:
- Wrong return type
- success is False
- No message

---

#### test_test_connection_with_password
**Purpose**: Verify connection test with password auth.

**Test Setup**:
- Mock no SSH keys
- Mock password prompt
- Mock successful connection

**Success Criteria**:
- Returns (True, message)
- Password prompted
- Connection succeeds

**Failure Conditions**:
- Password not requested
- Connection fails
- Wrong return type

---

#### test_test_connection_failure
**Purpose**: Verify handling of connection failure.

**Test Setup**:
- Mock failed SSH attempt

**Success Criteria**:
- Returns (False, error_message)
- success is False
- Error message descriptive

**Failure Conditions**:
- Returns True on failure
- Exception raised
- No error info

---

#### test_discover_storages
**Purpose**: Verify Proxmox storage discovery.

**Test Setup**:
- Mock pvesm status output with multiple storages

**Success Criteria**:
- Returns list of storages
- Length >= 2
- Contains "local" or "local-lvm"

**Failure Conditions**:
- Empty list
- Wrong parsing
- Missing storages

---

#### test_discover_storages_empty
**Purpose**: Verify handling of no storages found.

**Test Setup**:
- Mock empty pvesm output

**Success Criteria**:
- Returns empty list []
- No exception

**Failure Conditions**:
- Exception raised
- Non-empty list

---

#### test_get_storage_path
**Purpose**: Verify getting storage mount path.

**Test Setup**:
- Mock storage path query

**Success Criteria**:
- Returns string path or None
- No exception

**Failure Conditions**:
- Exception raised
- Invalid return

---

#### test_upload_file_iso
**Purpose**: Verify ISO file upload.

**Test Setup**:
- Mock file exists
- Mock successful upload

**Success Criteria**:
- Returns (True, message)
- success is True
- Upload completed

**Failure Conditions**:
- Returns False
- Upload fails
- Exception

---

#### test_upload_file_qcow2
**Purpose**: Verify qcow2 file upload.

**Test Setup**:
- Mock file exists
- Mock successful upload

**Success Criteria**:
- Returns (True, message)
- Uploads to ISO storage
- Success

**Failure Conditions**:
- Wrong storage type
- Upload fails

---

#### test_upload_file_failure
**Purpose**: Verify upload failure handling.

**Test Setup**:
- Mock upload returns error

**Success Criteria**:
- Returns (False, error)
- success is False
- Error message present

**Failure Conditions**:
- Exception raised
- Silent failure

---

#### test_upload_file_with_progress_callback
**Purpose**: Verify upload with progress reporting.
**Critical**: This test must not hang (was blocking on stdout iteration).

**Test Setup**:
- Mock Popen with iterable stdout
- Mock progress output "50%", "100%"
- Provide callback function

**Success Criteria**:
- Returns (True, message)
- Callback invoked with progress
- len(progress_calls) > 0
- No hang/timeout

**Failure Conditions**:
- Test hangs forever
- Callback not called
- Upload fails

---

#### test_list_files_iso
**Purpose**: Verify listing files in storage.

**Test Setup**:
- Mock ls output with filenames

**Success Criteria**:
- Returns list
- Contains expected files
- Correct parsing

**Failure Conditions**:
- Empty when files exist
- Wrong files
- Exception

---

#### test_list_files_empty
**Purpose**: Verify listing empty storage.

**Test Setup**:
- Mock empty ls output

**Success Criteria**:
- Returns empty list []
- No exception

**Failure Conditions**:
- Exception raised
- Non-empty list

---

#### test_invalid_host
**Purpose**: Verify handling of invalid hostname.

**Test Setup**:
- Create with empty or invalid hostname

**Success Criteria**:
- No exception during init
- hostname stored as provided
- Failure occurs on connection attempt

**Failure Conditions**:
- Exception on init
- Crash

---

#### test_invalid_user
**Purpose**: Verify handling of invalid username.

**Test Setup**:
- Create with empty username

**Success Criteria**:
- No exception during init
- username stored as provided
- Failure on connection

**Failure Conditions**:
- Exception on init

---

## updaters.py Tests

### TestDistroUpdater (5 tests)

#### test_get_latest_version_not_implemented
**Purpose**: Verify base class raises NotImplementedError.

**Success Criteria**:
- Raises NotImplementedError
- Cannot be called directly

**Failure Conditions**:
- Returns value (shouldn't)
- No exception

---

#### test_generate_download_links_not_implemented
**Purpose**: Verify base method not implemented.

**Success Criteria**:
- Raises NotImplementedError

**Failure Conditions**:
- Returns value
- Silent failure

---

#### test_update_section_not_implemented
**Purpose**: Verify update_section raises error in base class.

**Success Criteria**:
- Raises NotImplementedError

**Failure Conditions**:
- Returns value

---

#### test_add_metadata_comment
**Purpose**: Verify metadata comment added to sections.

**Test Setup**:
- Metadata with auto_updated=True and date

**Success Criteria**:
- Comment "<!-- Auto-updated: 2024-01-01 -->" present
- Original content preserved

**Failure Conditions**:
- No comment added
- Content lost

---

#### test_add_metadata_comment_no_metadata
**Purpose**: Verify no comment added without metadata.

**Test Setup**:
- metadata=None

**Success Criteria**:
- Section unchanged
- No <!-- --> tags

**Failure Conditions**:
- Comment added
- Section modified

---

### TestGetDistrowatchVersion (3 tests)

#### test_get_version_success
**Purpose**: Verify scraping DistroWatch for version.

**Test Setup**:
- Mock successful HTTP response with version

**Success Criteria**:
- Returns version string (not None)
- Version extracted correctly

**Failure Conditions**:
- Returns None on success
- Wrong version

---

#### test_get_version_http_error
**Purpose**: Verify handling of 404/HTTP errors.

**Test Setup**:
- Mock 404 response

**Success Criteria**:
- Returns None
- No exception raised

**Failure Conditions**:
- Exception propagates
- Crash

---

#### test_get_version_network_error
**Purpose**: Verify handling of network errors.

**Test Setup**:
- Mock raises network exception

**Success Criteria**:
- Returns None
- Exception caught

**Failure Conditions**:
- Unhandled exception
- Crash

---

### TestFedoraCloudUpdater (2 tests)

#### test_get_latest_version
**Purpose**: Verify getting latest Fedora Cloud versions.

**Test Setup**:
- Mock fetch_fedora_releases with versions 40, 39

**Success Criteria**:
- Returns version list or string
- version is not None

**Failure Conditions**:
- Returns None
- Exception raised

---

#### test_generate_download_links
**Purpose**: Verify generating Fedora Cloud download links.

**Test Setup**:
- Mock releases data

**Success Criteria**:
- Returns dict with version keys
- Contains '40' or has links

**Failure Conditions**:
- Wrong return type (not dict)
- Empty when data available

---

### TestUbuntuCloudUpdater (2 tests)

#### test_get_latest_version
**Purpose**: Verify getting Ubuntu Cloud version.

**Test Setup**:
- Mock HTML with release names

**Success Criteria**:
- Returns version (or None if parsing fails)
- No exception

**Failure Conditions**:
- Exception raised
- Crash on parse error

---

#### test_generate_download_links
**Purpose**: Verify generating Ubuntu links.

**Success Criteria**:
- Returns list or dict
- Proper structure

**Failure Conditions**:
- Wrong type
- Exception

---

### TestDebianCloudUpdater (2 tests)

#### test_get_latest_version
**Purpose**: Verify getting Debian version.

**Test Setup**:
- Mock response with version

**Success Criteria**:
- Returns version string or None
- No exception

**Failure Conditions**:
- Exception raised

---

#### test_generate_download_links
**Purpose**: Verify generating Debian links.

**Success Criteria**:
- Returns list
- len(links) >= 0 (may be empty without network)

**Failure Conditions**:
- Wrong type
- Exception

---

### TestRockyCloudUpdater (2 tests)

#### test_get_latest_version
**Purpose**: Verify getting Rocky Linux version.

**Test Setup**:
- Mock HTML response

**Success Criteria**:
- version is not None
- Valid version returned

**Failure Conditions**:
- Returns None
- Exception

---

#### test_generate_download_links
**Purpose**: Verify generating Rocky links.

**Success Criteria**:
- Returns list
- len(links) > 0

**Failure Conditions**:
- Empty list
- Wrong type

---

### TestDistroUpdaters (2 tests)

#### test_distro_updaters_exists
**Purpose**: Verify DISTRO_UPDATERS dict exists.

**Success Criteria**:
- Attribute exists
- Is dict type

**Failure Conditions**:
- Doesn't exist
- Wrong type

---

#### test_distro_updaters_has_cloud_images
**Purpose**: Verify cloud image updaters registered.

**Success Criteria**:
- DISTRO_UPDATERS contains cloud updater classes

**Failure Conditions**:
- Missing updaters
- Wrong structure

---

## Test Coverage Summary

- **Total Tests**: 100
- **auto_update.py**: 15 tests
- **config_manager.py**: 16 tests
- **configure.py**: 9 tests
- **downloads.py**: 10 tests
- **integration**: 9 tests
- **proxmox.py**: 23 tests
- **updaters.py**: 18 tests

## Critical Tests (Bug Prevention)

These tests specifically prevent known bugs or critical failures:

1. **test_get_status_includes_is_remote** - Prevents KeyError in UI code
2. **test_status_compatible_with_ui_code** - Ensures UI compatibility
3. **test_no_password_storage** - Security: No password leakage
4. **test_upload_file_with_progress_callback** - Prevents infinite hang
5. **test_local_download_shows_summary** - User feedback for downloads
6. **test_remote_vs_local_status_keys** - Manager compatibility

## Test Philosophy

1. **Isolation**: Each test is independent and can run alone
2. **Mocking**: External dependencies (network, SSH, filesystem) are mocked
3. **Clarity**: Test names describe what they test
4. **Coverage**: Both success and failure paths tested
5. **Documentation**: Each test documents expected behavior
6. **Regression Prevention**: Tests catch previously fixed bugs
