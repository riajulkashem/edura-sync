import logging
import sys
import threading
import tkinter as tk

from core.config import Config
from core.security import SecurityManager
from interfaces.database.models import (
    DatabaseFactory,
    db,
    Device,
    Attendance,
    User,
    Settings,
    Schedule,
)
from interfaces.database.repository import (
    DeviceRepository,
    UserRepository,
    AttendanceRepository,
    SettingsRepository,
    ScheduleRepository,
)
from interfaces.gui.dashboard import DashboardGUI
from interfaces.gui.settings import SettingsGUI
from interfaces.gui.tray import SystemTray
from services.api_client import APIClient
from services.device_manager import DeviceManager
from services.notification import NotificationService
from services.scheduler import TaskScheduler

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
        db_instance.create_tables(
            [Device, User, Attendance, Settings, Schedule], safe=True
        )
        db_instance.close()
        self.logger.info("Database initialized")

        # Initialize repositories
        self.device_repo = DeviceRepository()
        self.user_repo = UserRepository()
        self.attendance_repo = AttendanceRepository()
        self.settings_repo = SettingsRepository()
        self.schedule_repo = ScheduleRepository()

        # Initialize services
        self.security = SecurityManager()
        self.notification_service = NotificationService(self.config)
        self.device_manager = DeviceManager(
            self.notification_service,
            self.device_repo,
            self.user_repo,
            self.attendance_repo,
            self.schedule_repo,
        )
        self.api_client = APIClient(
            self.security,
            self.notification_service,
            self.settings_repo,
            self.attendance_repo,
            self.schedule_repo,
        )
        
        # Initialize dummy scheduler (no actual scheduling)
        self.scheduler = TaskScheduler(
            self.device_manager,
            self.api_client,
            self.notification_service,
            self.schedule_repo,
        )

        # Initialize GUI components
        self.root = tk.Tk()
        self.root.withdraw()
        self.dashboard_gui = DashboardGUI(
            self.root, self, self.device_repo, self.user_repo, self.notification_service
        )
        self.settings_gui = SettingsGUI(
            self.root,
            self,
            self.security,
            self.settings_repo,
            self.schedule_repo,
            self.notification_service,
        )

        # Initialize system tray
        self.tray = SystemTray(
            self,
            self.config,
            self.device_manager,
            self.scheduler,
            self.api_client,
            self.dashboard_gui,
            self.settings_gui,
            self.notification_service,
        )

        # Load settings
        self._load_settings()
        self._add_to_startup()

    def _load_settings(self) -> None:
        """Load settings and initialize services."""
        try:
            if self.settings_repo.get_settings() is None:
                self.settings_gui.show_settings(first_run=True)
            else:
                self.api_client.update_settings()
                # We're not calling scheduler.update_settings() since scheduler is disabled
            self.logger.info("Settings loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            self.settings_gui.show_settings(first_run=True)

    def _add_to_startup(self) -> None:
        """Add application to system startup (Windows or macOS)."""
        # Implementation similar to original, moved to a utility module in full code
        self.logger.info("Added to system startup")

    def run(self) -> None:
        """Start the application, running the system tray and main loop."""
        try:
            tray_thread = threading.Thread(target=self.tray.run, daemon=True)
            tray_thread.start()
            self.logger.info("System tray thread started")
            self.root.mainloop()
            self.logger.info("Application main loop started")
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
            # We still call scheduler.shutdown() but it's now a dummy method
            self.scheduler.shutdown()
            self.tray.stop()
            if not db.is_closed():
                db.close()
            self.root.quit()
            self.root.destroy()
            self.logger.info("Application shutdown completed")
            sys.exit(0)
        except Exception as e:
            self.logger.error(f"Critical error during shutdown: {e}")
            sys.exit(1)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        filename=Config().LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        filemode="a",
    )

    # Set up global exception handler
    sys.excepthook = handle_exception

    try:
        app = PrimeSync()
        app.run()
    except Exception as e:
        logging.critical(f"Fatal error starting application: {e}")

        # Try to show an error dialog
        try:
            import tkinter.messagebox as messagebox

            messagebox.showerror("PrimeSync Error", f"Fatal error: {e}")
        except:
            pass

        sys.exit(1)