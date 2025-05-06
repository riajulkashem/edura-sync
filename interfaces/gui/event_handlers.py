# interfaces/gui/event_handlers.py
"""
Event handlers for GUI components.
Contains callback methods for buttons and other interactive UI elements.
"""

import logging
import tkinter as tk
import requests
from typing import Callable, Dict

from core.constants import STATUS_COLORS, STATUS_MESSAGES, API_ENDPOINTS

logger = logging.getLogger(__name__)


class SettingsEventHandler:
    """Handles events for the Settings tab in the dashboard."""

    def __init__(
        self,
        app,
        security,
        settings_repo,
        notification_service,
        status_callback: Callable[[str, str], None],
    ):
        """
        Initialize settings event handler.

        Args:
            app: Main application instance
            security: Security manager for encryption/decryption
            settings_repo: Repository for settings data
            notification_service: Service for notifications
            status_callback: Function to update status message and color
        """
        self.app = app
        self.security = security
        self.settings_repo = settings_repo
        self.notification_service = notification_service
        self.status_callback = status_callback
        self.logger = logging.getLogger(__name__)
        self.auth_token = None

    def check_connection(
        self,
        url: str,
        username: str,
        password: str,
        institute_id: str,
        parent_widget: tk.Widget,
    ) -> bool:
        """
        Check connection to the API server using provided credentials.

        Args:
            url: API URL
            username: Username for authentication
            password: Password for authentication
            institute_id: Institute ID parameter
            parent_widget: Parent widget for UI updates

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not all([url, username, password, institute_id]):
            self.status_callback(
                STATUS_MESSAGES["FILL_ALL_FIELDS"], STATUS_COLORS["ERROR"]
            )
            return False

        # Show checking status
        self.status_callback(
            STATUS_MESSAGES["CONNECTION_CHECKING"], STATUS_COLORS["INFO"]
        )
        parent_widget.update()

        try:
            # Determine the token URL
            login_url = f"{url}{API_ENDPOINTS['TOKEN']}"

            # Try token-based authentication
            token_payload = {"username": username, "password": password}

            token_response = requests.post(
                login_url,
                json=token_payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if token_response.status_code == 200:
                # Token auth successful
                token_data = token_response.json()
                token = token_data.get("token") or token_data.get("access")

                if token:
                    # Save token for later use
                    self.auth_token = token

                    # Now try to access the API with the token to verify
                    headers = {"Authorization": f"Token {token}"}

                    # Use institute_id as a parameter
                    info_url = f"{url}{API_ENDPOINTS['INFO']}?institute={institute_id}"

                    info_response = requests.get(info_url, headers=headers, timeout=5)

                    if info_response.status_code == 200:
                        # Successfully connected with token
                        info_data = info_response.json()
                        self.status_callback(
                            f"Connected to {info_data.get('name', 'Django API')} v{info_data.get('version', '1.0')}",
                            STATUS_COLORS["SUCCESS"],
                        )
                        self.logger.info(f"Connected to Django API: {info_data}")
                        return True
                else:
                    self.status_callback(
                        "Authentication failed: No token received",
                        STATUS_COLORS["ERROR"],
                    )
                    return False
            else:
                # Authentication failed
                self.status_callback(
                    f"Authentication failed: {token_response.status_code}",
                    STATUS_COLORS["ERROR"],
                )
                self.logger.warning(
                    f"Authentication failed: {token_response.status_code}"
                )
                return False

        except requests.exceptions.ConnectionError:
            self.status_callback(
                "Connection error: Could not connect to server", STATUS_COLORS["ERROR"]
            )
            self.logger.error("Connection error: Failed to connect to server")
        except requests.exceptions.Timeout:
            self.status_callback("Connection timed out", STATUS_COLORS["ERROR"])
            self.logger.error("Connection error: Request timed out")
        except Exception as e:
            self.status_callback(f"Error: {str(e)}", STATUS_COLORS["ERROR"])
            self.logger.error(f"Connection test error: {e}")

        return False

    def save_settings(
        self, url: str, username: str, password: str, institute_id: str
    ) -> bool:
        """
        Save settings to the database and update related services.

        Args:
            url: API URL
            username: Username for authentication
            password: Password for authentication
            institute_id: Institute ID parameter

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            # Prepare data for saving
            data = {
                "cloud_api_url": url.strip(),
                "username": username.strip(),
                "password": self.security.encrypt(password.strip()),
                "institute_id": institute_id.strip(),
            }

            # Add auth_token to data if it exists
            if self.auth_token:
                data["auth_token"] = self.auth_token

            # Save settings to the database
            self.settings_repo.save_settings(**data)

            # Update API client with new settings
            self.app.api_client.update_settings()

            # Use status label for confirmation
            self.status_callback(
                STATUS_MESSAGES["SETTINGS_SAVED"], STATUS_COLORS["SUCCESS"]
            )
            self.logger.info("Settings saved successfully")

            # Notify user
            self.notification_service.notify(
                "Settings", "Settings saved successfully", "info"
            )
            return True
        except Exception as e:
            self.status_callback(f"Save error: {e}", STATUS_COLORS["ERROR"])
            self.logger.error(f"Save failed: {e}")
            return False

    def reset_settings(self, entries: Dict[str, tk.Entry]) -> None:
        """
        Reset all form fields.

        Args:
            entries: Dictionary of entry widgets to reset
        """
        try:
            for entry in entries.values():
                entry.delete(0, tk.END)

            self.status_callback(
                STATUS_MESSAGES["SETTINGS_RESET"], STATUS_COLORS["INFO"]
            )
            self.logger.info("Settings form reset")
        except Exception as e:
            self.logger.error(f"Failed to reset settings form: {e}")
            self.status_callback(f"Error: {str(e)}", STATUS_COLORS["ERROR"])


class DashboardEventHandler:
    """Handles events for the Dashboard tab."""

    def __init__(self, app, device_manager, notification_service):
        """
        Initialize dashboard event handler.

        Args:
            app: Main application instance
            device_manager: Device manager for device operations
            notification_service: Service for notifications
        """
        self.app = app
        self.device_manager = device_manager
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)

    def refresh_dashboard(self) -> None:
        """
        Refresh the dashboard data without reloading the window.
        """
        try:
            # Update device statuses
            self.device_manager.check_devices()
            self.logger.info("Dashboard data refreshed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to refresh dashboard data: {e}")
            self.notification_service.notify(
                "Error", f"Failed to refresh data: {str(e)}", "error"
            )
            return False
