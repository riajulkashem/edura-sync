import logging
import platform
from pathlib import Path
from typing import Optional
import tempfile
import shutil

from core.exceptions import NotificationError

try:
    from notify_py import Notify
    NOTIFY_AVAILABLE = True
except ImportError:
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
        try:
            if NOTIFY_AVAILABLE:
                # Create a custom icon in temp directory if it exists
                self.icon_path = self._prepare_notification_icon()
                self.logger.info("Notification system initialized with notify-py")
            else:
                self.logger.warning(
                    "notify-py not available, using fallback notifications"
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize notification system: {e}")
            # Don't raise error, continue with fallback

    def _prepare_notification_icon(self) -> Optional[str]:
        """
        Prepare custom notification icon for use with notify-py.
        Returns:
            Optional[str]: Path to prepared icon or None if unavailable
        """
        try:
            if self.config.ICON_PATH and self.config.ICON_PATH.exists():
                # Create a copy in a temp directory to ensure it's accessible
                temp_dir = Path(tempfile.gettempdir()) / "primesync"
                temp_dir.mkdir(exist_ok=True)

                temp_icon = temp_dir / "notification_icon.png"
                shutil.copy2(self.config.ICON_PATH, temp_icon)

                return str(temp_icon)
            return None
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
        try:
            # Log notification for debugging
            self.logger.debug(f"Notification: {title} - {message}")

            if NOTIFY_AVAILABLE:
                try:
                    notification = Notify()
                    notification.title = f"PrimeSync - {title}"
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
                    if platform.system() == "Darwin":  # macOS
                        notification.application_name = "PrimeSync"
                    elif platform.system() == "Windows":
                        pass  # Windows doesn't have this issue
                    else:  # Linux
                        notification.application_name = "PrimeSync"

                    notification.send(block=False)
                    self.logger.debug(f"Notification sent successfully: {title}")
                except Exception as e:
                    self.logger.error(f"Failed to send notification with notify-py: {e}")
                    # Fall back to logging
                    self._log_notification(title, message, notification_type)
            else:
                # Fallback to logging only if no notification system is available
                self._log_notification(title, message, notification_type)

        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            # Don't raise error, just log it

    def _log_notification(self, title: str, message: str, notification_type: str) -> None:
        """Log notification as fallback when notify-py is not available."""
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

    def _get_notification_icon(self, notification_type: str) -> Optional[str]:
        """
        Return an appropriate icon path based on notification type.

        Args:
            notification_type: Type of notification (info, error, warning)

        Returns:
            Optional[str]: Path to icon or None if not found
        """
        return self.icon_path
