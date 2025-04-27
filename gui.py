import logging
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from models import Device, User, Settings, Schedule, db
from security import SecurityManager


class PrimeSyncGUI:
    """Manages GUI components for the PrimeSync application."""

    def __init__(self, root: tk.Tk, app):
        self.root = root
        self.app = app
        self.logger = logging.getLogger(__name__)
        self.security = SecurityManager()
        self.last_synced_time = None
        self.dashboard_win = None

    def show_dashboard(self):
        """Show or update the main dashboard."""
        if self.dashboard_win and self.dashboard_win.winfo_exists():
            for widget in self.dashboard_win.winfo_children():
                widget.destroy()
        else:
            self.dashboard_win = tk.Toplevel(self.root)
            self.dashboard_win.title("PrimeSync Dashboard")
            self.dashboard_win.geometry("400x300")
            self.dashboard_win.resizable(False, False)
            self.dashboard_win.protocol("WM_DELETE_WINDOW", self.dashboard_win.destroy)

        style = ttk.Style()
        style.configure("TLabel", padding=5, font=("Helvetica", 12))

        frame = ttk.Frame(self.dashboard_win, padding=10)
        frame.pack(fill="both", expand=True)

        try:
            connected = Device.select().where(Device.status == "Online").count()
            total_devices = Device.select().count()
            total_users = User.select().count()
            last_synced = (self.last_synced_time.strftime("%Y-%m-%d %H:%M:%S")
                           if self.last_synced_time else "Never")

            ttk.Label(frame, text=f"Total Devices: {total_devices}").pack(pady=5)
            ttk.Label(frame, text=f"Connected: {connected} / Not Connected: {total_devices - connected}").pack(pady=5)
            ttk.Label(frame, text=f"Total Users: {total_users}").pack(pady=5)
            ttk.Label(frame, text=f"Last Synced: {last_synced}").pack(pady=5)

            ttk.Button(frame, text="Refresh", command=self.show_dashboard).pack(pady=10)
            self.logger.info("Dashboard displayed/updated.")
            self.show_notification("Dashboard", "Dashboard refreshed successfully", "info")
        except Exception as e:
            self.logger.error(f"Error displaying dashboard: {e}")
            self.show_notification("Error", "Failed to load dashboard", "error")

    def show_settings(self, first_run: bool = False):
        """Show the settings form."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("500x400")
        settings_win.resizable(False, False)

        style = ttk.Style()
        style.configure("TLabel", padding=5, font=("Helvetica", 10))
        style.configure("TEntry", padding=5)
        style.configure("TButton", padding=5)

        frame = ttk.Frame(settings_win, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Cloud API URL").pack()
        cloud_api_url = ttk.Entry(frame, width=50)
        cloud_api_url.pack(pady=5)
        cloud_api_url.insert(0, "https://api.example.com")

        ttk.Label(frame, text="Username").pack()
        username = ttk.Entry(frame, width=50)
        username.pack(pady=5)

        ttk.Label(frame, text="Password").pack()
        password = ttk.Entry(frame, width=50, show="*")
        password.pack(pady=5)

        ttk.Label(frame, text="Client Key").pack()
        client_key = ttk.Entry(frame, width=50)
        client_key.pack(pady=5)

        if Settings.select().exists():
            settings = Settings.get()
            cloud_api_url.delete(0, tk.END)
            cloud_api_url.insert(0, settings.cloud_api_url)
            username.delete(0, tk.END)
            username.insert(0, settings.username)
            password.delete(0, tk.END)
            password.insert(0, self.security.decrypt(settings.password))
            client_key.delete(0, tk.END)
            client_key.insert(0, settings.client_key)

        def save_settings():
            try:
                settings_data = {
                    "cloud_api_url": cloud_api_url.get(),
                    "username": username.get(),
                    "password": self.security.encrypt(password.get()),
                    "client_key": client_key.get()
                }
                with db.atomic():
                    if Settings.select().exists():
                        Settings.delete().execute()
                    Settings.create(**settings_data)

                if not Schedule.select().exists():
                    Schedule.create(
                        task_type="pull",
                        schedule_time="00:00",
                        enabled=True,
                        last_run=None
                    )
                    Schedule.create(
                        task_type="push",
                        schedule_time="00:30",
                        enabled=True,
                        last_run=None
                    )

                self.app.scheduler.update_settings()
                self.app.api_client.update_settings(Settings.get())
                self.show_notification("Success", "Settings saved successfully", "info")
                self.logger.info("Settings saved.")
                if first_run:
                    self.show_dashboard()
                settings_win.destroy()
            except Exception as e:
                self.logger.error(f"Failed to save settings: {e}")
                self.show_notification("Error", f"Failed to save settings: {str(e)}", "error")

        ttk.Button(frame, text="Save", command=save_settings).pack(pady=20)
        if first_run:
            settings_win.protocol("WM_DELETE_WINDOW", lambda: self.app.exit_app())

    def show_notification(self, title: str, message: str, type: str):
        """Show system notification with custom style."""
        try:
            from plyer import notification
            icon = str(self.app.config.ICON_PATH) if type == "info" else None
            notification.notify(
                title=title,
                message=message,
                app_name="PrimeSync Manager",
                app_icon=icon,
                timeout=5
            )
            self.logger.info(f"Notification shown: {title} - {message}")
        except Exception as e:
            self.logger.error(f"Failed to show notification: {e}")
            with open(self.app.config.LOG_FILE, 'a') as f:
                f.write(f"{datetime.now()} [NOTIFICATION] {title}: {message}\n")