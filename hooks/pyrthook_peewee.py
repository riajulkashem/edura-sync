# Runtime hook for peewee
# This ensures peewee is available at runtime when running from PyInstaller bundle

import sys
import os

# Ensure peewee can be imported from PyInstaller bundle
if hasattr(sys, '_MEIPASS'):
    # Running from PyInstaller bundle
    # The modules should already be in sys._MEIPASS, but ensure path is correct
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)
    
    # Try to import peewee to verify it's available
    try:
        import peewee
    except ImportError:
        # If still not found, try to locate it
        import importlib.util
        peewee_paths = [
            os.path.join(sys._MEIPASS, 'peewee'),
            os.path.join(sys._MEIPASS, 'peewee.py'),
        ]
        for path in peewee_paths:
            if os.path.exists(path):
                sys.path.insert(0, os.path.dirname(path) if os.path.isfile(path) else path)
                break
