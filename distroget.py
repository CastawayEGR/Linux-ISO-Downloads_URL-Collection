#!/usr/bin/env python3
import curses
import json
import os
import requests
import sys
import threading
import queue
import time
from pathlib import Path
from urllib.parse import urlparse

# URL of the GitHub raw text file
ISO_LIST_URL = "https://raw.githubusercontent.com/pljakobs/Linux-ISO-Downloads_URL-Collection/main/README.md"
REPO_HTTPS_URL = "https://github.com/pljakobs/Linux-ISO-Downloads_URL-Collection.git"
REPO_SSH_URL = "git@github.com:pljakobs/Linux-ISO-Downloads_URL-Collection.git"
REPO_FILE_PATH = "README.md"

# Global variable to store selections
selected_urls = []

# Config file location
CONFIG_FILE = Path.home() / ".config" / "distroget" / "config.json"

def load_config():
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config):
    """Save configuration to file."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save config: {e}")

def get_repo_url():
    """Get the repository URL based on user preference."""
    config = load_config()
    
    # Check if preference is already set
    if 'repo_url_type' in config:
        return REPO_SSH_URL if config['repo_url_type'] == 'ssh' else REPO_HTTPS_URL
    
    # Ask user for preference
    print("\nChoose repository access method:")
    print("1. HTTPS (username/password or token)")
    print("2. SSH (requires SSH key setup)")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == '1':
            config['repo_url_type'] = 'https'
            save_config(config)
            return REPO_HTTPS_URL
        elif choice == '2':
            config['repo_url_type'] = 'ssh'
            save_config(config)
            return REPO_SSH_URL
        else:
            print("Invalid choice. Please enter 1 or 2.")

def fetch_distrowatch_versions():
    """Fetch latest versions from DistroWatch RSS."""
    try:
        import xml.etree.ElementTree as ET
        r = requests.get('https://distrowatch.com/news/dwd.xml', timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        
        versions = {}
        for item in root.findall('.//item'):
            title = item.find('title').text if item.find('title') is not None else ''
            if title:
                # Parse "Distro Version" format
                parts = title.rsplit(' ', 1)
                if len(parts) == 2:
                    distro_name = parts[0]
                    version = parts[1]
                    versions[distro_name] = version
        return versions
    except Exception as e:
        print(f"Warning: Could not fetch DistroWatch versions: {e}")
        return {}

# Distro-specific updaters
class DistroUpdater:
    """Base class for distro-specific updaters."""
    
    @staticmethod
    def get_latest_version():
        """Get the latest version number."""
        raise NotImplementedError
    
    @staticmethod
    def generate_download_links(version):
        """Generate download links for a specific version."""
        raise NotImplementedError
    
    @staticmethod
    def update_section(content, version, links):
        """Update the distro's section in the markdown content."""
        raise NotImplementedError

class FedoraUpdater(DistroUpdater):
    """Updater for Fedora Workstation and Spins with multiple versions."""
    
    @staticmethod
    def get_latest_version():
        """Get latest Fedora versions (latest stable + previous)."""
        try:
            import re
            # List the releases directory (following redirects)
            r = requests.get('https://download.fedoraproject.org/pub/fedora/linux/releases/', 
                           timeout=10, allow_redirects=True)
            r.raise_for_status()
            
            # Find all version numbers
            versions = re.findall(r'href="(\d+)/"', r.text)
            if versions:
                # Return the two highest version numbers
                sorted_versions = sorted([int(v) for v in versions], reverse=True)
                return [str(v) for v in sorted_versions[:2]]
        except Exception as e:
            print(f"    Error fetching Fedora versions: {e}")
        
        return None
    
    @staticmethod
    def generate_download_links(versions):
        """Generate hierarchical Fedora structure with multiple versions."""
        import re
        
        if not versions or not isinstance(versions, list):
            return []
        
        # Structure: {version: {'Workstation': [urls], 'Spins': [urls]}}
        structure = {}
        
        for version_num in versions:
            structure[version_num] = {'Workstation': [], 'Spins': []}
            
            # Get Workstation edition
            try:
                workstation_url = f"https://download.fedoraproject.org/pub/fedora/linux/releases/{version_num}/Workstation/x86_64/iso"
                r = requests.get(workstation_url + "/", timeout=10, allow_redirects=True)
                r.raise_for_status()
                
                # Find Workstation ISO
                iso_pattern = re.compile(r'href="(Fedora-Workstation-Live[^"]*\.iso)"')
                matches = iso_pattern.findall(r.text)
                if matches:
                    structure[version_num]['Workstation'].append(f"{workstation_url}/{matches[0]}")
            except Exception as e:
                print(f"    Warning: Could not fetch Fedora {version_num} Workstation: {e}")
            
            # Get all Spins
            try:
                spins_url = f"https://download.fedoraproject.org/pub/fedora/linux/releases/{version_num}/Spins/x86_64/iso"
                r = requests.get(spins_url + "/", timeout=10, allow_redirects=True)
                r.raise_for_status()
                
                # Find all spin ISOs (deduplicate)
                iso_pattern = re.compile(r'href="(Fedora-[^"]*\.iso)"')
                matches = iso_pattern.findall(r.text)
                unique_isos = sorted(set(matches))
                
                for iso in unique_isos:
                    structure[version_num]['Spins'].append(f"{spins_url}/{iso}")
                    
            except Exception as e:
                print(f"    Warning: Could not fetch Fedora {version_num} Spins: {e}")
        
        return structure
    
    @staticmethod
    def update_section(content, versions, structure):
        """Update Fedora section with hierarchical markdown."""
        import re
        
        # Find any existing Fedora section (Fedora or Fedora Workstation)
        # Match only top-level ## sections (not ### subsections)
        pattern = r'## Fedora(?:\s+Workstation)?\s*\n(.*?)(?=\n## [^#]|\Z)'
        
        if structure:
            new_section = "## Fedora\n\n"
            
            for version in versions:
                if version not in structure:
                    continue
                
                version_data = structure[version]
                
                # Add Workstation subsection
                if version_data.get('Workstation'):
                    new_section += f"### Fedora {version} Workstation\n"
                    for url in version_data['Workstation']:
                        filename = url.split('/')[-1]
                        new_section += f"- [{filename}]({url})\n"
                    new_section += "\n"
                
                # Add Spins subsection
                if version_data.get('Spins'):
                    new_section += f"### Fedora {version} Spins\n"
                    for url in version_data['Spins']:
                        filename = url.split('/')[-1]
                        # Extract spin name from filename
                        match = re.search(r'Fedora-([^-]+)-', filename)
                        spin_name = match.group(1) if match else filename
                        new_section += f"- [{spin_name}]({url})\n"
                    new_section += "\n"
            
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, new_section, content, flags=re.DOTALL)
            else:
                # Add new section
                content = f"{content}\n{new_section}"
        
        return content

class DebianUpdater(DistroUpdater):
    """Updater for Debian with multiple desktop environments."""
    
    @staticmethod
    def get_latest_version():
        """Get latest Debian stable and testing versions."""
        try:
            import re
            # Get stable version
            r = requests.get('https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/', timeout=10)
            r.raise_for_status()
            
            # Extract version from filename like "debian-live-12.6.0-amd64-..."
            match = re.search(r'debian-live-(\d+\.\d+(?:\.\d+)?)-amd64', r.text)
            if match:
                full_version = match.group(1)
                stable = full_version.split('.')[0]
                # Return both stable and testing
                return {'stable': stable, 'testing': 'testing'}
        except Exception as e:
            print(f"    Error fetching Debian version: {e}")
        
        return None
    
    @staticmethod
    def generate_download_links(versions):
        """Generate hierarchical Debian structure with all desktop environments."""
        import re
        
        if not versions or not isinstance(versions, dict):
            return {}
        
        structure = {}
        
        # Define branches to fetch
        branches = []
        if 'stable' in versions:
            branches.append(('stable', 'current-live', versions['stable']))
        if 'testing' in versions:
            branches.append(('testing', 'weekly-live-builds', 'testing'))
        
        for branch_name, path, version_label in branches:
            base_url = f"https://cdimage.debian.org/debian-cd/{path}/amd64/iso-hybrid"
            
            try:
                r = requests.get(base_url + "/", timeout=10)
                r.raise_for_status()
                
                # Find all live ISO files
                iso_pattern = re.compile(r'href="(debian-live-[^"]+\.iso)"')
                matches = set(iso_pattern.findall(r.text))
                
                # Categorize by desktop environment
                for iso in sorted(matches):
                    iso_lower = iso.lower()
                    de_name = None
                    
                    if 'cinnamon' in iso_lower:
                        de_name = 'Cinnamon'
                    elif 'gnome' in iso_lower:
                        de_name = 'GNOME'
                    elif 'kde' in iso_lower:
                        de_name = 'KDE Plasma'
                    elif 'xfce' in iso_lower:
                        de_name = 'Xfce'
                    elif 'lxde' in iso_lower:
                        de_name = 'LXDE'
                    elif 'lxqt' in iso_lower:
                        de_name = 'LXQt'
                    elif 'mate' in iso_lower:
                        de_name = 'MATE'
                    
                    if de_name:
                        key = f"{branch_name}_{de_name}"
                        if key not in structure:
                            structure[key] = {'version': version_label, 'name': de_name, 'branch': branch_name, 'urls': []}
                        structure[key]['urls'].append(f"{base_url}/{iso}")
            
            except Exception as e:
                print(f"    Error fetching Debian {branch_name} ISOs: {e}")
        
        return structure
    
    @staticmethod
    def update_section(content, versions, structure):
        """Update Debian section with hierarchical desktop environments."""
        import re
        
        pattern = r'## Debian\s*\n(.*?)(?=\n## [^#]|\Z)'
        
        if structure:
            new_section = "## Debian\n\n"
            
            # Group by branch (stable, testing)
            by_branch = {}
            for key, data in structure.items():
                branch = data['branch']
                if branch not in by_branch:
                    by_branch[branch] = []
                by_branch[branch].append(data)
            
            # Add stable first, then testing
            for branch in ['stable', 'testing']:
                if branch not in by_branch:
                    continue
                    
                items = sorted(by_branch[branch], key=lambda x: x['name'])
                for item in items:
                    version_label = item['version']
                    de_name = item['name']
                    branch_label = branch.capitalize()
                    new_section += f"### Debian {version_label} {de_name} ({branch_label})\n"
                    for url in item['urls']:
                        filename = url.split('/')[-1]
                        new_section += f"- [{filename}]({url})\n"
                    new_section += "\n"
            
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, new_section, content, flags=re.DOTALL)
            else:
                content = f"{content}\n{new_section}"
        
        return content

class UbuntuUpdater(DistroUpdater):
    """Updater for Ubuntu with multiple flavors."""
    
    @staticmethod
    def get_latest_version():
        """Get latest Ubuntu LTS and latest versions."""
        try:
            import re
            r = requests.get('https://releases.ubuntu.com/', timeout=10)
            r.raise_for_status()
            
            # Find all version directories
            versions = re.findall(r'href="(\d+\.\d+)/"', r.text)
            if versions:
                # Sort all versions
                sorted_versions = sorted(versions, key=lambda x: tuple(map(int, x.split('.'))))
                latest = sorted_versions[-1] if sorted_versions else None
                
                # Filter for LTS versions (.04)
                lts_versions = [v for v in versions if v.endswith('.04')]
                if lts_versions:
                    lts_versions.sort(key=lambda x: tuple(map(int, x.split('.'))))
                    lts = lts_versions[-1]
                    # Return both if different, otherwise just latest
                    if latest and latest != lts:
                        return {'lts': lts, 'latest': latest}
                    else:
                        return {'lts': lts}
        except Exception as e:
            print(f"    Error fetching Ubuntu version: {e}")
        
        return None
    
    @staticmethod
    def generate_download_links(versions):
        """Generate hierarchical Ubuntu structure with all flavors."""
        if not versions or not isinstance(versions, dict):
            return {}
        
        import re
        structure = {}
        
        # Process each version type
        for version_type, version in versions.items():
            # Define Ubuntu flavors and their base URLs
            flavors = {
                'Ubuntu': f'https://releases.ubuntu.com/{version}/',
                'Kubuntu': f'https://cdimage.ubuntu.com/kubuntu/releases/{version}/release/',
                'Xubuntu': f'https://cdimage.ubuntu.com/xubuntu/releases/{version}/release/',
                'Lubuntu': f'https://cdimage.ubuntu.com/lubuntu/releases/{version}/release/',
                'Ubuntu MATE': f'https://cdimage.ubuntu.com/ubuntu-mate/releases/{version}/release/',
                'Ubuntu Budgie': f'https://cdimage.ubuntu.com/ubuntu-budgie/releases/{version}/release/',
            }
            
            for flavor, url in flavors.items():
                try:
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        # Find desktop ISO
                        iso_pattern = re.compile(r'href="([^"]*desktop-amd64\.iso)"')
                        matches = iso_pattern.findall(r.text)
                        if matches:
                            key = f"{version_type}_{flavor}"
                            structure[key] = {'version': version, 'flavor': flavor, 'type': version_type, 'urls': [f"{url}{matches[0]}"]}
                except Exception:
                    pass
        
        return structure
    
    @staticmethod
    def update_section(content, versions, structure):
        """Update Ubuntu section with hierarchical flavors."""
        import re
        
        pattern = r'## Ubuntu\s*\n(.*?)(?=\n## [^#]|\Z)'
        
        if structure:
            new_section = "## Ubuntu\n\n"
            
            # Group by version type (LTS, latest)
            by_type = {}
            for key, data in structure.items():
                version_type = data['type']
                if version_type not in by_type:
                    by_type[version_type] = []
                by_type[version_type].append(data)
            
            # Add LTS first, then latest
            for version_type in ['lts', 'latest']:
                if version_type not in by_type:
                    continue
                    
                items = sorted(by_type[version_type], key=lambda x: x['flavor'])
                for item in items:
                    version = item['version']
                    flavor = item['flavor']
                    type_label = 'LTS' if version_type == 'lts' else ''
                    new_section += f"### {flavor} {version} {type_label}\n".strip() + "\n"
                    for url in item['urls']:
                        filename = url.split('/')[-1]
                        new_section += f"- [{filename}]({url})\n"
                    new_section += "\n"
            
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, new_section, content, flags=re.DOTALL)
            else:
                content = f"{content}\n{new_section}"
        
        return content

# Registry of updaters
class OpenSUSEUpdater(DistroUpdater):
    """Updater for openSUSE."""
    
    @staticmethod
    def get_latest_version():
        """Get latest openSUSE versions."""
        try:
            import re
            # Try to detect Leap version from download directory
            r = requests.get('https://download.opensuse.org/distribution/leap/', timeout=10, allow_redirects=True)
            r.raise_for_status()
            
            # Find version directories
            versions = re.findall(r'href="(\d+\.\d+)/"', r.text)
            if versions:
                # Get the highest version
                latest_leap = max(versions, key=lambda x: tuple(map(int, x.split('.'))))
                return {'Leap': latest_leap, 'Tumbleweed': 'latest'}
        except Exception as e:
            print(f"    Error fetching openSUSE version: {e}")
        
        # Fallback to known latest version
        return {'Leap': '16.0', 'Tumbleweed': 'latest'}
    
    @staticmethod
    def generate_download_links(versions):
        """Generate openSUSE download links."""
        if not versions or not isinstance(versions, dict):
            return {}
        
        structure = {}
        
        # Leap
        if 'Leap' in versions:
            leap_version = versions['Leap']
            structure['Leap'] = [
                f"https://download.opensuse.org/distribution/leap/{leap_version}/iso/openSUSE-Leap-{leap_version}-DVD-x86_64-Media.iso"
            ]
        
        # Tumbleweed
        if 'Tumbleweed' in versions:
            structure['Tumbleweed'] = [
                "https://download.opensuse.org/tumbleweed/iso/openSUSE-Tumbleweed-DVD-x86_64-Current.iso"
            ]
        
        return structure
    
    @staticmethod
    def update_section(content, versions, structure):
        """Update openSUSE section."""
        import re
        
        pattern = r'## openSUSE\s*\n(.*?)(?=\n## [^#]|\Z)'
        
        if structure:
            new_section = "## openSUSE\n\n"
            
            if 'Leap' in structure and 'Leap' in versions:
                new_section += f"### openSUSE Leap {versions['Leap']}\n"
                for url in structure['Leap']:
                    filename = url.split('/')[-1]
                    new_section += f"- [{filename}]({url})\n"
                new_section += "\n"
            
            if 'Tumbleweed' in structure:
                new_section += "### openSUSE Tumbleweed\n"
                for url in structure['Tumbleweed']:
                    filename = url.split('/')[-1]
                    new_section += f"- [{filename}]({url})\n"
                new_section += "\n"
            
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, new_section, content, flags=re.DOTALL)
            else:
                content = f"{content}\n{new_section}"
        
        return content

# Registry of updaters
DISTRO_UPDATERS = {
    'Fedora': FedoraUpdater,
    'Debian': DebianUpdater,
    'Ubuntu': UbuntuUpdater,
    'openSUSE': OpenSUSEUpdater,
}

def update_iso_list_file(local_repo_path):
    """Update the ISO list file with latest versions from various sources."""
    file_path = Path(local_repo_path) / REPO_FILE_PATH
    if not file_path.exists():
        print(f"File {file_path} not found.")
        return False
    
    # Read current content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Update each distro
    for distro_name, updater_class in DISTRO_UPDATERS.items():
        try:
            print(f"Updating {distro_name}...")
            version = updater_class.get_latest_version()
            
            if version:
                # Handle both single version and list of versions
                if isinstance(version, list):
                    print(f"  Found versions: {', '.join(version)}")
                else:
                    print(f"  Found version: {version}")
                
                links = updater_class.generate_download_links(version)
                
                if links:
                    # Count links differently for hierarchical structures
                    if isinstance(links, dict):
                        total_links = sum(len(v) if isinstance(v, list) else sum(len(sv) for sv in v.values() if isinstance(sv, list)) 
                                        for v in links.values())
                        print(f"  Generated {total_links} download link(s)")
                    else:
                        print(f"  Generated {len(links)} download link(s)")
                    
                    content = updater_class.update_section(content, version, links)
                    
                    if isinstance(version, list):
                        changes_made.append(f"{distro_name} {', '.join(version)}")
                    else:
                        changes_made.append(f"{distro_name} {version}")
                else:
                    print("  Could not generate download links")
            else:
                print("  Could not determine latest version")
        except Exception as e:
            print(f"  Error updating {distro_name}: {e}")
            import traceback
            traceback.print_exc()
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nUpdated: {', '.join(changes_made)}")
        return True
    else:
        print("\nNo changes needed.")
        return False

def update_repository():
    """Clone/update the repository and commit changes."""
    import subprocess
    import tempfile
    
    # Get the repository URL based on user preference
    repo_url = get_repo_url()
    
    # Use a temporary directory for the repo
    temp_dir = Path(tempfile.gettempdir()) / 'distroget_repo'
    
    try:
        if temp_dir.exists():
            # Pull latest changes
            print(f"Updating existing repository at {temp_dir}...")
            subprocess.run(['git', '-C', str(temp_dir), 'pull'], check=True, capture_output=True)
        else:
            # Clone the repository
            print(f"Cloning repository to {temp_dir}...")
            print(f"Using: {repo_url}...")
            subprocess.run(['git', 'clone', repo_url, str(temp_dir)], check=True, capture_output=True)
        
        # Update the file
        if update_iso_list_file(temp_dir):
            # Commit changes
            subprocess.run(['git', '-C', str(temp_dir), 'add', REPO_FILE_PATH], check=True)
            subprocess.run(
                ['git', '-C', str(temp_dir), 'commit', '-m', 'Auto-update distro versions'],
                check=True
            )
            
            print("\nChanges committed. Push to GitHub? (y/n): ", end='')
            response = input().strip().lower()
            if response == 'y':
                print("Pushing to GitHub...")
                result = subprocess.run(['git', '-C', str(temp_dir), 'push'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print("✓ Changes pushed to GitHub!")
                    print("\nRestarting script to fetch updated ISO list...")
                    # Wait a moment for GitHub to process
                    import time
                    time.sleep(2)
                else:
                    print(f"✗ Push failed: {result.stderr}")
                    print(f"You can manually push from: {temp_dir}")
            else:
                print("Changes not pushed. You can manually push later from:", temp_dir)
        
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")
        print(f"You may need to set up authentication or check the repository at {temp_dir}")
    except Exception as e:
        print(f"Error updating repository: {e}")

class DownloadManager:
    """Manages parallel downloads in background threads."""
    def __init__(self, target_dir, is_remote=False, remote_host=None, remote_path=None, max_workers=3):
        self.target_dir = target_dir
        self.is_remote = is_remote
        self.remote_host = remote_host
        self.remote_path = remote_path
        self.max_workers = max_workers
        self.download_queue = queue.Queue()
        self.active_downloads = {}
        self.completed = set()
        self.completed_urls = set()
        self.failed = set()
        self.retry_counts = {}  # Track retry attempts per URL
        self.max_retries = 3
        self.lock = threading.Lock()
        self.workers = []
        self.running = True
        
    def start(self):
        """Start download worker threads."""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def _worker(self):
        """Worker thread that processes downloads."""
        while self.running:
            try:
                url = self.download_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            
            filename = url.split('/')[-1]
            with self.lock:
                self.active_downloads[url] = {'filename': filename, 'progress': 0, 'total': 0}
            
            try:
                self._download_file(url, filename)
                with self.lock:
                    self.completed.add(url)
                    self.completed_urls.add(url)
                    if url in self.active_downloads:
                        del self.active_downloads[url]
                    # Clear retry count on success
                    if url in self.retry_counts:
                        del self.retry_counts[url]
            except Exception as e:
                with self.lock:
                    # Get current retry count
                    retry_count = self.retry_counts.get(url, 0)
                    
                    if retry_count < self.max_retries:
                        # Retry the download
                        self.retry_counts[url] = retry_count + 1
                        # Re-queue with delay (exponential backoff)
                        import time
                        time.sleep(2 ** retry_count)  # 1s, 2s, 4s delays
                        self.download_queue.put(url)
                    else:
                        # Max retries exceeded
                        self.failed.add(url)
                    
                    if url in self.active_downloads:
                        del self.active_downloads[url]
            finally:
                self.download_queue.task_done()
    
    def _download_file(self, url, filename):
        """Download a single file."""
        import tempfile
        import subprocess
        
        if self.is_remote:
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, filename)
        else:
            local_path = os.path.join(self.target_dir, filename)
            if os.path.exists(local_path):
                return  # Skip existing files
        
        # Download the file
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        
        with open(local_path, 'wb') as f:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    with self.lock:
                        if url in self.active_downloads:
                            self.active_downloads[url]['progress'] = downloaded
                            self.active_downloads[url]['total'] = total
        
        # If remote, scp the file
        if self.is_remote:
            remote_file = f"{self.remote_host}:{self.remote_path}/{filename}"
            subprocess.run(['scp', local_path, remote_file], capture_output=True, text=True, check=False)
            os.remove(local_path)
    
    def add_download(self, url):
        """Add a URL to the download queue."""
        self.download_queue.put(url)
    
    def get_status(self):
        """Get current download status."""
        with self.lock:
            return {
                'active': dict(self.active_downloads),
                'completed': len(self.completed),
                'completed_urls': set(self.completed_urls),
                'failed': len(self.failed),
                'retry_counts': dict(self.retry_counts),
                'queued': self.download_queue.qsize()
            }
    
    def stop(self):
        """Stop all workers."""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=1)

def download_iso(url, target_dir, is_remote=False, remote_host=None, remote_path=None):
    filename = os.path.basename(urlparse(url).path)
    
    if is_remote:
        # Download to temp location first
        import tempfile
        temp_dir = tempfile.gettempdir()
        local_path = os.path.join(temp_dir, filename)
    else:
        local_path = os.path.join(target_dir, filename)
        if os.path.exists(local_path):
            print(f"Skipping {filename}, already exists.")
            return
    
    try:
        # Download the file
        r = requests.get(url, stream=True)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        with open(local_path, 'wb') as f:
            downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    done = int(50 * downloaded / total) if total else 0
                    sys.stdout.write(f"\rDownloading {filename}: [{'#'*done}{'.'*(50-done)}]")
                    sys.stdout.flush()
        print(f"\nDownloaded {filename}")
        
        # If remote, scp the file
        if is_remote:
            remote_file = f"{remote_host}:{remote_path}/{filename}"
            print(f"Transferring to {remote_file}...")
            import subprocess
            result = subprocess.run(['scp', local_path, remote_file], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully transferred {filename} to {remote_host}")
                os.remove(local_path)  # Clean up temp file
            else:
                print(f"Error transferring {filename}: {result.stderr}")
    except Exception as e:
        print(f"\nError downloading {url}: {e}")

def fetch_iso_list():
    """Fetch ISO list from local repo if available, otherwise from GitHub."""
    import tempfile
    import subprocess
    import shutil
    
    # Check if git is available
    git_available = shutil.which('git') is not None
    
    # Try local repository first
    temp_dir = Path(tempfile.gettempdir()) / 'distroget_repo'
    local_file = temp_dir / REPO_FILE_PATH
    
    if git_available:
        try:
            if temp_dir.exists() and local_file.exists():
                # Update existing repo
                subprocess.run(['git', '-C', str(temp_dir), 'fetch'], 
                             capture_output=True, timeout=5, check=False)
                subprocess.run(['git', '-C', str(temp_dir), 'pull'], 
                             capture_output=True, timeout=5, check=False)
                print("Using local repository (updated)")
            else:
                # Clone the repository
                print("Cloning repository for local use...")
                repo_url = get_repo_url()
                subprocess.run(['git', 'clone', repo_url, str(temp_dir)], 
                             capture_output=True, timeout=30, check=True)
                print("Repository cloned successfully")
            
            # Read from local file
            with open(local_file, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
        except Exception as e:
            print(f"Warning: Git operation failed ({e}), fetching from GitHub...")
            lines = None
    else:
        print("Git not available, fetching from GitHub...")
        lines = None
    
    # Fall back to GitHub if git operations failed
    if lines is None:
        try:
            r = requests.get(ISO_LIST_URL, timeout=10)
            r.raise_for_status()
            lines = r.text.splitlines()
            print("Fetched from GitHub")
        except Exception as e:
            print(f"Error fetching ISO list: {e}")
            sys.exit(1)
    
    # Parse the markdown content into a hierarchical structure
    try:
        distro_dict = {}
        path_stack = []  # Track current path: [distro, subcategory, subsubcategory, ...]
        current_dict = distro_dict
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Determine heading level
            if stripped.startswith("#### "):
                # Level 4: sub-subcategory (e.g., specific spin)
                heading = stripped[5:].strip()
                level = 4
            elif stripped.startswith("### "):
                # Level 3: subcategory (e.g., Workstation, Server, Spins)
                heading = stripped[4:].strip()
                level = 3
            elif stripped.startswith("## "):
                # Level 2: main distro (e.g., Fedora)
                heading = stripped[3:].strip()
                level = 2
            else:
                heading = None
                level = 0
            
            if heading:
                # Navigate to correct level in hierarchy
                if level == 2:
                    # Top-level distro
                    path_stack = [heading]
                    current_dict = distro_dict
                    if heading not in current_dict:
                        current_dict[heading] = {}
                    current_dict = current_dict[heading]
                elif level == 3:
                    # Subcategory under distro
                    if len(path_stack) >= 1:
                        path_stack = path_stack[:1] + [heading]
                    else:
                        path_stack = [heading]
                    
                    # Navigate to parent
                    current_dict = distro_dict
                    if path_stack[0] in current_dict:
                        current_dict = current_dict[path_stack[0]]
                        if heading not in current_dict:
                            current_dict[heading] = {}
                        current_dict = current_dict[heading]
                elif level == 4:
                    # Sub-subcategory
                    if len(path_stack) >= 2:
                        path_stack = path_stack[:2] + [heading]
                    
                    # Navigate to parent
                    current_dict = distro_dict
                    for p in path_stack[:-1]:
                        if p in current_dict:
                            current_dict = current_dict[p]
                    
                    if heading not in current_dict:
                        current_dict[heading] = {}
                    current_dict = current_dict[heading]
            
            # List item with URL (- [Name](URL))
            elif stripped.startswith("- ["):
                # Parse markdown link format: [Name](URL)
                import re
                match = re.match(r'- \[([^\]]+)\]\(([^\)]+)\)', stripped)
                if match:
                    name = match.group(1)
                    url = match.group(2)
                    entry = f"{name}: {url}"
                    
                    # Add to current level
                    if not isinstance(current_dict, list):
                        # Convert dict to list if we're adding items
                        if not current_dict:  # Empty dict
                            # Navigate back and replace with list
                            parent_dict = distro_dict
                            for p in path_stack[:-1]:
                                parent_dict = parent_dict[p]
                            parent_dict[path_stack[-1]] = [entry]
                            current_dict = parent_dict[path_stack[-1]]
                        else:
                            # Has subcategories, add to special "_items" key
                            if "_items" not in current_dict:
                                current_dict["_items"] = []
                            current_dict["_items"].append(entry)
                    else:
                        current_dict.append(entry)
        
        return distro_dict
    except Exception as e:
        print(f"Error parsing ISO list: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def extract_urls_from_node(node):
    """Recursively extract all URLs from a node."""
    urls = []
    if isinstance(node, list):
        # List of items - extract URLs
        for entry in node:
            if ": " in entry:
                url = entry.split(": ", 1)[1]
                urls.append(url)
    elif isinstance(node, dict):
        # Dictionary - recurse into children
        for key, value in node.items():
            if key != "_items":  # Skip special _items key
                urls.extend(extract_urls_from_node(value))
        # Also check _items
        if "_items" in node:
            urls.extend(extract_urls_from_node(node["_items"]))
    return urls

def extract_urls_for_path(distro_dict, item_path):
    """Extract URLs for a specific item path."""
    path_parts = item_path.split('/')
    current_node = distro_dict
    
    for part in path_parts:
        if isinstance(current_node, dict):
            if part in current_node:
                current_node = current_node[part]
            else:
                return []
        else:
            return []
    
    return extract_urls_from_node(current_node)

# Curses menu
def curses_menu(stdscr, distro_dict):
    import time
    
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    current_row = 0
    scroll_offset = 0
    path_stack = []
    menu_stack = [sorted(distro_dict.keys(), key=str.lower)]  # start with sorted top-level distros (case-insensitive)
    row_stack = []  # Track cursor position for each level
    selected_items = set()
    target_directory = None
    search_mode = False
    search_buffer = ""
    last_key_time = 0
    search_timeout = 3.0  # seconds
    needs_redraw = True  # Track when screen needs redrawing
    download_manager = None  # Will be initialized when target_directory is set
    downloaded_items = set()  # Track which items have been queued for download

    while True:
        current_menu = menu_stack[-1]
        height, width = stdscr.getmaxyx()
        
        # Clear search buffer if timeout exceeded
        if search_mode:
            current_time = time.time()
            if search_buffer and (current_time - last_key_time) > search_timeout:
                search_buffer = ""
                search_mode = False
                needs_redraw = True
        
        # Only clear and redraw if needed
        if needs_redraw:
            stdscr.clear()
            needs_redraw = False
        
        # Calculate split screen dimensions
        left_width = int(width * 0.6)
        right_width = width - left_width - 1
        
        # Count selected ISOs (leaf nodes only)
        iso_count = sum(1 for path in selected_items if '/' in path and not any(other.startswith(path + '/') for other in selected_items))
        
        # Draw header
        dest_info = f" | Dest: {target_directory}" if target_directory else ""
        header = f"Navigate: ↑↓, Select: SPACE, Enter/→: Enter, ←/ESC: Back, /: Search, A: All, D: Set Dir, Q: Quit"
        stdscr.addstr(0, 0, header[:width-1])
        
        # Draw path/search line
        path_display = f"Path: {'/'.join(path_stack) if path_stack else 'root'} | Selected: {iso_count}{dest_info}"
        if search_mode and search_buffer:
            path_display += f" | Search: {search_buffer}"
        elif search_mode:
            path_display += " | Search: _"
        stdscr.addstr(1, 0, path_display[:width-1])
        
        # Draw left box border (menu)
        for y in range(2, height):
            stdscr.addch(y, left_width, '│')
        stdscr.addstr(2, 0, '┌' + '─' * (left_width - 1) + '┤')
        stdscr.addstr(2, 1, ' ISO Selection ')
        if height > 2:
            stdscr.addstr(height - 1, 0, '└' + '─' * (left_width - 1) + '┴')
        
        # Draw right box border (downloads)
        stdscr.addstr(2, left_width + 1, '┌' + '─' * (right_width - 3) + '┐')
        stdscr.addstr(2, left_width + 2, ' Downloads ')
        # Don't draw to the last character position to avoid curses error
        if height > 2 and width > left_width + 1:
            bottom_line = '└' + '─' * (right_width - 3) + '┘'
            # Don't write the last character if it's at the screen edge
            if left_width + 1 + len(bottom_line) >= width:
                bottom_line = bottom_line[:-1]
            stdscr.addstr(height - 1, left_width + 1, bottom_line)
        for y in range(3, height - 1):
            if width > 1:
                stdscr.addch(y, width - 1, '│')
        
        # Calculate visible area for left panel
        menu_height = height - 4  # Space for borders
        
        if not current_menu:
            stdscr.addstr(3, 1, "No items available."[:left_width-2])
        else:
            # Adjust scroll offset to keep current row visible
            if current_row < scroll_offset:
                scroll_offset = current_row
            elif current_row >= scroll_offset + menu_height:
                scroll_offset = current_row - menu_height + 1
            
            # Display visible items in left panel
            for idx in range(scroll_offset, min(scroll_offset + menu_height, len(current_menu))):
                item = current_menu[idx]
                item_path = "/".join(path_stack + [item])
                
                # Determine checkbox state
                if item_path in selected_items:
                    prefix = "[x]"
                elif path_stack == []:  # Top-level distro
                    # Check if any child items are selected
                    has_selected = any(sel.startswith(item + "/") for sel in selected_items)
                    prefix = "[o]" if has_selected else "[ ]"
                else:
                    prefix = "[ ]"
                
                display_line = f"{prefix} {item}"[:left_width-2]
                screen_row = idx - scroll_offset + 3
                
                if idx == current_row:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(screen_row, 1, display_line + ' ' * (left_width - 2 - len(display_line)))
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(screen_row, 1, display_line)
        
        # Draw download status in right panel
        download_y = 3
        if download_manager:
            status = download_manager.get_status()
            
            # Summary line
            summary = f"Total: {iso_count} | Done: {status['completed']}"
            stdscr.addstr(download_y, left_width + 2, summary[:right_width-3])
            download_y += 1
            
            if status['queued'] > 0:
                queued_line = f"Queued: {status['queued']}"
                stdscr.addstr(download_y, left_width + 2, queued_line[:right_width-3])
                download_y += 1
            
            if status['failed'] > 0:
                stdscr.attron(curses.color_pair(4))
                failed_line = f"Failed: {status['failed']}"
                stdscr.addstr(download_y, left_width + 2, failed_line[:right_width-3])
                stdscr.attroff(curses.color_pair(4))
                download_y += 1
            
            download_y += 1
            
            # Show active downloads
            active_items = list(status['active'].items())
            if active_items:
                stdscr.addstr(download_y, left_width + 2, "Active downloads:"[:right_width-3])
                download_y += 1
                
                for url, info in active_items[:menu_height - 10]:
                    filename = info['filename'][:right_width-5]
                    progress = info['progress']
                    total = info['total']
                    
                    if total > 0:
                        pct = int(100 * progress / total)
                        bar_width = min(right_width - 8, 20)
                        filled = int(bar_width * progress / total)
                        bar = '█' * filled + '░' * (bar_width - filled)
                        
                        stdscr.attron(curses.color_pair(3))
                        stdscr.addstr(download_y, left_width + 2, filename[:right_width-3])
                        stdscr.attroff(curses.color_pair(3))
                        download_y += 1
                        
                        progress_line = f"{bar} {pct}%"
                        stdscr.addstr(download_y, left_width + 2, progress_line[:right_width-3])
                        download_y += 1
                    else:
                        stdscr.attron(curses.color_pair(3))
                        stdscr.addstr(download_y, left_width + 2, filename[:right_width-3])
                        stdscr.attroff(curses.color_pair(3))
                        download_y += 1
                        stdscr.addstr(download_y, left_width + 2, "Starting..."[:right_width-3])
                        download_y += 1
            
            # Show list of all downloaded/queued items
            if download_y < height - 3:
                download_y += 1
                if downloaded_items:
                    stdscr.addstr(download_y, left_width + 2, "Download queue:"[:right_width-3])
                    download_y += 1
                    
                    for url in list(downloaded_items)[:menu_height - download_y]:
                        filename = url.split('/')[-1][:right_width-5]
                        retry_count = status.get('retry_counts', {}).get(url, 0)
                        
                        # Check status
                        if url in status['active']:
                            marker = "⬇"
                            color = 3  # Yellow
                        elif url in status.get('completed_urls', set()):
                            marker = "✓"
                            color = 2  # Green
                        elif retry_count > 0:
                            # Show retry attempt with red indicators
                            marker = "●" * retry_count
                            color = 4  # Red
                        else:
                            marker = "⋯"
                            color = 0  # Normal
                        
                        if color > 0:
                            stdscr.attron(curses.color_pair(color))
                        stdscr.addstr(download_y, left_width + 2, f"{marker} {filename}"[:right_width-3])
                        if color > 0:
                            stdscr.attroff(curses.color_pair(color))
                        download_y += 1
                        
                        if download_y >= height - 2:
                            break
        else:
            stdscr.addstr(download_y, left_width + 2, "Set target dir (D)"[:right_width-3])
            download_y += 1
            stdscr.addstr(download_y, left_width + 2, "to start downloads"[:right_width-3])
        
        stdscr.timeout(100)  # 100ms timeout for getch to allow search timeout checking
        key = stdscr.getch()
        
        if key == -1:  # No key pressed (timeout)
            # Redraw if downloads are active to update progress
            if download_manager:
                status = download_manager.get_status()
                needs_redraw = len(status['active']) > 0
            else:
                needs_redraw = False
            continue
        
        needs_redraw = True  # Key was pressed, redraw on next iteration
        
        if not current_menu:
            # Handle empty menu case
            if key in [curses.KEY_ENTER, ord('\n')]:
                if len(menu_stack) > 1:
                    path_stack.pop()
                    menu_stack.pop()
                    current_row = 0
            elif key in [ord('q'), ord('Q')]:
                break
            continue
        
        # Handle search mode
        if search_mode:
            if key == 27:  # ESC - exit search mode
                search_mode = False
                search_buffer = ""
                current_row = 0
                scroll_offset = 0
            elif key in [curses.KEY_ENTER, ord('\n')]:
                # Exit search mode and stay on current selection
                search_mode = False
                search_buffer = ""
            elif key in [curses.KEY_BACKSPACE, 127, 8]:  # Backspace
                if search_buffer:
                    search_buffer = search_buffer[:-1]
                    last_key_time = time.time()
                    # Re-search with shorter buffer
                    if search_buffer:
                        for idx, item in enumerate(current_menu):
                            if item.lower().startswith(search_buffer):
                                current_row = idx
                                break
                else:
                    search_mode = False
            elif 32 <= key <= 126 and key not in [ord('/')]:
                # Add character to search
                search_buffer += chr(key).lower()
                last_key_time = time.time()
                
                # Find first matching item
                for idx, item in enumerate(current_menu):
                    if item.lower().startswith(search_buffer):
                        current_row = idx
                        break
            continue
        
        # Normal navigation mode
        if key == ord('/') and path_stack == []:  # Start search mode (only at top level)
            search_mode = True
            search_buffer = ""
            last_key_time = time.time()
        elif key in [curses.KEY_UP, ord('k')]:
            current_row = (current_row - 1) % len(current_menu)
        elif key in [curses.KEY_DOWN, ord('j')]:
            current_row = (current_row + 1) % len(current_menu)
        elif key == ord(' '):
            item_path = "/".join(path_stack + [current_menu[current_row]])
            if item_path in selected_items:
                selected_items.remove(item_path)
            else:
                selected_items.add(item_path)
                # If download manager is active, queue download immediately
                if download_manager:
                    urls = extract_urls_for_path(distro_dict, item_path)
                    for url in urls:
                        if url not in downloaded_items:
                            download_manager.add_download(url)
                            downloaded_items.add(url)
        elif key in [ord('a'), ord('A')]:
            # Select all items in current menu
            for item in current_menu:
                item_path = "/".join(path_stack + [item])
                selected_items.add(item_path)
        elif key in [ord('d'), ord('D')]:
            # Set target directory
            curses.endwin()
            target_directory = input("\nEnter target directory (or hostname:/path for remote): ").strip()
            
            # Initialize download manager if directory was set
            if target_directory and not download_manager:
                is_remote = ':' in target_directory and not target_directory.startswith('/')
                
                if is_remote:
                    remote_host, remote_path = target_directory.split(':', 1)
                    
                    # Test SSH connection
                    print(f"\nTesting SSH connection to {remote_host}...")
                    import subprocess
                    test_result = subprocess.run(
                        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', 
                         remote_host, 'echo "SSH OK"'], 
                        capture_output=True, 
                        text=True,
                        timeout=10
                    )
                    
                    if test_result.returncode != 0:
                        print(f"\nSSH connection test failed. This might mean:")
                        print("  - Password authentication is required")
                        print("  - SSH keys are not set up")
                        print("  - Host is unreachable")
                        print(f"\nError: {test_result.stderr.strip()}")
                        print("\nFor password-free operation, set up SSH keys:")
                        print(f"  ssh-copy-id {remote_host}")
                        print("\nPress Enter to continue anyway or Ctrl+C to cancel...")
                        try:
                            input()
                        except KeyboardInterrupt:
                            print("\nCancelled.")
                            stdscr = curses.initscr()
                            curses.curs_set(0)
                            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
                            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
                            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
                            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
                            target_directory = None
                            continue
                    else:
                        print("SSH connection OK!")
                    
                    if target_directory:
                        # Create remote directory
                        print(f"Creating remote directory {remote_path}...")
                        mkdir_result = subprocess.run(
                            ['ssh', remote_host, f'mkdir -p {remote_path}'], 
                            capture_output=True, 
                            text=True,
                            timeout=10
                        )
                        if mkdir_result.returncode != 0:
                            print(f"Warning: Could not create remote directory: {mkdir_result.stderr}")
                        
                        download_manager = DownloadManager(None, is_remote=True, remote_host=remote_host, remote_path=remote_path)
                else:
                    Path(target_directory).mkdir(parents=True, exist_ok=True)
                    download_manager = DownloadManager(target_directory)
                
                if download_manager:
                    download_manager.start()
                    
                    # Queue any already-selected items for download
                    for item_path in selected_items:
                        urls = extract_urls_for_path(distro_dict, item_path)
                        for url in urls:
                            if url not in downloaded_items:
                                download_manager.add_download(url)
                                downloaded_items.add(url)
            
            stdscr = curses.initscr()
            curses.curs_set(0)
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        elif key in [curses.KEY_ENTER, ord('\n'), curses.KEY_RIGHT, ord('l')]:
            selected = current_menu[current_row]
            
            # Navigate to the selected item
            current_node = distro_dict
            for p in path_stack:
                current_node = current_node[p]
            
            # Check if selected item has children
            if isinstance(current_node, dict):
                next_node = current_node.get(selected)
                if next_node and (isinstance(next_node, dict) or isinstance(next_node, list)):
                    # Has children - navigate into it
                    row_stack.append(current_row)
                    path_stack.append(selected)
                    
                    # Build next menu
                    if isinstance(next_node, dict):
                        menu_stack.append(sorted(next_node.keys(), key=str.lower))
                    else:
                        menu_stack.append(next_node)
                    
                    current_row = 0
                    scroll_offset = 0
                else:
                    # Leaf node or item - toggle selection
                    item_path = "/".join(path_stack + [selected])
                    if item_path in selected_items:
                        selected_items.remove(item_path)
                    else:
                        selected_items.add(item_path)
            else:
                # In a list - toggle selection
                item_path = "/".join(path_stack + [selected])
                if item_path in selected_items:
                    selected_items.remove(item_path)
                else:
                    selected_items.add(item_path)
        elif key in [27, curses.KEY_LEFT, ord('h')]:  # 27 is ESC
            # Clear search buffer or go back
            if search_buffer:
                search_buffer = ""
                current_row = 0
                scroll_offset = 0
            elif len(menu_stack) > 1:
                path_stack.pop()
                menu_stack.pop()
                current_row = row_stack.pop() if row_stack else 0
                scroll_offset = 0
        elif key in [ord('q'), ord('Q')]:
            break
    # Return selected items mapped to actual URLs
    final_urls = []
    
    def extract_urls_from_node(node):
        """Recursively extract all URLs from a node."""
        urls = []
        if isinstance(node, list):
            # List of items - extract URLs
            for entry in node:
                if ": " in entry:
                    url = entry.split(": ", 1)[1]
                    urls.append(url)
        elif isinstance(node, dict):
            # Dictionary - recurse into children
            for key, value in node.items():
                if key != "_items":  # Skip special _items key
                    urls.extend(extract_urls_from_node(value))
            # Also check _items
            if "_items" in node:
                urls.extend(extract_urls_from_node(node["_items"]))
        return urls
    
    for sel in selected_items:
        parts = sel.split("/")
        
        # Navigate to the selected node
        current_node = distro_dict
        for part in parts:
            if isinstance(current_node, dict) and part in current_node:
                current_node = current_node[part]
            elif isinstance(current_node, list):
                # Match item in list
                for entry in current_node:
                    if entry.startswith(part):
                        if ": " in entry:
                            url = entry.split(": ", 1)[1]
                            final_urls.append(url)
                        break
                current_node = None
                break
            else:
                current_node = None
                break
        
        # Extract URLs from the final node
        if current_node:
            final_urls.extend(extract_urls_from_node(current_node))
    
    # Stop download manager if it was started
    if download_manager:
        download_manager.stop()
    
    return final_urls, target_directory

def main():
    config = load_config()
    print("Fetching distros...")
    distro_dict = fetch_iso_list()
    selected_urls, target_dir = curses.wrapper(curses_menu, distro_dict)
    if not selected_urls:
        print("No ISOs selected, exiting.")
        sys.exit(0)
    
    # If downloads already happened in background, we're done
    if target_dir:
        print("Downloads completed in background.")
        sys.exit(0)
    
    # Save target directory to config if set
    if target_dir:
        config['target_directory'] = target_dir
        save_config(config)

if __name__ == "__main__":
    # Check for --update-repo flag
    if len(sys.argv) > 1 and sys.argv[1] == '--update-repo':
        update_repository()
    else:
        main()

