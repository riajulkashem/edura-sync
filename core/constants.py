# core/constants.py
"""
Application-wide constants for EduraSync.
Centralizes all static values used throughout the application.
"""

# Application information
APP_NAME = "EduraSync"
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
DEFAULT_DB_NAME = "edurasync.db"
DB_PRAGMAS = {
    "journal_mode": "wal",  # Write-Ahead Logging for better concurrency
    "foreign_keys": 1,  # Enable foreign key support
    "cache_size": -1024 * 16,  # 16MB cache size
}

# Minimal pragmas for background/low-resource mode
DB_PRAGMAS_MINIMAL = {
    "journal_mode": "wal",
    "foreign_keys": 1,
    "cache_size": -1024 * 4,  # 4MB cache size
    "synchronous": "NORMAL",
    "temp_store": "MEMORY",
}

# API Endpoints for DRF backend
API_ENDPOINTS = {
    "ATTENDANCE": "/api/attendance/attendance-log/",  # Attendance data endpoint
    "USERS": "/api/attendance/fingerprint-device/users-list/",  # Users endpoint
    "TEST": "/api/attendance/fingerprint-device/test/"  # Test endpoint
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
    "DEVICES_STATUS": "Check Device Status",
    "SYNC_DATA": "Perform Full Sync",
    "POST_CLOUD": "Upload Attendance",
    "PULL_MACHINE": "Fetch New Logs",
    "DASHBOARD": "Open Dashboard",
    "SETTINGS": "App Settings",
    "EXIT": "Minimize to Tray",
    "QUIT": "Quit Application",
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
    "sync_id": "",
    "sync_time": None,
}