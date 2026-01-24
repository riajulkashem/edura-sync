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
    # Explicitly include peewee and playhouse packages
    includes=['peewee', 'playhouse'],
    datas=[
        # Include assets directory
        (str(project_root / "assets"), "assets"),
    ],
    hiddenimports=[
        # Application modules
        "core",
        "core.config",
        "core.constants",
        "core.exceptions",
        "core.operation_manager",
        "core.utils",
        "core.validation",
        "interfaces",
        "interfaces.database",
        "interfaces.database.models",
        "interfaces.database.repository",
        "interfaces.database.base_repository",
        "interfaces.gui_pyside6",
        "interfaces.gui_pyside6.dashboard",
        "interfaces.gui_pyside6.tray",
        "interfaces.gui_pyside6.device_management",
        "interfaces.gui_pyside6.gui_utils",
        "interfaces.gui_pyside6.ui_utils",
        "services",
        "services.api_sync",
        "services.device_manager",
        "services.device_utils",
        "services.notification",
        # Peewee ORM and extensions - collect all submodules
        "peewee",
        "peewee_migrate",
        "playhouse",
        "playhouse.sqlite_ext",
        "playhouse.migrate",
        "playhouse.reflection",
        "playhouse.db_url",
        # ZK device library
        "zk",
        # HTTP requests and dependencies
        "requests",
        "requests.packages",
        "requests.packages.urllib3",
        "urllib3",
        "urllib3.util",
        "urllib3.contrib",
        "certifi",
        "charset_normalizer",
        "idna",
        # PySide6 Qt framework - collect all submodules
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",
        # Logging
        "loguru",
        # Notifications
        "notifypy",
        # Date/time
        "tzlocal",
        # Cryptography (for some dependencies)
        "cryptography",
        "cryptography.hazmat",
        "cryptography.hazmat.primitives",
        "cffi",
        # Standard library modules that might be missed
        "sqlite3",
        "logging",
        "logging.handlers",
    ],
    hookspath=[str(project_root / "hooks")],  # Use custom hooks directory
    hooksconfig={},
    runtime_hooks=[],  # Runtime hooks disabled - using build-time collection instead
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
    upx=False,  # Disable UPX compression (requires UPX to be installed)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Temporarily enable console to see errors
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "icon.png") if (project_root / "assets" / "icon.png").exists() else None,
)

# COLLECT creates the directory structure when noarchive=False
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EduraSync",
)