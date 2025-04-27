import logging
import requests
from datetime import datetime
from models import Attendance, Settings, Schedule
from security import SecurityManager


class APIClient:
    """Handles cloud API interactions."""

    def __init__(self, security: SecurityManager):
        self.logger = logging.getLogger(__name__)
        self.security = security
        self.settings = None

    def update_settings(self, settings: Settings):
        """Update API client with new settings."""
        self.settings = settings

    def post_to_cloud(self):
        """Post attendance data to cloud API."""
        if not self.settings:
            self.logger.error("Settings not configured")
            return

        try:
            url = self.settings.cloud_api_url
            username = self.settings.username
            password = self.security.decrypt(self.settings.password)
            client_key = self.settings.client_key

            data = [
                {
                    "user_id": att.user.user_id,
                    "timestamp": att.timestamp.isoformat(),
                    "status": att.status,
                    "punch": att.punch
                }
                for att in Attendance.select()
            ]

            response = requests.post(
                url,
                json={"data": data, "client_key": client_key},
                auth=(username, password),
                timeout=10
            )
            response.raise_for_status()

            push_schedule = Schedule.get_or_none(task_type="push")
            if push_schedule:
                push_schedule.last_run = datetime.now()
                push_schedule.save()

            self.logger.info("Data posted to cloud successfully")
            self.show_notification("Cloud Sync", "Data posted to cloud successfully", "info")
        except requests.RequestException as e:
            self.logger.error(f"Failed to post data to cloud: {e}")
            self.show_notification("Error", f"Failed to post data to cloud: {str(e)}", "error")

    def show_notification(self, title: str, message: str, type: str):
        """Delegate notification to GUI."""
        try:
            from gui import PrimeSyncGUI
            PrimeSyncGUI.show_notification(self, title, message, type)
        except Exception as e:
            self.logger.error(f"Failed to delegate notification: {e}")