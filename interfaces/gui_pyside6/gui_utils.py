# interfaces/gui_pyside6/gui_utils.py
"""
Utility functions for common GUI operations and patterns.
"""

import logging
from typing import Callable, Any
from weakref import WeakSet

from PySide6.QtWidgets import QMessageBox, QPushButton, QHBoxLayout, QWidget, QLayout, QFrame
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QIcon

from core.exceptions import GUIError
from core.config import Config
from core.operation_manager import OperationManager

# Keep track of temporary objects for proper cleanup
_temporary_objects = WeakSet()


class GUIHelpers:
    """Helper class for common GUI operations."""
    
    @staticmethod
    def show_message(parent, title: str, message: str, msg_type: str = "info"):
        """
        Show a message box with the specified type.
        
        Args:
            parent: Parent widget
            title: Message box title
            message: Message content
            msg_type: Type of message ('info', 'warning', 'error', 'question')
        """
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        # Set custom application icon
        icon_path = Config().ICON_PATH
        if icon_path and icon_path.exists():
            msg_box.setWindowIcon(QIcon(QPixmap(str(icon_path))))
        
        if msg_type == "info":
            msg_box.setIcon(QMessageBox.Information)
        elif msg_type == "warning":
            msg_box.setIcon(QMessageBox.Warning)
        elif msg_type == "error":
            msg_box.setIcon(QMessageBox.Critical)
        elif msg_type == "question":
            msg_box.setIcon(QMessageBox.Question)
            
        # Track temporary object for cleanup
        _temporary_objects.add(msg_box)
        
        return msg_box.exec()
    
    @staticmethod
    def create_social_links(parent_layout, links: list):
        """
        Create social media links.
        
        Args:
            parent_layout: Layout to add links to
            links: List of tuples (text, url)
        """
        links_frame = QFrame()
        links_layout = QHBoxLayout(links_frame)

        for text, url in links:
            link_btn = QPushButton(text)
            link_btn.clicked.connect(lambda checked, u=url: QDesktopServices.openUrl(QUrl(u)))
            links_layout.addWidget(link_btn)
            # Track temporary objects for cleanup
            _temporary_objects.add(link_btn)

        parent_layout.addWidget(links_frame)
        # Track temporary objects for cleanup
        _temporary_objects.add(links_frame)
        _temporary_objects.add(links_layout)
    
    @staticmethod
    def clear_layout(layout):
        """
        Clear all widgets from a layout with proper cleanup.
        
        Args:
            layout: Layout to clear
        """
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    # Schedule widget for deletion instead of immediate deletion
                    child.widget().deleteLater()
    
    @staticmethod
    def cleanup_temporary_objects():
        """
        Clean up temporary objects.
        This method should be called periodically or during application shutdown.
        """
        count = len(_temporary_objects)
        # Objects in WeakSet are automatically removed when they are deleted
        # This is just for logging purposes
        logging.info(f"Cleaned up {count} temporary objects")


class ActionHandler:
    """Handler for common action patterns in the GUI."""
    
    def __init__(self, notification_service, status_manager):
        self.notification_service = notification_service
        self.status_manager = status_manager
        self.logger = logging.getLogger(__name__)
        self.operation_manager = OperationManager()
    
    def perform_action(self, action_func, action_name, refresh_callback=None):
        """
        Perform an action with error handling, operation locking, and proper status reporting.
        
        Args:
            action_func: Function to execute
            action_name: Name of the action for logging
            refresh_callback: Optional callback to refresh UI after action
        """
        if not action_func:
            error_msg = f"{action_name} not available"
            self.status_manager.show_status_log(error_msg, "error")
            self.notification_service.notify("Error", error_msg, "error")
            return
        
        # Acquire operation lock
        if not self.operation_manager.acquire_operation_lock(action_name):
            current_op = self.operation_manager.get_current_operation()
            warning_msg = f"Cannot {action_name} - {current_op} already in progress"
            self.logger.warning(warning_msg)
            self.status_manager.show_status_log(warning_msg, "warning")
            self.notification_service.notify(
                "Operation Blocked",
                f"{warning_msg}. Please wait.",
                "warning"
            )
            return
        
        try:
            self.status_manager.show_status_log(f"Executing {action_name}...", "info")
            self.logger.info(f"Starting action: {action_name}")
            
            # Execute the action and check result if it returns a boolean
            result = action_func()
            
            # Handle different return types
            if result is False:  # Explicit False indicates failure
                error_msg = f"{action_name} failed"
                self.logger.error(error_msg)
                self.status_manager.show_status_log(error_msg, "error")
                # Don't send duplicate notification - the action should have already notified
            elif result is True or result is None:  # True or None indicates success
                success_msg = f"{action_name} completed successfully"
                self.logger.info(success_msg)
                self.status_manager.show_status_log(success_msg, "success")
                # Only send success notification if action doesn't handle its own notifications
                if not hasattr(action_func, '__self__') or 'api_sync' not in str(action_func.__self__):
                    self.notification_service.notify(
                        "Success", success_msg, "info"
                    )
            else:
                # Handle other return types
                self.logger.info(f"{action_name} completed with result: {result}")
                self.status_manager.show_status_log(f"{action_name} completed", "info")
                
            # Refresh UI after action if callback provided
            if refresh_callback:
                refresh_callback()
                
        except Exception as e:
            error_msg = f"{action_name} failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.status_manager.show_status_log(error_msg, "error")
            self.notification_service.notify(
                "Error",
                f"{action_name} failed: {str(e)}",
                "error"
            )
        finally:
            # Always release the operation lock
            self.operation_manager.release_operation_lock(action_name)


def handle_gui_errors(func: Callable) -> Callable:
    """
    Decorator to handle GUI errors consistently.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"GUI Error in {func.__name__}: {e}")
            # Re-raise as GUIError for consistent error handling
            raise GUIError(f"GUI Error in {func.__name__}: {str(e)}")
    return wrapper