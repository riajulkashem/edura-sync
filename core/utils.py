# core/utils.py
"""
Utility functions for common operations and patterns.
"""

import logging
from typing import Callable, Any, Optional
from functools import wraps

from core.exceptions import DatabaseError


def handle_db_errors(operation_name: str, logger: logging.Logger = None):
    """
    Decorator to handle common database errors in a consistent way.
    
    Args:
        operation_name: Name of the operation for logging
        logger: Logger instance to use (optional)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"Error {operation_name}: {e}"
                if logger:
                    logger.error(error_msg)
                raise DatabaseError(error_msg)
        return wrapper
    return decorator


def safe_db_operation(operation_name: str, operation_func: Callable, *args, **kwargs) -> Any:
    """
    Safely execute a database operation with consistent error handling.
    
    Args:
        operation_name: Name of the operation for logging
        operation_func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the operation
        
    Raises:
        DatabaseError: If the operation fails
    """
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        error_msg = f"Error {operation_name}: {e}"
        logging.getLogger(__name__).error(error_msg)
        raise DatabaseError(error_msg)


def get_nested_attr(obj: Any, attr_path: str, default: Any = None) -> Any:
    """
    Get a nested attribute from an object using dot notation.
    
    Args:
        obj: Object to get attribute from
        attr_path: Dot-separated attribute path (e.g., 'user.profile.name')
        default: Default value if attribute is not found
        
    Returns:
        Attribute value or default
    """
    try:
        attrs = attr_path.split('.')
        for attr in attrs:
            obj = getattr(obj, attr)
        return obj
    except (AttributeError, TypeError):
        return default


def format_iso_datetime(dt) -> Optional[str]:
    """
    Format a datetime object as ISO string.
    
    Args:
        dt: Datetime object to format
        
    Returns:
        ISO formatted string or None if dt is None
    """
    if dt:
        return dt.isoformat()
    return None