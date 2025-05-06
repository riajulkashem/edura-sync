import logging
import sys
import threading
import tkinter as tk
from pathlib import Path

from core.config import Config
from core.constants import LOG_MESSAGES, DEFAULT_SETTING
from core.security import SecurityManager
from interfaces.database.models import (
    DatabaseFactory,
    db,
    Device,
    Attendance,
    User,
    Settings,
)
from interfaces.database.repository import (
    DeviceRepository,
    UserRepository,
    AttendanceRepository,
    SettingsRepository,
)
from interfaces.gui.dashboard import DashboardGUI
from interfaces.gui.tray import SystemTray
from services.api_client import APIClient
from services.device_manager import DeviceManager
from services.notification import NotificationService
from core.scheduler import SchedulerService


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log unhandled exceptions"""
    logging.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    return sys.__excepthook__(exc_type, exc_value, exc_traceback)


class PrimeSync:
    """
    Main application class for PrimeSync, managing system tray, GUI, and services.
    Acts as a facade to coordinate subsystems.
    """

    def __init__(self):
        """Initialize the application with all dependencies."""
        self.running: bool = True
        self.config: Config = Config()
        self.logger = logging.getLogger(__name__)

        # Initialize database
        db_instance = DatabaseFactory.get_database(str(self.config.DB_PATH))
        db_instance.connect()
        db_instance.create_tables([Device, User, Attendance, Settings], safe=True)
        db_instance.close()
        self.logger.info(LOG_MESSAGES["DB_INITIALIZED"])

        # Initialize repositories
        self.device_repo = DeviceRepository()
        self.user_repo = UserRepository()
        self.attendance_repo = AttendanceRepository()
        self.settings_repo = SettingsRepository()

        # Initialize services
        self.security = SecurityManager()
        self.notification_service = NotificationService(self.config)
        self.device_manager = DeviceManager(
            self.notification_service,
            self.device_repo,
            self.user_repo,
            self.attendance_repo,
        )
        self.api_client = APIClient(
            self.security,
            self.notification_service,
            self.settings_repo,
            self.attendance_repo,
            self.device_manager,
        )

        # Initialize GUI components
        self.root = tk.Tk()
        self.root.withdraw()
        self.dashboard_gui = DashboardGUI(
            self.root,
            self,
            self.device_repo,
            self.user_repo,
            self.notification_service,
            self.settings_repo,
            self.api_client,
            self.security,
        )

        # In the PrimeSync.__init__ method, after initializing dashboard_gui
        # Update the dashboard with all required dependencies
        self.dashboard_gui.settings_repo = self.settings_repo
        self.dashboard_gui.api_client = self.api_client
        self.dashboard_gui.security = self.security
        self.dashboard_gui.set_device_manager(self.device_manager)

        # Initialize system tray
        self.tray = SystemTray(
            self,
            self.config,
            self.device_manager,
            self.api_client,
            self.dashboard_gui,
            self.notification_service,
        )

        # Load settings
        self._load_settings()
        self._add_to_startup()

        # Initialize scheduler after all other components
        self.scheduler = SchedulerService(self.settings_repo, self.api_client)

    def _load_settings(self) -> None:
        """Load settings and initialize services."""
        try:
            settings = self.settings_repo.get_settings()

            if settings is None:
                # Create default settings if none exist
                self.settings_repo.save_settings(**DEFAULT_SETTING)
                self.logger.info(
                    "Created default settings - please update them in the dashboard"
                )
                self.notification_service.notify(
                    "Settings",
                    "Default settings created. Please update them in the dashboard.",
                    "info",
                )

            # Update API client with settings
            self.api_client.update_settings()

            # Show dashboard
            self.dashboard_gui.show_dashboard()
            self.logger.info(LOG_MESSAGES["SETTINGS_LOADED"])

        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            # Still show dashboard with error notification
            self.dashboard_gui.show_dashboard()
            self.notification_service.notify(
                "Error",
                f"Failed to load settings: {str(e)}. Please update settings in the dashboard.",
                "error",
            )

    def _add_to_startup(self) -> None:
        """Add application to system startup (Windows or macOS)."""
        try:
            import os
            import platform
            import sys

            if platform.system() == "Windows":
                # Windows autostart is handled by the installer (registry)
                pass
            elif platform.system() == "Darwin":  # macOS
                import plistlib

                # Create a macOS LaunchAgent plist file
                home = os.path.expanduser("~")
                launch_agents_dir = os.path.join(home, "Library/LaunchAgents")

                if not os.path.exists(launch_agents_dir):
                    os.makedirs(launch_agents_dir)

                plist_path = os.path.join(
                    launch_agents_dir, "com.primesync.trayapp.plist"
                )

                if getattr(sys, "frozen", False):
                    # Running as compiled app
                    executable_path = sys.executable
                else:
                    # Running as script
                    executable_path = sys.executable
                    script_path = os.path.abspath(sys.argv[0])
                    executable_path = f"{executable_path} {script_path}"

                plist_content = {
                    "Label": "com.primesync.trayapp",
                    "ProgramArguments": [executable_path],
                    "RunAtLoad": True,
                    "KeepAlive": False,
                }

                with open(plist_path, "wb") as f:
                    plistlib.dump(plist_content, f)

            self.logger.info("Added to system startup")
        except Exception as e:
            self.logger.error(f"Failed to add to startup: {e}")

    # In main.py - update the run method
    def run(self) -> None:
        """Start the application, running the system tray and main loop."""
        print("Start the application, running the system tray and main loop")
        try:
            # Check settings before starting
            settings = self.settings_repo.get_settings()

            if not settings:
                self.logger.warning("No settings found. Using defaults.")
                self.notification_service.notify(
                    "Settings",
                    "No settings found. Please configure in the dashboard.",
                    "warning",
                )
            else:
                # Auto-start scheduler if enabled in settings
                if settings.is_scheduler_enabled:
                    self.scheduler.start()
                    self.logger.info("Scheduler auto-started based on settings")
                else:
                    self.logger.info("Scheduler not started (disabled in settings)")

            # Start tray icon - change to non-daemon for more reliable execution
            tray_thread = threading.Thread(target=self.tray.run, daemon=False)
            tray_thread.start()
            self.logger.info(LOG_MESSAGES["TRAY_STARTED"])

            # Start GUI
            self.root.mainloop()
            self.logger.info("Application main loop started")

            # Wait for tray thread to complete if mainloop exits
            if tray_thread.is_alive():
                tray_thread.join()

        except Exception as e:
            self.logger.error(f"Error running application: {e}")
            self.exit_app()

    def exit_app(self) -> None:
        """Cleanly exit the application, shutting down all components."""
        if not self.running:
            self.logger.info("Exit requested but application already shutting down")
            return
        self.running = False
        self.logger.info("Initiating application shutdown")

        try:
            self.tray.stop()
            if not db.is_closed():
                db.close()
            self.root.quit()
            self.root.destroy()
            self.logger.info(LOG_MESSAGES["APP_SHUTDOWN"])
            sys.exit(0)
        except Exception as e:
            self.logger.error(f"Critical error during shutdown: {e}")
            sys.exit(1)

        # Stop the scheduler
        if hasattr(self, 'scheduler'):
            self.scheduler.stop()


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/primesync.log"), logging.StreamHandler()],
    )

    # Set exception handler
    sys.excepthook = handle_exception

    # Create and run application
    app = PrimeSync()
    try:
        print("Starting PrimeSync application...")
        app.run()
    except KeyboardInterrupt:
        print("Application terminated by user")
        app.exit_app()
    except Exception as e:
        print(f"Critical error: {e}")
        logging.error(f"Critical error: {e}", exc_info=True)
        app.exit_app()
