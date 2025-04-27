import logging
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

import pystray
from PIL import Image

from api_client import APIClient
from config import Config
from device_manager import DeviceManager
from gui import PrimeSyncGUI
from models import Settings, db, Device, User, Attendance, Schedule
from scheduler import TaskScheduler
from security import SecurityManager

# Configure logging
logging.basicConfig(
    filename=Config.LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    filemode='a'
)


class PrimeSync:
    """Main system tray application for PrimeSync device management."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.config = Config()
        self.security = SecurityManager()
        self.device_manager = DeviceManager()
        self.api_client = APIClient(self.security)
        self.gui = PrimeSyncGUI(self.root, self)
        self.scheduler = TaskScheduler(self.device_manager, self.api_client)
        self.icon = None
        self.running = True
        self.tray_thread = None
        self.setup_tray()
        self.initialize_db()
        self.load_settings()
        self.add_to_startup()

    def setup_tray(self):
        """Set up system tray icon and menu."""
        try:
            icon_path = self.config.ICON_PATH
            if not icon_path.exists():
                raise FileNotFoundError("Icon file not found")
            image = Image.open(icon_path)
        except Exception as e:
            logging.error(f"Failed to load icon: {e}")
            image = Image.new('RGB', (64, 64), color='blue')

        menu = (
            pystray.MenuItem("Check Devices Status", self.device_manager.check_devices),
            pystray.MenuItem("Sync Data", self.scheduler.sync_data),
            pystray.MenuItem("Post Data to Cloud", self.api_client.post_to_cloud),
            pystray.MenuItem("Pull Data from Machine", self.device_manager.pull_data),
            pystray.MenuItem("Settings", self.gui.show_settings),
            pystray.MenuItem("Show Dashboard", self.gui.show_dashboard),
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.icon = pystray.Icon("PrimeSync", image, "PrimeSync Manager", menu)
        logging.info("System tray initialized.")

    def initialize_db(self):
        """Initialize database and create tables if they don't exist."""
        try:
            db.connect()
            db.create_tables([Device, User, Attendance, Settings, Schedule], safe=True)
            logging.info("Database initialized.")
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            raise
        finally:
            db.close()

    def load_settings(self):
        """Load settings from database or prompt for first-time setup."""
        db.connect()
        try:
            if Settings.select().count() > 1:
                Settings.delete().where(Settings.id != Settings.select().order_by(Settings.id).get().id).execute()
                logging.info("Cleaned up multiple settings rows, kept only the first one.")

            if not Settings.select().exists():
                self.gui.show_settings(first_run=True)
            else:
                settings = Settings.get()
                self.api_client.update_settings(settings)
                self.scheduler.update_settings()
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            self.gui.show_settings(first_run=True)
        finally:
            db.close()

    def add_to_startup(self):
        """Add application to system startup (Windows or macOS)."""
        import platform
        exe_path = sys.executable if not hasattr(sys, 'frozen') else sys.executable
        app_name = "PrimeSync"

        if platform.system() == "Windows":
            try:
                import win32api
                import win32con
                key = win32api.RegOpenKey(
                    win32con.HKEY_CURRENT_USER,
                    "Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                    0,
                    win32con.KEY_SET_VALUE
                )
                win32api.RegSetValueEx(key, app_name, 0, win32con.REG_SZ, f'"{exe_path}"')
                win32api.RegCloseKey(key)
                logging.info("Added to Windows startup.")
            except Exception as e:
                logging.error(f"Failed to add to Windows startup: {e}")

        elif platform.system() == "Darwin":
            try:
                plist = {
                    "Label": app_name,
                    "ProgramArguments": [exe_path],
                    "RunAtLoad": True,
                    "KeepAlive": True
                }
                plist_path = Path.home() / f"Library/LaunchAgents/{app_name}.plist"
                with open(plist_path, "wb") as f:
                    import plistlib
                    plistlib.dump(plist, f)
                subprocess.run(["launchctl", "load", str(plist_path)], check=True)
                logging.info("Added to macOS startup.")
            except Exception as e:
                logging.error(f"Failed to add to macOS startup: {e}")

    def exit_app(self):
        """Cleanly exit the application."""
        if not self.running:
            return
        self.running = False
        logging.info("Initiating application shutdown.")
        try:
            self.scheduler.shutdown()
            logging.info("Scheduler shut down.")

            if self.icon:
                self.icon.stop()
                self.icon = None
                logging.info("System tray stopped.")

            if not db.is_closed():
                db.close()
                logging.info("Database connection closed.")

            try:
                self.root.quit()
                self.root.destroy()
                logging.info("Tkinter root destroyed.")
            except tk.TclError as e:
                logging.warning(f"Tkinter root already destroyed: {e}")

            if self.tray_thread:
                self.tray_thread.join(timeout=2.0)
                logging.info("Tray thread terminated.")

            logging.info("Application exited cleanly.")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error during exit: {e}")
            sys.exit(1)

    def run(self):
        """Start the application."""
        try:
            self.tray_thread = threading.Thread(target=self.icon.run, daemon=False)
            self.tray_thread.start()
            self.root.mainloop()
        except Exception as e:
            logging.error(f"Error running application: {e}")
            self.exit_app()


if __name__ == "__main__":
    try:
        app = PrimeSync()
        app.run()
    except Exception as e:
        logging.critical(f"Fatal error starting application: {e}")
        sys.exit(1)