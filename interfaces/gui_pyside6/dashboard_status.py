# interfaces/gui_pyside6/dashboard_status.py
"""
Status manager for the EduraSync dashboard using PySide6.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PySide6.QtCore import Qt


class DashboardStatus:
    """Status manager for the EduraSync dashboard."""

    def __init__(self, dashboard_gui):
        self.dashboard_gui = dashboard_gui
        self.logger = logging.getLogger(__name__)
        self.status_widget = None
        self.status_label = None
        self.connection_status_label = None

    def show_status_log(self, message: str, level: str = "info"):
        """Show status log message."""
        # Create status label if it doesn't exist
        if not self.status_label and self.dashboard_gui.main_window:
            self._create_status_label()

        # Update status label
        if self.status_label:
            self.status_label.setText(message)
            
            # Set color based on level
            color_map = {
                "success": "green",
                "error": "red",
                "warning": "orange",
                "info": "blue"
            }
            color = color_map.get(level, "black")
            self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

            # Show the label
            self.status_label.show()

    def hide_status_log(self):
        """Hide status log."""
        if self.status_label:
            self.status_label.hide()

    def update_connection_status(self, message: str, status: str = "info"):
        """Update connection status."""
        self.show_status_log(message, status)

    def update_status_label(self, message, color="black"):
        """Update status label."""
        self.show_status_log(message, "info")
        if self.status_label:
            self.status_label.setStyleSheet(f"color: {color};")

    def _create_status_label(self):
        """Create status label in the main window."""
        if self.dashboard_gui.main_window:
            # Add status label to the main window
            self.status_label = QLabel()
            self.status_label.setWordWrap(True)
            self.status_label.hide()  # Hidden by default
            
            # Add to the main window's layout
            central_widget = self.dashboard_gui.main_window.centralWidget()
            if central_widget and central_widget.layout():
                central_widget.layout().addWidget(self.status_label)