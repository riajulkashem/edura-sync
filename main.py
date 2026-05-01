import logging
import sys
import os
import argparse
from pathlib import Path
from logging.handlers import RotatingFileHandler
import sqlite3
import traceback

# Set up EARLY logging BEFORE anything else to catch startup crashes
def setup_early_logging():
    """Set up logging as early as possible, even before Config is initialized."""
    # Determine log file location
    if getattr(sys, "frozen", False):
        # Running as installed app - use APPDATA or fallback to temp
        if sys.platform.startswith("win"):
            appdata = os.getenv("APPDATA")
            if appdata:
                log_dir = Path(appdata) / "EduraSync" / "logs"
            else:
                log_dir = Path.home() / "AppData" / "Roaming" / "EduraSync" / "logs"
        else:
            log_dir = Path.home() / ".local" / "share" / "EduraSync" / "logs"
        
        # Fallback to temp directory if we can't write to APPDATA
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "edurasync.log"
            # Test write access
            test_file = log_dir / ".writetest"
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()
        except Exception:
            # Use temp directory as last resort
            import tempfile
            log_dir = Path(tempfile.gettempdir()) / "EduraSync"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "edurasync.log"
    else:
        # Running from source
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "edurasync.log"
    
    # Set up file handler
    try:
        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    except Exception as e:
        # If file logging fails, at least log to console
        file_handler = None
        print(f"WARNING: Could not set up file logging: {e}", file=sys.stderr)
    
    # Set up console handler ONLY when running from source (not in frozen/bundled app)
    # In bundled mode, keep output in file only to avoid PowerShell window
    if not getattr(sys, "frozen", False):
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
    else:
        console_handler = None
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()  # Clear any existing handlers
    if file_handler:
        root_logger.addHandler(file_handler)
    if console_handler:
        root_logger.addHandler(console_handler)
    
    # Log the log file location
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")
    print(f"EduraSync log file location: {log_file}", file=sys.stderr)
    
    return str(log_file)

# Set up logging immediately
LOG_FILE_PATH = setup_early_logging()

# Import peewee early to ensure it's available
try:
    import peewee
except ImportError as e:
    # If running from PyInstaller bundle, try to fix the path
    logging.error(f"Failed to import peewee: {e}", exc_info=True)
    if hasattr(sys, '_MEIPASS'):
        peewee_path = os.path.join(sys._MEIPASS, 'peewee')
        if os.path.exists(peewee_path):
            sys.path.insert(0, sys._MEIPASS)
            import peewee
        else:
            error_msg = f"peewee module not found. _MEIPASS: {sys._MEIPASS}, Error: {e}"
            logging.error(error_msg)
            print(f"CRITICAL ERROR: {error_msg}", file=sys.stderr)
            raise ImportError(error_msg)
    else:
        raise

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QTime, QObject
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
from interfaces.gui_pyside6.main_window import MainWindow
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
    if exc_type is KeyboardInterrupt:
        # Allow normal exit on Ctrl+C
        sys.exit(0)
    
    # Log to file if logging is set up
    try:
        logging.error(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    except Exception:
        pass  # If logging fails, at least print to console
    
    # Always print to console/stderr
    print("\n" + "="*80, file=sys.stderr)
    print("CRITICAL ERROR: Unhandled exception occurred!", file=sys.stderr)
    print("="*80, file=sys.stderr)
    print(f"Exception Type: {exc_type.__name__}", file=sys.stderr)
    print(f"Exception Value: {exc_value}", file=sys.stderr)
    print("\nTraceback:", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
    print("\n" + "="*80, file=sys.stderr)
    print(f"Log file location: {LOG_FILE_PATH}", file=sys.stderr)
    print("="*80 + "\n", file=sys.stderr)
    
    # Try to show a message box if Qt is available
    try:
        from PySide6.QtWidgets import QMessageBox, QApplication
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("EduraSync - Critical Error")
            msg.setText(f"An unexpected error occurred:\n\n{exc_value}\n\nCheck the log file for details:\n{LOG_FILE_PATH}")
            msg.setDetailedText(traceback.format_exception(exc_type, exc_value, exc_traceback))
            msg.exec()
    except Exception:
        pass  # If GUI is not available, just continue


class EduraSync(QObject):
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
        super().__init__()
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
            # Apply design system to the Qt application
            from interfaces.gui_pyside6.theme import apply_theme
            apply_theme(qt_app)

            self.dashboard_gui = MainWindow(
                self,
                self.device_repo,
                self.user_repo,
                self.notification_service,
                self.settings_repo,
                self.api_sync,
            )
            self.dashboard_gui.set_device_manager(self.device_manager)
            self.logger.info("MainWindow GUI initialized")
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
        # Register tray as notification callback
        self.notification_service.set_gui_callback(self.tray.show_message)

        # Initialize operation manager
        self.operation_manager = OperationManager()
        
        # Timers for periodic tasks
        self.scheduled_timers = {}  # Dict to store timers by task name
        self._last_task_run = {}   # Track last run minute per task to prevent double-fire

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
                raise DatabaseError(f"Unable to prepare fallback database directory: {fallback_dir}") from e

            fallback_db_path = str(fallback_dir / self.config.DB_NAME)
            self.logger.info(f"Attempting fallback database path: {fallback_db_path}")

            # Reset the singleton so get_database() creates a fresh instance at the fallback path.
            DatabaseFactory.reset()
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
            # Determine first-run: no settings row yet
            first_run = self.settings_repo.get_settings() is None

            if first_run:
                # Show onboarding wizard before the main window
                from interfaces.gui_pyside6.onboarding import OnboardingWizard
                from PySide6.QtWidgets import QDialog
                wizard = OnboardingWizard(self.settings_repo)
                if wizard.exec() == QDialog.DialogCode.Accepted:
                    # Reload settings so API sync picks them up
                    self.api_sync.load_settings()
                    self.logger.info("Onboarding completed — settings saved")
                else:
                    self.logger.warning("Onboarding cancelled — proceeding without settings")

            self.dashboard_gui.show_dashboard(first_run=first_run)
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
            
        # Start timer for daily sync only when enabled and a time is configured
        is_enabled = getattr(settings, "is_sync_enabled", True)
        if settings.sync_time and is_enabled:
            self._schedule_daily_task(settings.sync_time, self._full_sync, "daily_synchronization")
        elif not is_enabled:
            # Cancel any existing scheduled task when sync is disabled
            self._stop_timer("daily_synchronization")
            
        # Start interval-based sync if configured
        sync_interval = getattr(settings, "sync_interval", 0)
        if sync_interval > 0:
            self._schedule_interval_task(sync_interval, self._full_sync, "interval_synchronization")
        else:
            self._stop_timer("interval_synchronization")

        # Trigger initial sync on startup if enabled
        auto_startup = getattr(settings, "auto_sync_on_startup", False)
        if auto_startup:
            # Delay startup sync by 10 seconds to allow the app to fully initialize
            self.logger.info("Auto-sync on startup is enabled - scheduling initial sync...")
            QTimer.singleShot(10000, self._full_sync)
            
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
        # Stop and clean up any existing timer for this task before creating a new one.
        if task_name in self.scheduled_timers:
            old_timer = self.scheduled_timers.pop(task_name)
            if old_timer and old_timer.isActive():
                old_timer.stop()
            old_timer.deleteLater()

        timer = QTimer(self)
        timer.timeout.connect(lambda: self._check_and_run_task(target_time, task_function, task_name))
        timer.start(60000)  # Check every minute

        self.scheduled_timers[task_name] = timer
        self.logger.info(f"Scheduled daily task '{task_name}' for {target_time}")

    def _schedule_interval_task(self, interval_minutes: int, task_function, task_name: str):
        """Schedule a repeating task to run every X minutes."""
        self._stop_timer(task_name)

        ms = interval_minutes * 60 * 1000
        timer = QTimer(self)
        timer.timeout.connect(task_function)
        timer.start(ms)

        self.scheduled_timers[task_name] = timer
        self.logger.info(f"Scheduled interval task '{task_name}' every {interval_minutes} minutes")

    def _stop_timer(self, task_name: str):
        """Stop and remove a timer by name."""
        if task_name in self.scheduled_timers:
            old_timer = self.scheduled_timers.pop(task_name)
            if old_timer:
                if old_timer.isActive():
                    old_timer.stop()
                old_timer.deleteLater()
            self.logger.info(f"Stopped and removed timer: {task_name}")

    def _check_and_run_task(self, target_time, task_function, task_name: str):
        """Check if it's time to run the task and execute it."""
        current_time = QTime.currentTime()
        if (current_time.hour() == target_time.hour and
                current_time.minute() == target_time.minute):
            self.logger.info(f"Triggering scheduled task: {task_name}")
            # Prevent double-fire within the same minute window
            run_key = (current_time.hour(), current_time.minute())
            if self._last_task_run.get(task_name) == run_key:
                return
            self._last_task_run[task_name] = run_key
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
        
        # Clean up GUI resources
        if self.dashboard_gui:
            self.dashboard_gui.cleanup()

        # Stop and clean up tray (cleanup() calls stop() internally)
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
    # Check for Windows service commands before starting GUI/service logic
    # Commands: install, update, remove, start, stop, restart, debug
    SERVICE_COMMANDS = ['install', 'update', 'remove', 'start', 'stop', 'restart', 'debug']
    
    # Filter sys.argv to find the command even if a script path is passed (e.g. by an old ServiceManager)
    # This makes the app robust against variations in how it's called.
    filtered_args = [arg for arg in sys.argv if not arg.lower().endswith('.py') and not '_internal' in arg]
    
    # Check if any of our service commands are in the arguments
    has_service_cmd = any(cmd in sys.argv for cmd in SERVICE_COMMANDS)
    
    if has_service_cmd:
        try:
            # We need to make sure the root directory is in sys.path to import 'scripts'
            root_dir = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
                
            from scripts.install_service import EduraSyncService
            import win32serviceutil
            
            # If we found a service command but it wasn't at argv[1], 
            # we may need to clean up sys.argv for win32serviceutil
            if len(sys.argv) > 1 and sys.argv[1] not in SERVICE_COMMANDS:
                # Reconstruct sys.argv without the script path
                new_argv = [sys.argv[0]] + [arg for arg in sys.argv[1:] if arg in SERVICE_COMMANDS or arg.startswith('--')]
                sys.argv = new_argv
                
            win32serviceutil.HandleCommandLine(EduraSyncService)
            sys.exit(0)
        except Exception as e:
            # In case of error, log it and exit
            print(f"Service Management Error: {e}", file=sys.stderr)
            logging.error(f"Service Management Error: {e}", exc_info=True)
            sys.exit(1)

    # Global exception handler - set up early
    
    try:
        logger = logging.getLogger(__name__)
        logger.info("="*80)
        logger.info("EduraSync starting...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Log file: {LOG_FILE_PATH}")
        logger.info("="*80)
        
        # Create Qt application
        logger.info("Initializing Qt application...")
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # Keep running in tray
        logger.info("Qt application initialized")

        # Create main application instance
        logger.info("Creating EduraSync instance...")
        prime_sync = EduraSync(app, headless=args.headless, service=args.service)
        logger.info("EduraSync instance created")

        # Set up signal handlers before starting
        import signal
        signal.signal(signal.SIGINT, lambda sig, frame: prime_sync.exit_app())
        signal.signal(signal.SIGTERM, lambda sig, frame: prime_sync.exit_app())
        logger.info("Signal handlers set up")

        # Initialize and run components
        logger.info("Starting application...")
        prime_sync.run()
        logger.info("Application started successfully")

        # Start Qt event loop
        logger.info("Starting Qt event loop...")
        exit_code = app.exec()
        logger.info(f"Application exiting with code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        # Catch any exception during startup and log it
        error_msg = f"Fatal error during startup: {e}"
        logging.critical(error_msg, exc_info=True)
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"FATAL ERROR: {error_msg}", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        print(f"Log file location: {LOG_FILE_PATH}", file=sys.stderr)
        print("Please check the log file for details.", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # Try to show error dialog
        try:
            from PySide6.QtWidgets import QMessageBox, QApplication
            if QApplication.instance():
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("EduraSync - Fatal Error")
                msg.setText(f"Failed to start EduraSync:\n\n{error_msg}\n\nCheck the log file:\n{LOG_FILE_PATH}")
                msg.setDetailedText(traceback.format_exc())
                msg.exec()
        except Exception:
            pass
        
        sys.exit(1)
