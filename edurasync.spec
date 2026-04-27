# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for EduraSync (PyInstaller 6.x compatible).

Changes vs. the old spec:
  - cipher / block_cipher removed (deprecated in PyInstaller 6)
  - EXE no longer receives binaries/datas (those go to COLLECT only)
  - hiddenimports updated for the redesigned package layout:
      interfaces.gui_pyside6.main_window, .theme, .onboarding,
      .screens.*, .widgets.*, services.sync_workers, …
"""

import sys
import os
from pathlib import Path

# PyInstaller should be run from the project root.
try:
    project_root = Path(__file__).parent.absolute()
except NameError:
    project_root = Path(os.getcwd()).absolute()

sys.path.append(str(project_root))

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "assets"), "assets"),
        # install_service.py is looked up at runtime by ServiceManager._get_service_script_path()
        (str(project_root / "scripts"), "scripts"),
    ],
    hiddenimports=[
        # ── Core ──────────────────────────────────────────────────────────────
        "core",
        "core.config",
        "core.constants",
        "core.exceptions",
        "core.operation_manager",
        "core.utils",
        "core.validation",

        # ── Database layer ────────────────────────────────────────────────────
        "interfaces",
        "interfaces.database",
        "interfaces.database.models",
        "interfaces.database.repository",
        "interfaces.database.base_repository",

        # ── GUI — new architecture ─────────────────────────────────────────────
        "interfaces.gui_pyside6",
        "interfaces.gui_pyside6.main_window",
        "interfaces.gui_pyside6.theme",
        "interfaces.gui_pyside6.onboarding",
        "interfaces.gui_pyside6.tray",
        # Screens
        "interfaces.gui_pyside6.screens",
        "interfaces.gui_pyside6.screens.dashboard_screen",
        "interfaces.gui_pyside6.screens.devices_screen",
        "interfaces.gui_pyside6.screens.attendance_screen",
        "interfaces.gui_pyside6.screens.settings_screen",
        "interfaces.gui_pyside6.screens.about_screen",
        # Widgets
        "interfaces.gui_pyside6.widgets",
        "interfaces.gui_pyside6.widgets.stat_card",
        "interfaces.gui_pyside6.widgets.status_badge",
        "interfaces.gui_pyside6.widgets.sidebar",
        "interfaces.gui_pyside6.widgets.spinner",
        "interfaces.gui_pyside6.widgets.confirm_dialog",
        # Device management helpers
        "interfaces.gui_pyside6.device_management",

        # ── Services ──────────────────────────────────────────────────────────
        "services",
        "services.api_sync",
        "services.device_manager",
        "services.device_utils",
        "services.notification",
        "services.sync_workers",
        "services.service_manager",

        # ── Peewee ORM ────────────────────────────────────────────────────────
        "peewee",
        "playhouse",
        "playhouse.sqlite_ext",
        "playhouse.migrate",
        "playhouse.reflection",
        "playhouse.db_url",

        # ── ZKTeco device library ──────────────────────────────────────────────
        "zk",
        "zk.base",
        "zk.exception",
        "zk.finger",
        "zk.user",
        "zk.attendance",

        # ── HTTP / networking ─────────────────────────────────────────────────
        "requests",
        "requests.adapters",
        "requests.auth",
        "requests.packages",
        "urllib3",
        "urllib3.util",
        "urllib3.contrib",
        "certifi",
        "charset_normalizer",
        "idna",

        # ── PySide6 / Qt ──────────────────────────────────────────────────────
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtNetwork",

        # ── Windows service (pywin32) ─────────────────────────────────────────
        # Only used at runtime on Windows; safe to list on all platforms.
        "win32serviceutil",
        "win32service",
        "win32event",
        "servicemanager",
        "pywintypes",

        # ── Miscellaneous ─────────────────────────────────────────────────────
        "loguru",
        "notifypy",
        "tzlocal",
        "cryptography",
        "cryptography.hazmat",
        "cryptography.hazmat.primitives",
        "cffi",
        "sqlite3",
        "logging",
        "logging.handlers",
        "threading",
        "datetime",
        "csv",
        "pathlib",
    ],
    hookspath=[str(project_root / "hooks")] if (project_root / "hooks").exists() else [],
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
        "IPython",
        "test",
        "unittest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],          # binaries/datas go to COLLECT, not here, for a directory build
    exclude_binaries=True,
    name="EduraSync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,   # Windowed — no console window; logs go to the log file
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "icon.png") if (project_root / "assets" / "icon.png").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EduraSync",
)
