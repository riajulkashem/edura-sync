# interfaces/gui/form_manager.py
"""
Form management component for handling form fields, validation, and data management.
Provides common patterns for form handling across the application.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from tkinter import ttk

from core.exceptions import ValidationError, ConfigurationError
from interfaces.gui.ui_utils import (
    create_label,
    create_entry,
    get_form_values,
    validate_required_fields,
)


class FormManager:
    """
    Manages form fields, validation, and data handling.
    Provides common patterns for form management.
    """

    def __init__(self, parent=None, notification_service=None):
        """
        Initialize form manager.
        
        Args:
            parent: Parent widget for form components
            notification_service: Service for user notifications
        """
        self.parent = parent
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
        
        # Form state
        self.form_fields = {}
        self.field_configs = {}
        self.validators = {}
        self.default_values = {}
        
        # Form metadata
        self.form_title = ""
        self.required_fields = []

    def add_field(self, name: str, label: str, field_type: str = "entry", 
                  required: bool = False, default: Any = None, 
                  validator: Optional[Callable] = None, **kwargs) -> None:
        """
        Add a form field with configuration.
        
        Args:
            name: Field name
            label: Field label text
            field_type: Type of field (entry, text, combobox, etc.)
            required: Whether field is required
            default: Default value for field
            validator: Custom validation function
            **kwargs: Additional field configuration
        """
        self.field_configs[name] = {
            'label': label,
            'type': field_type,
            'required': required,
            'default': default,
            'kwargs': kwargs
        }
        
        if required:
            self.required_fields.append(name)
            
        if default is not None:
            self.default_values[name] = default
            
        if validator:
            self.validators[name] = validator
            
        self.logger.debug(f"Added field: {name} ({field_type})")

    def create_form(self, parent=None) -> ttk.Frame:
        """
        Create the form with all configured fields.
        
        Args:
            parent: Parent widget (uses self.parent if not specified)
            
        Returns:
            Frame containing the form
        """
        try:
            parent = parent or self.parent
            if not parent:
                raise ConfigurationError("No parent widget specified")
                
            form_frame = ttk.Frame(parent)
            form_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Create form title if specified
            if self.form_title:
                title_label = create_label(form_frame, text=self.form_title, font=("TkDefaultFont", 12, "bold"))
                title_label.pack(pady=(0, 10))
            
            # Create fields
            for i, (name, config) in enumerate(self.field_configs.items()):
                self._create_field_widget(form_frame, name, config, i)
                
            self.logger.info(f"Created form with {len(self.field_configs)} fields")
            return form_frame
            
        except Exception as e:
            self.logger.error(f"Failed to create form: {e}")
            raise ConfigurationError(f"Form creation failed: {str(e)}")

    def _create_field_widget(self, parent: ttk.Frame, name: str, config: Dict, row: int) -> None:
        """
        Create a single field widget.
        
        Args:
            parent: Parent frame
            name: Field name
            config: Field configuration
            row: Row number for layout
        """
        try:
            # Create label
            label = create_label(parent, text=config['label'])
            label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)
            
            # Create field widget based on type
            field_type = config['type']
            kwargs = config['kwargs']
            
            if field_type == "entry":
                widget = create_entry(parent, **kwargs)
            elif field_type == "text":
                widget = ttk.Text(parent, **kwargs)
            elif field_type == "combobox":
                widget = ttk.Combobox(parent, **kwargs)
            elif field_type == "checkbutton":
                widget = ttk.Checkbutton(parent, **kwargs)
            else:
                raise ValueError(f"Unsupported field type: {field_type}")
                
            widget.grid(row=row, column=1, sticky="ew", padx=(0, 0), pady=2)
            
            # Set default value
            if name in self.default_values:
                default_value = self.default_values[name]
                if hasattr(widget, 'insert'):
                    widget.insert(0, str(default_value))
                elif hasattr(widget, 'set'):
                    widget.set(default_value)
                    
            # Store widget reference
            self.form_fields[name] = widget
            
        except Exception as e:
            self.logger.error(f"Failed to create field {name}: {e}")
            raise ConfigurationError(f"Field creation failed: {str(e)}")

    def get_values(self) -> Dict[str, str]:
        """
        Get all form field values.
        
        Returns:
            Dictionary of field names and values
        """
        return get_form_values(self.form_fields)

    def set_values(self, values: Dict[str, Any]) -> None:
        """
        Set form field values.
        
        Args:
            values: Dictionary of field names and values
        """
        try:
            for name, value in values.items():
                if name in self.form_fields:
                    widget = self.form_fields[name]
                    if hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                        widget.delete(0, 'end')
                        widget.insert(0, str(value))
                    elif hasattr(widget, 'set'):
                        widget.set(value)
                    elif hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                        widget.delete('1.0', 'end')
                        widget.insert('1.0', str(value))
                        
            self.logger.debug(f"Set values for {len(values)} fields")
            
        except Exception as e:
            self.logger.error(f"Failed to set form values: {e}")
            raise ConfigurationError(f"Failed to set form values: {str(e)}")

    def clear_form(self) -> None:
        """Clear all form fields."""
        try:
            for widget in self.form_fields.values():
                if hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                    widget.delete(0, 'end')
                elif hasattr(widget, 'set'):
                    widget.set('')
                elif hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                    widget.delete('1.0', 'end')
                    
            self.logger.debug("Form cleared")
            
        except Exception as e:
            self.logger.error(f"Failed to clear form: {e}")

    def validate_form(self, required_fields: Optional[List[str]] = None) -> bool:
        """
        Validate form fields.
        
        Args:
            required_fields: List of required fields (uses self.required_fields if not specified)
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            required = required_fields or self.required_fields
            
            # Validate required fields
            if not validate_required_fields(
                self.form_fields, 
                required, 
                notify=self.notification_service.notify if self.notification_service else None
            ):
                return False
                
            # Run custom validators
            for name, validator in self.validators.items():
                if name in self.form_fields:
                    widget = self.form_fields[name]
                    value = widget.get() if hasattr(widget, 'get') else None
                    
                    try:
                        if not validator(value):
                            error_msg = f"Validation failed for field: {name}"
                            self.logger.warning(error_msg)
                            if self.notification_service:
                                self.notification_service.notify("Validation Error", error_msg, "error")
                            return False
                    except Exception as e:
                        error_msg = f"Validator error for field {name}: {e}"
                        self.logger.error(error_msg)
                        if self.notification_service:
                            self.notification_service.notify("Validation Error", error_msg, "error")
                        return False
                        
            self.logger.debug("Form validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Form validation error: {e}")
            return False

    def get_field_value(self, name: str) -> Optional[str]:
        """
        Get value of a specific field.
        
        Args:
            name: Field name
            
        Returns:
            Field value or None if not found
        """
        try:
            if name in self.form_fields:
                widget = self.form_fields[name]
                if hasattr(widget, 'get'):
                    return widget.get()
            return None
        except Exception as e:
            self.logger.error(f"Failed to get field value for {name}: {e}")
            return None

    def set_field_value(self, name: str, value: Any) -> bool:
        """
        Set value of a specific field.
        
        Args:
            name: Field name
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if name in self.form_fields:
                widget = self.form_fields[name]
                if hasattr(widget, 'delete') and hasattr(widget, 'insert'):
                    widget.delete(0, 'end')
                    widget.insert(0, str(value))
                elif hasattr(widget, 'set'):
                    widget.set(value)
                else:
                    return False
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to set field value for {name}: {e}")
            return False

    def enable_field(self, name: str) -> bool:
        """
        Enable a form field.
        
        Args:
            name: Field name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if name in self.form_fields:
                self.form_fields[name].configure(state="normal")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to enable field {name}: {e}")
            return False

    def disable_field(self, name: str) -> bool:
        """
        Disable a form field.
        
        Args:
            name: Field name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if name in self.form_fields:
                self.form_fields[name].configure(state="disabled")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to disable field {name}: {e}")
            return False

    def get_form_status(self) -> Dict[str, Any]:
        """
        Get form status information.
        
        Returns:
            Dictionary with form status
        """
        return {
            'field_count': len(self.form_fields),
            'required_fields': len(self.required_fields),
            'validators': len(self.validators),
            'default_values': len(self.default_values)
        } 