import logging
import tkinter as tk
from tkinter import ttk
import requests
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
        self.root = root
        self.app = app
        self.security = security
        self.settings_repo = settings_repo
        self.schedule_repo = schedule_repo
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)

    def _load_icon(self, window: tk.Toplevel) -> None:
        try:
            icon_path = Config().ICON_PATH
            if icon_path and icon_path.exists():
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                window.iconphoto(True, photo)
                window._icon = photo
                self.logger.info(f"Icon set for {window.title()}")
        except Exception as e:
            self.logger.error(f"Icon load failed: {e}")

    def show_settings(self, first_run: bool = False) -> None:
        """
        Show the settings form for cloud API and scheduler settings.
        Uses grid layout exclusively to ensure all widgets appear.
        """
        self.logger.info("Opening settings window")

        try:
            # Create the window and basic configuration
            settings_win = tk.Toplevel(self.root)
            settings_win.title("Settings")
            settings_win.geometry("500x450")
            settings_win.resizable(False, False)

            # Bring window to front and ensure it's visible
            settings_win.attributes('-topmost', True)
            settings_win.update()
            settings_win.attributes('-topmost', False)

            # Load the icon
            self._load_icon(settings_win)

            # Configure styles
            style = ttk.Style()
            style.configure("TLabel", padding=5, font=("Helvetica", 10))
            style.configure("TEntry", padding=5)
            style.configure("TButton", padding=5)

            # Main frame
            frame = ttk.Frame(settings_win, padding=10)
            frame.grid(row=0, column=0, sticky='nsew')
            settings_win.grid_columnconfigure(0, weight=1)
            settings_win.grid_rowconfigure(0, weight=1)
            frame.grid_columnconfigure(0, weight=0)
            frame.grid_columnconfigure(1, weight=1)

            # Input fields
            labels = ["Cloud API URL", "Username", "Password", "Client Key"]
            entries = []
            for idx, text in enumerate(labels):
                ttk.Label(frame, text=text).grid(
                    row=idx,
                    column=0,
                    sticky='w',
                    pady=5,
                    padx=5
                )
                show = '*' if text == 'Password' else None
                ent = ttk.Entry(frame, width=50, show=show)
                ent.grid(
                    row=idx,
                    column=1,
                    sticky='we',
                    pady=5,
                    padx=5
                )
                entries.append(ent)
            cloud_api_url, username, password, client_key = entries

            # Status label
            status_label = ttk.Label(
                frame,
                text="Here is the status of your connection...",
                foreground="gray",
                font=("Helvetica", 10)
            )
            status_label.grid(
                row=len(labels),
                column=0,
                columnspan=2,
                pady=10
            )

            # Pre-fill existing settings
            settings = self.settings_repo.get_settings()
            if settings:
                cloud_api_url.delete(0, tk.END)
                cloud_api_url.insert(0, settings.cloud_api_url or "")
                
                username.delete(0, tk.END)
                username.insert(0, settings.username or "")
                
                # Handle possible decryption failures
                try:
                    decrypted_password = self.security.decrypt(settings.password)
                    password.delete(0, tk.END)
                    password.insert(0, decrypted_password)
                except Exception as e:
                    self.logger.error(f"Failed to decrypt password: {e}")
                    password.delete(0, tk.END)
                    # Leave password field empty if decryption fails
                
                client_key.delete(0, tk.END)
                client_key.insert(0, settings.client_key or "")
                
                # Update status label to inform about decryption issues
                if not settings.password or not self.security.decrypt(settings.password):
                    status_label.config(
                        text="Password decryption failed. Please enter a new password.",
                        foreground="orange"
                    )

            def check_connection():
                url = cloud_api_url.get().strip()
                user = username.get().strip()
                pwd = password.get().strip()
                key = client_key.get().strip()
                if not all([url, user, pwd, key]):
                    status_label.config(text="Please fill all fields", foreground="red")
                    return
                try:
                    resp = requests.get(url, auth=(user, pwd), timeout=5)
                    if resp.ok:
                        status_label.config(text="Connection successful", foreground="green")
                        # Use logging instead of notification which might cause issues
                        self.logger.info("Connection test successful")
                    else:
                        status_label.config(
                            text=f"Connection failed: {resp.status_code}",
                            foreground="red"
                        )
                        self.logger.warning(f"Connection test failed: {resp.status_code}")
                except Exception as e:
                    status_label.config(text=f"Error: {e}", foreground="red")
                    self.logger.error(f"Connection test error: {e}")

            def save_settings():
                try:
                    data = {
                        'cloud_api_url': cloud_api_url.get().strip(),
                        'username': username.get().strip(),
                        'password': self.security.encrypt(password.get().strip()),
                        'client_key': client_key.get().strip(),
                    }
                    self.settings_repo.save_settings(data)
                    if not self.schedule_repo.get_all():
                        self.schedule_repo.model.create(
                            task_type='pull', schedule_time='00:00', enabled=True
                        )
                        self.schedule_repo.model.create(
                            task_type='push', schedule_time='00:30', enabled=True
                        )
                    self.app.api_client.update_settings()
                    self.app.scheduler.update_settings()
                    # Use status label instead of notification for confirmation
                    status_label.config(text="Settings saved successfully", foreground="green")
                    self.logger.info("Settings saved successfully")

                    if first_run:
                        self.app.dashboard_gui.show_dashboard()
                    settings_win.destroy()
                except Exception as e:
                    status_label.config(text=f"Save error: {e}", foreground="red")
                    self.logger.error(f"Save failed: {e}")

            # In settings.py, add a reset button

            # Buttons layout
            button_frame = ttk.Frame(frame)
            button_frame.grid(
                row=len(labels) + 1,
                column=0,
                columnspan=2,
                sticky='ew',
                pady=15
            )

            button_frame.grid_columnconfigure(0, weight=1)
            button_frame.grid_columnconfigure(1, weight=1)
            button_frame.grid_columnconfigure(2, weight=1)

            # Reset button function
            def reset_settings():
                try:
                    cloud_api_url.delete(0, tk.END)
                    username.delete(0, tk.END)
                    password.delete(0, tk.END)
                    client_key.delete(0, tk.END)
                    status_label.config(
                        text="Settings reset. Enter new values and save.",
                        foreground="blue"
                    )
                    self.logger.info("Settings form reset")
                except Exception as e:
                    self.logger.error(f"Failed to reset settings form: {e}")
                    status_label.config(
                        text=f"Error: {str(e)}",
                        foreground="red"
                    )

            # Add the buttons
            reset_btn = ttk.Button(
                button_frame,
                text="Reset",
                command=reset_settings,
                padding=8
            )
            reset_btn.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

            check_btn = ttk.Button(
                button_frame,
                text="Check Connection",
                command=check_connection,
                padding=8
            )
            check_btn.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

            save_btn = ttk.Button(
                button_frame,
                text="Save Settings",
                command=save_settings,
                padding=8
            )
            save_btn.grid(row=0, column=2, padx=5, pady=5, sticky='ew')

            button_frame.update()

            # Prevent window close on first run
            if first_run:
                settings_win.protocol(
                    "WM_DELETE_WINDOW",
                    lambda: self.app.exit_app()
                )

            # Force update
            settings_win.update_idletasks()

        except Exception as e:
            self.logger.error(f"Failed to open settings window: {e}")
            # Try to show a simple message if the main window fails
            try:
                import tkinter.messagebox as messagebox
                messagebox.showerror("Error", f"Failed to open settings: {e}")
            except Exception as msg_err:
                self.logger.error(f"Also failed to show error message: {msg_err}")