# core/validation.py
"""
Input validation utilities for the EduraSync application.
Provides validation functions for user inputs, URLs, IP addresses, and other data.
"""

import re
from typing import Dict, Any
from urllib.parse import urlparse
from core.exceptions import ValidationError


class Validator:
    """Utility class for data validation."""

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """
        Validate IPv4 address format.
        
        Args:
            ip: IP address string to validate
            
        Returns:
            bool: True if valid IPv4 address
            
        Raises:
            ValidationError: If IP address format is invalid
        """
        if not ip:
            raise ValidationError("IP address cannot be empty")

        # IPv4 pattern
        pattern = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        if not re.match(pattern, ip):
            raise ValidationError(f"Invalid IP address format: {ip}")
        return True

    @staticmethod
    def validate_port(port: int) -> bool:
        """
        Validate port number range.
        
        Args:
            port: Port number to validate
            
        Returns:
            bool: True if valid port number
            
        Raises:
            ValidationError: If port number is out of range
        """
        if not isinstance(port, int):
            raise ValidationError("Port must be an integer")
        if not (1 <= port <= 65535):
            raise ValidationError(f"Port number {port} out of valid range (1-65535)")
        return True

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL string to validate
            
        Returns:
            bool: True if valid URL
            
        Raises:
            ValidationError: If URL format is invalid
        """
        if not url:
            raise ValidationError("URL cannot be empty")

        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValidationError(f"Invalid URL format: {url}")
        except Exception:
            raise ValidationError(f"Invalid URL format: {url}")
        return True

    @staticmethod
    def validate_device_model(model: str) -> bool:
        """
        Validate device model name.
        
        Args:
            model: Device model string to validate
            
        Returns:
            bool: True if valid device model
            
        Raises:
            ValidationError: If device model is invalid
        """
        if not model:
            raise ValidationError("Device model cannot be empty")
        if len(model) > 50:
            raise ValidationError("Device model name too long (max 50 characters)")
        return True

    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """
        Validate user ID format.
        
        Args:
            user_id: User ID string to validate
            
        Returns:
            bool: True if valid user ID
            
        Raises:
            ValidationError: If user ID is invalid
        """
        if not user_id:
            raise ValidationError("User ID cannot be empty")
        if len(user_id) > 50:
            raise ValidationError("User ID too long (max 50 characters)")
        return True


class SettingsValidator:
    """Validator for application settings."""

    @staticmethod
    def validate_api_settings(settings: Dict[str, Any]) -> bool:
        """
        Validate API settings.
        
        Args:
            settings: Dictionary of API settings
            
        Returns:
            bool: True if settings are valid
            
        Raises:
            ValidationError: If settings are invalid
        """
        if not settings.get('cloud_api_url'):
            raise ValidationError("Cloud API URL is required")
        
        if not settings.get('sync_id'):
            raise ValidationError("Sync ID is required")
            
        # Validate URL format
        Validator.validate_url(settings['cloud_api_url'])
        
        return True