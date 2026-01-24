# PyInstaller hook for peewee
# This ensures all peewee modules are collected

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all peewee submodules
hiddenimports = collect_submodules('peewee')

# Also collect playhouse modules
hiddenimports += collect_submodules('playhouse')

# Collect any data files
datas = collect_data_files('peewee')
