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
        self.info_url = '/api/info/'
        self.root = root
        self.app = app
        self.security = security
        self.settings_repo = settings_repo
        self.schedule_repo = schedule_repo
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
        self.auth_token = None

    def _load_icon(self, window: tk.Toplevel) -> None:
        """Load and set the application icon for the window."""
        try:
            icon_path = Config().ICON_PATH
            if icon_path and icon_path.exists():
                img = Image.open(icon_path)
                photo = ImageTk.PhotoImage(img)
                window.iconphoto(True, photo)
                window._icon = photo  # Keep a reference to prevent garbage collection
                self.logger.info(f"Icon set for {window.title()}")
        except Exception as e:
            self.logger.error(f"Icon load failed: {e}")

    def show_settings(self, first_run: bool = False) -> None:
        """
        Show the settings form for cloud API and scheduler settings.
        Uses grid layout exclusively to ensure all widgets appear.

        Args:
            first_run: If True, prevents closing the window without saving settings
        """
        self.logger.info("Opening settings window")

        try:
            # Create the window and basic configuration
            settings_win = tk.Toplevel(self.root)
            settings_win.title("Settings")
            settings_win.geometry("500x550")
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
            labels = ["Cloud API URL", "Username", "Password", "Institute ID"]
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
            cloud_api_url, username, password, institute_id = entries

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
                    if settings.password:
                        decrypted_password = self.security.decrypt(settings.password)
                        password.delete(0, tk.END)
                        password.insert(0, decrypted_password)
                except Exception as e:
                    self.logger.error(f"Failed to decrypt password: {e}")
                    password.delete(0, tk.END)
                    # Leave password field empty if decryption fails

                institute_id.delete(0, tk.END)
                institute_id.insert(0, settings.institute_id or "")

                # Store existing auth token if available
                if hasattr(settings, 'auth_token') and settings.auth_token:
                    self.auth_token = settings.auth_token

                # Update status label to inform about decryption issues
                if not settings.password or (settings.password and not password.get()):
                    status_label.config(
                        text="Password decryption failed. Please enter a new password.",
                        foreground="orange"
                    )

            def check_connection():
                """Check connection to the API server using provided credentials."""
                url = cloud_api_url.get().strip()
                user = username.get().strip()
                pwd = password.get().strip()
                inst_id = institute_id.get().strip()
                if not all([url, user, pwd, inst_id]):
                    status_label.config(text="Please fill all fields", foreground="red")
                    return False

                # Show checking status
                status_label.config(text="Checking connection...", foreground="blue")
                settings_win.update()

                try:
                    # Determine the token URL
                    login_url = f'{url}/api/token/'

                    # Try token-based authentication
                    token_payload = {
                        "username": user,
                        "password": pwd
                    }

                    token_response = requests.post(
                        login_url,
                        json=token_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )

                    if token_response.status_code == 200:
                        # Token auth successful
                        token_data = token_response.json()
                        token = token_data.get('token') or token_data.get('access')

                        if token:
                            # Save token to the instance for later use
                            self.auth_token = token

                            # Now try to access the API with the token to verify
                            headers = {"Authorization": f"Token {token}"}

                            # Use institute_id as a parameter
                            info_url = f'{url}{self.info_url}?institute={inst_id}'

                            info_response = requests.get(
                                info_url,
                                headers=headers,
                                timeout=5
                            )

                            if info_response.status_code == 200:
                                # Successfully connected with token
                                info_data = info_response.json()
                                status_label.config(
                                    text=f"Connected to {info_data.get('name', 'Django API')} v{info_data.get('version', '1.0')}",
                                    foreground="green"
                                )
                                self.logger.info(f"Connected to Django API: {info_data}")
                                return True
                        else:
                            status_label.config(text="Authentication failed: No token received", foreground="red")
                            return False
                    else:
                        # Authentication failed
                        status_label.config(
                            text=f"Authentication failed: {token_response.status_code}",
                            foreground="red"
                        )
                        self.logger.warning(f"Authentication failed: {token_response.status_code}")
                        return False

                except requests.exceptions.ConnectionError:
                    status_label.config(text="Connection error: Could not connect to server", foreground="red")
                    self.logger.error("Connection error: Failed to connect to server")
                except requests.exceptions.Timeout:
                    status_label.config(text="Connection timed out", foreground="red")
                    self.logger.error("Connection error: Request timed out")
                except Exception as e:
                    status_label.config(text=f"Error: {str(e)}", foreground="red")
                    self.logger.error(f"Connection test error: {e}")

                return False

            def save_settings():
                """Save settings to the database and update related services."""
                try:
                    # Prepare data for saving
                    data = {
                        'cloud_api_url': cloud_api_url.get().strip(),
                        'username': username.get().strip(),
                        'password': self.security.encrypt(password.get().strip()),
                        'institute_id': institute_id.get().strip(),
                    }
                    # Add auth_token to data if it exists
                    if self.auth_token:
                        data['auth_token'] = self.auth_token

                    # Save settings to the database
                    self.settings_repo.save_settings(data)

                    # Update API client with new settings
                    self.app.api_client.update_settings()

                    # Use status label instead of notification for confirmation
                    status_label.config(text="Settings saved successfully", foreground="green")
                    self.logger.info("Settings saved successfully")

                    # If it's the first run, show the dashboard
                    if first_run:
                        self.app.dashboard_gui.show_dashboard()

                    # Close the settings window
                    settings_win.destroy()
                except Exception as e:
                    status_label.config(text=f"Save error: {e}", foreground="red")
                    self.logger.error(f"Save failed: {e}")

            # Add help text for Django API
            help_frame = ttk.LabelFrame(frame, text="Django API Connection Help")
            help_frame.grid(
                row=len(labels) + 2,
                column=0,
                columnspan=2,
                sticky='ew',
                pady=(15, 5),
                padx=5
            )

            help_text = (
                "For Django REST API, use these URL formats:\n"
                "• Token auth: http://your-django-site.com/api/token/\n"
                "• API base: http://your-django-site.com/api/\n"
                "Username and password should match your Django login.\n"
                "Institute ID is your organization identifier in the system."
            )

            help_label = ttk.Label(
                help_frame,
                text=help_text,
                font=("Helvetica", 9),
                foreground="gray"
            )
            help_label.pack(padx=10, pady=10, fill="both")

            # Button layout
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
                """Reset all form fields."""
                try:
                    cloud_api_url.delete(0, tk.END)
                    username.delete(0, tk.END)
                    password.delete(0, tk.END)
                    institute_id.delete(0, tk.END)
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

            # Add buttons
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

            # Force update to ensure buttons are visible
            button_frame.update()

            # Prevent window close on first run
            if first_run:
                settings_win.protocol(
                    "WM_DELETE_WINDOW",
                    lambda: self.app.exit_app()
                )

            # Force update of all widgets
            settings_win.update_idletasks()
        except Exception as e:
            self.logger.error(f"Failed to show settings window: {e}")