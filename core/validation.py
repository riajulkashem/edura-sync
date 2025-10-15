# core/validation.py
"""
Input validation utilities for the PrimeSync application.
Provides validation functions for various data types and formats.
"""

import re
import ipaddress
from typing import Dict, Any
from datetime import time

from core.exceptions import ValidationError


class Validator:
    """Static validation methods for various data types."""

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """
        Validate IPv4 address format.

        Args:
            ip: IP address string to validate

        Returns:
            bool: True if valid IPv4 address

        Raises:
            ValidationError: If IP address is invalid
        """
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            raise ValidationError(f"Invalid IP address format: {ip}")

    @staticmethod
    def validate_port(port: int) -> bool:
        """
        Validate port number.

        Args:
            port: Port number to validate

        Returns:
            bool: True if valid port number

        Raises:
            ValidationError: If port number is invalid
        """
        if not isinstance(port, int):
            raise ValidationError("Port must be an integer")

        if port < 1 or port > 65535:
            raise ValidationError(f"Port must be between 1 and 65535, got: {port}")

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
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError("URL cannot be empty")

        # Basic URL validation pattern
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            raise ValidationError(f"Invalid URL format: {url}")

        return True

    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Validate username format.

        Args:
            username: Username string to validate

        Returns:
            bool: True if valid username

        Raises:
            ValidationError: If username is invalid
        """
        if not username:
            raise ValidationError("Username cannot be empty")

        if len(username) < 3 or len(username) > 50:
            raise ValidationError("Username must be between 3 and 50 characters")

        # Allow alphanumeric characters, underscores, and hyphens
        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            raise ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )

        return True

    @staticmethod
    def validate_password(password: str) -> bool:
        """
        Validate password strength.

        Args:
            password: Password string to validate

        Returns:
            bool: True if valid password

        Raises:
            ValidationError: If password is invalid
        """
        if not password:
            raise ValidationError("Password cannot be empty")

        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")

        return True

    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        """
        Validate time format (HH:MM).

        Args:
            time_str: Time string to validate

        Returns:
            bool: True if valid time format

        Raises:
            ValidationError: If time format is invalid
        """
        if not time_str:
            return True  # Empty time is allowed

        try:
            time.fromisoformat(time_str)
            return True
        except ValueError:
            raise ValidationError(f"Invalid time format: {time_str}. Use HH:MM format")

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
            raise ValidationError("Device model cannot exceed 50 characters")

        # Allow alphanumeric characters, spaces, and common symbols
        if not re.match(r"^[a-zA-Z0-9\s\-_\.]+$", model):
            raise ValidationError("Device model contains invalid characters")

        return True

    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """
        Validate user ID format.

        Args:
            user_id: User ID string to validate

        Returns:
            bool: True if valid user ID
        """
        if not user_id:
            raise ValidationError("User ID cannot be empty")

        return True


class SettingsValidator:
    """Validator for application settings."""

    @staticmethod
    def validate_api_settings(settings: Dict[str, Any]) -> bool:
        """
        Validate API settings.

        Args:
            settings: Dictionary containing API settings

        Returns:
            bool: True if all settings are valid

        Raises:
            ValidationError: If any setting is invalid
        """
        errors = []

        # Validate cloud API URL
        if "cloud_api_url" in settings:
            try:
                Validator.validate_url(settings["cloud_api_url"])
            except ValidationError as e:
                errors.append(f"Cloud API URL: {e.message}")

        # Validate time settings
        if "in_time_process" in settings and settings["in_time_process"]:
            try:
                Validator.validate_time_format(str(settings["in_time_process"]))
            except ValidationError as e:
                errors.append(f"In Time Process: {e.message}")

        if "out_time_process" in settings and settings["out_time_process"]:
            try:
                Validator.validate_time_format(str(settings["out_time_process"]))
            except ValidationError as e:
                errors.append(f"Out Time Process: {e.message}")

        if errors:
            raise ValidationError("; ".join(errors))

        return True


class DeviceValidator:
    """Validator for device configuration."""

    @staticmethod
    def validate_device_settings(settings: Dict[str, Any]) -> bool:
        """
        Validate device settings.

        Args:
            settings: Dictionary containing device settings

        Returns:
            bool: True if all settings are valid

        Raises:
            ValidationError: If any setting is invalid
        """
        errors = []

        # Validate IP address
        if "ip_address" in settings:
            try:
                Validator.validate_ip_address(settings["ip_address"])
            except ValidationError as e:
                errors.append(f"IP Address: {e.message}")

        # Validate port
        if "port" in settings:
            try:
                Validator.validate_port(settings["port"])
            except ValidationError as e:
                errors.append(f"Port: {e.message}")

        # Validate device model
        if "device_model" in settings:
            try:
                Validator.validate_device_model(settings["device_model"])
            except ValidationError as e:
                errors.append(f"Device Model: {e.message}")

        if errors:
            raise ValidationError("; ".join(errors))

        return True
