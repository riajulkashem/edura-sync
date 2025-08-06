# core/constants.py
"""
Application-wide constants for PrimeSync.
Centralizes all static values used throughout the application.
"""

# Application information
APP_NAME = "PrimeSync"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Attendance synchronization system"

# Developer information
DEVELOPER = {
    "NAME": "Riajul Kashem",
    "DESIGNATION": "Software Engineer",
    "FACEBOOK": "facebook.com/riajul.kashem",
    "GITHUB": "riajulkashem",
    "LINKEDIN": "riajulkashem",
}

# Database configuration
DEFAULT_DB_NAME = "primesync.db"
DB_PRAGMAS = {
    "journal_mode": "wal",  # Write-Ahead Logging for better concurrency
    "foreign_keys": 1,  # Enable foreign key support
    "cache_size": -1024 * 64,  # 64MB cache size
}

# API Endpoints for DRF backend
API_ENDPOINTS = {
    "TOKEN": "/api/token/",  # JWT token endpoint
    "REFRESH": "/api/token/refresh/",  # JWT refresh endpoint
    "INFO": "/api/institute/{institute_id}/info/",  # Institute info endpoint
    "ATTENDANCE": "/api/attendance/",  # Attendance data endpoint
    "USERS": "/api/attendance/device-users/",  # Users endpoint
    "DEVICES": "/api/devices/",  # Devices endpoint
}

# UI Configuration
UI_CONFIG = {
    "DASHBOARD_SIZE": "800x600",
    "DEFAULT_FONT": ("TkDefaultFont", 10),
    "HEADER_FONT": ("TkDefaultFont", 12, "bold"),
    "SMALL_FONT": ("TkDefaultFont", 8),
    "DEFAULT_PADDING": 10,
}

# Status messages
STATUS_MESSAGES = {
    "SETTINGS_NOT_FOUND": "Settings not configured",
    "CONNECTION_SUCCESS": "Connection successful!",
    "CONNECTION_CHECKING": "Checking connection...",
    "SETTINGS_SAVED": "Settings saved successfully",
    "SETTINGS_RESET": "Settings form reset",
    "FILL_ALL_FIELDS": "Please fill in all required fields",
}

# Status colors
STATUS_COLORS = {
    "SUCCESS": "green",
    "ERROR": "red",
    "WARNING": "orange",
    "INFO": "blue",
}

# Table names
TABLE_NAMES = {
    "DEVICES": "devices",
    "USERS": "users",
    "ATTENDANCE": "attendance_logs",
    "SETTINGS": "settings",
}

# Device defaults
DEVICE_DEFAULTS = {
    "PORT": 4370,
    "PASSWORD": "",
    "STATUS": "Offline",
}

# Menu items
MENU_ITEMS = {
    "DEVICES_STATUS": "Devices Status",
    "SYNC_DATA": "Sync Data",
    "POST_CLOUD": "Post Cloud",
    "PULL_MACHINE": "Pull Machine",
    "DASHBOARD": "Dashboard",
    "SETTINGS": "Settings",
    "EXIT": "Exit",
    "QUIT": "Quit",
}

# Log messages
LOG_MESSAGES = {
    "DB_INITIALIZED": "Database initialized successfully",
    "SETTINGS_LOADED": "Settings loaded successfully",
    "DASHBOARD_DISPLAYED": "Dashboard displayed successfully",
    "SETTINGS_SAVED": "Settings saved successfully",
    "TRAY_STARTED": "System tray started",
    "APP_SHUTDOWN": "Application shutdown complete",
}

# Default settings
DEFAULT_SETTING = {
    "cloud_api_url": "",
    "username": "",
    "password": "",
    "institute_id": "",
    "in_time_process": None,
    "out_time_process": None,
    "created_at": None,
    "updated_at": None,
}
