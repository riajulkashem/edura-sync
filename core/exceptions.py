# core/exceptions.py
"""
Custom exceptions for the EduraSync application.
Provides a hierarchy of application-specific exceptions for consistent error handling.
"""

import functools
import logging


class EduraSyncError(Exception):
    """Base exception for all EduraSync application errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class DatabaseError(EduraSyncError):
    """Raised when database operations fail."""
    pass


class ConfigurationError(EduraSyncError):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(EduraSyncError):
    """Raised when data validation fails."""
    pass


class GUIError(EduraSyncError):
    """Raised when GUI operations fail."""
    pass


class DeviceError(EduraSyncError):
    """Raised when device operations fail."""
    pass


class ConnectionError(DeviceError):
    """Raised when device connection fails."""
    pass


class APIError(EduraSyncError):
    """Base class for API-related errors."""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    pass


class APICallError(APIError):
    """Raised when API calls fail."""
    pass


class NotificationError(EduraSyncError):
    """Raised when notification operations fail."""
    pass


class SchedulerError(EduraSyncError):
    """Raised when scheduler operations fail."""
    pass


def handle_exceptions(func):
    """
    Decorator to handle exceptions consistently.
    Logs the exception and re-raises as appropriate EduraSyncError.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EduraSyncError:
            # Re-raise EduraSyncErrors as they are already properly formatted
            raise
        except Exception as e:
            # Log unexpected errors and wrap them in EduraSyncError
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise EduraSyncError(f"Unexpected error in {func.__name__}: {str(e)}")
    return wrapper