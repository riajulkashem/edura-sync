# services/notification.py

import logging
from datetime import datetime
import os
from typing import Optional
import platform
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from core.config import Config

class NotificationService:
    """
    Centralized service for handling system notifications in the PrimeSync application.
    Uses notify-py for cross-platform notifications with fallback to logging.
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
        self.app_name = "PrimeSync Manager"
        
        # Check if notification is available
        self.notification_available = False
        self.notifier = None
        
        try:
            # Try to import notify-py
            from notifypy import Notify
            
            # Create a notifier instance
            self.notifier = Notify()
            self.notifier.application_name = self.app_name
            
            # Set default icon if available
            if self.config.ICON_PATH and self.config.ICON_PATH.exists():
                self.notifier.icon = str(self.config.ICON_PATH)
            
            # Test notification system
            test_notify = Notify()
            test_notify.application_name = self.app_name
            test_notify.title = "Initialization"
            test_notify.message = "Application starting..."
            
            # Only actually send test notification on production
            # test_notify.send(block=False)
            
            self.notification_available = True
            self.logger.info("Notification system initialized successfully with notify-py")
        except ImportError as e:
            self.logger.warning(f"notify-py import failed: {e}")
        except Exception as e:
            self.logger.warning(f"Notification system initialization failed: {e}")
    
    def _write_to_log_file(self, title: str, message: str) -> None:
        """
        Write notification content to the application log file.
        
        Args:
            title: The notification title
            message: The notification message
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] {title}: {message}"
            
            # Just use the logger instead of a separate file
            self.logger.info(log_message)
        except Exception as e:
            self.logger.error(f"Failed to write to notification log: {e}")
    
    def _get_notification_icon(self, notification_type: str) -> Optional[str]:
        """
        Return an appropriate icon path based on notification type.
        
        Args:
            notification_type: Type of notification (info, error, warning)
            
        Returns:
            Optional[str]: Path to icon or None if not found
        """
        # Use the default application icon for all notification types for now
        if self.config.ICON_PATH and self.config.ICON_PATH.exists():
            return str(self.config.ICON_PATH)
        
        # Can be expanded to use different icons for different notification types
        return None
    
    def _show_tkinter_message(self, title: str, message: str) -> None:
        """
        Display a tkinter message box as a fallback notification method.
        
        Args:
            title: The notification title
            message: The notification message
        """
        try:
            # Create a temporary root window that won't be shown
            root = tk.Tk()
            root.withdraw()
            
            # Show message dialog
            if "error" in title.lower():
                messagebox.showerror(title, message)
            elif "warning" in title.lower():
                messagebox.showwarning(title, message)
            else:
                messagebox.showinfo(title, message)
            
            # Clean up
            root.destroy()
        except Exception as e:
            self.logger.error(f"Failed to show tkinter message: {e}")
    
    def notify(self, title: str, message: str, notification_type: str) -> None:
        """
        Send a notification to the user, either via system notification or log file.
        Args:
            title: The title of the notification.
            message: The message content of the notification.
            notification_type: Type of notification ('info', 'error', etc.).
        """
        notification_title = f"PrimeSync - {notification_type.capitalize()}"
        
        # Always log to file first
        self._write_to_log_file(notification_title, message)
        self.logger.info(f"Sending notification: {notification_title} - {message}")
        
        # Skip system notification if unavailable
        if not self.notification_available or not self.notifier:
            self.logger.warning("Notification system unavailable, using log file only")
            # Try to show a tkinter message as fallback
            self._show_tkinter_message(notification_title, message)
            return
            
        try:
            # Import here to ensure it only happens when needed
            from notifypy import Notify
            
            # Create a new notification
            notification = Notify()
            notification.application_name = self.app_name
            notification.title = notification_title
            notification.message = message
            
            # Set icon based on notification type
            icon = self._get_notification_icon(notification_type)
            if icon:
                notification.icon = icon
            
            # Send non-blocking notification
            notification.send(block=False)
            
            self.logger.info(f"Notification sent successfully: {notification_title} - {message}")
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            # Fallback to tkinter
            self._show_tkinter_message(notification_title, message)