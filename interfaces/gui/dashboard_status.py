# interfaces/gui/dashboard_status.py
"""
Dashboard status logging component.
Handles status log display and management.
"""

import logging
import threading
import time
from tkinter import ttk

from core.constants import UI_CONFIG
from interfaces.gui.ui_utils import (
    create_label,
    create_text,
    create_scrollbar,
)


class DashboardStatus:
    """Manages dashboard status logging functionality."""

    def __init__(self, dashboard_gui):
        """Initialize status manager with dashboard reference."""
        self.dashboard = dashboard_gui
        self.logger = logging.getLogger(__name__)
        
        # Status logging components
        self.status_log_frame = None
        self.status_log_text = None
        self.status_log_visible = False
        self.status_log_timer = None

    def show_status_log(self, message: str, level: str = "info"):
        """
        Show a status log message in the dashboard.
        
        Args:
            message: The log message to display
            level: Log level (info, success, warning, error)
        """
        try:
            if not self.status_log_frame:
                self._create_status_log_area()

            # Get color for log level
            color = self.dashboard.status_colors.get(level, "black")
            
            # Add timestamp
            timestamp = time.strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}\n"
            
            # Insert message at the beginning
            self.status_log_text.insert("1.0", formatted_message)
            
            # Apply color to the new message
            start = "1.0"
            end = f"1.{len(formatted_message)}"
            self.status_log_text.tag_add(level, start, end)
            self.status_log_text.tag_config(level, foreground=color)
            
            # Show status log area
            if not self.status_log_visible:
                self.status_log_frame.pack(fill="x", padx=10, pady=5)
                self.status_log_visible = True
            
            # Auto-hide after 5 seconds
            if self.status_log_timer:
                self.status_log_timer.cancel()
            
            self.status_log_timer = threading.Timer(5.0, self.hide_status_log)
            self.status_log_timer.start()
            
        except Exception as e:
            self.logger.error(f"Error showing status log: {e}")

    def hide_status_log(self):
        """Hide the status log area."""
        try:
            if self.status_log_frame and self.status_log_visible:
                self.status_log_frame.pack_forget()
                self.status_log_visible = False
                
            if self.status_log_timer:
                self.status_log_timer.cancel()
                self.status_log_timer = None
                
        except Exception as e:
            self.logger.error(f"Error hiding status log: {e}")

    def _create_status_log_area(self):
        """Create the status log display area."""
        try:
            # Create status log frame
            self.status_log_frame = ttk.LabelFrame(
                self.dashboard.dashboard_win, text="Status Log", padding=5
            )
            
            # Create text widget with scrollbar
            text_frame = ttk.Frame(self.status_log_frame)
            text_frame.pack(fill="both", expand=True)
            
            self.status_log_text = create_text(
                text_frame, 
                height=4, 
                width=60,
                wrap="word",
                state="normal"
            )
            
            scrollbar = create_scrollbar(text_frame, orient="vertical")
            
            # Configure scrollbar
            self.status_log_text.configure(yscrollcommand=scrollbar.set)
            scrollbar.configure(command=self.status_log_text.yview)
            
            # Pack widgets
            self.status_log_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Configure text widget
            self.status_log_text.configure(
                font=("Consolas", 9),
                background="#f0f0f0",
                foreground="black"
            )
            
        except Exception as e:
            self.logger.error(f"Error creating status log area: {e}")
            raise

    def update_status_label(self, message, color="black"):
        """Update the main status label."""
        try:
            if self.dashboard.status_label:
                self.dashboard.status_label.configure(text=message, foreground=color)
        except Exception as e:
            self.logger.error(f"Error updating status label: {e}")

    def update_connection_status(self, message: str, status: str = "info"):
        """Update the connection status label."""
        try:
            if self.dashboard.connection_status_label:
                color = self.dashboard.status_colors.get(status, "black")
                self.dashboard.connection_status_label.configure(
                    text=message, 
                    foreground=color
                )
        except Exception as e:
            self.logger.error(f"Error updating connection status: {e}") 