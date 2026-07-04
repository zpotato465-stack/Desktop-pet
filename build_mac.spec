# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for macOS .app
# Run: pyinstaller build_mac.spec

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
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='duck that carries you over a disproportionately small gap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='duck that carries you over a disproportionately small gap',
)

app = BUNDLE(
    coll,
    name='duck that carries you over a disproportionately small gap.app',
    # icon='assets/duck_icon.icns',  # uncomment if you add an .icns icon
    bundle_identifier='com.duckpet.quackers',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'LSUIElement': True,   # background app (no dock icon)
        'CFBundleShortVersionString': '1.2.0',
        'NSScreenCaptureUsageDescription':
            'Quackers needs to see your screen to comment on what you\'re doing.',
    },
)
