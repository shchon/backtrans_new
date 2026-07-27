"""
Download an open-source Chinese font for the Android build.
This script is used in CI (GitHub Actions) where Windows fonts are not available.
"""
import os
import shutil
import subprocess
import sys


def get_font():
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
    os.makedirs(font_dir, exist_ok=True)

    # Try multiple font sources in order of preference
    candidates = [
        # 1. Already downloaded
        os.path.join(font_dir, 'NotoSansSC-Regular.otf'),
        os.path.join(font_dir, 'NotoSansSC.otf'),
        os.path.join(font_dir, 'msyh.ttc'),
        # 2. System fonts (Ubuntu/Debian)
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    ]

    for path in candidates:
        if os.path.exists(path):
            if path.startswith(font_dir):
                print(f'Font already exists: {path}')
                return path
            # Copy to fonts directory
            dest = os.path.join(font_dir, os.path.basename(path))
            shutil.copy2(path, dest)
            print(f'Copied {path} -> {dest}')
            return dest

    # Try to install via apt
    print('No font found, trying to install via apt...')
    try:
        subprocess.run(
            ['sudo', 'apt', 'install', '-y', 'fonts-wqy-microhei'],
            capture_output=True, text=True, check=True
        )
        src = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        if os.path.exists(src):
            dest = os.path.join(font_dir, 'wqy-microhei.ttc')
            shutil.copy2(src, dest)
            print(f'Installed and copied: {dest}')
            return dest
    except Exception as e:
        print(f'apt install failed: {e}')

    return None


if __name__ == '__main__':
    path = get_font()
    if path:
        print(f'\nFont ready: {path}')
        sys.exit(0)
    else:
        print('\nFailed to get font!')
        print('The app will still work but Chinese characters may show as squares.')
        sys.exit(0)  # Non-fatal - app can still run without the font