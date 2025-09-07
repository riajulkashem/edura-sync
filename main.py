import logging
import sys
import threading
import tkinter as tk
from pathlib import Path

from core.config import Config
from core.constants import LOG_MESSAGES, DEFAULT_SETTING
from core.security import SecurityManager
from core.exceptions import DatabaseError, ConfigurationError, ValidationError
from interfaces.database.models import DatabaseFactory, db, initialize_database
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

        try:
            # Initialize database with proper error handling
            self._initialize_database()

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
                self.user_repo,
                self.device_repo,
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

        except DatabaseError as e:
            self.logger.error(f"Database initialization failed: {e.message}")
            self.notification_service.notify(
                "Error", f"Database error: {e.message}", "error"
            )
            raise
        except ConfigurationError as e:
            self.logger.error(f"Configuration error: {e.message}")
            self.notification_service.notify(
                "Error", f"Configuration error: {e.message}", "error"
            )
            raise
        except Exception as e:
            self.logger.error(f"Application initialization failed: {e}")
            raise

    def _initialize_database(self) -> None:
        """Initialize database with proper error handling."""
        try:
            db_instance = DatabaseFactory.get_database(str(self.config.DB_PATH))
            db_instance.connect()

            # Use the new initialization function
            initialize_database()

            self.logger.info(LOG_MESSAGES["DB_INITIALIZED"])
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Failed to initialize database: {str(e)}")

    def _load_settings(self) -> None:
        """Load settings and initialize services."""
        try:
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

            # Update API client with settings
            self.api_client.update_settings()

            # Show dashboard
            self.dashboard_gui.show_dashboard()
            self.logger.info(LOG_MESSAGES["SETTINGS_LOADED"])

        except DatabaseError as e:
            self.logger.error(f"Database error loading settings: {e.message}")
            # Still show dashboard with error notification
            self.dashboard_gui.show_dashboard()
            self.notification_service.notify(
                "Error",
                f"Database error loading settings: {e.message}. Please check database connection.",
                "error",
            )
        except ValidationError as e:
            self.logger.error(f"Validation error loading settings: {e.message}")
            self.dashboard_gui.show_dashboard()
            self.notification_service.notify(
                "Error",
                f"Settings validation error: {e.message}. Please check settings in dashboard.",
                "error",
            )
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
        """Add application to system startup (Windows only)."""
        try:
            import os
            import platform
            import sys

            if platform.system() == "Windows":
                # Windows autostart is handled by the installer (registry)
                pass
            else:
                self.logger.info("System startup not supported on this platform")

        except Exception as e:
            self.logger.error(f"Failed to add to startup: {e}")

    def run(self) -> None:
        """Start the application, running the system tray and main loop."""
        try:
            # Check if settings exist and are valid before starting
            if not self.settings_repo.get_settings():
                self.logger.warning("No settings found. Using defaults.")
                self.notification_service.notify(
                    "Settings",
                    "No settings found. Please configure in the dashboard.",
                    "warning",
                )

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
        """Cleanly exit the application with improved error handling for threading issues."""
        if not self.running:
            self.logger.info("Exit requested but application already shutting down")
            return
        self.running = False
        self.logger.info("Initiating application shutdown")

        try:
            # Stop tray first to prevent further callbacks
            self.tray.stop()
            
            # Schedule GUI cleanup on the main thread if it exists
            if hasattr(self, 'root') and self.root:
                try:
                    # Check if we're in the main thread
                    import threading
                    if threading.current_thread() is threading.main_thread():
                        self._cleanup_gui()
                    else:
                        # Schedule cleanup on main thread
                        self.root.after(0, self._cleanup_gui)
                        # Give time for the main thread to process
                        import time
                        time.sleep(0.1)
                except Exception as e:
                    self.logger.error(f"Error during GUI cleanup: {e}")
            
            # Close database connection
            if not db.is_closed():
                db.close()
                
            self.logger.info("Application shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        finally:
            # Force exit if we're not in the main thread
            import threading
            if threading.current_thread() is not threading.main_thread():
                import os
                os._exit(0)
            else:
                sys.exit(0)
    
    def _cleanup_gui(self) -> None:
        """Clean up GUI components safely."""
        try:
            if hasattr(self, 'root') and self.root:
                # Withdraw window first
                self.root.withdraw()
                # Then quit the main loop
                self.root.quit()
                # Finally destroy (this may fail if not in main thread)
                try:
                    self.root.destroy()
                except RuntimeError as e:
                    if "main thread is not in main loop" in str(e):
                        self.logger.warning("Cannot destroy GUI from non-main thread, forcing exit")
                    else:
                        raise
        except Exception as e:
            self.logger.error(f"Error cleaning up GUI: {e}")


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
