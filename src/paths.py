"""Shared resource/config path helpers.

Lives in its own module so that pet/chat/setup can import it without
importing the entry script (which PyInstaller treats specially).
"""

import json
import os
import sys


def get_resource_path(relative_path: str) -> str:
    """Absolute path to a bundled resource — works in dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def get_config_path() -> str:
    if sys.platform == 'darwin':
        config_dir = os.path.expanduser('~/Library/Application Support/DuckPet')
    elif sys.platform == 'win32':
        config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'DuckPet')
    else:
        config_dir = os.path.expanduser('~/.config/DuckPet')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'config.json')


def load_config() -> dict:
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: dict):
    with open(get_config_path(), 'w') as f:
        json.dump(config, f, indent=2)
