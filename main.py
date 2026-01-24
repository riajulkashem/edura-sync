import logging
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, time as dt_time
from logging.handlers import RotatingFileHandler
import sqlite3

# Import peewee early to ensure it's available
try:
    import peewee
except ImportError as e:
    # If running from PyInstaller bundle, try to fix the path
    if hasattr(sys, '_MEIPASS'):
        import importlib.util
        peewee_path = os.path.join(sys._MEIPASS, 'peewee')
        if os.path.exists(peewee_path):
            sys.path.insert(0, sys._MEIPASS)
            import peewee
        else:
            raise ImportError(f"peewee module not found. _MEIPASS: {sys._MEIPASS}, Error: {e}")
    else:
        raise

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QTime
from PySide6.QtGui import QIcon, QPixmap

from core.config import Config
from core.constants import APP_NAME, DB_PRAGMAS_MINIMAL, LOG_MESSAGES, DEFAULT_SETTING
from core.operation_manager import OperationManager
from core.exceptions import ValidationError, DatabaseError
from interfaces.database.models import DatabaseFactory, initialize_database, db
from interfaces.database.repository import (
    DeviceRepository, SettingsRepository, 
    UserRepository, AttendanceRepository
)
from interfaces.gui_pyside6.dashboard import DashboardGUI
from interfaces.gui_pyside6.tray import SystemTray
from services.api_sync import APISync
from services.device_manager import DeviceManager
from services.notification import NotificationService


# Parse command-line arguments
def parse_arguments():
    """Parse command-line arguments for operational modes."""
    parser = argparse.ArgumentParser(
        description='EduraSync - ZKTeco Attendance Synchronization Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Run with full GUI
  python main.py --headless         Run with tray only (minimal resources)
  python main.py --service          Run as Windows service (no GUI)
        """
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run in headless mode (system tray only, no dashboard window)'
    )
    parser.add_argument(
        '--service',
        action='store_true',
        help='Run as Windows service (no GUI at all, scheduled tasks only)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'{APP_NAME} {Config().VERSION}'
    )
    
    return parser.parse_args()


args = parse_arguments()


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log unhandled exceptions"""
    logging.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


class PrimeSync:
    """
    Main application class for EduraSync, managing GUI and services.
    Acts as a facade to coordinate subsystems.
    """

    def __init__(self, qt_app, headless=False, service=False):
        """Initialize the application with all dependencies.
        
        Args:
            qt_app: Qt application instance
            headless: Run without dashboard (tray only)
            service: Run as service (no GUI at all)
        """
        self.running: bool = True
        self.headless = headless
        self.service = service
        self.config: Config = Config()
        self.qt_app = qt_app
        self.logger = logging.getLogger(__name__)

        # Set application icon
        self._set_application_icon()

        # Initialize database with proper error handling
        self._initialize_database()

        # Initialize repositories
        self.device_repo = DeviceRepository()
        self.user_repo = UserRepository()
        self.attendance_repo = AttendanceRepository()
        self.settings_repo = SettingsRepository()

        # Initialize services
        self.notification_service = NotificationService(self.config)
        self.device_manager = DeviceManager(
            self.notification_service,
            self.device_repo,
            self.user_repo,
            self.attendance_repo,
        )
        
        # Enable background optimization mode
        if self.headless or self.service:
            self.device_manager.background_mode = True
            
        self.api_sync = APISync(
            self.notification_service,
            self.settings_repo,
            self.attendance_repo,
            self.user_repo,
            self.device_repo,
            self.device_manager,
        )

        # Initialize GUI components - skip dashboard in headless/service mode
        if not self.headless and not self.service:
            self.dashboard_gui = DashboardGUI(
                self,
                self.device_repo,
                self.user_repo,
                self.notification_service,
                self.settings_repo,
                self.api_sync,
            )

            # Update the dashboard with all required dependencies
            self.dashboard_gui.settings_repo = self.settings_repo
            self.dashboard_gui.api_sync = self.api_sync
            self.dashboard_gui.set_device_manager(self.device_manager)
            self.logger.info("Dashboard GUI initialized")
        else:
            self.dashboard_gui = None
            mode_str = "service" if self.service else "headless"
            self.logger.info(f"Running in {mode_str} mode - dashboard disabled")

        # Initialize system tray
        self.tray = SystemTray(
            self,
            self.config,
            self.device_manager,
            self.api_sync,
            self.dashboard_gui,  # Can be None in service mode
            self.notification_service,
        )

        # Initialize operation manager
        self.operation_manager = OperationManager()
        
        # Timers for periodic tasks
        self.scheduled_timers = {}  # Dict to store timers by task name

        # Load settings
        self._load_settings()

    def _set_application_icon(self):
        """Set the application icon."""
        try:
            icon_path = self.config.ICON_PATH
            if icon_path and icon_path.exists():
                icon = QIcon(QPixmap(str(icon_path)))
                self.qt_app.setWindowIcon(icon)
                self.logger.info(f"Application icon set from {icon_path}")
            else:
                self.logger.warning("Application icon not found")
        except Exception as e:
            self.logger.error(f"Failed to set application icon: {e}")

    def _initialize_database(self) -> None:
        """Initialize database with proper error handling."""
        # Use minimal pragmas if in headless or service mode
        pragmas = None
        if self.headless or self.service:
            pragmas = DB_PRAGMAS_MINIMAL
            self.logger.info("Using minimal database pragmas for background mode")
        # Try connecting to the configured database path first. If that fails
        # (e.g. disk I/O error, permission issues), try a sensible per-user
        # fallback directory depending on the platform.
        db_instance = DatabaseFactory.get_database(str(self.config.DB_PATH), pragmas=pragmas)
        try:
            db_instance.connect()
        except (peewee.OperationalError, sqlite3.OperationalError, Exception) as e:
            # Log the original error and attempt fallback
            self.logger.error(f"Failed to open database at {self.config.DB_PATH}: {e}")

            # Build a platform-appropriate fallback directory
            if sys.platform == "darwin":
                fallback_dir = Path.home() / "Library" / "Application Support" / "EduraSync"
            elif sys.platform.startswith("win"):
                fallback_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "EduraSync"
            else:
                fallback_dir = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "EduraSync"

            try:
                fallback_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                # If we cannot create fallback dir, re-raise original error as DatabaseError
                raise DatabaseError(f"Unable to prepare fallback database directory: {fallback_dir}") from e

            fallback_db_path = str(fallback_dir / self.config.DB_NAME)
            self.logger.info(f"Attempting fallback database path: {fallback_db_path}")

            # Create a new database instance pointed to the fallback path
            db_instance = DatabaseFactory.get_database(fallback_db_path, pragmas=pragmas)
            try:
                db_instance.connect()
            except (peewee.OperationalError, sqlite3.OperationalError, Exception) as e2:
                self.logger.error(f"Fallback DB connect failed: {e2}")
                raise DatabaseError(f"Database connection failed for configured and fallback locations: {e2}")

        # Use the new initialization function
        initialize_database()

        self.logger.info(LOG_MESSAGES["DB_INITIALIZED"])

    def _load_settings(self) -> None:
        """Load settings and initialize services."""
        settings = self.settings_repo.get_settings()

        if settings is None:
            # Create default settings if none exist
            try:
                self.settings_repo.save_settings(**DEFAULT_SETTING)
                self.logger.info(
                    "Created default settings - please update them in the dashboard"
                )
                self.notification_service.notify(
                    "Settings",
                    "Default settings created. Please update them in the dashboard.",
                    "info",
                )
            except ValidationError as e:
                self.logger.error(f"Failed to create default settings: {e.message}")
                self.notification_service.notify(
                    "Error",
                    f"Failed to create default settings: {e.message}",
                    "error",
                )

        # Update API sync with settings
        self.api_sync.load_settings()

        self.logger.info(LOG_MESSAGES["SETTINGS_LOADED"])

    def run(self) -> None:
        """Initialize and start all application components."""
        # Show dashboard only in GUI mode
        if not self.headless and not self.service:
            self.dashboard_gui.show_dashboard()
            # Start periodic refresh
            self.dashboard_gui.start_periodic_refresh(30000)
        
        # Start system tray (always, unless service mode)
        if not self.service:
            self.tray.run()
        
        # Schedule daily tasks (always)
        self._start_periodic_tasks()
        
        self.logger.info("EduraSync application components started")


    def _start_periodic_tasks(self):
        """Start periodic tasks based on settings."""
        # Timers will be created as needed
        
        # Existing tasks...
        settings = self.settings_repo.get_settings()
        if not settings:
            return
            
        # Start timer for daily sync if set
        if settings.sync_time:
            self._schedule_daily_task(settings.sync_time, self._full_sync, "daily_synchronization")
            
        # Trigger initial cleanup
        QTimer.singleShot(5000, self._periodic_cleanup_startup)

    def _periodic_cleanup_startup(self):
        """Initial cleanup on startup."""
        if not self.operation_manager.acquire_operation_lock("Startup Cleanup"):
            return

        try:
            self.logger.info("Running initial database cleanup...")
            deleted_count = self.attendance_repo.cleanup_posted_attendance(days_old=1)
            self.logger.info(f"Initial cleanup complete. Deleted {deleted_count} records.")
        except Exception as e:
            self.logger.error(f"Error during initial cleanup: {e}")
        finally:
            self.operation_manager.release_operation_lock("Startup Cleanup")

    def _periodic_cleanup(self):
        """Run periodic database cleanup (typically after successful posting)."""
        if not self.operation_manager.acquire_operation_lock("DB Cleanup"):
            self.logger.warning("Skipping cleanup: Another operation in progress")
            return

        try:
            self.logger.info("Running database maintenance cleanup...")
            deleted_count = self.attendance_repo.cleanup_posted_attendance(days_old=1)
            self.logger.info(f"Cleanup complete. Deleted {deleted_count} old attendance records.")
            
            # Vacuum database to reclaim space
            from interfaces.database.models import db
            db.execute_sql('VACUUM')
            self.logger.info("Database VACUUM complete.")
        except Exception as e:
            self.logger.error(f"Error during database cleanup: {e}")
        finally:
            self.operation_manager.release_operation_lock("DB Cleanup")

    def _schedule_daily_task(self, target_time, task_function, task_name: str):
        """Schedule a daily task to run at the specified time."""
        # Create a timer that checks every minute
        timer = QTimer()
        timer.timeout.connect(lambda: self._check_and_run_task(target_time, task_function))
        timer.start(60000)  # Check every minute
        
        # Store timer with task name
        self.scheduled_timers[task_name] = timer
            
        self.logger.info(f"Scheduled daily task '{task_name}' for {target_time}")

    def _check_and_run_task(self, target_time, task_function):
        """Check if it's time to run the task and execute it."""
        current_time = QTime.currentTime()
        # Check if current time matches target time (within a minute)
        if (current_time.hour() == target_time.hour and 
            current_time.minute() == target_time.minute):
            try:
                task_function()
            except Exception as e:
                self.logger.error(f"Error in periodic task: {e}")
                self.notification_service.notify(
                    "Error",
                    f"Periodic task failed: {str(e)}",
                    "error"
                )

    def _pull_attendance_data(self):
        """Pull attendance data from devices."""
        if not self.operation_manager.acquire_operation_lock("Fetching device logs..."):
            self.logger.warning("Skipping scheduled pull: Another operation in progress")
            return

        self.logger.info("Running scheduled attendance pull")
        try:
            self.device_manager.pull_data()
            self.notification_service.notify(
                "Attendance Pull",
                "Scheduled attendance data pull completed",
                "info"
            )
        except Exception as e:
            self.logger.error(f"Failed to pull attendance data: {e}")
            self.notification_service.notify(
                "Error",
                f"Failed to pull attendance data: {str(e)}",
                "error"
            )
        finally:
            self.operation_manager.release_operation_lock("Fetching device logs...")

    def _push_to_cloud(self):
        """Push data to cloud."""
        if not self.operation_manager.acquire_operation_lock("Uploading to cloud..."):
            self.logger.warning("Skipping scheduled push: Another operation in progress")
            return

        self.logger.info("Running scheduled cloud push")
        try:
            self.api_sync.post_to_cloud()
            self.notification_service.notify(
                "Cloud Push",
                "Scheduled data push to cloud completed",
                "info"
            )
            
            # Run background cleanup after successful posting
            QTimer.singleShot(2000, self._periodic_cleanup)
        except Exception as e:
            self.logger.error(f"Failed to push data to cloud: {e}")
            self.notification_service.notify(
                "Error",
                f"Failed to push data to cloud: {str(e)}",
                "error"
            )
        finally:
            self.operation_manager.release_operation_lock("Uploading to cloud...")

    def _full_sync(self):
        """Perform a full synchronization: pull from device, then push to cloud."""
        if not self.operation_manager.acquire_operation_lock("Daily synchronization..."):
            self.logger.warning("Skipping scheduled full sync: Another operation in progress")
            return

        self.logger.info("Starting scheduled full synchronization")
        try:
            # 1. Pull data
            self.device_manager.pull_data()
            
            # 2. Push to cloud (with a small delay to ensure DB is ready)
            # We release the lock first so _push_to_cloud can acquire its own
            self.operation_manager.release_operation_lock("Daily synchronization...")
            QTimer.singleShot(5000, self._push_to_cloud)
            
        except Exception as e:
            # Handle lock release if not already released in try block
            if self.operation_manager.get_current_operation() == "Daily synchronization...":
                self.operation_manager.release_operation_lock("Daily synchronization...")
                
            self.logger.error(f"Full synchronization failed: {e}")
            self.notification_service.notify(
                "Sync Error",
                f"Scheduled synchronization failed: {str(e)}",
                "error"
            )

    def exit_app(self) -> None:
        """Cleanly exit the application."""
        if not self.running:
            self.logger.info("Exit requested but application already shutting down")
            return
        self.running = False
        self.logger.info("Initiating application shutdown")

        # Stop periodic tasks
        if self.dashboard_gui:
            self.dashboard_gui.stop_periodic_refresh()
        
        # Stop all scheduled timers
        for timer_name, timer in self.scheduled_timers.items():
            if timer:
                timer.stop()
                self.logger.debug(f"Stopped timer: {timer_name}")
        self.scheduled_timers.clear()
        
        # Stop tray
        self.tray.stop()
        
        # Clean up GUI resources
        if self.dashboard_gui:
            self.dashboard_gui.cleanup()
        self.tray.cleanup()
        
        # Close API sync session
        self.api_sync.close()
        
        # Close database connection
        if not db.is_closed():
            db.close()
            
        self.logger.info("Application shutdown complete")
        
        sys.exit(0)

    def _setup_logging(self) -> None:
        """Configure logging to file or stdout based on execution context."""
        log_file = None if getattr(sys, "frozen", False) else "logs/edurasync.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            filemode="a",
        )

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Setup logging with rotation
    file_handler = RotatingFileHandler(
        "logs/edurasync.log",
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler]
    )

    # Global exception handler
    sys.excepthook = handle_exception

    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Create main application instance
    prime_sync = PrimeSync(app, headless=args.headless, service=args.service)

    # Set up signal handlers before starting
    import signal
    signal.signal(signal.SIGINT, lambda sig, frame: prime_sync.exit_app())
    signal.signal(signal.SIGTERM, lambda sig, frame: prime_sync.exit_app())

    # Initialize and run components
    prime_sync.run()

    # Start Qt event loop (only if not in service mode which might handle its own loop)
    # Actually, even in service mode we need the QTimer loop
    sys.exit(app.exec())
