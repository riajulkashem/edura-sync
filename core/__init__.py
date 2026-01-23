"""
Core module for the EduraSync application.
Contains shared utilities, constants, exceptions, and configuration.
"""

from .exceptions import (
    EduraSyncError,
    DatabaseError,
    ConfigurationError,
    ValidationError,
    GUIError,
    DeviceError,
    ConnectionError,
    APIError,
    AuthenticationError,
    APICallError,
    NotificationError,
    SchedulerError,
    handle_exceptions,
)

__all__ = [
    "EduraSyncError",
    "DatabaseError",
    "ConfigurationError",
    "ValidationError",
    "GUIError",
    "DeviceError",
    "ConnectionError",
    "APIError",
    "AuthenticationError",
    "APICallError",
    "NotificationError",
    "SchedulerError",
    "handle_exceptions",
]