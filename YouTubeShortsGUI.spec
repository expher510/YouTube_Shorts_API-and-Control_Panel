# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['short_app.py'],
    pathex=[],
    binaries=[('ngrok.exe', '.')],
    datas=[('c:/Users/DELL/OneDrive/Desktop/antigravity/firstproject/.venv/Lib/site-packages/customtkinter', 'customtkinter')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YouTubeShortsGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
