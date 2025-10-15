# core/exceptions.py
"""
Custom exceptions for the PrimeSync application.
Provides a hierarchy of application-specific exceptions for better error handling.
"""

import logging


class PrimeSyncError(Exception):
    """Base exception for all PrimeSync application errors."""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
        # Log the error when it's created
        logging.getLogger(__name__).error(f"{self.__class__.__name__}: {message}")


class DatabaseError(PrimeSyncError):
    """Exception raised for database-related errors."""
    pass


class ConfigurationError(PrimeSyncError):
    """Exception raised for configuration-related errors."""
    pass


class ValidationError(PrimeSyncError):
    """Exception raised for data validation errors."""
    pass


class GUIError(PrimeSyncError):
    """Exception raised for GUI-related errors."""
    pass


class DeviceError(PrimeSyncError):
    """Base exception for device-related errors."""
    pass


class DeviceConnectionError(DeviceError):
    """Exception raised when device connection fails."""
    pass


class DeviceOperationError(DeviceError):
    """Exception raised when device operations fail."""
    pass


class APIError(PrimeSyncError):
    """Base exception for API-related errors."""
    pass


class APICallError(APIError):
    """Exception raised when API calls fail."""
    pass


class APIAuthenticationError(APIError):
    """Exception raised when API authentication fails."""
    pass


class APINetworkError(APIError):
    """Exception raised when network issues occur during API calls."""
    pass


class NotificationError(PrimeSyncError):
    """Exception raised for notification-related errors."""
    pass


class SchedulerError(PrimeSyncError):
    """Exception raised for scheduler-related errors."""
    pass


def handle_exception(func):
    """
    Decorator to handle exceptions in a consistent way.
    Logs the exception and re-raises as appropriate PrimeSyncError.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PrimeSyncError:
            # Re-raise PrimeSyncErrors as they are already properly formatted
            raise
        except Exception as e:
            # Log unexpected errors and wrap them in PrimeSyncError
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise PrimeSyncError(f"Unexpected error in {func.__name__}: {str(e)}")
    return wrapper