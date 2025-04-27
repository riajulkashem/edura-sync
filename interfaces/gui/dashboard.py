# interfaces/gui/dashboard.py
import logging
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from typing import Optional
from datetime import datetime
from core.config import Config
from interfaces.database.repository import DeviceRepository, UserRepository
from services.notification import NotificationService


class DashboardGUI:
    """
    Manages the dashboard GUI for the PrimeSync application.
    Displays device status, user counts, and sync information.
    """

    def __init__(
        self,
        root: tk.Tk,
        app: "PrimeSync",
        device_repo: DeviceRepository,
        user_repo: UserRepository,
        notification_service: NotificationService,
    ):
        """
        Initialize the dashboard GUI with dependencies.
        Args:
            root: The root Tkinter window.
            app: Reference to the main PrimeSync application.
            device_repo: Repository for device data.
            user_repo: Repository for user data.
            notification_service: Service for sending notifications.
        """
        self.root = root
        self.app = app
        self.device_repo = device_repo
        self.user_repo = user_repo
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
        self.dashboard_win: Optional[tk.Toplevel] = None
        self.last_synced_time: Optional[datetime] = None

    def _load_icon(self, window: tk.Toplevel) -> None:
        """
        Load and set the application icon for a Tkinter window.
        Args:
            window: The Tkinter window to set the icon for.
        """
        try:
            config = Config()
            icon_path = config.ICON_PATH
            if icon_path and icon_path.exists() and icon_path.is_file():
                icon_image = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_image)
                window.iconphoto(True, icon_photo)
                # Store reference to prevent garbage collection
                window._icon = icon_photo
                self.logger.info(f"Set icon for window: {window.title()}")
            else:
                self.logger.warning(f"Icon file not available at {icon_path}")
        except Exception as e:
            self.logger.error(f"Failed to set icon for window {window.title()}: {e}")

    def show_dashboard(self) -> None:
        """Show or update the main dashboard window."""
        self.logger.info("Opening or updating dashboard window")
        try:
            # Close existing dashboard if open
            if self.dashboard_win and self.dashboard_win.winfo_exists():
                self.dashboard_win.destroy()

            # Create new dashboard window
            self.dashboard_win = tk.Toplevel(self.root)
            self.dashboard_win.title("PrimeSync Dashboard")
            self.dashboard_win.geometry("400x300")
            self.dashboard_win.resizable(False, False)
            self._load_icon(self.dashboard_win)
            self.dashboard_win.protocol("WM_DELETE_WINDOW", self.dashboard_win.destroy)

            # Configure style
            style = ttk.Style()
            style.configure("TLabel", padding=5, font=("Helvetica", 12))

            # Create main frame
            frame = ttk.Frame(self.dashboard_win, padding=10)
            frame.pack(fill="both", expand=True)

            # Fetch data
            connected = self.device_repo.count_online()
            total_devices = self.device_repo.count_total()
            total_users = self.user_repo.count_total()
            last_synced = (
                self.last_synced_time.strftime("%Y-%m-%d %H:%M:%S")
                if self.last_synced_time
                else "Never"
            )
            db_path = str(Config().DB_PATH)

            # Display data
            ttk.Label(frame, text=f"Total Devices: {total_devices}").pack(pady=5)
            ttk.Label(
                frame,
                text=f"Connected: {connected} / Not Connected: {total_devices - connected}",
            ).pack(pady=5)
            ttk.Label(frame, text=f"Total Users: {total_users}").pack(pady=5)
            ttk.Label(frame, text=f"Last Synced: {last_synced}").pack(pady=5)
            ttk.Label(frame, text=f"Database Path: {db_path}").pack(pady=5)

            # Add refresh button
            ttk.Button(frame, text="Refresh", command=self.show_dashboard).pack(pady=10)

            self.logger.info("Dashboard displayed successfully")
            self.notification_service.notify(
                "Dashboard", "Dashboard refreshed successfully", "info"
            )
        except Exception as e:
            self.logger.error(f"Error displaying dashboard: {e}")
            self.notification_service.notify(
                "Error", f"Failed to load dashboard: {str(e)}", "error"
            )

    def update_last_synced(self, synced_time: datetime) -> None:
        """
        Update the last synced time for display.
        Args:
            synced_time: The timestamp of the last sync.
        """
        self.last_synced_time = synced_time
        self.logger.debug(f"Updated last synced time to {synced_time}")
