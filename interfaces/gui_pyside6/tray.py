import logging
import platform
from typing import Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMessageBox
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QCoreApplication, QTimer

from core.exceptions import GUIError, ConnectionError, APICallError
from core.config import Config
from core.constants import APP_NAME
from core.operation_manager import OperationManager, operation_lock
from pathlib import Path


class SystemTray:
    """
    Manages the system tray icon and menu for the EduraSync application using PySide6.
    Provides quick access to application actions.
    """

    def __init__(
        self,
        app,
        config,
        device_manager,
        api_sync,
        dashboard_gui,
        notification_service,
    ):
        """
        Initialize the system tray with dependencies.
        Args:
            app: Reference to the main EduraSync application.
            config: Application configuration.
            device_manager: Service for device management.
            api_sync: Service for cloud API interactions.
            dashboard_gui: Dashboard GUI component.
            notification_service: Service for sending notifications.
        """
        self.app = app
        self.config = config
        self.device_manager = device_manager
        self.api_sync = api_sync
        self.dashboard_gui = dashboard_gui
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
        self.tray_icon: Optional[QSystemTrayIcon] = None
        
        # Timers for periodic tasks
        self.device_check_timer = None
        self.data_sync_timer = None
        
        # Get operation manager instance
        self.operation_manager = OperationManager()
        
        # Check if system tray is supported on this platform
        self.is_tray_supported = self._is_tray_supported()
        if self.is_tray_supported:
            self._setup_tray()
        else:
            self.logger.info("System tray disabled on this platform")

    def _is_tray_supported(self) -> bool:
        """Check if system tray is supported on the current platform."""
        # Check if system tray is available (removed macOS restriction)
        return QSystemTrayIcon.isSystemTrayAvailable()

    def _run_action(self, action, description: str):
        """
        Creates a wrapper function for tray menu actions with error handling and operation locking.

        Args:
            action: The function to run
            description: Description of the action for logging
        """
        def wrapper():
            # Check if an operation is already in progress
            if self.operation_manager.is_operation_in_progress():
                current_op = self.operation_manager.get_current_operation()
                self.logger.warning(
                    f"Cannot start {description} - {current_op} already in progress"
                )
                self.notification_service.notify(
                    "Operation Blocked",
                    f"Cannot {description.lower()} - {current_op} is in progress. Please wait.",
                    "warning"
                )
                return
            
            # Acquire lock for this operation
            if not self.operation_manager.acquire_operation_lock(description):
                return
            
            try:
                self.logger.info(f"Running action: {description}")
                action()
                self.logger.info(f"Completed action: {description}")
            except (ConnectionError, APICallError) as e:
                self.logger.error(f"Operation error in {description}: {e.message}")
                self.notification_service.notify(
                    "Error", f"Failed to {description.lower()}: {e.message}", "error"
                )
            except Exception as e:
                self.logger.error(f"Unexpected error in {description}: {e}")
                self.notification_service.notify(
                    "Error", f"Failed to {description.lower()}: {str(e)}", "error"
                )
            finally:
                # Always release the operation lock
                self.operation_manager.release_operation_lock(description)
        return wrapper

    def _setup_tray(self) -> None:
        """Set up the system tray icon and menu."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        
        # Set icon
        icon_path = self.config.ICON_PATH
        if icon_path and icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
            self.logger.info(f"Loaded tray icon from {icon_path}")
        else:
            # Use default application icon
            self.tray_icon.setIcon(QApplication.style().standardIcon(QApplication.StandardPixmap.SP_ComputerIcon))
            self.logger.warning(f"Icon file not available at {icon_path}, using default")

        # Create context menu
        tray_menu = QMenu()

        # Add menu items
        tray_menu.addAction(QAction("Check Device Status", tray_menu, 
                          triggered=self._run_action(self.device_manager.check_devices, "Checking device status...")))
        
        tray_menu.addAction(QAction("Perform Full Sync", tray_menu, 
                          triggered=self._run_action(self.api_sync.sync_data, "Daily synchronization...")))
        
        tray_menu.addAction(QAction("Upload Attendance", tray_menu, 
                          triggered=self._run_action(self.api_sync.post_to_cloud, "Uploading to cloud...")))
        
        tray_menu.addAction(QAction("Fetch New Logs", tray_menu, 
                          triggered=self._run_action(self.device_manager.pull_data, "Fetching device logs...")))
        
        tray_menu.addAction(QAction("Sync User Profiles", tray_menu, 
                          triggered=self._run_action(self.api_sync.sync_users, "Updating profiles...")))
        
        # Add periodic task controls
        tray_menu.addSeparator()
        tray_menu.addAction(QAction("Start Auto-Check", tray_menu, 
                          triggered=self.start_periodic_device_check))
        tray_menu.addAction(QAction("Stop Auto-Check", tray_menu, 
                          triggered=self.stop_periodic_device_check))
        
        tray_menu.addSeparator()
        
        # Dashboard actions - only if dashboard exists
        if self.dashboard_gui:
            tray_menu.addAction(QAction("Open Dashboard", tray_menu, 
                               triggered=self._run_action(self.dashboard_gui.show_dashboard, "Opening Dashboard...")))
            
            tray_menu.addAction(QAction("App Settings", tray_menu, 
                               triggered=lambda: self.dashboard_gui.show_dashboard(first_run=True)))
        else:
            # Headless mode - show simple info
            tray_menu.addAction(QAction("Running in Headless Mode", tray_menu, enabled=False))
        
        tray_menu.addSeparator()
        
        tray_menu.addAction(QAction("Quit Application", tray_menu, 
                          triggered=self._run_action(self.app.exit_app, "Shutting down...")))

        # Set context menu
        self.tray_icon.setContextMenu(tray_menu)

        # Connect tray icon activation
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

    def _on_tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click always shows dashboard
            if self.dashboard_gui:
                self.dashboard_gui.show_dashboard()
        
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click behavior
            # On macOS, single click standard is to show the menu (handled by Qt)
            # Opening a window simultaneously is confusing.
            if platform.system() != 'Darwin':
                if self.dashboard_gui:
                    self.dashboard_gui.show_dashboard()
            else:
                self.logger.debug("macOS: Single click handled by context menu")

    def start_periodic_device_check(self, interval_ms=60000):
        """Start periodic device checking using QTimer."""
        if self.device_check_timer is None:
            self.device_check_timer = QTimer()
            self.device_check_timer.timeout.connect(lambda: self._run_action(self.device_manager.check_devices, "Periodic Device Check")())
            self.device_check_timer.start(interval_ms)  # Default 60 seconds
            self.logger.info(f"Started periodic device check every {interval_ms} ms")
            self.notification_service.notify(
                "Auto-Check", 
                f"Started periodic device check every {interval_ms//1000} seconds", 
                "info"
            )
        elif not self.device_check_timer.isActive():
            self.device_check_timer.start(interval_ms)

    def stop_periodic_device_check(self):
        """Stop periodic device checking."""
        if self.device_check_timer and self.device_check_timer.isActive():
            self.device_check_timer.stop()
            self.logger.info("Stopped periodic device check")
            self.notification_service.notify(
                "Auto-Check", 
                "Stopped periodic device check", 
                "info"
            )

    def start_periodic_data_sync(self, interval_ms=300000):
        """Start periodic data synchronization using QTimer."""
        if self.data_sync_timer is None:
            self.data_sync_timer = QTimer()
            self.data_sync_timer.timeout.connect(lambda: self._run_action(self.api_sync.sync_data, "Periodic Data Sync")())
            self.data_sync_timer.start(interval_ms)  # Default 5 minutes
            self.logger.info(f"Started periodic data sync every {interval_ms} ms")
            self.notification_service.notify(
                "Auto-Sync", 
                f"Started periodic data sync every {interval_ms//60000} minutes", 
                "info"
            )
        elif not self.data_sync_timer.isActive():
            self.data_sync_timer.start(interval_ms)

    def stop_periodic_data_sync(self):
        """Stop periodic data synchronization."""
        if self.data_sync_timer and self.data_sync_timer.isActive():
            self.data_sync_timer.stop()
            self.logger.info("Stopped periodic data sync")
            self.notification_service.notify(
                "Auto-Sync", 
                "Stopped periodic data sync", 
                "info"
            )

    def run(self) -> None:
        """Run the system tray icon."""
        if self.tray_icon:
            self.tray_icon.show()
        elif not self.is_tray_supported:
            # On platforms where tray is not supported, show a message and keep the dashboard open
            self.logger.info("System tray not available - running in dashboard mode")
            # The dashboard is already shown in the main app run method

    def stop(self) -> None:
        """Stop the system tray icon and clean up resources."""
        # Stop timers
        self.stop_periodic_device_check()
        self.stop_periodic_data_sync()
        
        # Clean up timer objects
        if self.device_check_timer:
            self.device_check_timer.deleteLater()
            self.device_check_timer = None
            
        if self.data_sync_timer:
            self.data_sync_timer.deleteLater()
            self.data_sync_timer = None
        
        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()
            self.logger.info("System tray stopped")

    def cleanup(self):
        """Clean up resources."""
        self.stop()
        self.logger.info("SystemTray resources cleaned up")