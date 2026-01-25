# core/config.py
"""Application configuration management."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from core.constants import APP_VERSION


class Config:
    """
    Singleton configuration class managing application paths and settings.
    Supports both bundled (PyInstaller) and source execution contexts.
    """

    _instance = None

    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize configuration paths and logging (called once)."""
        self.logger = logging.getLogger(__name__)
        self._setup_base_paths()
        self._setup_data_paths()
        self._setup_icon_paths()
        self._ensure_directories()
        self._setup_logging()

    def _setup_base_paths(self) -> None:
        """Determine base directory based on execution context (bundled vs source)."""
        if getattr(sys, "frozen", False):
            # Running as PyInstaller bundle
            self.BASE_DIR = Path(sys._MEIPASS)
            self.INSTALL_DIR = Path("C:/Program Files/EduraSync")
        else:
            # Running from source
            self.BASE_DIR = Path(__file__).parent.parent
            self.INSTALL_DIR = self.BASE_DIR

    def _setup_data_paths(self) -> None:
        """Set DATA_DIR with fallback strategy: try INSTALL_DIR/data, then platform-specific user dir."""
        # Try INSTALL_DIR/data first
        preferred = self.INSTALL_DIR / "data"
        if self._test_writable_dir(preferred):
            self.DATA_DIR = preferred
            return

        # Fall back to platform-specific user data directory
        if sys.platform.startswith("win"):
            self.DATA_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "EduraSync"
        elif sys.platform == "darwin":
            self.DATA_DIR = Path.home() / "Library" / "Application Support" / "EduraSync"
        else:  # Linux and others
            xdg = os.getenv("XDG_DATA_HOME")
            self.DATA_DIR = Path(xdg) / "EduraSync" if xdg else Path.home() / ".local" / "share" / "EduraSync"

        # Final fallback: current working directory
        if not self._test_writable_dir(self.DATA_DIR):
            self.DATA_DIR = Path.cwd() / "data"

    def _setup_icon_paths(self) -> None:
        """Set ICON_PATH with fallback from INSTALL_DIR to BASE_DIR."""
        for base_dir in [self.INSTALL_DIR, self.BASE_DIR]:
            icon_path = base_dir / "assets" / "icon.png"
            if icon_path.exists() and os.access(str(icon_path), os.R_OK):
                self.ICON_PATH = icon_path
                return
        self.ICON_PATH = None

    def _ensure_directories(self) -> None:
        """Create required directories."""
        dirs = [
            self.DATA_DIR / "logs",
            self.DATA_DIR,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> None:
        """Configure logging with file and console handlers."""
        # Determine log file path
        if getattr(sys, "frozen", False):
            log_file = str(self.LOG_FILE)
        else:
            log_file = "logs/edurasync.log"

        # File handler (5 MB rotating logs, 5 backups)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    @staticmethod
    def _test_writable_dir(path: Path) -> bool:
        """Test if a directory exists and is writable."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".writetest"
            test_file.write_text("ok")
            test_file.unlink()
            return True
        except Exception:
            return False

    @property
    def LOG_FILE(self) -> Path:
        """Path to the log file."""
        return self.DATA_DIR / "logs" / "edurasync.log"

    @property
    def DB_PATH(self) -> Path:
        """Path to the database file."""
        return self.DATA_DIR / "edurasync.db"

    @property
    def VERSION(self) -> str:
        """Application version."""
        return APP_VERSION
