# interfaces/gui/__init__.py
"""
GUI module for the PrimeSync application.
Contains components for dashboard, settings, and system tray interfaces.
"""

from .dashboard import DashboardGUI
from .tray import SystemTray

__all__ = [
    "DashboardGUI",
    "SystemTray",
]
