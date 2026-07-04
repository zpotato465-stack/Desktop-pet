#!/usr/bin/env python3
"""
Duck That Carries You Over A Disproportionately Small Gap
Desktop Pet powered by Google Gemini
"""

import os
import sys

from paths import load_config, save_config


def main():
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Duck That Carries You Over A Disproportionately Small Gap")
    app.setQuitOnLastWindowClosed(False)

    config = load_config()
    api_key = config.get('gemini_api_key', '') or os.environ.get('GEMINI_API_KEY', '')

    if not api_key:
        from PySide6.QtWidgets import QDialog
        from setup_dialog import SetupDialog
        dialog = SetupDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            api_key = dialog.api_key
            config['gemini_api_key'] = api_key
            save_config(config)
        # "Skip" still launches the duck — it just can't chat until a key is set.

    from pet import DuckPet
    duck = DuckPet(api_key=api_key, config=config, save_config_fn=save_config)
    duck.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
