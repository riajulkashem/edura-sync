# interfaces/gui/settings.py
import logging
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from core.security import SecurityManager
from core.config import Config
from interfaces.database.repository import SettingsRepository, ScheduleRepository
from services.notification import NotificationService


class SettingsGUI:
    """
    Manages the settings GUI for the PrimeSync application.
    Allows configuration of cloud API settings and schedules.
    """


    def __init__(
        self,
        root: tk.Tk,
        app: "PrimeSync",
        security: SecurityManager,
        settings_repo: SettingsRepository,
        schedule_repo: ScheduleRepository,
        notification_service: NotificationService,
    ):
        """
        Initialize the settings GUI with dependencies.
        Args:
            root: The root Tkinter window.
            app: Reference to the main PrimeSync application.
            security: SecurityManager for encryption/decryption.
            settings_repo: Repository for settings data.
            schedule_repo: Repository for schedule data.
            notification_service: Service for sending notifications.
        """
        self.root = root
        self.app = app
        self.security = security
        self.settings_repo = settings_repo
        self.schedule_repo = schedule_repo
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)

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
                window._icon = icon_photo  # Prevent garbage collection
                self.logger.info(f"Set icon for window: {window.title()}")
            else:
                self.logger.warning(f"Icon file not available at {icon_path}")
        except Exception as e:
            self.logger.error(f"Failed to set icon for window {window.title()}: {e}")

    def show_settings(self, first_run: bool = False) -> None:
        """
        Show the settings form for configuring cloud API and schedules.
        Args:
            first_run: Whether this is the first run, preventing window closure.
        """
        self.logger.info("Opening settings window")
        try:
            settings_win = tk.Toplevel(self.root)
            settings_win.title("Settings")
            settings_win.geometry("500x400")
            settings_win.resizable(False, False)
            self._load_icon(settings_win)

            # Configure style
            style = ttk.Style()
            style.configure("TLabel", padding=5, font=("Helvetica", 10))
            style.configure("TEntry", padding=5)
            style.configure("TButton", padding=5)

            # Create main frame
            frame = ttk.Frame(settings_win, padding=10)
            frame.pack(fill="both", expand=True)

            # Cloud API URL
            ttk.Label(frame, text="Cloud API URL").pack()
            cloud_api_url = ttk.Entry(frame, width=50)
            cloud_api_url.pack(pady=5)
            cloud_api_url.insert(0, "https://api.example.com")

            # Username
            ttk.Label(frame, text="Username").pack()
            username = ttk.Entry(frame, width=50)
            username.pack(pady=5)

            # Password
            ttk.Label(frame, text="Password").pack()
            password = ttk.Entry(frame, width=50, show="*")
            password.pack(pady=5)

            # Client Key
            ttk.Label(frame, text="Client Key").pack()
            client_key = ttk.Entry(frame, width=50)
            client_key.pack(pady=5)

            # Load existing settings
            settings = self.settings_repo.get_settings()
            if settings:
                cloud_api_url.delete(0, tk.END)
                cloud_api_url.insert(0, settings.cloud_api_url)
                username.delete(0, tk.END)
                username.insert(0, settings.username)
                password.delete(0, tk.END)
                password.insert(0, self.security.decrypt(settings.password))
                client_key.delete(0, tk.END)
                client_key.insert(0, settings.client_key)

            def save_settings():
                """Save settings and initialize schedules if needed."""
                try:
                    settings_data = {
                        "cloud_api_url": cloud_api_url.get(),
                        "username": username.get(),
                        "password": self.security.encrypt(password.get()),
                        "client_key": client_key.get(),
                    }
                    self.settings_repo.save_settings(settings_data)

                    # Initialize default schedules if none exist
                    if not self.schedule_repo.get_all():
                        self.schedule_repo.model.create(
                            task_type="pull",
                            schedule_time="00:00",
                            enabled=True,
                            last_run=None,
                        )
                        self.schedule_repo.model.create(
                            task_type="push",
                            schedule_time="00:30",
                            enabled=True,
                            last_run=None,
                        )

                    # Update services
                    self.app.api_client.update_settings()
                    self.app.scheduler.update_settings()

                    self.notification_service.notify(
                        "Success", "Settings saved successfully", "info"
                    )
                    self.logger.info("Settings saved successfully")
                    if first_run:
                        self.app.dashboard_gui.show_dashboard()
                    settings_win.destroy()
                except Exception as e:
                    self.logger.error(f"Failed to save settings: {e}")
                    self.notification_service.notify(
                        "Error", f"Failed to save settings: {str(e)}", "error"
                    )

            # Add save button
            ttk.Button(frame, text="Save", command=save_settings).pack(pady=20)

            # Prevent closing during first run
            if first_run:
                settings_win.protocol("WM_DELETE_WINDOW", lambda: self.app.exit_app())

        except Exception as e:
            self.logger.error(f"Error displaying settings window: {e}")
            self.notification_service.notify(
                "Error", f"Failed to display settings: {str(e)}", "error"
            )
