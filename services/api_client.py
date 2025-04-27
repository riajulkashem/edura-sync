# services/api_client.py
import logging
from datetime import datetime

import requests

from core.security import SecurityManager
from interfaces.database.repository import (
    AttendanceRepository,
    SettingsRepository,
    ScheduleRepository,
)
from services.notification import NotificationService


class APIClient:
    """
    Handles interactions with the cloud API for syncing attendance data.
    Uses dependency injection for security, notification, and repository services.
    """

    def __init__(
        self,
        security: SecurityManager,
        notification_service: NotificationService,
        settings_repo: SettingsRepository,
        attendance_repo: AttendanceRepository,
        schedule_repo: ScheduleRepository,
    ):
        """
        Initialize the API client with injected dependencies.
        Args:
            security: SecurityManager for encryption/decryption.
            notification_service: Service for sending notifications.
            settings_repo: Repository for settings data.
            attendance_repo: Repository for attendance data.
            schedule_repo: Repository for schedule data.
        """
        self.logger = logging.getLogger(__name__)
        self.security = security
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.attendance_repo = attendance_repo
        self.schedule_repo = schedule_repo
        self.settings = None
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from the repository."""
        self.settings = self.settings_repo.get_settings()
        if self.settings:
            self.logger.info("API client settings loaded")
        else:
            self.logger.warning("No settings found in repository")

    def update_settings(self) -> None:
        """Reload settings from the repository."""
        self._load_settings()
        self.logger.info("API client settings updated")

    def post_to_cloud(self) -> None:
        """Post attendance data to the cloud API."""
        self.logger.info("Starting data post to cloud API")
        if not self.settings:
            self.logger.error("Settings not configured")
            self.notification_service.notify(
                "Error", "Settings not configured", "error"
            )
            return

        try:
            url = self.settings.cloud_api_url
            username = self.settings.username
            password = self.security.decrypt(self.settings.password)
            client_key = self.settings.client_key

            # Fetch attendance data
            attendances = self.attendance_repo.get_all()
            data = [
                {
                    "user_id": att.user.user_id,
                    "timestamp": att.timestamp.isoformat(),
                    "status": att.status,
                    "punch": att.punch,
                }
                for att in attendances
            ]
            data_count = len(data)
            self.logger.info(
                f"Preparing to send {data_count} attendance records to {url}"
            )

            # Send data to cloud
            response = requests.post(
                url,
                json={"data": data, "client_key": client_key},
                auth=(username, password),
                timeout=10,
            )
            response.raise_for_status()

            # Update schedule last run time
            push_schedule = self.schedule_repo.get_by_task_type("push")
            if push_schedule:
                self.schedule_repo.update_last_run(push_schedule.id, datetime.now())
                self.logger.info("Updated push schedule last_run time")

            self.logger.info(f"Data posted to cloud successfully: {data_count} records")
            self.notification_service.notify(
                "Cloud Sync",
                f"Data posted to cloud successfully: {data_count} records",
                "info",
            )
        except requests.RequestException as e:
            self.logger.error(f"Failed to post data to cloud: {e}")
            self.notification_service.notify(
                "Error", f"Failed to post data to cloud: {str(e)}", "error"
            )
