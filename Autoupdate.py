import tkinter as tk
from tkinter import messagebox, ttk
import requests
import json
import threading
import os
import sys
import subprocess
import platform
from urllib.request import urlretrieve
import base64

class AutoUpdater:
    def __init__(self, current_version, main_app):
        self.current_version = current_version
        self.main_app = main_app
        self.github_base = "https://api.github.com/repos/ReinaldoAssis/Foxtail"
        self.download_url = None
        self.new_version = None
        
    def check_for_updates(self):
        """Check GitHub for updates and prompt user if available"""
        try:
            # Get version from db.json in GitHub repo
            response = requests.get(f"{self.github_base}/contents/db.json")
            if response.status_code != 200:
                return
                
            # Decode base64 content properly
            base64_content = response.json()['content']
            # Remove newlines that GitHub adds to the base64 string
            base64_content = base64_content.replace('\n', '')
            # Decode base64 to bytes, then decode bytes to string
            json_str = base64.b64decode(base64_content).decode('utf-8')
            content = json.loads(json_str)
            
            # The version is stored in _default.1.version in your db.json
            self.new_version = content.get('_default', {}).get('1', {}).get('version')
            
            if self.new_version and self.new_version != self.current_version:
                self._prompt_update()
                
        except Exception as e:
            print(f"Error checking for updates: {e}")
    
    def _prompt_update(self):
        """Show update prompt to user"""
        result = messagebox.askyesno(
            "Update Available",
            f"A new version ({self.new_version}) is available. Would you like to update now?"
        )
        if result:
            self._get_latest_release()
    
    def _get_latest_release(self):
        """Get download URL for latest release"""
        try:
            response = requests.get(f"{self.github_base}/releases/latest")
            if response.status_code != 200:
                messagebox.showerror("Error", "Could not fetch latest release")
                return
                
            assets = response.json()['assets']
            system = platform.system().lower()
            
            # Find correct asset based on OS
            for asset in assets:
                name = asset['name'].lower()
                if system == 'windows' and name.endswith('.exe'):
                    self.download_url = asset['browser_download_url']
                    break
                elif system == 'darwin' and name.endswith('.app.zip'):
                    self.download_url = asset['browser_download_url']
                    break
                    
            if self.download_url:
                self._start_download()
            else:
                messagebox.showerror("Error", f"No compatible release found for {system}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get latest release: {e}")
    
    def _start_download(self):
        """Start download in separate thread with progress bar"""
        # Create progress window
        progress_window = tk.Toplevel(self.main_app)
        progress_window.title("Downloading Update")
        progress_window.geometry("300x150")
        
        label = tk.Label(progress_window, text="Downloading update...")
        label.pack(pady=10)
        
        progress_bar = ttk.Progressbar(
            progress_window, 
            orient="horizontal", 
            length=200, 
            mode="determinate"
        )
        progress_bar.pack(pady=10)
        
        # Start download thread
        thread = threading.Thread(
            target=self._download_update,
            args=(progress_bar, progress_window),
            daemon=True
        )
        thread.start()
        
    def _download_update(self, progress_bar, progress_window):
        """Download the update and show progress"""
        try:
            # Get file size for progress calculation
            response = requests.get(self.download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # Determine new filename
            filename = os.path.basename(self.download_url)
            temp_file = f"new_{filename}"
            
            # Download with progress
            block_size = 1024
            downloaded = 0
            
            def update_progress(count, block_size, total_size):
                downloaded = count * block_size
                if total_size > 0:
                    percent = (downloaded * 100) / total_size
                    progress_bar['value'] = percent
                    self.main_app.update_idletasks()
            
            urlretrieve(self.download_url, temp_file, reporthook=update_progress)
            
            # Schedule update installation
            self._schedule_update(temp_file, progress_window)
            
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("Error", f"Download failed: {e}")
    
    def _schedule_update(self, new_file, progress_window):
        """Schedule the update installation after app closes"""
        current_exec = sys.executable
        if getattr(sys, 'frozen', False):
            current_exec = sys.executable
        else:
            current_exec = os.path.abspath(__file__)
            
        # Create update script
        script_content = f'''
import os
import time
import subprocess

time.sleep(1)  # Wait for main app to close
try:
    os.remove("{current_exec}")  # Remove old version
    os.rename("{new_file}", "{current_exec}")  # Rename new version
    subprocess.Popen(["{current_exec}"])  # Start new version
except Exception as e:
    print(f"Update failed: {{e}}")
'''
        
        with open("updater.py", "w") as f:
            f.write(script_content)
            
        # Start update script and close app
        subprocess.Popen([sys.executable, "updater.py"])
        progress_window.destroy()
        self.main_app.quit()