# core/exceptions.py
"""
Custom exception classes for the PrimeSync application.
Provides specific error types for different subsystems to improve error handling.
"""


class PrimeSyncError(Exception):
    """Base exception class for PrimeSync application errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ConfigurationError(PrimeSyncError):
    """Raised when configuration initialization or validation fails."""

    pass


class DatabaseError(PrimeSyncError):
    """Raised when database operations fail."""

    pass


class DeviceConnectionError(PrimeSyncError):
    """Raised when connecting to a ZKTeco device fails."""

    pass


class APICallError(PrimeSyncError):
    """Raised when cloud API calls fail."""

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
