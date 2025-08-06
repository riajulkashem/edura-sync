# services/api_sync.py
"""
API data synchronization operations.
Handles cloud data synchronization and database operations.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, List

from core.constants import API_ENDPOINTS
from core.exceptions import APICallError, APIAuthenticationError, APINetworkError
from interfaces.database.models import Device, User


class APISync:
    """Handles API data synchronization operations."""

    def __init__(self, auth_manager, notification_service, settings_repo, 
                 attendance_repo, user_repo, device_repo, device_manager):
        self.auth_manager = auth_manager
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.attendance_repo = attendance_repo
        self.user_repo = user_repo
        self.device_repo = device_repo
        self.device_manager = device_manager
        self.logger = logging.getLogger(__name__)
        
        # Settings
        self.cloud_api_url = ""
        self.username = ""
        self.password = ""
        self.institute_id = ""

    def load_settings(self) -> None:
        """Load settings from repository."""
        try:
            settings = self.settings_repo.get_settings()
            if settings:
                self.cloud_api_url = settings.cloud_api_url or ""
                self.username = settings.username or ""
                if settings.password:
                    # Note: This assumes security manager is available in the calling context
                    # In a real implementation, you'd pass the decrypted password
                    self.password = settings.password
                else:
                    self.password = ""
                self.institute_id = settings.institute_id or ""
            else:
                # Set default values if no settings exist
                self.cloud_api_url = ""
                self.username = ""
                self.password = ""
                self.institute_id = ""
        except Exception as e:
            self.logger.error(f"Failed to load settings: {e}")
            # Set default values on error
            self.cloud_api_url = ""
            self.username = ""
            self.password = ""
            self.institute_id = ""

    def test_connection(self, url: str, username: str, password: str, institute_id: str) -> bool:
        """
        Test connection to DRF backend with JWT authentication.
        
        Args:
            url: Base API URL
            username: Username for authentication
            password: Password for authentication
            institute_id: Institute ID for testing
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Authenticate and get JWT tokens
            token_data = self.auth_manager.authenticate_with_jwt(url, username, password)
            self.auth_manager.token_manager.set_tokens(
                token_data["access_token"],
                token_data["refresh_token"],
                int(token_data["expires_in"]) if "expires_in" in token_data else None,
            )
            
            # Test API access with institute info endpoint
            test_url = f"{url.rstrip('/')}/api/institute/{institute_id}/info/"
            response = self.auth_manager.make_authenticated_request("GET", test_url)
            
            if response.status_code == 200:
                institute_data = self.auth_manager.parse_response(response)
                self.logger.info(f"Successfully connected to institute: {institute_data.get('name', 'Unknown')}")
                return True
            else:
                self.logger.error(f"API access test failed: {response.status_code}")
                return False
                
        except (APIAuthenticationError, APINetworkError, APICallError) as e:
            self.logger.error(f"Connection test failed: {e.message}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during connection test: {e}")
            return False

    def post_to_cloud(self) -> None:
        """Post attendance data to the cloud API using JWT authentication."""
        self.logger.info("Starting data post to cloud")
        try:
            # Get pending attendance records
            attendance_data = self.attendance_repo.cloud_format()
            if not attendance_data:
                self.logger.warning("No valid attendance data to post")
                return

            # Post to API using JWT authentication
            url = f"{self.cloud_api_url.rstrip('/')}{API_ENDPOINTS['ATTENDANCE']}"
            response = self.auth_manager.make_authenticated_request("POST", url, {"attendance": attendance_data})

            if response.status_code == 200:
                # Mark records as posted
                pending_attendance = self.attendance_repo.get_pending()
                for record in pending_attendance:
                    record.posted = True
                    record.save()

                self.logger.info(
                    f"Successfully posted {len(attendance_data)} attendance records"
                )
                self.notification_service.notify(
                    "Sync Success",
                    f"Posted {len(attendance_data)} attendance records to cloud",
                    "info",
                )
            else:
                raise APICallError(f"API returned status code {response.status_code}")

        except APINetworkError as e:
            self.logger.error(f"Network error posting to cloud: {e.message}")
            self.notification_service.notify(
                "Sync Error", f"Network error: {e.message}", "error"
            )
        except APIAuthenticationError as e:
            self.logger.error(f"Authentication error posting to cloud: {e.message}")
            self.notification_service.notify(
                "Sync Error", f"Authentication error: {e.message}", "error"
            )
        except APICallError as e:
            self.logger.error(f"API error posting to cloud: {e.message}")
            self.notification_service.notify(
                "Sync Error", f"API error: {e.message}", "error"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error posting to cloud: {e}")
            self.notification_service.notify(
                "Sync Error", f"Unexpected error: {str(e)}", "error"
            )

    def sync_data(self) -> bool:
        """
        Synchronize data with the cloud API.
        Returns:
            bool: True if sync was successful, False otherwise.
        """
        self.logger.info("Starting data synchronization")
        try:
            # Pull data from devices first
            self.device_manager.pull_data()

            # Then post to cloud
            self.post_to_cloud()

            self.logger.info("Data synchronization completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Data synchronization failed: {e}")
            self.notification_service.notify(
                "Sync Error", f"Data synchronization failed: {str(e)}", "error"
            )
            return False

    def sync_users(self) -> bool:
        """
        Synchronize users and devices from the cloud API and save to the database then migrate to devices.
        Returns:
            bool: True if sync was successful, False otherwise.
        """
        self.logger.info("Starting user and device synchronization")
        try:
            # Step 1: Pull users and devices from cloud API
            cloud_data = self._pull_users_from_cloud()
            if not cloud_data:
                self.logger.error("Failed to pull users and devices from cloud")
                self.notification_service.notify(
                    "Sync Users", "Failed to pull users and devices from cloud", "error"
                )
                return False

            # Step 2: Save devices to database
            devices_saved = self._save_cloud_devices_to_database(cloud_data["devices"])
            self.logger.info(f"Saved {devices_saved} devices to database")

            # Step 3: Save users to database
            users_saved = self._save_cloud_users_to_database(cloud_data["users"])
            self.logger.info(f"Saved {users_saved} users to database")

            # Step 4: Migrate users to devices
            self.device_manager.migrate_user_to_device()

            self.logger.info("User and device synchronization completed successfully")
            self.notification_service.notify(
                "Sync Users", 
                f"Successfully synced {users_saved} users and {devices_saved} devices from cloud", 
                "info"
            )
            return True

        except Exception as e:
            self.logger.error(f"User and device synchronization failed: {e}")
            self.notification_service.notify(
                "Sync Users", f"User and device synchronization failed: {str(e)}", "error"
            )
            return False

    def _pull_users_from_cloud(self) -> Optional[Dict]:
        """
        Pull users and devices from the cloud API.
        Returns:
            Optional[Dict]: Dictionary containing users and devices or None if failed.
        """
        try:
            # Use the attendance device-users endpoint
            url = f"{self.cloud_api_url.rstrip('/')}{API_ENDPOINTS['USERS']}{self.institute_id}/"
            response = self.auth_manager.make_authenticated_request("GET", url)
            
            if response.status_code == 200:
                data = self.auth_manager.parse_response(response)
                
                # Extract users from the structured response
                users = data.get("users", [])
                
                # Extract devices
                devices = data.get("devices", [])
                
                self.logger.info(f"Successfully pulled {len(users)} users and {len(devices)} devices from cloud")
                return {
                    "users": users,
                    "devices": devices
                }
            else:
                self.logger.error(f"Users endpoint returned status code {response.status_code}")
                self.logger.error(f"Response content: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to pull users from cloud: {e}")
            return None

    def _save_cloud_devices_to_database(self, cloud_devices: List[Dict]) -> int:
        """
        Save devices from cloud to database.
        Args:
            cloud_devices: List of device dictionaries from cloud API
        Returns:
            int: Number of devices saved/updated
        """
        saved_count = 0
        
        for device_data in cloud_devices:
            try:
                # Check if device already exists
                existing_device = self.device_repo.get_by_ip(device_data.get('ip'))
                
                if not existing_device:
                    # Create new device
                    device = Device(
                        name=device_data.get('name', ''),
                        ip_address=device_data.get('ip', ''),
                        port=device_data.get('port', 4370),
                        password=device_data.get('password', ''),
                        device_model=device_data.get('model', 'Unknown'),
                        status='Offline'
                    )
                    device.save()
                    saved_count += 1
                    self.logger.debug(f"Created new device: {device.name} ({device.ip_address})")
                else:
                    # Update existing device
                    existing_device.name = device_data.get('name', existing_device.name)
                    existing_device.port = device_data.get('port', existing_device.port)
                    existing_device.password = device_data.get('password', existing_device.password)
                    existing_device.device_model = device_data.get('model', existing_device.device_model)
                    existing_device.save()
                    saved_count += 1
                    self.logger.debug(f"Updated existing device: {existing_device.name} ({existing_device.ip_address})")
                    
            except Exception as e:
                self.logger.error(f"Error saving device {device_data.get('ip', 'unknown')}: {e}")
                continue
        
        return saved_count

    def _save_cloud_users_to_database(self, cloud_users: List[Dict]) -> int:
        """
        Save users from cloud to database.
        Args:
            cloud_users: List of user dictionaries from cloud API
        Returns:
            int: Number of users saved/updated
        """
        saved_count = 0
        
        for user_data in cloud_users:
            try:
                # Check if user already exists
                existing_user = self.user_repo.get_by_user_id(user_data.get('user_id'))
                
                if not existing_user:
                    # Create new user
                    user = User(
                        uid=user_data.get('uid', 0),
                        name=user_data.get('name', ''),
                        user_type=user_data.get('user_type', 'STUDENT'),
                        role=user_data.get('role', 0),
                        password=user_data.get('password', ''),
                        group_id=user_data.get('group_id'),
                        user_id=user_data.get('user_id', ''),
                        card=user_data.get('card'),
                        device_code=user_data.get('device_code'),
                        saved_to_device=False
                    )
                    user.save()
                    saved_count += 1
                    self.logger.debug(f"Created new user: {user.name} ({user.user_id})")
                else:
                    # Update existing user
                    existing_user.name = user_data.get('name', existing_user.name)
                    existing_user.user_type = user_data.get('user_type', existing_user.user_type)
                    existing_user.role = user_data.get('role', existing_user.role)
                    existing_user.password = user_data.get('password', existing_user.password)
                    existing_user.group_id = user_data.get('group_id', existing_user.group_id)
                    existing_user.card = user_data.get('card', existing_user.card)
                    existing_user.device_code = user_data.get('device_code', existing_user.device_code)
                    existing_user.save()
                    saved_count += 1
                    self.logger.debug(f"Updated existing user: {existing_user.name} ({existing_user.user_id})")
                    
            except Exception as e:
                self.logger.error(f"Error saving user {user_data.get('user_id', 'unknown')}: {e}")
                continue
        
        return saved_count 