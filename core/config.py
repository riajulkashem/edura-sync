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

        # Configure logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Determine base paths based on execution context (bundled or source)
        self._set_base_paths()
        self._set_data_paths()
        self._set_icon_path()

        # Define database and log file paths
        self.LOG_FILE: Path = self.DATA_DIR / "logs" / "primesync.log"
        self.DB_NAME: str = "primesync.db"
        self.DB_PATH: Path = self.DATA_DIR / self.DB_NAME

        # Validate icon path
        self._validate_icon_path()
        self.logger.info(f"Resolved ICON_PATH: {self.ICON_PATH}")

        # Ensure required directories exist
        self.ensure_dirs()

    def _setup_logging(self) -> None:
        """Configure logging to file or stdout based on execution context."""
        log_file = None if getattr(sys, "frozen", False) else "logs/primesync.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            filemode="a",
        )

    def _set_base_paths(self) -> None:
        """Set BASE_DIR and INSTALL_DIR based on whether running as bundled or source."""
        if getattr(sys, "frozen", False):
            self.BASE_DIR = Path(sys._MEIPASS)  # PyInstaller temp directory
            self.INSTALL_DIR = (
                Path("C:/Program Files/PrimeSyncTrayApp")
                if sys.platform == "win32"
                else Path.home() / "Applications/PrimeSyncTrayApp"
            )
        else:
            self.BASE_DIR = Path(__file__).parent.parent  # Project root
            self.INSTALL_DIR = self.BASE_DIR

    def _set_data_paths(self) -> None:
        """Set DATA_DIR, preferring INSTALL_DIR with fallback to APPDATA or home."""
        self.DATA_DIR = self.INSTALL_DIR / "data"
        if not os.access(str(self.DATA_DIR), os.W_OK):
            self.DATA_DIR = (
                Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
                / "PrimeSync"
            )

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
