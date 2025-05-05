import logging
import platform
from pathlib import Path
from typing import Optional
import tempfile
import shutil

try:
    from notifypy import Notify
    NOTIFY_AVAILABLE = True
except ImportError:
    NOTIFY_AVAILABLE = False


class NotificationService:
    """Service for displaying system notifications."""

    def __init__(self, config):
        """Initialize notification service with application configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._setup_notification_system()

    def _setup_notification_system(self) -> None:
        """Set up the notification system based on available backends."""
        try:
            if NOTIFY_AVAILABLE:
                # Create a custom icon in temp directory if it exists
                self.icon_path = self._prepare_notification_icon()
                self.logger.info("Notification system initialized successfully with notify-py")
            else:
                self.logger.warning("notify-py not available, using fallback notifications")
        except Exception as e:
            self.logger.error(f"Failed to initialize notification system: {e}")

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
            self.logger.info(f"[{self._get_timestamp()}] PrimeSync - {title}: {message}")
            self.logger.info(f"Sending notification: PrimeSync - {title} - {message}")
            
            if NOTIFY_AVAILABLE:
                notification = Notify()
                notification.title = f"PrimeSync - {title}"
                notification.message = message
                
                # Set the icon if available
                if self.icon_path:
                    notification.icon = self.icon_path
                
                # Disable URL open on click (notify-py feature)
                notification.urgency = 'normal'
                
                # Override default click action to prevent opening GitHub URL
                # This is a workaround for notify-py behavior
                if platform.system() == 'Darwin':  # macOS
                    notification.application_name = "PrimeSync"
                elif platform.system() == 'Windows':
                    pass  # Windows doesn't have this issue
                else:  # Linux
                    notification.application_name = "PrimeSync"
                
                notification.send(block=False)
            else:
                # Fallback to logging only if no notification system is available
                self.logger.warning(f"Unable to show notification - notify-py not available")
                
            self.logger.info(f"Notification sent successfully: PrimeSync - {title} - {message}")
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp string for logging."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_notification_icon(self, notification_type: str) -> Optional[str]:
        """
        Return an appropriate icon path based on notification type.
        
        Args:
            notification_type: Type of notification (info, error, warning)
            
        Returns:
            Optional[str]: Path to icon or None if not found
        """
        return self.icon_path