import os
import sys


def get_app_dir() -> str:
    """Return the directory where config/data should be stored.
    In dev: project root. In PyInstaller bundle: next to the .exe.
    On Android/Kivy: use Kivy's user_data_dir."""
    # Android Kivy app
    if 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_PRIVATE' in os.environ:
        try:
            from kivy.utils import platform
            if platform == 'android':
                from android.storage import app_storage_path
                return str(app_storage_path())
        except ImportError:
            pass
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_dir() -> str:
    return os.path.join(get_app_dir(), "config")


def get_data_dir() -> str:
    return os.path.join(get_app_dir(), "data")
