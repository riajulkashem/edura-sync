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

# API endpoints
API_ENDPOINTS = {
    "TOKEN": "/api/token/",
    "INFO": "/api/info/",
    "SYNC": "/api/sync/",
    "ATTENDANCE": "/api/attendance/",
}

# UI configuration
UI_CONFIG = {
    "DASHBOARD_SIZE": "550x750",
    "DEFAULT_FONT": ("Helvetica", 12),
    "HEADER_FONT": ("Helvetica", 14, "bold"),
    "SMALL_FONT": ("Helvetica", 10),
    "DEFAULT_ICON_SIZE": (64, 64),
    "DEFAULT_ICON_COLOR": "blue",
}

# Status messages
STATUS_MESSAGES = {
    "SETTINGS_NOT_FOUND": "Settings not configured",
    "CONNECTION_SUCCESS": "Connection successful!",
    "CONNECTION_CHECKING": "Checking connection...",
    "SETTINGS_SAVED": "Settings saved successfully",
    "SETTINGS_RESET": "Settings reset. Enter new values and save.",
    "FILL_ALL_FIELDS": "Please fill all fields",
}

# Status colors
STATUS_COLORS = {
    "INFO": "blue",
    "SUCCESS": "green",
    "WARNING": "orange",
    "ERROR": "red",
    "NEUTRAL": "gray",
}

# Table names
TABLE_NAMES = {
    "DEVICES": "devices",
    "USERS": "users",
    "ATTENDANCE": "attendance_logs",
    "SETTINGS": "settings",
    "SCHEDULES": "schedules",
}

# Device settings
DEVICE_DEFAULTS = {
    "PORT": 4370,
    "PASSWORD": "0",
    "MODEL": "ZKTeco",
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
    "DB_INITIALIZED": "Database initialized",
    "SETTINGS_LOADED": "Settings loaded successfully",
    "DASHBOARD_DISPLAYED": "Dashboard displayed successfully",
    "SETTINGS_SAVED": "Settings saved successfully",
    "TRAY_STARTED": "System tray thread started",
    "APP_SHUTDOWN": "Application shutdown completed",
}

# Settings fields
DEFAULT_SETTING = {
    "CLOUD_API_URL": "http://localhost:8000",
    "USERNAME": "Username",
    "PASSWORD": "Password",
    "INSTITUTE_ID": "Institute ID",
}
