"""Build BackTranslate into a standalone .exe using PyInstaller."""
import subprocess
import sys
import shutil
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Remove known-incompatible backport packages
for pkg in ["enum34", "typing"]:
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", pkg, "-y"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

print("Installing PyInstaller...")
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "pyinstaller"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

# Clean old builds
for d in ["dist", "build"]:
    path = os.path.join(HERE, d)
    if os.path.exists(path):
        shutil.rmtree(path)
print("Building...")
args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--name", "BackTranslate",
    "--onefile",
    "--windowed",
    "--clean",
    os.path.join(HERE, "backtranslate", "main.py"),
]
subprocess.check_call(args, cwd=HERE)

exe = os.path.join(HERE, "dist", "BackTranslate.exe")
if os.path.exists(exe):
    size_mb = os.path.getsize(exe) / (1024 * 1024)
    print(f"\nBuild complete! ({size_mb:.0f} MB)")
    print(f"  {exe}")
else:
    print("\nBuild FAILED. Check output above.")
    sys.exit(1)
