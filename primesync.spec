import sys
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
from pathlib import Path
from win32com.client import Dispatch

block_cipher = None

# Collect zk library and other dependencies
zk_data = collect_data_files('zk')
hiddenimports = collect_submodules('zk') + [
    'peewee',
    'apscheduler',
    'pystray',
    'notify-py',  # Replace plyer with notify-py
    'PIL',
    'cryptography',
    'requests',
    'win32com'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icon.png', 'assets'),
        ('logs', 'logs'),
        ('data', 'data')
    ] + zk_data,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Update the EXE section to include a proper icon
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PrimeSyncTrayApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
    icon='assets/icon.png'
)

# The COLLECT path should be simpler for Inno Setup to locate
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PrimeSyncTrayApp'
)

# Post-build step to create Start Menu shortcut on Windows
if sys.platform == 'win32':
    start_menu_dir = Path(r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\PrimeSyncTrayApp')
    start_menu_dir.mkdir(parents=True, exist_ok=True)
    shortcut_path = start_menu_dir / 'PrimeSyncTrayApp.lnk'
    target_path = Path(r'C:\Program Files\PrimeSyncTrayApp\PrimeSyncTrayApp.exe')
    icon_path = Path(r'C:\Program Files\PrimeSyncTrayApp\assets\icon.png')

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(target_path)
    shortcut.WorkingDirectory = str(target_path.parent)
    shortcut.IconLocation = str(icon_path)
    shortcut.Description = 'PrimeSync Tray App for device management'
    shortcut.save()

app = BUNDLE(
    coll,
    name='PrimeSyncTrayApp.app',
    icon='assets/icon.png',
    bundle_identifier='com.primesync.trayapp',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True
    }
)