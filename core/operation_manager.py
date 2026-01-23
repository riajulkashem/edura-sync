# core/operation_manager.py
"""
Operation manager to prevent concurrent operations that cause crashes.
Implements thread-safe operation locking with GUI state callbacks.
"""

import logging
import threading
from typing import Callable, Optional
from functools import wraps


class OperationManager:
    """
    Singleton operation manager for thread-safe operation locking.
    Prevents concurrent operations that could cause application crashes.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize operation manager."""
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self.logger = logging.getLogger(__name__)
        self._operation_lock = threading.Lock()
        self._operation_in_progress = False
        self._current_operation = None
        self._state_callbacks = []

    def is_operation_in_progress(self) -> bool:
        """Check if any operation is currently in progress."""
        with self._operation_lock:
            return self._operation_in_progress

    def get_current_operation(self) -> Optional[str]:
        """Get the name of the current operation."""
        with self._operation_lock:
            return self._current_operation

    def register_state_callback(self, callback: Callable[[bool, Optional[str]], None]):
        """
        Register a callback for operation state changes.
        
        Args:
            callback: Function to call with (is_busy, operation_name) when state changes
        """
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)
            self.logger.debug(f"Registered state callback: {callback.__name__}")

    def unregister_state_callback(self, callback: Callable):
        """Unregister a state callback."""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)
            self.logger.debug(f"Unregistered state callback: {callback.__name__}")

    def _notify_state_change(self, is_busy: bool, operation_name: Optional[str] = None):
        """Notify all registered callbacks of state change."""
        for callback in self._state_callbacks:
            try:
                callback(is_busy, operation_name)
            except Exception as e:
                self.logger.error(f"Error in state callback {callback.__name__}: {e}")

    def acquire_operation_lock(self, operation_name: str) -> bool:
        """
        Acquire lock for an operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            bool: True if lock acquired, False if another operation is in progress
        """
        with self._operation_lock:
            if self._operation_in_progress:
                self.logger.warning(
                    f"Cannot start '{operation_name}': '{self._current_operation}' is in progress"
                )
                return False
            
            self._operation_in_progress = True
            self._current_operation = operation_name
            self.logger.info(f"Started operation: {operation_name}")
            self._notify_state_change(True, operation_name)
            return True

    def release_operation_lock(self, operation_name: str):
        """
        Release lock for an operation.
        
        Args:
            operation_name: Name of the operation
        """
        with self._operation_lock:
            if self._current_operation != operation_name:
                self.logger.warning(
                    f"Lock release mismatch: expected '{self._current_operation}', got '{operation_name}'"
                )
            
            self._operation_in_progress = False
            self._current_operation = None
            self.logger.info(f"Completed operation: {operation_name}")
            self._notify_state_change(False, None)


def operation_lock(operation_name: str):
    """
    Decorator to automatically manage operation locking.
    
    Args:
        operation_name: Name of the operation for logging
        
    Usage:
        @operation_lock("Pull Data")
        def pull_data(self):
            # operation code
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = OperationManager()
            
            # Try to acquire lock
            if not manager.acquire_operation_lock(operation_name):
                # Operation already in progress, skip this call
                logger = logging.getLogger(func.__module__)
                logger.warning(f"Skipping '{operation_name}' - another operation is in progress")
                return None
            
            try:
                # Execute the operation
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Re-raise exception after releasing lock
                logger = logging.getLogger(func.__module__)
                logger.error(f"Error in operation '{operation_name}': {e}", exc_info=True)
                raise
            finally:
                # Always release lock
                manager.release_operation_lock(operation_name)
        
        return wrapper
    return decorator
