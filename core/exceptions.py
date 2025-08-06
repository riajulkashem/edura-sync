# core/exceptions.py
"""
Custom exception classes for the PrimeSync application.
Provides specific error types for different subsystems to improve error handling.
"""


class PrimeSyncError(Exception):
    """Base exception class for PrimeSync application errors."""

    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ConfigurationError(PrimeSyncError):
    """Raised when configuration initialization or validation fails."""

    pass


class DatabaseError(PrimeSyncError):
    """Raised when database operations fail."""

    pass


class DeviceConnectionError(PrimeSyncError):
    """Raised when connecting to a ZKTeco device fails."""

    pass


class DeviceOperationError(PrimeSyncError):
    """Raised when device operations (read/write) fail."""

    pass


class APICallError(PrimeSyncError):
    """Raised when cloud API calls fail."""

    pass


class APIAuthenticationError(PrimeSyncError):
    """Raised when API authentication fails."""

    pass


class APINetworkError(PrimeSyncError):
    """Raised when network issues occur during API calls."""

    pass


class NotificationError(PrimeSyncError):
    """Raised when notification delivery fails."""

    pass


class SchedulerError(PrimeSyncError):
    """Raised when scheduler operations fail."""

    pass


class SecurityError(PrimeSyncError):
    """Raised when encryption or decryption operations fail."""

    pass


class ValidationError(PrimeSyncError):
    """Raised when input validation fails."""

    pass


class FileOperationError(PrimeSyncError):
    """Raised when file operations fail."""

    pass


class ThreadingError(PrimeSyncError):
    """Raised when threading operations fail."""

    pass


class GUIError(PrimeSyncError):
    """Raised when GUI operations fail."""

    pass


class DataSyncError(PrimeSyncError):
    """Raised when data synchronization operations fail."""

    pass


class UserManagementError(PrimeSyncError):
    """Raised when user management operations fail."""

    pass


class AttendanceProcessingError(PrimeSyncError):
    """Raised when attendance data processing fails."""

    pass
