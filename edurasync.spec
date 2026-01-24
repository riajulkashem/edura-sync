# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

# Get the project root directory
# __file__ may not be available in PyInstaller context, so use current working directory
# PyInstaller should be run from the project root
try:
    project_root = Path(__file__).parent.absolute()
except NameError:
    # Fallback to current working directory if __file__ is not available
    project_root = Path(os.getcwd()).absolute()

sys.path.append(str(project_root))

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Include assets directory
        (str(project_root / "assets"), "assets"),
    ],
    hiddenimports=[
        "core",
        "interfaces",
        "interfaces.database",
        "interfaces.gui_pyside6",
        "services",
        "peewee",
        "zk",
        "requests",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "pytest",
        "tkinter",
        "notebook",
        "jedi",
    ],
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
    name="EduraSync",
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
    icon=str(project_root / "assets" / "icon.png") if (project_root / "assets" / "icon.png").exists() else None,
)