# interfaces/gui_pyside6/dashboard.py
"""
Main dashboard GUI for the EduraSync application using PySide6.
Coordinates dashboard components and manages the main window.
"""

import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QTextEdit, QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon

from core.config import Config
from core.constants import APP_NAME
from core.operation_manager import OperationManager
from interfaces.database.repository import (
    AttendanceRepository,
)
from interfaces.gui_pyside6.dashboard_settings import DashboardSettings
from interfaces.gui_pyside6.dashboard_content import DashboardContent
from interfaces.gui_pyside6.dashboard_status import DashboardStatus
from interfaces.gui_pyside6.device_management import DeviceManagementWidget
from interfaces.gui_pyside6.gui_utils import GUIHelpers, ActionHandler, handle_gui_errors


class DashboardGUI:
    """Main GUI dashboard for the EduraSync application using PySide6."""

    def __init__(
        self,
        app,
        device_repo,
        user_repo,
        notification_service,
        settings_repo=None,
        api_sync=None,
    ):
        """Initialize the dashboard GUI with required components."""
        self.logger = logging.getLogger(__name__)
        self.app = app
        self.device_repo = device_repo
        self.user_repo = user_repo
        self.attendance_repo = AttendanceRepository()  # Add missing attendance repo
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.api_sync = api_sync
        self.device_manager = None

        # UI components
        self.main_window = None
        self.tab_widget = None
        self.status_bar = None

        # Initialize component managers
        self.settings_manager = DashboardSettings(self)
        self.content_manager = DashboardContent(self)
        self.status_manager = DashboardStatus(self)
        
        # Initialize action handler
        self.action_handler = ActionHandler(notification_service, self.status_manager)
        
        # Get operation manager instance
        self.operation_manager = OperationManager()
        
        # Timer for periodic updates
        self.refresh_timer = None

    def show_dashboard(self, first_run=False):
        """Show or update the main dashboard window."""
        # Create main window if it doesn't exist
        if self.main_window is None:
            self._create_main_window()
        # Show the window and bring it to front
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

        # Select settings tab on first run
        if first_run:
            self.tab_widget.setCurrentIndex(1)  # Settings tab

    def hide_dashboard(self):
        """Hide the dashboard window instead of destroying it."""
        if self.main_window:
            self.main_window.hide()

    def _create_main_window(self):
        """Create the main application window."""
        self.main_window = QMainWindow()
        self.main_window.setWindowTitle(f"{APP_NAME} Dashboard")
        self.main_window.resize(800, 600)

        # Set window icon
        self._set_window_icon()

        # Create central widget
        central_widget = QWidget()
        self.main_window.setCentralWidget(central_widget)

        # Create main layout
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_dashboard_tab()
        self._create_device_management_tab()
        self.settings_manager.create_settings_tab(self.tab_widget)
        self._create_credits_tab()

        # Connect tab change signal to refresh settings data if needed
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Create status bar
        self.status_bar = self.main_window.statusBar()
        self.status_bar.showMessage("Ready")

        # Add Quit button that minimizes to tray instead of exiting
        quit_button = QPushButton("Minimize to Tray")
        quit_button.clicked.connect(self._minimize_to_tray)
        main_layout.addWidget(quit_button, alignment=Qt.AlignCenter)

        # Connect window close event to hide instead of destroy
        self.main_window.closeEvent = self._on_window_close

    def _on_window_close(self, event):
        """Handle window close event by hiding instead of destroying."""
        event.ignore()  # Don't actually close the window
        self.hide_dashboard()  # Just hide it

    def _on_tab_changed(self, index):
        """Handle tab change events."""
        # Index 2 is typically Settings (Dashboard[0], Device[1], Settings[2])
        # But we check for the settings widget itself to be safe
        active_widget = self.tab_widget.widget(index)
        # Check if settings_manager's widget is active
        # We need a way to identify it or just refresh always on index matching
        if index == 2: # Settings tab
            self.settings_manager._update_device_list()

    def _minimize_to_tray(self):
        """Minimize the application to system tray."""
        self.hide_dashboard()
        # Show notification that app is still running
        self.notification_service.notify(
            "EduraSync",
            "Application minimized to system tray. Click the tray icon to restore.",
            "info"
        )

    def _set_window_icon(self):
        """Set the window icon."""
        try:
            icon_path = Config().ICON_PATH
            if icon_path and icon_path.exists():
                self.main_window.setWindowIcon(QIcon(QPixmap(str(icon_path))))
        except Exception as e:
            self.logger.warning(f"Failed to set window icon: {e}")

    @handle_gui_errors
    def _create_dashboard_tab(self):
        """Create the dashboard tab."""
        dashboard_widget = QWidget()
        layout = QVBoxLayout(dashboard_widget)

        # Create scroll area for dashboard content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Store reference to content widget for updates
        self.dashboard_content = scroll_content

        # Initial content update
        self.content_manager.update_dashboard_content(scroll_layout)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        self.tab_widget.addTab(dashboard_widget, "🏠 Dashboard")
        
    @handle_gui_errors
    def _create_device_management_tab(self):
        """Create the device management tab."""
        self.device_management_widget = DeviceManagementWidget()
        self.tab_widget.addTab(self.device_management_widget, "🔧 Device Management")

    @handle_gui_errors
    def _create_credits_tab(self):
        """Create the credits tab."""
        credits_widget = QWidget()
        layout = QVBoxLayout(credits_widget)

        # Add logo
        config = Config()
        logo_path = config.BASE_DIR / "assets" / "logo.png"
        if logo_path.exists():
            from PySide6.QtGui import QPixmap
            from PySide6.QtWidgets import QLabel
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            # Scale the logo to a reasonable size
            pixmap = pixmap.scaled(200, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)

        # Credits content
        credits_text = f"""
                {APP_NAME} - Attendance Management System

                Version: {Config().VERSION}
                Author: Softzenix Limited

                This application provides attendance management for ZKTeco devices
                with cloud synchronization capabilities.

                For support and updates, visit our website.

                Rupan Chakraborty
                Phone: +880 1912-884839
                Email: rupan@softzenix.com

                Riajul Kashem
                Phone: +880 1777824258
                Email: riajul@softzenix.com
                        """

        # Create text widget
        text_widget = QTextEdit()
        text_widget.setPlainText(credits_text)
        text_widget.setReadOnly(True)
        layout.addWidget(text_widget)

        # Create social links
        self._create_social_links(layout)

        self.tab_widget.addTab(credits_widget, "ℹ️ About")

    def _create_social_links(self, parent_layout):
        """Create social media links."""
        links = [
            ("Website", "https://edurabd.com"),
        ]
        GUIHelpers.create_social_links(parent_layout, links)

    # Action methods
    def _check_devices(self):
        """Check device connections."""
        self.action_handler.perform_action(
            lambda: self.device_manager.check_devices(), 
            "Checking device status...",
            self._refresh_dashboard
        )

    def _pull_data(self):
        """Pull data from devices."""
        self.action_handler.perform_action(
            lambda: self.device_manager.pull_data(), 
            "Fetching device logs...",
            self._refresh_dashboard
        )

    def _sync_users(self):
        """Sync users with cloud."""
        self.action_handler.perform_action(
            lambda: self.api_sync.sync_users(), 
            "Updating profiles...",
            self._refresh_dashboard
        )

    def _sync_to_cloud(self):
        """Sync data to cloud."""
        self.action_handler.perform_action(
            lambda: self.api_sync.post_to_cloud(), 
            "Uploading to cloud...",
            self._refresh_dashboard
        )

    def _refresh_dashboard(self):
        """Refresh dashboard data."""
        # Save resources if window is not visible
        if not self.main_window.isVisible():
            self.logger.debug("Dashboard hidden - skipping UI refresh")
            return

        # Refresh content in the dashboard tab
        if hasattr(self, 'dashboard_content') and self.dashboard_content:
            # Clear existing layout
            GUIHelpers.clear_layout(self.dashboard_content.layout())
            # Update content
            self.content_manager.update_dashboard_content(self.dashboard_content.layout())
        
        self.show_status_log("Dashboard refreshed", "info")

    def start_periodic_refresh(self, interval_ms=30000):
        """Start periodic dashboard refresh using QTimer."""
        if self.refresh_timer is None:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self._refresh_dashboard)
            self.refresh_timer.start(interval_ms)  # Default 30 seconds
            self.logger.info(f"Started periodic refresh every {interval_ms} ms")
        elif not self.refresh_timer.isActive():
            self.refresh_timer.start(interval_ms)

    def stop_periodic_refresh(self):
        """Stop periodic dashboard refresh."""
        if self.refresh_timer and self.refresh_timer.isActive():
            self.refresh_timer.stop()
            self.logger.info("Stopped periodic refresh")

    def set_device_manager(self, device_manager):
        """Set the device manager reference."""
        self.device_manager = device_manager

    # Delegate methods to component managers
    def show_status_log(self, message: str, level: str = "info"):
        """Show status log message."""
        self.status_manager.show_status_log(message, level)
        # Update status bar
        if self.status_bar:
            self.status_bar.showMessage(message)

    def hide_status_log(self):
        """Hide status log."""
        self.status_manager.hide_status_log()

    def _update_connection_status(self, message: str, status: str = "info"):
        """Update connection status."""
        self.status_manager.update_connection_status(message, status)

    def update_status_label(self, message, color="black"):
        """Update status label."""
        self.status_manager.update_status_label(message, color)

    def cleanup(self):
        """Clean up resources."""
        # Stop any timers
        self.stop_periodic_refresh()
        
        # Clean up timer object
        if self.refresh_timer:
            self.refresh_timer.deleteLater()
            self.refresh_timer = None
            
        # Clean up main window
        if self.main_window:
            self.main_window.deleteLater()
            self.main_window = None
            
        self.logger.info("DashboardGUI resources cleaned up")

    @handle_gui_errors
    def _flush_database(self):
        """Flush all database tables with Reset Key (Sync ID) verification."""
        from PySide6.QtWidgets import QMessageBox, QInputDialog, QLineEdit
        from interfaces.database.models import flush_database
        
        # Get actual Sync ID from settings
        settings = self.settings_repo.get_settings()
        actual_sync_id = settings.sync_id if settings else ""
        
        # 1. Verification of intent
        reply = QMessageBox.critical(
            self.main_window, "DANGEROUS: Flush Database",
            "This will delete ALL local devices, users, and attendance records forever.\n\n"
            "Are you absolutely sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 2. Reset Key verification
            key, ok = QInputDialog.getText(
                self.main_window, "SECURITY CHECK", 
                "Enter Sync ID as RESET KEY to authorize:", 
                QLineEdit.Password
            )
            
            if not ok or key != actual_sync_id:
                QMessageBox.warning(self.main_window, "Access Denied", "Incorrect Reset Key.")
                return

            if flush_database():
                self.notification_service.notify("Database", "All local data has been flushed.", "info")
                self._refresh_dashboard()
                # Also refresh device management if it exists
                if hasattr(self, 'device_management_widget'):
                    self.device_management_widget.load_devices()
            else:
                QMessageBox.warning(self.main_window, "Error", "Failed to flush database.")