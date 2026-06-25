#!/usr/bin/env python3
"""
Duck That Carries You Over A Disproportionately Small Gap
Desktop Pet powered by Google Gemini
"""

import sys
import os
import json

def get_resource_path(relative_path):
    """Get absolute path to resource — works for dev and PyInstaller bundles."""
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)

def get_config_path():
    if sys.platform == 'darwin':
        config_dir = os.path.expanduser('~/Library/Application Support/DuckPet')
    elif sys.platform == 'win32':
        config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'DuckPet')
    else:
        config_dir = os.path.expanduser('~/.config/DuckPet')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'config.json')

def load_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config):
    with open(get_config_path(), 'w') as f:
        json.dump(config, f, indent=2)

def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("Duck That Carries You Over A Disproportionately Small Gap")
    app.setQuitOnLastWindowClosed(False)

    config = load_config()
    api_key = config.get('gemini_api_key', '') or os.environ.get('GEMINI_API_KEY', '')

    if not api_key:
        from setup_dialog import SetupDialog
        from PySide6.QtWidgets import QDialog
        dialog = SetupDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            api_key = dialog.api_key
            config['gemini_api_key'] = api_key
            save_config(config)
        else:
            sys.exit(0)

    from pet import DuckPet
    duck = DuckPet(api_key=api_key, config=config, save_config_fn=save_config)
    duck.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
