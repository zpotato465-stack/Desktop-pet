# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Windows .exe
# Run: pyinstaller build_windows.spec

import os

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('assets/*.png', 'assets'),
    ],
    hiddenimports=[
        'google.genai',
        'mss',
        'PIL',
        'PIL.Image',
        'pygame',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'paths',
        'gemini',
        'bubble',
        'audio',
        'file_ops',
        'setup_dialog',
        'chat_dialog',
        'find_dialog',
        'pet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='duck that carries you over a disproportionately small gap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/duck_icon.ico',  # uncomment if you add an icon file
)
