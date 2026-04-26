import logging
import platform
from pathlib import Path
from typing import Optional

from core.constants import APP_NAME
from core.exceptions import NotificationError

try:
    from notify_py import Notify
    NOTIFY_AVAILABLE = True
except ImportError:
    NOTIFY_AVAILABLE = False
except Exception:
    # Handle other potential import issues
    NOTIFY_AVAILABLE = False


class NotificationService:
    """Service for displaying system notifications."""

    def __init__(self, config):
        """Initialize notification service with application configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.icon_path = None
        self._setup_notification_system()

    def _setup_notification_system(self) -> None:
        """Set up the notification system based on available backends."""
        if NOTIFY_AVAILABLE:
            # Create a custom icon in temp directory if it exists
            self.icon_path = self._prepare_notification_icon()
            self.logger.info("Notification system initialized successfully with notify-py")
        else:
            self.logger.info(
                "System notifications not available (notify-py not installed). "
                "Using log-based notifications. Install notify-py for desktop notifications."
            )

    def _prepare_notification_icon(self) -> Optional[str]:
        """
        Prepare notification icon for use with notify-py.
        Returns:
            Optional[str]: Path to icon or None if unavailable
        """
        try:
            if self.config.ICON_PATH and self.config.ICON_PATH.exists():
                # Use original icon path directly
                return str(self.config.ICON_PATH)
        except Exception as e:
            self.logger.error(f"Failed to prepare notification icon: {e}")
        return None

    def notify(self, title: str, message: str, notification_type: str = "info") -> None:
        """
        Display a notification with the given title and message.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, error, warning)
        """
        # Log notification for debugging
        self.logger.debug(f"Notification: {title} - {message}")

        if NOTIFY_AVAILABLE:
            self._send_desktop_notification(title, message, notification_type)
        else:
            # Fallback to logging only if no notification system is available
            self._log_notification(title, message, notification_type)

    def _send_desktop_notification(self, title: str, message: str, notification_type: str) -> None:
        """
        Send a desktop notification using notify-py.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, error, warning)
        """
        try:
            notification = Notify()
            # Avoid "EduraSync - EduraSync" when caller already prefixes the title
            notification.title = title if title.startswith(APP_NAME) else f"{APP_NAME} — {title}"
            notification.message = message

            # Set the icon if available
            if self.icon_path:
                notification.icon = self.icon_path

            # Set urgency based on notification type
            urgency_map = {
                "error": "critical",
                "warning": "normal", 
                "info": "low"
            }
            notification.urgency = urgency_map.get(notification_type, "normal")

            # Platform-specific settings
            if platform.system() == "Windows":
                notification.application_name = "EduraSync"
            else:  # Linux/macOS
                notification.application_name = "EduraSync"

            notification.send(block=False)
            self.logger.debug(f"Desktop notification sent successfully: {title}")
        except Exception as e:
            self.logger.error(f"Failed to send notification with notify-py: {e}")
            # Fall back to logging
            self._log_notification(title, message, notification_type)

    def _log_notification(self, title: str, message: str, notification_type: str) -> None:
        """
        Log notification as fallback when notify-py is not available.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, error, warning)
        """
        level_map = {
            "error": "ERROR",
            "warning": "WARNING", 
            "info": "INFO"
        }
        level = level_map.get(notification_type, "INFO")
        
        log_message = f"NOTIFICATION [{level}]: {title} - {message}"
        if level == "ERROR":
            self.logger.error(log_message)
        elif level == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
