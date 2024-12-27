
import os
import time
import subprocess

time.sleep(1)  # Wait for main app to close
try:
    os.remove("C:\Users\escritorio\Documents\Programacao geral\Foxtail\Autoupdate.py")  # Remove old version
    os.rename("new_Foxtail.exe", "C:\Users\escritorio\Documents\Programacao geral\Foxtail\Autoupdate.py")  # Rename new version
    subprocess.Popen(["C:\Users\escritorio\Documents\Programacao geral\Foxtail\Autoupdate.py"])  # Start new version
except Exception as e:
    print(f"Update failed: {e}")
