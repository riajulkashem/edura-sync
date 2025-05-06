# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect zk library and other dependencies
zk_data = collect_data_files('zk')
hiddenimports = collect_submodules('zk') + [
    'peewee',
    'peewee_migrate',
    'apscheduler',
    'pystray',
    'notify_py',
    'PIL',
    'cryptography',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.bindings.openssl',
    'requests',
    'loguru',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
    'six',
    'tzlocal',
    'interfaces.database.models',
    'core.security',
    'services.notification'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/icon.png', 'assets'),
    ] + zk_data,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['ruff', 'pyobjc_core', 'pyobjc_framework_Cocoa', 'pyobjc_framework_Quartz'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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