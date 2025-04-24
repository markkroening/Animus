# -*- mode: python ; coding: utf-8 -*-
import os

# Get the absolute path to the animus_cli directory
animus_cli_dir = os.path.join(os.path.dirname(os.path.abspath(SPEC)), 'animus_cli')

a = Analysis(
    ['animus_cli/main.py'],  # Changed to use main.py as entry point
    pathex=[],
    binaries=[],
    datas=[
        ('powershell/collect_logs.ps1', 'powershell'),
        (animus_cli_dir, 'animus_cli'),  # Include the entire animus_cli directory
    ],
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
    name='animus',  # Changed to lowercase to match command name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
