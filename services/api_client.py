# services/api_client.py
"""
Main API client for PrimeSync application.
Coordinates API authentication and synchronization operations.
"""

import logging
from typing import Optional

from core.security import SecurityManager
from interfaces.database.repository import (
    AttendanceRepository, 
    SettingsRepository, 
    UserRepository, 
    DeviceRepository
)
from services.device_manager import DeviceManager
from services.api_auth import JWTTokenManager, APIAuthentication
from services.api_sync import APISync


class APIClient:
    """Main API client that coordinates authentication and synchronization."""

    def __init__(
        self,
        security: SecurityManager,
        notification_service,
        settings_repo: SettingsRepository,
        attendance_repo: AttendanceRepository,
        user_repo: UserRepository,
        device_repo: DeviceRepository,
        device_manager: DeviceManager,
    ):
        """Initialize the API client with required dependencies."""
        self.logger = logging.getLogger(__name__)
        self.security = security
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.attendance_repo = attendance_repo
        self.user_repo = user_repo
        self.device_repo = device_repo
        self.device_manager = device_manager

        # Initialize JWT token manager
        self.token_manager = JWTTokenManager(security)
        
        # Initialize authentication manager
        self.auth_manager = APIAuthentication(self.token_manager)
        
        # Initialize sync manager
        self.sync_manager = APISync(
            self.auth_manager,
            notification_service,
            settings_repo,
            attendance_repo,
            user_repo,
            device_repo,
            device_manager
        )
        
        # Pass security manager to sync manager for password decryption
        self.sync_manager.security_manager = security

        # Load initial settings
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from repository."""
        try:
            self.sync_manager.load_settings()
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")

    def update_settings(self) -> None:
        """Update settings from repository."""
        try:
            self.sync_manager.load_settings()
            self.logger.info("API client settings updated")
        except Exception as e:
            self.logger.error(f"Failed to update settings: {e}")

    def test_connection(self, url: str, username: str, password: str, sync_id: str) -> bool:
        """
        Test connection to the cloud API using desktop login.
        
        Args:
            url: Base API URL
            username: Username for authentication
            password: Password for authentication
            sync_id: Institute sync ID for testing
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        return self.sync_manager.test_connection(url, username, password, sync_id)

    def post_to_cloud(self) -> None:
        """Post attendance data to the cloud API."""
        self.sync_manager.post_to_cloud()

    def sync_data(self) -> bool:
        """
        Synchronize data with the cloud API.
        
        Returns:
            bool: True if sync was successful, False otherwise
        """
        return self.sync_manager.sync_data()

    def sync_users(self) -> bool:
        """
        Synchronize users and devices from the cloud API.
        
        Returns:
            bool: True if sync was successful, False otherwise
        """
        return self.sync_manager.sync_users()

    def get_token_manager(self) -> JWTTokenManager:
        """Get the JWT token manager."""
        return self.token_manager

    def get_auth_manager(self) -> APIAuthentication:
        """Get the authentication manager."""
        return self.auth_manager

    def get_sync_manager(self) -> APISync:
        """Get the synchronization manager."""
        return self.sync_manager
