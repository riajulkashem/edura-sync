# interfaces/gui/dashboard.py
import logging
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import ttk

from core.config import Config
from core.constants import UI_CONFIG, APP_NAME
from interfaces.gui.ui_utils import (
    create_window,
    setup_styles,
    create_notebook,
    create_tab,
    load_icon,
    create_button,
)


class DashboardGUI:
    """GUI dashboard for the PrimeSync application."""

    def __init__(
        self,
        root,
        app,
        device_repo,
        user_repo,
        notification_service,
        settings_repo=None,
        api_client=None,
        security=None,
    ):
        """Initialize the dashboard GUI with required components."""
        self.logger = logging.getLogger(__name__)
        self.root = root
        self.app = app
        self.device_repo = device_repo
        self.user_repo = user_repo
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.api_client = api_client
        self.security = security
        self.device_manager = None

        # UI components initialized to None
        self.dashboard_win = None
        self.dashboard_content = None
        self.status_label = None

        # Form fields
        self.cloud_api_url = None
        self.username = None
        self.password = None
        self.institute_id = None
        self.process_time = None
        self.is_scheduler_enabled = None

    def show_dashboard(self, first_run=False):
        """Show or update the main dashboard window."""
        self.logger.info("Opening or updating dashboard window")
        try:
            # Close existing dashboard if open
            if self.dashboard_win and self.dashboard_win.winfo_exists():
                self.dashboard_win.destroy()

            # Create new dashboard window
            self.dashboard_win = create_window(
                self.root, f"{APP_NAME} Dashboard", UI_CONFIG["DASHBOARD_SIZE"]
            )
            load_icon(self.dashboard_win, Config().ICON_PATH)

            # Hide instead of destroy on close
            self.dashboard_win.protocol("WM_DELETE_WINDOW", self.dashboard_win.withdraw)

            # Configure style and create notebook
            setup_styles()
            notebook = create_notebook(self.dashboard_win)

            # Create tabs
            dashboard_frame = create_tab(notebook, "Dashboard")
            settings_frame = create_tab(notebook, "Settings")
            credits_frame = create_tab(notebook, "Credits")

            # Initialize tab contents
            self._create_dashboard_tab(dashboard_frame)
            self._create_settings_tab(settings_frame)
            self._create_credits_tab(credits_frame)

            # Select settings tab on first run
            if first_run:
                notebook.select(1)

            # Add Quit button
            quit_btn = create_button(
                self.dashboard_win, "Quit", self.dashboard_win.withdraw
            )
            quit_btn.pack(pady=(0, 10))

            self.logger.info("Dashboard displayed successfully")
        except Exception as e:
            self.logger.error(f"Error displaying dashboard: {e}")

    def _create_dashboard_tab(self, frame):
        """Create the dashboard tab with content."""
        try:
            frame.columnconfigure(0, weight=1)

            # Create frame for content without scrollbar
            self.dashboard_content = ttk.Frame(frame)
            self.dashboard_content.grid(row=0, column=0, sticky="nsew")
            frame.rowconfigure(0, weight=1)

            # Initial content update
            self._update_dashboard_content()
            self.logger.info("Dashboard tab created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create dashboard tab: {e}")

    def _create_settings_tab(self, frame):
        """Create the settings tab with configuration options."""
        try:
            # Layout configuration
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=3)

            # Check dependencies
            if not self.settings_repo:
                ttk.Label(
                    frame,
                    text="Error: Settings repository not available",
                    foreground="red",
                ).grid(row=0, column=0, columnspan=2, pady=20)
                self.logger.error("settings_repo not available for settings tab")
                return

            # Load current settings
            try:
                settings = self.settings_repo.get_settings()
            except Exception as e:
                settings = None
                ttk.Label(
                    frame, text=f"Error loading settings: {str(e)}", foreground="red"
                ).grid(row=0, column=0, columnspan=2, pady=20)
                self.logger.error(f"Error loading settings: {e}")

            # Status label
            self.status_label = ttk.Label(frame, text="", foreground="black")
            self.status_label.grid(
                row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5
            )

            # API Settings section
            self._create_api_settings_section(frame, settings, row_start=1)

            # Time Settings section
            self._create_time_settings_section(frame, settings, row_start=7)

            # Save button
            if self.security:
                save_button = ttk.Button(
                    frame, text="Save Settings", command=self._save_settings
                )
                save_button.grid(row=10, column=0, columnspan=2, pady=20)
            else:
                ttk.Label(
                    frame,
                    text="Save functionality not available - missing security component",
                    foreground="red",
                ).grid(row=10, column=0, columnspan=2, pady=20)
                self.logger.error("security manager not available for settings tab")

            self.logger.info("Settings tab created successfully")

        except Exception as e:
            self.logger.error(f"Error creating settings tab: {e}")
            ttk.Label(
                frame,
                text=f"Error creating settings interface: {str(e)}",
                foreground="red",
            ).grid(row=0, column=0, columnspan=2, pady=20)

    def _create_api_settings_section(self, parent, settings, row_start):
        """Create API settings form fields section."""
        # Section header
        ttk.Label(parent, text="API Settings", font=("TkDefaultFont", 12, "bold")).grid(
            row=row_start, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5)
        )

        # Cloud API URL
        ttk.Label(parent, text="Cloud API URL:").grid(
            row=row_start + 1, column=0, sticky="w", padx=10, pady=5
        )
        self.cloud_api_url = ttk.Entry(parent, width=40)
        self.cloud_api_url.grid(
            row=row_start + 1, column=1, sticky="ew", padx=10, pady=5
        )
        if settings and hasattr(settings, "cloud_api_url"):
            self.cloud_api_url.insert(0, settings.cloud_api_url)

        # Username
        ttk.Label(parent, text="Username:").grid(
            row=row_start + 2, column=0, sticky="w", padx=10, pady=5
        )
        self.username = ttk.Entry(parent, width=40)
        self.username.grid(row=row_start + 2, column=1, sticky="ew", padx=10, pady=5)
        if settings and hasattr(settings, "username"):
            self.username.insert(0, settings.username)

        # Password
        ttk.Label(parent, text="Password:").grid(
            row=row_start + 3, column=0, sticky="w", padx=10, pady=5
        )
        self.password = ttk.Entry(parent, width=40, show="*")
        self.password.grid(row=row_start + 3, column=1, sticky="ew", padx=10, pady=5)
        if settings and hasattr(settings, "password") and self.security:
            self.password.insert(0, self.security.decrypt(settings.password))

        # Institute ID
        ttk.Label(parent, text="Institute ID:").grid(
            row=row_start + 4, column=0, sticky="w", padx=10, pady=5
        )
        self.institute_id = ttk.Entry(parent, width=40)
        self.institute_id.grid(
            row=row_start + 4, column=1, sticky="ew", padx=10, pady=5
        )
        if settings and hasattr(settings, "institute_id"):
            self.institute_id.insert(0, settings.institute_id)

        # Check Connection button
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row_start + 5, column=0, columnspan=2, pady=10)
        check_connection_btn = ttk.Button(
            button_frame, text="Check Connection", command=self._check_api_connection
        )
        check_connection_btn.pack(side="left", padx=5)

    def _create_time_settings_section(self, parent, settings, row_start):
        """Create scheduler settings form fields section."""
        # Section header
        ttk.Label(
            parent, text="Scheduler Settings", font=("TkDefaultFont", 12, "bold")
        ).grid(row=row_start, column=0, columnspan=2, sticky="w", padx=10, pady=(20, 5))

        # Process Time
        ttk.Label(parent, text="Process Time:").grid(
            row=row_start + 1, column=0, sticky="w", padx=10, pady=5
        )
        self.process_time = ttk.Entry(parent, width=10)
        self.process_time.grid(row=row_start + 1, column=1, sticky="w", padx=10, pady=5)
        ttk.Label(parent, text="Format: HH:MM (24-hour)").grid(
            row=row_start + 1, column=1, sticky="e", padx=10, pady=5
        )

        default_process_time = "15:00"
        if settings and hasattr(settings, "process_time") and settings.process_time:
            self.process_time.insert(0, settings.process_time.strftime("%H:%M"))
        else:
            self.process_time.insert(0, default_process_time)

        # Enable/Disable Scheduler
        ttk.Label(parent, text="Enable Scheduler:").grid(
            row=row_start + 2, column=0, sticky="w", padx=10, pady=5
        )

        # Create a variable to hold the checkbox state
        self.is_scheduler_enabled = tk.BooleanVar()
        scheduler_checkbox = ttk.Checkbutton(
            parent, variable=self.is_scheduler_enabled, onvalue=True, offvalue=False
        )
        scheduler_checkbox.grid(
            row=row_start + 2, column=1, sticky="w", padx=10, pady=5
        )

        # Set default value from settings
        if settings and hasattr(settings, "is_scheduler_enabled"):
            self.is_scheduler_enabled.set(settings.is_scheduler_enabled)
        else:
            self.is_scheduler_enabled.set(False)

    def _create_credits_tab(self, frame):
        """Create the credits tab with about information."""
        try:
            frame.columnconfigure(0, weight=1)

            # App name and version
            ttk.Label(
                frame, text=f"{APP_NAME}", font=("TkDefaultFont", 16, "bold")
            ).pack(pady=(20, 5))

            # Version
            try:
                from core.version import version

                version_text = f"Version {version}"
            except ImportError:
                version_text = "Version 1.0"
            ttk.Label(frame, text=version_text).pack(pady=(0, 20))

            # Description
            ttk.Label(
                frame,
                text="A system tray application for managing ZKTeco devices,\n"
                + "pulling attendance data, and syncing with a cloud API.",
                justify="center",
            ).pack(pady=10)

            # Developer info
            ttk.Label(
                frame,
                text="Developed by Riajul Kashem",
                font=("TkDefaultFont", 10, "bold"),
            ).pack(pady=(20, 0))
            ttk.Label(frame, text="Copyright © 2025").pack(pady=(0, 5))

            # Website with hyperlink
            website_frame = ttk.Frame(frame)
            website_frame.pack(pady=10)
            ttk.Label(website_frame, text="Website: ").grid(row=0, column=0)
            website_label = ttk.Label(
                website_frame,
                text="https://github.com/riajulkashem",
                foreground="blue",
                cursor="hand2",
            )
            website_label.grid(row=0, column=1)
            website_label.bind(
                "<Button-1>",
                lambda e: webbrowser.open_new("https://github.com/riajulkashem"),
            )

            self.logger.info("Credits tab created successfully")
        except Exception as e:
            self.logger.error(f"Error creating credits tab: {e}")

    def _update_dashboard_content(self):
        """Update dashboard content with current data."""
        try:
            # Clear existing content
            for widget in self.dashboard_content.winfo_children():
                widget.destroy()

            # Check dependencies
            if not self.device_repo:
                ttk.Label(
                    self.dashboard_content,
                    text="Error: Device repository not available",
                    foreground="red",
                ).pack(pady=20)
                self.logger.error("device_repo not available for dashboard update")
                return

            # Get device data
            devices = self.device_repo.get_all()

            # Build status overview section
            self._build_status_section(devices)

            # Build device status section
            self._build_devices_section(devices)

            # Build actions section
            self._build_actions_section()

            self.logger.info("Dashboard content updated successfully")
        except Exception as e:
            self.logger.error(f"Failed to update dashboard content: {e}")

    def _build_status_section(self, devices):
        """Build the status overview section."""
        # Section header
        ttk.Label(
            self.dashboard_content,
            text="Status Overview",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Create status frame
        status_frame = ttk.Frame(self.dashboard_content)
        status_frame.pack(fill="x", padx=10, pady=5)

        # Get settings if available
        if self.settings_repo:
            try:
                settings = self.settings_repo.get_settings()

                # Last Sync Time
                ttk.Label(status_frame, text="Last Synced:").grid(
                    row=0, column=0, sticky="w", padx=5, pady=2
                )
                last_sync_text = "Never"
                if settings and hasattr(settings, "last_sync") and settings.last_sync:
                    last_sync_text = settings.last_sync.strftime("%Y-%m-%d %H:%M:%S")
                ttk.Label(status_frame, text=last_sync_text).grid(
                    row=0, column=1, sticky="w", padx=5, pady=2
                )

                # Last Post Time
                ttk.Label(status_frame, text="Last Post Cloud:").grid(
                    row=1, column=0, sticky="w", padx=5, pady=2
                )
                last_post_text = "Never"
                if settings and hasattr(settings, "last_post") and settings.last_post:
                    last_post_text = settings.last_post.strftime("%Y-%m-%d %H:%M:%S")
                ttk.Label(status_frame, text=last_post_text).grid(
                    row=1, column=1, sticky="w", padx=5, pady=2
                )

                # Pending Attendance
                ttk.Label(status_frame, text="Pending Attendance For Post:").grid(
                    row=2, column=0, sticky="w", padx=5, pady=2
                )
                pending_count = (
                    settings.attendance_pending
                    if hasattr(settings, "attendance_pending")
                    else 0
                )
                ttk.Label(status_frame, text=str(pending_count)).grid(
                    row=2, column=1, sticky="w", padx=5, pady=2
                )

                # User count
                ttk.Label(status_frame, text="Total Users:").grid(
                    row=3, column=0, sticky="w", padx=5, pady=2
                )
                total_users = self.user_repo.count() if self.user_repo else 0
                ttk.Label(status_frame, text=str(total_users)).grid(
                    row=3, column=1, sticky="w", padx=5, pady=2
                )

                # Device count
                ttk.Label(status_frame, text="Total Devices:").grid(
                    row=4, column=0, sticky="w", padx=5, pady=2
                )
                total_devices = len(devices) if devices else 0
                online_devices = (
                    sum(1 for device in devices if device.status == "Online")
                    if devices
                    else 0
                )
                ttk.Label(
                    status_frame,
                    text=f"{online_devices} online / {total_devices} total",
                ).grid(row=4, column=1, sticky="w", padx=5, pady=2)

            except Exception as e:
                ttk.Label(
                    status_frame,
                    text=f"Error loading settings: {str(e)}",
                    foreground="red",
                ).grid(row=0, column=0, columnspan=2, padx=5, pady=2)
                self.logger.error(f"Error loading settings for dashboard: {e}")
        else:
            ttk.Label(
                status_frame,
                text="Settings information not available",
                foreground="red",
            ).grid(row=0, column=0, columnspan=2, padx=5, pady=2)

    def _build_devices_section(self, devices):
        """Build the device status section."""
        # Section header
        ttk.Label(
            self.dashboard_content,
            text="Device Status",
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(15, 5))

        if not devices:
            ttk.Label(self.dashboard_content, text="No devices configured").pack(
                anchor="w", padx=20, pady=5
            )
            return

        # Create a frame for each device
        for device in devices:
            device_frame = ttk.Frame(self.dashboard_content)
            device_frame.pack(fill="x", padx=20, pady=2)

            # Status indicator
            status_color = "green" if device.status == "Online" else "red"
            ttk.Label(device_frame, text="●", foreground=status_color).grid(
                row=0, column=0, padx=5
            )

            # Device info
            ttk.Label(
                device_frame, text=f"{device.device_model} ({device.ip_address})"
            ).grid(row=0, column=1, sticky="w")
            ttk.Label(device_frame, text=device.status).grid(row=0, column=2, padx=10)

    def _build_actions_section(self):
        """Build the actions button section."""
        # Section header
        ttk.Label(
            self.dashboard_content, text="Actions", font=("TkDefaultFont", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        button_frame = ttk.Frame(self.dashboard_content)
        button_frame.pack(fill="x", padx=10, pady=5)

        # Refresh button - always present
        refresh_button = ttk.Button(
            button_frame, text="Refresh Dashboard", command=self._refresh_dashboard
        )
        refresh_button.grid(row=0, column=0, padx=5, pady=5)
        # Cloud API buttons
        sync_button = ttk.Button(
            button_frame,
            text="Sync Data",
            command=lambda: self._perform_action(
                self.api_client.sync_data, "Syncing data"
            ),
        )
        sync_button.grid(row=0, column=1, padx=5, pady=5)

        post_cloud_button = ttk.Button(
            button_frame,
            text="Post to Cloud",
            command=lambda: self._perform_action(
                self.api_client.post_to_cloud, "Posting data to cloud"
            ),
        )
        post_cloud_button.grid(row=0, column=2, padx=5, pady=5)

        # Device management buttons
        check_devices_button = ttk.Button(
            button_frame,
            text="Check Devices",
            command=lambda: self._perform_action(
                self.device_manager.check_devices, "Checking devices"
            ),
        )
        check_devices_button.grid(row=1, column=0, padx=5, pady=5)

        pull_data_button = ttk.Button(
            button_frame,
            text="Pull Attendance",
            command=lambda: self._perform_action(
                self.device_manager.pull_data, "Pulling attendance data"
            ),
        )
        pull_data_button.grid(row=1, column=1, padx=5, pady=5)

        sync_device = ttk.Button(
            button_frame,
            text="Sync Device",
            command=lambda: self._perform_action(
                self.device_manager.migrate_user_to_device, "Syncing User To Device"
            ),
        )
        sync_device.grid(row=1, column=2, padx=5, pady=5)

    def _refresh_dashboard(self):
        """Refresh dashboard content."""
        try:
            self._update_dashboard_content()
        except Exception as e:
            self.logger.error(f"Failed to refresh dashboard: {e}")

    def set_device_manager(self, device_manager):
        """Set the device manager instance."""
        self.device_manager = device_manager

    def _perform_action(self, action_func, action_name):
        """Execute an action with proper UI feedback."""
        if not action_func:
            self.notification_service.notify(
                "Error",
                f"Cannot perform {action_name}: required component not available",
                "error",
            )
            return False

        try:
            # Update status if available
            if hasattr(self, "status_label") and self.status_label:
                self.status_label.config(
                    text=f"Performing {action_name}...", foreground="blue"
                )
                # Force UI update
                if self.dashboard_win:
                    self.dashboard_win.update()

            # Execute the action
            result = action_func()

            # Update status with result
            if hasattr(self, "status_label") and self.status_label:
                if result:
                    self.status_label.config(
                        text=f"{action_name} completed successfully", foreground="green"
                    )
                else:
                    error_msg = f"{action_name} failed"
                    if (
                        self.api_client
                        and hasattr(self.api_client, "last_error")
                        and self.api_client.last_error
                    ):
                        error_msg = f"Failed: {self.api_client.last_error}"
                    self.status_label.config(text=error_msg, foreground="red")

            # Refresh dashboard with new data
            self._refresh_dashboard()
            return result

        except Exception as e:
            self.logger.error(f"Error performing {action_name}: {e}")

            # Update status with error
            if hasattr(self, "status_label") and self.status_label:
                self.status_label.config(text=f"Error: {str(e)}", foreground="red")

            # Show notification
            self.notification_service.notify(
                "Error", f"Failed to {action_name.lower()}: {str(e)}", "error"
            )
            return False

    def _save_settings(self):
        """Save settings from form fields."""
        # Check dependencies
        if not self.settings_repo:
            self.notification_service.notify(
                "Error",
                "Cannot save settings: Settings repository not available",
                "error",
            )
            return

        if not self.security:
            self.notification_service.notify(
                "Error", "Cannot save settings: Security manager not available", "error"
            )
            return

        try:
            # Validate time format
            process_time = self.process_time.get()

            try:
                process_time_obj = datetime.strptime(process_time, "%H:%M").time()
            except ValueError:
                self.notification_service.notify(
                    "Error",
                    "Invalid time format. Please use HH:MM (24-hour format).",
                    "error",
                )
                return

            # Encrypt password if provided
            password = self.password.get()
            encrypted_password = self.security.encrypt(password) if password else None

            # Prepare settings data
            settings_data = {
                "cloud_api_url": self.cloud_api_url.get(),
                "username": self.username.get(),
                "institute_id": self.institute_id.get(),
                "process_time": process_time_obj,
                "is_scheduler_enabled": self.is_scheduler_enabled.get(),
            }

            # Only update password if provided
            if encrypted_password:
                settings_data["password"] = encrypted_password

            # Save settings
            self.settings_repo.save_settings(**settings_data)

            # Update API client
            if self.api_client:
                self.api_client.update_settings()

            # Notify success
            self.notification_service.notify(
                "Settings", "Settings saved successfully", "info"
            )

            # Refresh dashboard
            self._refresh_dashboard()

        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            self.notification_service.notify(
                "Error", f"Failed to save settings: {str(e)}", "error"
            )

    def _check_api_connection(self):
        """Check connection to the API with current form values."""
        if not self.api_client:
            self._update_status_label(
                "Cannot check connection: API client not available", "red"
            )
            return

        # Get form values
        url = self.cloud_api_url.get()
        username = self.username.get()
        password = self.password.get()
        institute_id = self.institute_id.get()

        # Validate inputs
        if not all([url, username, password, institute_id]):
            self._update_status_label("Please fill in all API fields", "red")
            return

        # Update status
        self._update_status_label("Checking connection...", "blue")

        try:
            import requests
            from core.constants import API_ENDPOINTS

            # Update UI
            if self.dashboard_win:
                self.dashboard_win.update()

            # Get token URL and attempt authentication
            login_url = f"{url}{API_ENDPOINTS['TOKEN']}"

            self._update_status_label(f"Connecting to {login_url}...", "blue")

            token_response = requests.post(
                login_url,
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if token_response.status_code == 200:
                token_data = token_response.json()
                token = token_data.get("token") or token_data.get("access")

                if token:
                    # Store token in API client
                    self.api_client.auth_token = token

                    # Try API access with token
                    self._update_status_label(
                        "Authenticated successfully. Checking API access...", "blue"
                    )
                    if self.dashboard_win:
                        self.dashboard_win.update()

                    info_url = f"{url}{API_ENDPOINTS['INFO']}?institute={institute_id}"
                    info_response = requests.get(
                        info_url, headers={"Authorization": f"Token {token}"}, timeout=5
                    )

                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        self._update_status_label(
                            f"Connected to {info_data.get('name', 'Django API')} v{info_data.get('version', '1.0')}",
                            "green",
                        )
                        return True
                    else:
                        self._update_status_label(
                            f"API access failed: {info_response.status_code} - {info_response.text}",
                            "red",
                        )
                else:
                    self._update_status_label(
                        "Authentication failed: No token received", "red"
                    )
            else:
                self._update_status_label(
                    f"Authentication failed: {token_response.status_code} - {token_response.text}",
                    "red",
                )
        except requests.exceptions.ConnectionError:
            self._update_status_label(
                "Connection error: Could not connect to server", "red"
            )
        except requests.exceptions.Timeout:
            self._update_status_label("Connection timed out", "red")
        except Exception as e:
            self._update_status_label(f"Error: {str(e)}", "red")

        return False

    def _update_status_label(self, message, color="black"):
        """Update the status label with message and color."""
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.config(text=message, foreground=color)
            # Force UI update
            if self.dashboard_win:
                self.dashboard_win.update()
