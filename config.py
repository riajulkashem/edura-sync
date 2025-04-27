from pathlib import Path
import sys

class Config:
    """Application configuration."""

    BASE_DIR = Path(__file__).parent
    if getattr(sys, 'frozen', False):
        # Running in a bundle (PyInstaller)
        BASE_DIR = Path(sys._MEIPASS)
    LOG_FILE = BASE_DIR / "logs" / "primesync.log"
    ICON_PATH = BASE_DIR / "assets" / "icon.png"
    DB_NAME = "primesync.db"
    DB_PATH = BASE_DIR / DB_NAME

    @classmethod
    def ensure_dirs(cls):
        """Ensure required directories exist."""
        cls.LOG_FILE.parent.mkdir(exist_ok=True)
        cls.ICON_PATH.parent.mkdir(exist_ok=True)
        cls.DB_PATH.parent.mkdir(exist_ok=True)

Config.ensure_dirs()