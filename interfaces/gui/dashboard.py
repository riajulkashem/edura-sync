# interfaces/gui/dashboard.py
"""
Main dashboard GUI for the PrimeSync application.
Coordinates dashboard components and manages the main window.
"""

import logging
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import ttk
import threading
import time

from core.config import Config
from core.constants import UI_CONFIG, APP_NAME, STATUS_COLORS, DEFAULT_SETTING
from core.exceptions import GUIError, ConfigurationError
from interfaces.gui.ui_utils import (
    create_window,
    setup_styles,
    create_notebook,
    create_tab,
    load_icon,
    create_button,
)
from interfaces.gui.dashboard_settings import DashboardSettings
from interfaces.gui.dashboard_content import DashboardContent
from interfaces.gui.dashboard_status import DashboardStatus
from interfaces.database.repository import (
    DeviceRepository,
    UserRepository,
    SettingsRepository,
)
from services.notification import NotificationService
from core.security import SecurityManager


class DashboardGUI:
    """Main GUI dashboard for the PrimeSync application."""

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

        # UI components
        self.dashboard_win = None
        self.dashboard_content = None
        self.status_label = None
        self.connection_status_label = None

        # Status colors
        self.status_colors = {
            "success": "green",
            "error": "red", 
            "warning": "orange",
            "info": "blue"
        }

        # Initialize component managers
        self.settings_manager = DashboardSettings(self)
        self.content_manager = DashboardContent(self)
        self.status_manager = DashboardStatus(self)

    def show_dashboard(self, first_run=False):
        """Show or update the main dashboard window."""
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
            self.settings_manager.create_settings_tab(settings_frame)
            self._create_credits_tab(credits_frame)

            # Select settings tab on first run
            if first_run:
                notebook.select(1)

            # Add Quit button
            quit_btn = create_button(
                self.dashboard_win, "Quit", self.dashboard_win.withdraw
            )
            quit_btn.pack(pady=(0, 10))

        except Exception as e:
            self.logger.error(f"Error displaying dashboard: {e}")
            self.notification_service.notify(
                "Error", f"Failed to load dashboard: {str(e)}", "error"
            )
            raise GUIError(f"Failed to display dashboard: {str(e)}")

    def _create_dashboard_tab(self, frame):
        """Create the dashboard tab with scrollable content."""
        try:
            frame.columnconfigure(0, weight=1)

            # Create scrollable frame
            canvas = tk.Canvas(frame)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            self.dashboard_content = ttk.Frame(canvas)

            self.dashboard_content.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
            )

            canvas.create_window((0, 0), window=self.dashboard_content, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Pack scrollable components
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Bind mouse wheel to scroll
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            canvas.bind_all("<MouseWheel>", _on_mousewheel)

            # Initial content update
            self.content_manager.update_dashboard_content()

        except Exception as e:
            self.logger.error(f"Failed to create dashboard tab: {e}")
            raise GUIError(f"Failed to create dashboard tab: {str(e)}")

    def _create_credits_tab(self, frame):
        """Create the credits tab."""
        try:
            # Credits content
            credits_text = f"""
{APP_NAME} - Attendance Management System

Version: {Config().VERSION}
Author: PrimeSync Team

This application provides attendance management for ZKTeco devices
with cloud synchronization capabilities.

Features:
• Device Management
• Attendance Tracking
• Cloud Synchronization
• Real-time Monitoring
• User Management

For support and updates, visit our website.
            """

            # Create text widget
            text_widget = tk.Text(frame, wrap="word", padx=20, pady=20)
            text_widget.insert("1.0", credits_text)
            text_widget.configure(state="disabled")
            text_widget.pack(fill="both", expand=True)

            # Create social links
            self._create_social_links(frame)

        except Exception as e:
            self.logger.error(f"Failed to create credits tab: {e}")
            raise GUIError(f"Failed to create credits tab: {str(e)}")

    def _create_social_links(self, parent):
        """Create social media links."""
        try:
            links_frame = ttk.Frame(parent)
            links_frame.pack(pady=20)

            links = [
                ("Website", "https://primesync.com"),
                ("GitHub", "https://github.com/primesync"),
                ("Documentation", "https://docs.primesync.com"),
            ]

            for text, url in links:
                link_btn = create_button(
                    links_frame, 
                    text=text, 
                    command=lambda u=url: webbrowser.open(u)
                )
                link_btn.pack(side="left", padx=10)

        except Exception as e:
            self.logger.error(f"Failed to create social links: {e}")

    # Action methods
    def _check_devices(self):
        """Check device connections."""
        self._perform_action(self.device_manager.check_devices, "Check Devices")

    def _pull_data(self):
        """Pull data from devices."""
        self._perform_action(self.device_manager.pull_data, "Pull Data")

    def _sync_users(self):
        """Sync users with cloud."""
        self._perform_action(self.api_client.sync_users, "Sync Users")

    def _sync_to_cloud(self):
        """Sync data to cloud."""
        self._perform_action(self.api_client.post_to_cloud, "Sync to Cloud")

    def _refresh_dashboard(self):
        """Refresh dashboard data."""
        try:
            self.content_manager.update_dashboard_content()
            self.show_status_log("Dashboard refreshed", "info")
        except Exception as e:
            self.logger.error(f"Error refreshing dashboard: {e}")
            self.show_status_log(f"Failed to refresh dashboard: {str(e)}", "error")

    def set_device_manager(self, device_manager):
        """Set the device manager reference."""
        self.device_manager = device_manager

    def _perform_action(self, action_func, action_name):
        """Perform an action with error handling."""
        try:
            if action_func:
                self.show_status_log(f"Executing {action_name}...", "info")
                action_func()
                self.show_status_log(f"{action_name} completed successfully", "success")
                self.notification_service.notify(
                    "Success", f"{action_name} completed successfully", "info"
                )
                # Refresh dashboard after action
                self._refresh_dashboard()
            else:
                error_msg = f"{action_name} not available"
                self.show_status_log(error_msg, "error")
                self.notification_service.notify(
                    "Error", error_msg, "error"
                )
        except Exception as e:
            error_msg = f"Failed to {action_name.lower()}: {str(e)}"
            self.logger.error(f"Error performing {action_name}: {e}")
            self.show_status_log(error_msg, "error")
            self.notification_service.notify(
                "Error", error_msg, "error"
            )

    # Delegate methods to component managers
    def show_status_log(self, message: str, level: str = "info"):
        """Show status log message."""
        self.status_manager.show_status_log(message, level)

    def hide_status_log(self):
        """Hide status log."""
        self.status_manager.hide_status_log()

    def _update_connection_status(self, message: str, status: str = "info"):
        """Update connection status."""
        self.status_manager.update_connection_status(message, status)

    def update_status_label(self, message, color="black"):
        """Update status label."""
        self.status_manager.update_status_label(message, color)
