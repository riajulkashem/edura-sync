# interfaces/gui/event_handlers.py
"""
Event handlers for GUI components.
Contains callback methods for buttons and other interactive UI elements.
"""

import logging
import requests
from datetime import datetime
from tkinter import messagebox

from core.exceptions import (
    GUIError,
    APICallError,
    APIAuthenticationError,
    APINetworkError,
    ConfigurationError,
    ValidationError,
)
from core.constants import API_ENDPOINTS
from interfaces.gui.ui_utils import (
    show_error_dialog,
    show_info_dialog,
    show_confirm_dialog,
)


class EventHandlers:
    """Event handlers for GUI components."""

    def __init__(self, notification_service, settings_repo, api_client):
        """Initialize event handlers with dependencies."""
        self.logger = logging.getLogger(__name__)
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.api_client = api_client

    def test_api_connection(self, url, sync_id):
        """Test API connection with sync_id authentication."""
        try:
            # Validate inputs
            if not all([url, sync_id]):
                raise ValidationError("Please fill in API URL and Sync ID fields")

            # Use the API client's test_connection method
            if self.api_client:
                return self.api_client.test_connection(url, sync_id)
            else:
                raise ConfigurationError("API client not available")

        except ValidationError:
            raise
        except ConfigurationError:
            raise
        except Exception as e:
            raise GUIError(f"Connection test failed: {str(e)}")

    def save_settings(self, settings_data):
        """Save settings with validation."""
        try:
            if not self.settings_repo or not self.security:
                raise ConfigurationError(
                    "Settings repository or security manager not available"
                )

            # Validate required fields
            required_fields = ["cloud_api_url", "sync_id"]
            for field in required_fields:
                if not settings_data.get(field):
                    raise ValidationError(f"Missing required field: {field}")

            # Add timestamp
            settings_data["updated_at"] = datetime.now()

            # Save settings
            self.settings_repo.save_settings(**settings_data)

            # Update API client
            if self.api_client:
                self.api_client.update_settings()

            self.notification_service.notify(
                "Settings", "Settings saved successfully", "info"
            )

        except (ConfigurationError, ValidationError) as e:
            self.logger.error(f"Configuration error saving settings: {e.message}")
            self.notification_service.notify(
                "Error", f"Configuration error: {e.message}", "error"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            self.notification_service.notify(
                "Error", f"Failed to save settings: {str(e)}", "error"
            )
            raise GUIError(f"Failed to save settings: {str(e)}")

    def reset_settings_form(self, form_fields):
        """Reset all form fields."""
        try:
            for field in form_fields:
                if hasattr(field, "delete"):
                    field.delete(0, "end")
                elif hasattr(field, "set"):
                    field.set("")

            self.notification_service.notify("Info", "Settings form reset", "info")

        except Exception as e:
            self.logger.error(f"Failed to reset settings form: {e}")
            self.notification_service.notify(
                "Error", f"Failed to reset form: {str(e)}", "error"
            )
            raise GUIError(f"Failed to reset form: {str(e)}")

    def refresh_dashboard_data(self, dashboard_gui):
        """Refresh dashboard data."""
        try:
            if not dashboard_gui:
                raise ConfigurationError("Dashboard GUI not available")

            dashboard_gui._refresh_dashboard()
            self.notification_service.notify("Info", "Dashboard data refreshed", "info")

        except ConfigurationError as e:
            self.logger.error(f"Configuration error refreshing dashboard: {e.message}")
            self.notification_service.notify(
                "Error", f"Configuration error: {e.message}", "error"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to refresh dashboard data: {e}")
            self.notification_service.notify(
                "Error", f"Failed to refresh dashboard: {str(e)}", "error"
            )
            raise GUIError(f"Failed to refresh dashboard: {str(e)}")
