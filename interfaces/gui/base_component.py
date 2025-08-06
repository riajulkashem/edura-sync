# interfaces/gui/base_component.py
"""
Base component class for GUI components.
Provides common initialization and error handling patterns.
"""

import logging
from typing import Optional, Dict, Any
from tkinter import ttk

from core.exceptions import GUIError, ConfigurationError


class BaseComponent:
    """
    Base class for GUI components with common patterns.
    Provides error handling, logging, and initialization utilities.
    """

    def __init__(self, parent=None, logger_name: Optional[str] = None):
        """
        Initialize base component.
        
        Args:
            parent: Parent component or widget
            logger_name: Custom logger name (defaults to class name)
        """
        self.parent = parent
        self.logger = logging.getLogger(logger_name or self.__class__.__name__)
        
        # Component state
        self._initialized = False
        self._widgets = {}
        self._callbacks = {}
        
        # Error handling
        self._error_handlers = {}
        self._default_error_handler = self._default_error_handler

    def initialize(self, **kwargs) -> None:
        """
        Initialize the component with given parameters.
        
        Args:
            **kwargs: Initialization parameters
            
        Raises:
            ConfigurationError: If initialization fails
        """
        try:
            if self._initialized:
                self.logger.warning("Component already initialized")
                return
                
            self._setup_component(**kwargs)
            self._initialized = True
            self.logger.debug("Component initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize component: {e}")
            raise ConfigurationError(f"Component initialization failed: {str(e)}")

    def _setup_component(self, **kwargs) -> None:
        """
        Setup component-specific initialization.
        Override in subclasses.
        
        Args:
            **kwargs: Initialization parameters
        """
        pass

    def create_widget(self, widget_type: str, parent=None, **kwargs) -> Any:
        """
        Create a widget with error handling.
        
        Args:
            widget_type: Type of widget to create
            parent: Parent widget
            **kwargs: Widget configuration
            
        Returns:
            Created widget
            
        Raises:
            GUIError: If widget creation fails
        """
        try:
            parent = parent or self.parent
            if not parent:
                raise GUIError("No parent widget specified")
                
            widget = getattr(ttk, widget_type)(parent, **kwargs)
            self._widgets[widget_type] = widget
            return widget
            
        except Exception as e:
            self.logger.error(f"Failed to create {widget_type} widget: {e}")
            raise GUIError(f"Widget creation failed: {str(e)}")

    def register_callback(self, name: str, callback: callable) -> None:
        """
        Register a callback function.
        
        Args:
            name: Callback name
            callback: Callback function
        """
        self._callbacks[name] = callback
        self.logger.debug(f"Registered callback: {name}")

    def register_error_handler(self, error_type: type, handler: callable) -> None:
        """
        Register an error handler for specific exception types.
        
        Args:
            error_type: Exception type to handle
            handler: Error handler function
        """
        self._error_handlers[error_type] = handler
        self.logger.debug(f"Registered error handler for {error_type.__name__}")

    def handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle errors using registered handlers or default handler.
        
        Args:
            error: Exception to handle
            context: Context information for the error
        """
        try:
            # Try to find specific error handler
            error_type = type(error)
            if error_type in self._error_handlers:
                self._error_handlers[error_type](error, context)
            else:
                # Use default error handler
                self._default_error_handler(error, context)
                
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")

    def _default_error_handler(self, error: Exception, context: str = "") -> None:
        """
        Default error handler.
        
        Args:
            error: Exception to handle
            context: Context information for the error
        """
        self.logger.error(f"Error in {context}: {error}")
        # Could add notification or UI feedback here

    def safe_execute(self, func: callable, *args, context: str = "", **kwargs) -> Any:
        """
        Execute a function with error handling.
        
        Args:
            func: Function to execute
            *args: Function arguments
            context: Context for error reporting
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if error occurs
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_error(e, context)
            return None

    def get_widget(self, name: str) -> Optional[Any]:
        """
        Get a widget by name.
        
        Args:
            name: Widget name
            
        Returns:
            Widget or None if not found
        """
        return self._widgets.get(name)

    def get_callback(self, name: str) -> Optional[callable]:
        """
        Get a callback by name.
        
        Args:
            name: Callback name
            
        Returns:
            Callback function or None if not found
        """
        return self._callbacks.get(name)

    def cleanup(self) -> None:
        """
        Clean up component resources.
        Override in subclasses if needed.
        """
        try:
            # Clear widgets
            for widget in self._widgets.values():
                if hasattr(widget, 'destroy'):
                    widget.destroy()
            self._widgets.clear()
            
            # Clear callbacks
            self._callbacks.clear()
            
            # Clear error handlers
            self._error_handlers.clear()
            
            self._initialized = False
            self.logger.debug("Component cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def is_initialized(self) -> bool:
        """
        Check if component is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Get component status information.
        
        Returns:
            Dictionary with status information
        """
        return {
            'initialized': self._initialized,
            'widget_count': len(self._widgets),
            'callback_count': len(self._callbacks),
            'error_handler_count': len(self._error_handlers)
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        if exc_type:
            self.handle_error(exc_val, "context manager exit") 