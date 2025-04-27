# services/notification.py

import logging
from datetime import datetime
from typing import Optional
from core.config import Config
from pathlib import Path
from notifypy import Notify


class NotificationService:
    """
    Centralized service for handling system notifications in the PrimeSync application.
    Implements the Observer pattern to notify users via system notifications or log file fallback.
    Uses notifypy for cross-platform notifications and integrates with the application configuration.
    """

    def __init__(self, config: Config):
        """
        Initialize the notification service with configuration.
        Args:
            config: Application configuration for log file and icon paths.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.info("NotificationService initialized")
        self.notify = Notify(
            default_notification_title="Notice",
            default_application_name="PrimeSync",
            default_notification_icon="assets/icon.png",
        )

    def notify(self, title: str, message: str, notification_type: str) -> None:
        """
        Send a notification to the user, either via system notification or log file.
        Args:
            title: The title of the notification.
            message: The message content of the notification.
            notification_type: Type of notification ('info', 'error', etc.).
        """
        notification_title = f"PrimeSync - {notification_type.capitalize()}"
        icon = self._get_notification_icon(notification_type)
        self.logger.info(
            f"Sending notification: {notification_title} - {message} (icon: {icon})"
        )

        try:

            self.notify.title = notification_title
            self.notify.message = message
            if icon:
                self.notify.icon = icon

            self.notify.send()


            self.logger.info(
                f"Notification sent successfully: {notification_title} - {message}"
            )
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            self._write_to_log_file(notification_title, message)
            self.logger.info(
                f"Fell back to log file for notification: {notification_title} - {message}"
            )

    def _get_notification_icon(self, notification_type: str) -> Optional[str]:
        """
        Determine the icon path for the notification based on type.
        Args:
            notification_type: Type of notification ('info', 'error', etc.).
        Returns:
            Optional[str]: Path to the icon file or None if unavailable.
        """
        if notification_type.lower() == "info":
            icon_path = self.config.ICON_PATH
            if icon_path and icon_path.exists() and icon_path.is_file():
                self.logger.debug(f"Using icon for notification: {icon_path}")
                return str(icon_path)
            self.logger.warning(f"Icon not found or inaccessible at {icon_path}")
        return None

    def _write_to_log_file(self, title: str, message: str) -> None:
        """
        Write a notification message to the log file as a fallback.
        Args:
            title: The title of the notification.
            message: The message content of the notification.
        """
        try:
            log_file: Path = self.config.LOG_FILE
            with log_file.open("a") as f:
                f.write(f"{datetime.now()} [NOTIFICATION] {title}: {message}\n")
            self.logger.debug(f"Wrote notification to log file: {title} - {message}")
        except Exception as e:
            self.logger.error(f"Failed to write notification to log file: {e}")
