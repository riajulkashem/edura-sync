# interfaces/gui/dashboard.py
import logging
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Optional, Dict

from core.config import Config
from core.constants import (
    UI_CONFIG,
    STATUS_COLORS,
    DEVELOPER,
    APP_NAME
)
from interfaces.database.repository import DeviceRepository, UserRepository
from interfaces.gui.event_handlers import SettingsEventHandler, DashboardEventHandler
from interfaces.gui.ui_utils import (
    create_window,
    setup_styles,
    create_notebook,
    create_tab,
    load_icon,
    create_button,
    create_labeled_entry
)
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

        # Initialize event handlers
        self.settings_handler = SettingsEventHandler(
            self.app,
            self.app.security,
            self.app.settings_repo,
            self.notification_service,
            self._update_status_label
        )

        self.dashboard_handler = DashboardEventHandler(
            self.app,
            self.app.device_manager,
            self.notification_service
        )

    def show_dashboard(self, first_run: bool = False) -> None:
        """
        Show or update the main dashboard window.

        Args:
            first_run: If True, select the settings tab
        """
        self.logger.info("Opening or updating dashboard window")
        try:
            # Close existing dashboard if open
            if self.dashboard_win and self.dashboard_win.winfo_exists():
                self.dashboard_win.destroy()

            # Create new dashboard window
            self.dashboard_win = create_window(
                self.root,
                f"{APP_NAME} Dashboard",
                UI_CONFIG["DASHBOARD_SIZE"]
            )

            # Load icon
            load_icon(self.dashboard_win, Config().ICON_PATH)

            # Change window closing behavior to hide instead of destroy
            self.dashboard_win.protocol("WM_DELETE_WINDOW", self.dashboard_win.withdraw)

            # Configure style
            setup_styles()

            # Create notebook for tabs
            notebook = create_notebook(self.dashboard_win)

            # Create all tabs
            dashboard_frame = create_tab(notebook, "Dashboard")
            settings_frame = create_tab(notebook, "Settings")
            credits_frame = create_tab(notebook, "Credits")

            # Initialize tab contents
            self._create_dashboard_tab(dashboard_frame)
            self._create_settings_tab(settings_frame)
            self._create_credits_tab(credits_frame)

            # If it's the first run, select the settings tab
            if first_run:
                notebook.select(1)  # Index 1 is the settings tab

            # Add Quit button at the bottom of main window
            quit_btn = create_button(
                self.dashboard_win,
                "Quit",
                self.dashboard_win.withdraw
            )
            quit_btn.pack(pady=(0, 10))

            self.logger.info("Dashboard displayed successfully")
        except Exception as e:
            self.logger.error(f"Error displaying dashboard: {e}")
            self.notification_service.notify(
                "Error", f"Failed to load dashboard: {str(e)}", "error"
            )

    def _create_dashboard_tab(self, parent_frame: ttk.Frame) -> None:
        """
        Create the main dashboard tab content.
        
        Args:
            parent_frame: Parent frame for dashboard content
        """
        try:
            # Add header
            header = ttk.Label(parent_frame, text=f"{APP_NAME} Status Dashboard", style="Header.TLabel")
            header.pack(pady=(0, 20))

            # Create a content frame with border
            self.content_frame = ttk.Frame(parent_frame, relief="groove", borderwidth=2, padding=15)
            self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)

            # Populate the content frame
            self._update_dashboard_content(self.content_frame)

            # Create a container for the buttons
            action_container = ttk.Frame(parent_frame)
            action_container.pack(pady=15, fill="x")
            
            # Create top row buttons frame
            button_frame_top = ttk.Frame(action_container)
            button_frame_top.pack(fill="x", pady=(0, 5))
            
            # Configure columns for even spacing
            for i in range(4):
                button_frame_top.columnconfigure(i, weight=1)
            
            # Add first row of action buttons
            refresh_btn = create_button(
                button_frame_top, 
                "Refresh",
                self._refresh_dashboard_data
            )
            refresh_btn.grid(row=0, column=0, padx=3, sticky="ew")
            
            sync_btn = create_button(
                button_frame_top, 
                "Sync Data", 
                lambda: self._run_action_and_refresh(
                    self.app.api_client.sync_data, 
                    "Syncing data..."
                )
            )
            sync_btn.grid(row=0, column=1, padx=3, sticky="ew")
            
            pull_btn = create_button(
                button_frame_top, 
                "Pull Machine", 
                lambda: self._run_action_and_refresh(
                    self.app.device_manager.pull_data, 
                    "Pulling data from machines..."
                )
            )
            pull_btn.grid(row=0, column=2, padx=3, sticky="ew")
            
            post_btn = create_button(
                button_frame_top, 
                "Post Cloud", 
                lambda: self._run_action_and_refresh(
                    self.app.api_client.post_to_cloud, 
                    "Posting data to cloud..."
                )
            )
            post_btn.grid(row=0, column=3, padx=3, sticky="ew")
            
            # Create bottom row buttons frame
            button_frame_bottom = ttk.Frame(action_container)
            button_frame_bottom.pack(fill="x", pady=(5, 0))
            
            # Add second row of action buttons (for now just Check Devices)
            check_devices_btn = create_button(
                button_frame_bottom, 
                "Check Devices", 
                lambda: self._run_action_and_refresh(
                    self.app.device_manager.check_devices,
                    "Checking devices..."
                )
            )
            check_devices_btn.pack(fill="x")
            
            self.logger.info("Dashboard tab created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create dashboard tab: {e}")
            self.notification_service.notify(
                "Error", f"Failed to create dashboard tab: {str(e)}", "error"
            )

    def _create_settings_tab(self, parent_frame: ttk.Frame) -> None:
        """
        Create the settings tab content.

        Args:
            parent_frame: Parent frame for settings content
        """
        try:
            # Main frame for settings
            frame = ttk.Frame(parent_frame)
            frame.pack(fill="both", expand=True)

            # Settings header
            header = ttk.Label(frame, text="Application Settings", style="Header.TLabel")
            header.grid(row=0, column=0, columnspan=2, pady=(0, 15))

            # Configure grid
            frame.grid_columnconfigure(0, weight=0)
            frame.grid_columnconfigure(1, weight=1)

            # Input fields
            entries = {}
            entries["url"] = create_labeled_entry(frame, "Cloud API URL", 1)
            entries["username"] = create_labeled_entry(frame, "Username", 2)
            entries["password"] = create_labeled_entry(frame, "Password", 3, show='*')
            entries["institute_id"] = create_labeled_entry(frame, "Institute ID", 4)

            # Status label
            self.status_label = ttk.Label(
                frame,
                text="Enter your API settings...",
                foreground=STATUS_COLORS["NEUTRAL"],
                font=UI_CONFIG["SMALL_FONT"]
            )
            self.status_label.grid(
                row=5,
                column=0,
                columnspan=2,
                pady=10
            )

            # Pre-fill existing settings
            settings = self.app.settings_repo.get_settings()
            if settings:
                self._populate_settings_form(entries, settings)

            # Add help text for Django API
            help_frame = ttk.LabelFrame(frame, text="Django API Connection Help")
            help_frame.grid(
                row=7,
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

            # Button frame
            button_frame = ttk.Frame(frame)
            button_frame.grid(
                row=6,
                column=0,
                columnspan=2,
                sticky='ew',
                pady=15
            )

            button_frame.grid_columnconfigure(0, weight=1)
            button_frame.grid_columnconfigure(1, weight=1)
            button_frame.grid_columnconfigure(2, weight=1)

            # Add buttons
            reset_btn = create_button(
                button_frame,
                "Reset",
                lambda: self.settings_handler.reset_settings(entries)
            )
            reset_btn.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

            check_btn = create_button(
                button_frame,
                "Check Connection",
                lambda: self.settings_handler.check_connection(
                    entries["url"].get().strip(),
                    entries["username"].get().strip(),
                    entries["password"].get().strip(),
                    entries["institute_id"].get().strip(),
                    parent_frame
                )
            )
            check_btn.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

            save_btn = create_button(
                button_frame,
                "Save Settings",
                lambda: self.settings_handler.save_settings(
                    entries["url"].get().strip(),
                    entries["username"].get().strip(),
                    entries["password"].get().strip(),
                    entries["institute_id"].get().strip()
                )
            )
            save_btn.grid(row=0, column=2, padx=5, pady=5, sticky='ew')

            self.logger.info("Settings tab created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create settings tab: {e}")
            if hasattr(self, "notification_service"):
                self.notification_service.notify(
                    "Error", f"Failed to create settings tab: {str(e)}", "error"
                )

    def _create_credits_tab(self, parent_frame: ttk.Frame) -> None:
        """
        Create the credits tab content.

        Args:
            parent_frame: Parent frame for credits content
        """
        try:
            # Create main container
            main_frame = ttk.Frame(parent_frame, padding=20)
            main_frame.pack(fill="both", expand=True)

            # Add header
            header = ttk.Label(main_frame, text="Developer Information", style="Header.TLabel")
            header.pack(pady=(0, 20))

            # Developer info - using a frame with border
            info_frame = ttk.Frame(main_frame, relief="groove", borderwidth=2, padding=15)
            info_frame.pack(fill="both", expand=True)

            # Developer details from constants
            ttk.Label(info_frame, text=f"Name: {DEVELOPER['NAME']}", style="Credits.TLabel").pack(anchor="w", pady=5)
            ttk.Label(info_frame, text=f"Designation: {DEVELOPER['DESIGNATION']}", style="Credits.TLabel").pack(
                anchor="w", pady=5)

            # Social links with blue text
            ttk.Label(info_frame, text=f"FB: {DEVELOPER['FACEBOOK']}", style="CreditsLink.TLabel").pack(anchor="w",
                                                                                                        pady=5)
            ttk.Label(info_frame, text=f"Github: {DEVELOPER['GITHUB']}", style="CreditsLink.TLabel").pack(anchor="w",
                                                                                                          pady=5)
            ttk.Label(info_frame, text=f"LinkedIn: {DEVELOPER['LINKEDIN']}", style="CreditsLink.TLabel").pack(
                anchor="w", pady=5)

            self.logger.info("Credits tab created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create credits tab: {e}")

    def _populate_settings_form(self, entries: Dict[str, ttk.Entry], settings) -> None:
        """
        Populate settings form with existing settings.

        Args:
            entries: Dictionary of entry widgets
            settings: Settings object from database
        """
        try:
            entries["url"].delete(0, tk.END)
            entries["url"].insert(0, settings.cloud_api_url or "")

            entries["username"].delete(0, tk.END)
            entries["username"].insert(0, settings.username or "")

            # Handle possible decryption failures
            try:
                if settings.password:
                    decrypted_password = self.app.security.decrypt(settings.password)
                    entries["password"].delete(0, tk.END)
                    entries["password"].insert(0, decrypted_password)
            except Exception as e:
                self.logger.error(f"Failed to decrypt password: {e}")
                entries["password"].delete(0, tk.END)

            entries["institute_id"].delete(0, tk.END)
            entries["institute_id"].insert(0, settings.institute_id or "")

            # Store existing auth token if available
            if hasattr(settings, 'auth_token') and settings.auth_token:
                self.settings_handler.auth_token = settings.auth_token
        except Exception as e:
            self.logger.error(f"Failed to populate settings form: {e}")

    def _update_status_label(self, message: str, color: str) -> None:
        """
        Update the status label with message and color.

        Args:
            message: Status message
            color: Status color
        """
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.config(text=message, foreground=color)

    def _update_dashboard_content(self, content_frame: ttk.Frame) -> None:
        """
        Update dashboard content with fresh data.
        
        Args:
            content_frame: Frame containing dashboard content
        """
        try:
            # Clear existing widgets first
            for widget in content_frame.winfo_children():
                widget.destroy()
        
            # Fetch updated data
            connected = self.device_repo.count_online()
            total_devices = self.device_repo.count_total()
            total_users = self.user_repo.count_total()
            self.last_synced_time = self._get_last_sync_time()
            last_synced = (
                self.last_synced_time.strftime("%Y-%m-%d %H:%M:%S")
                if self.last_synced_time
                else "Never"
            )
            db_path = str(Config().DB_PATH)
    
            # Determine status styles
            device_status_style = "Good.TLabel" if connected == total_devices else "Warning.TLabel"
            sync_status_style = "Good.TLabel" if self.last_synced_time else "Warning.TLabel"
    
            # Display data with better formatting and status colors
            ttk.Label(content_frame, text="Device Status:", font=UI_CONFIG["HEADER_FONT"]).pack(anchor="w", pady=(0, 5))
            ttk.Label(
                content_frame, 
                text=f"Total Devices: {total_devices}",
            ).pack(anchor="w", padx=15)
            ttk.Label(
                content_frame,
                text=f"Connected: {connected} / Not Connected: {total_devices - connected}",
                style=device_status_style
            ).pack(anchor="w", padx=15, pady=(0, 10))
        
            ttk.Label(content_frame, text="User Information:", font=UI_CONFIG["HEADER_FONT"]).pack(anchor="w", pady=(5, 5))
            ttk.Label(content_frame, text=f"Total Users: {total_users}").pack(anchor="w", padx=15, pady=(0, 10))
        
            ttk.Label(content_frame, text="Synchronization:", font=UI_CONFIG["HEADER_FONT"]).pack(anchor="w", pady=(5, 5))
            ttk.Label(
                content_frame, 
                text=f"Last Synced: {last_synced}",
                style=sync_status_style
            ).pack(anchor="w", padx=15)
        
            ttk.Label(content_frame, text="System Information:", font=UI_CONFIG["HEADER_FONT"]).pack(anchor="w", pady=(10, 5))
            ttk.Label(content_frame, text=f"Database: {db_path}").pack(anchor="w", padx=15)
            
            self.logger.info("Dashboard content updated successfully")
        except Exception as e:
            self.logger.error(f"Failed to update dashboard content: {e}")
            
        # Force UI update
        content_frame.update()

    def _get_last_sync_time(self) -> Optional[datetime]:
        """
        Get the last sync time from API client or device manager.

        Returns:
            Optional[datetime]: Last sync time or None
        """
        try:
            # Check if API client has last_sync attribute
            if hasattr(self.app.api_client, 'last_sync') and self.app.api_client.last_sync:
                return self.app.api_client.last_sync

            # Otherwise, check if any device has a last_pulled value
            latest_device = self.device_repo.get_latest_pulled()
            if latest_device and latest_device.last_pulled:
                return latest_device.last_pulled

            return None
        except Exception as e:
            self.logger.error(f"Failed to get last sync time: {e}")
            return None

    def _refresh_dashboard_data(self) -> None:
        """Refresh dashboard data without reloading the entire window."""
        try:
            self._run_action_and_refresh(lambda: True, "Refreshing dashboard...")
            self.notification_service.notify(
                "Dashboard", "Dashboard refreshed successfully", "info"
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh dashboard: {e}")
            self.notification_service.notify(
                "Error", f"Failed to refresh dashboard: {str(e)}", "error"
            )

    def _run_action_and_refresh(self, action_func, status_message=None):
        """
        Run an action and refresh the dashboard content.
        
        Args:
            action_func: Function to run
            status_message: Optional status message to display during action
        """
        try:
            # Show status message if provided
            if status_message and hasattr(self, 'dashboard_win') and self.dashboard_win.winfo_exists():
                # Create or update a status label at the bottom of the dashboard
                if not hasattr(self, 'status_message_label'):
                    self.status_message_label = ttk.Label(
                        self.dashboard_win, 
                        text="", 
                        foreground=STATUS_COLORS["INFO"]
                    )
                    self.status_message_label.pack(side="bottom", pady=(0, 5))
                
                # Update status message
                self.status_message_label.config(text=status_message)
                self.status_message_label.update()
            
            # Run the action
            result = action_func()
            
            # Refresh dashboard content
            if hasattr(self, 'content_frame') and self.content_frame:
                self._update_dashboard_content(self.content_frame)
                
            # Clear status message
            if hasattr(self, 'status_message_label'):
                self.status_message_label.config(text="")
            
            # Show notification based on result
            if result is not None:
                if result:
                    self.notification_service.notify(
                        "Success", "Operation completed successfully", "info"
                    )
                else:
                    self.notification_service.notify(
                        "Warning", "Operation completed with warnings", "warning"
                    )
            else:
                # If no result, assume success
                self.notification_service.notify(
                    "Success", "Operation completed", "info"
                )
                
            self.logger.info(f"Action {action_func.__name__} completed and dashboard refreshed")
            
        except Exception as e:
            self.logger.error(f"Failed to run action {action_func.__name__}: {e}")
            self.notification_service.notify(
                "Error", f"Failed to complete operation: {str(e)}", "error"
            )
            
            # Clear status message on error
            if hasattr(self, 'status_message_label'):
                self.status_message_label.config(text="")