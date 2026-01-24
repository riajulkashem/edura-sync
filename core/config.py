# core/config.py
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from core.constants import APP_VERSION


class Singleton:
    """Implements the Singleton pattern to ensure a single instance of a class."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


class Config(Singleton):
    """
    Singleton configuration class for managing application paths and settings.
    Handles paths for logs, database, and assets, with support for bundled (PyInstaller) and source execution.
    """

    def __init__(self):
        """Initialize configuration, setting up paths and logging."""
        if hasattr(self, "_initialized"):  # Prevent re-initialization in Singleton
            return
        self._initialized = True

        # Determine base paths based on execution context (bundled or source)
        self._set_base_paths()
        self._set_data_paths()
        self._set_icon_path()

        # Define database and log file paths
        self.LOG_FILE: Path = self.DATA_DIR / "logs" / "edurasync.log"
        self.DB_NAME: str = "edurasync.db"
        self.DB_PATH: Path = self.DATA_DIR / self.DB_NAME

        # Ensure required directories exist (including logs directory)
        self.ensure_dirs()

        # Configure logging AFTER paths are set up
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Validate icon path
        self._validate_icon_path()
        self.logger.info(f"Resolved ICON_PATH: {self.ICON_PATH}")
        self.logger.info(f"Log file location: {self.LOG_FILE}")

    def _setup_logging(self) -> None:
        """Configure logging to file based on execution context."""
        from logging.handlers import RotatingFileHandler
        
        # Always log to file when installed (frozen) or when running from source
        if getattr(sys, "frozen", False):
            # Running as installed application - use LOG_FILE path
            log_file = str(self.LOG_FILE)
        else:
            # Running from source - use relative path
            log_file = "logs/edurasync.log"
            # Ensure logs directory exists
            Path("logs").mkdir(exist_ok=True)
        
        # Set up rotating file handler (5 MB max, 5 backup files)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        
        # Also add console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        
        # Configure root logger with both handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    def _set_base_paths(self) -> None:
        """Set BASE_DIR and INSTALL_DIR based on whether running as bundled or source."""
        if getattr(sys, "frozen", False):
            self.BASE_DIR = Path(sys._MEIPASS)  # PyInstaller temp directory
            self.INSTALL_DIR = Path("C:/Program Files/EduraSync")
        else:
            self.BASE_DIR = Path(__file__).parent.parent  # Project root
            self.INSTALL_DIR = self.BASE_DIR

    def _set_data_paths(self) -> None:
        """Set DATA_DIR, preferring INSTALL_DIR with fallback to a platform-appropriate user data dir.

        Instead of using os.access on a path that may not exist, try to create the
        directory under INSTALL_DIR; if that fails, fall back to a writable per-platform
        user data directory (Windows APPDATA, macOS ~/Library/Application Support,
        otherwise ~/.local/share).
        """
        preferred = self.INSTALL_DIR / "data"
        try:
            preferred.mkdir(parents=True, exist_ok=True)
            # Try to write a tiny temp file to ensure writability
            test_file = preferred / ".writetest"
            with open(test_file, "w") as f:
                f.write("ok")
            test_file.unlink()
            self.DATA_DIR = preferred
            return
        except Exception:
            # Fall through to platform-specific user data dir
            pass

        if sys.platform.startswith("win"):
            appdata = os.getenv("APPDATA")
            if appdata:
                self.DATA_DIR = Path(appdata) / "EduraSync"
            else:
                self.DATA_DIR = Path.home() / "AppData" / "Roaming" / "EduraSync"
        elif sys.platform == "darwin":
            # macOS: use Library/Application Support
            self.DATA_DIR = Path.home() / "Library" / "Application Support" / "EduraSync"
        else:
            # Linux / other: use XDG or ~/.local/share
            xdg = os.getenv("XDG_DATA_HOME")
            if xdg:
                self.DATA_DIR = Path(xdg) / "EduraSync"
            else:
                self.DATA_DIR = Path.home() / ".local" / "share" / "EduraSync"

        # Ensure the fallback dir exists
        try:
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            # As a last resort, use current working directory /data
            self.DATA_DIR = Path.cwd() / "data"
            self.DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _set_icon_path(self) -> None:
        """Set ICON_PATH, preferring INSTALL_DIR with fallback to BASE_DIR."""
        self.ICON_PATH: Optional[Path] = self.INSTALL_DIR / "assets" / "icon.png"
        self.BACKUP_ICON_PATH: Optional[Path] = (
            self.INSTALL_DIR / "assets" / "backup-icon.png"
        )
        if not self.ICON_PATH.exists() or not os.access(str(self.ICON_PATH), os.R_OK):
            self.logger.warning(
                f"Icon not found in INSTALL_DIR at {self.ICON_PATH}, trying BASE_DIR"
            )
            self.ICON_PATH = self.BASE_DIR / "assets" / "icon.png"

    def _validate_icon_path(self) -> None:
        """Validate ICON_PATH and set to None if invalid."""
        if self.ICON_PATH and (
            not self.ICON_PATH.exists() or not os.access(str(self.ICON_PATH), os.R_OK)
        ):
            self.logger.warning(
                f"Icon file not found or inaccessible at {self.ICON_PATH}"
            )
            self.ICON_PATH = None

    def ensure_dirs(self) -> None:
        """Ensure required directories for logs, database, and assets exist."""
        self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if self.ICON_PATH:
            self.ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info("Ensured required directories exist")

    @property
    def VERSION(self):
        """Return the application version from constants."""
        return APP_VERSION
