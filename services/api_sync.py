# services/api_sync.py
import logging
import requests
from typing import Dict, Optional, List

from core.constants import API_ENDPOINTS
from core.exceptions import APICallError
from interfaces.database.models import Device, User


class APISync:
    """Handles API data synchronization operations."""

    def __init__(self, notification_service, settings_repo, attendance_repo, user_repo, device_repo, device_manager):
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.attendance_repo = attendance_repo
        self.user_repo = user_repo
        self.device_repo = device_repo
        self.device_manager = device_manager
        self.logger = logging.getLogger(__name__)
        # Settings
        self.cloud_api_url = ""
        self.sync_id = ""  # Only sync_id is used
        # Connection pooling
        self._session = requests.Session()
        # Set default headers for all requests
        self._session.headers.update({
            'User-Agent': 'EduraSync/1.0',
            'Content-Type': 'application/json'
        })

    def load_settings(self) -> None:
        """Load settings from repository."""
        settings = self.settings_repo.get_settings()
        if settings:
            self.cloud_api_url = settings.cloud_api_url or ""
            self.sync_id = settings.sync_id or ""
        else:
            self.cloud_api_url = ""
            self.sync_id = ""
            self.logger.warning("No settings found - using empty values")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {"x-sync-id": self.sync_id}

    def _get_endpoint(self, endpoint_key: str) -> str:
        """Get API endpoint from constants."""
        return API_ENDPOINTS.get(endpoint_key, "")

    def _handle_api_response(self, response, success_message: str = None) -> bool:
        """
        Handle API response and return success status.
        
        Args:
            response: requests.Response object
            success_message: Optional success message to log
            
        Returns:
            bool: True if response is successful, False otherwise
        """
        if response.status_code in [200, 201, 204]:
            if success_message:
                self.logger.info(success_message)
            return True
        else:
            error_msg = f"API returned status code {response.status_code}"
            if response.text:
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('detail', response.text)}"
                except:
                    error_msg += f": {response.text}"
            self.logger.error(f"API error: {error_msg}")
            raise APICallError(error_msg)

    def _make_api_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an API request with common error handling.

        A default timeout of (connect=10s, read=60s) is applied to every request
        unless the caller explicitly passes a different ``timeout`` value.

        Args:
            method: HTTP method ('GET', 'POST', 'PUT', 'DELETE')
            endpoint: API endpoint
            **kwargs: Additional arguments passed to requests (e.g. json, timeout)

        Returns:
            requests.Response: API response
        """
        url = f"{self.cloud_api_url.rstrip('/')}{endpoint}"
        headers = self._get_headers()

        # Merge caller-provided headers with auth headers.
        if 'headers' in kwargs:
            kwargs['headers'].update(headers)
        else:
            kwargs['headers'] = headers

        # Apply a sensible default timeout so the main thread never blocks forever.
        kwargs.setdefault('timeout', (10, 60))  # (connect, read) in seconds

        response = getattr(self._session, method.lower())(url, **kwargs)
        return response

    def test_connection(self, url: str, sync_id: str) -> bool:
        """
        Test connection to the cloud API using sync_id only.
        
        Args:
            url: Base API URL
            sync_id: Institute sync ID for testing
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        # Save current settings temporarily
        original_cloud_api_url = self.cloud_api_url
        original_sync_id = self.sync_id
        
        # Set temporary settings for testing
        self.cloud_api_url = url
        self.sync_id = sync_id
        
        try:
            # Test connection using sync_id only
            endpoint = self._get_endpoint('TEST')
            
            # Use the standard API request method for consistency
            response = self._make_api_request('GET', endpoint, timeout=10)
            
            # Handle successful response (200)
            if response.status_code == 200:
                try:
                    data = response.json()
                    detail = data.get('detail', 'Connection successful')
                    institute_name = data.get('institute_name', 'Unknown Institute')
                    message = f"{detail} - {institute_name}"
                    self.logger.info(f"API connection test successful: {message}")
                    self.notification_service.notify(
                        "Connection Test",
                        message,
                        "info"
                    )
                except Exception:
                    # Fallback if JSON parsing fails
                    self.logger.info(f"API connection test successful (Status: {response.status_code})")
                    self.notification_service.notify(
                        "Connection Test",
                        f"API connection successful (Status: {response.status_code})",
                        "info"
                    )
                return True
            # Handle authentication error (401) - Invalid sync ID
            elif response.status_code == 401:
                try:
                    data = response.json()
                    detail = data.get('detail', 'Invalid Sync ID')
                    self.logger.error(f"API connection test failed: {detail}")
                    self.notification_service.notify(
                        "Connection Test",
                        detail,
                        "error"
                    )
                except Exception:
                    # Fallback if JSON parsing fails
                    error_msg = "Invalid Sync ID: No Institute matches the given query."
                    self.logger.error(f"API connection test failed: {error_msg}")
                    self.notification_service.notify(
                        "Connection Test",
                        error_msg,
                        "error"
                    )
                return False
            # Handle other status codes
            elif response.status_code in [403, 404]:
                # Connection successful but endpoint issue
                self.logger.info(f"API connection test successful (Status: {response.status_code})")
                self.notification_service.notify(
                    "Connection Test",
                    f"API connection successful (Status: {response.status_code})",
                    "info"
                )
                return True
            else:
                error_msg = f"API returned status code {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg += f": {error_data.get('detail', response.text)}"
                    except:
                        error_msg += f": {response.text}"
                self.logger.error(f"API connection test failed: {error_msg}")
                self.notification_service.notify(
                    "Connection Test",
                    f"API connection failed: {error_msg}",
                    "error"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error during connection test: {e}")
            self.notification_service.notify(
                "Connection Test",
                f"Connection test failed: {str(e)}",
                "error"
            )
            return False
        finally:
            # Restore original settings
            self.cloud_api_url = original_cloud_api_url
            self.sync_id = original_sync_id

    def post_to_cloud(self) -> None:
        """Post attendance data to the cloud API using sync_id only."""
        self.logger.info("Starting data post to cloud")
        attendance_data = self.attendance_repo.cloud_format()
        if not attendance_data:
            self.logger.warning("No valid attendance data to post")
            self.notification_service.notify(
                "Sync Info", "No pending attendance data to sync", "info"
            )
            return

        self.logger.info(f"Posting {len(attendance_data)} attendance records to cloud")
        endpoint = '/api/attendance/attendance-log/'
        
        # Prepare payload for API (strip the internal DB id before sending)
        api_payload = []
        for record in attendance_data:
            payload_item = record.copy()
            self.logger.debug(f"Processing attendance record: {payload_item}")
            payload_item.pop("id", None)
            api_payload.append(payload_item)
            
        response = self._make_api_request(
            'POST', 
            endpoint, 
            json=api_payload
        )

        if self._handle_api_response(
            response, 
            f"Successfully posted {len(attendance_data)} attendance records"
        ):
            attendance_ids = [record["id"] for record in attendance_data if "id" in record]
            if attendance_ids:
                posted_count = self.attendance_repo.mark_as_posted(attendance_ids)
                self.logger.info(f"Marked {posted_count} attendance records as posted")
            self.notification_service.notify(
                "Sync Success",
                f"Posted {len(attendance_data)} attendance records to cloud",
                "info",
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
        # Check if we have proper API configuration
        if not all([self.cloud_api_url, self.sync_id]):
            self.logger.error("API configuration incomplete - missing URL or sync_id")
            self.notification_service.notify(
                "Sync Users", "API configuration incomplete. Please check settings.", "error"
            )
            return False

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

    def _pull_users_from_cloud(self) -> Optional[Dict]:
        """
        Pull users and devices from the cloud API using sync_id only.
        Returns:
            Optional[Dict]: Dictionary containing users and devices or None if failed.
        """
        endpoint = self._get_endpoint('USERS')
        response = self._make_api_request('GET', endpoint)
        
        if self._handle_api_response(response):
            try:
                data = response.json()
            except Exception as exc:
                self.logger.error(f"Cloud response is not valid JSON: {exc}\nRaw body: {response.text[:500]}")
                return None

            users = data.get("users", [])
            devices = data.get("devices", [])

            if not isinstance(users, list):
                self.logger.warning(f"Expected 'users' list but got {type(users).__name__}: {users!r}")
                users = []
            if not isinstance(devices, list):
                self.logger.warning(f"Expected 'devices' list but got {type(devices).__name__}: {devices!r}")
                devices = []

            # Validate individual user records and report missing expected fields
            _expected_user_keys = {"id", "name", "type", "card", "device_id"}
            for idx, u in enumerate(users[:3]):  # sample first 3 only
                missing = _expected_user_keys - set(u.keys())
                extra   = set(u.keys()) - _expected_user_keys - {"role", "password", "group_id", "device_code", "card_number"}
                if missing:
                    self.logger.warning(f"User[{idx}] missing keys: {missing} — record: {u}")
                if extra:
                    self.logger.debug(f"User[{idx}] unexpected extra keys: {extra}")

            self.logger.info(
                f"Cloud data received — {len(users)} users, {len(devices)} devices"
            )
            return {"users": users, "devices": devices}
        return None

    def _save_cloud_devices_to_database(self, cloud_devices: List[Dict]) -> int:
        """
        Save devices from cloud to database.
        Args:
            cloud_devices: List of device dictionaries from cloud API
        Returns:
            int: Number of devices saved/updated
        """
        # Debug: Check if cloud_devices is actually a list
        if not isinstance(cloud_devices, list):
            self.logger.error(f"Expected list but got {type(cloud_devices)}: {cloud_devices}")
            return 0
            
        saved_count = 0
        
        for device_data in cloud_devices:
            # Check if device already exists
            existing_device = self.device_repo.get_by_ip(device_data.get('ip'))

            if not existing_device:
                # Create new device
                device = Device(
                    cloud_id=device_data.get('id'), # Save cloud primary key
                    ip_address=device_data.get('ip', ''),
                    port=device_data.get('port', 4370),
                    password=device_data.get('password', ''),
                    device_model=device_data.get('name', 'Unknown'),
                    status='Offline'
                )
                device.save()
                saved_count += 1
                self.logger.debug(f"Created new device: {device.device_model} ({device.ip_address}, Cloud ID: {device.cloud_id})")
            else:
                # Update existing device
                existing_device.cloud_id = device_data.get('id', existing_device.cloud_id)
                existing_device.port = device_data.get('port', existing_device.port)
                existing_device.password = device_data.get('password', existing_device.password)
                existing_device.device_model = device_data.get('name', existing_device.device_model)
                existing_device.save()
                saved_count += 1
                self.logger.debug(f"Updated existing device: {existing_device.device_model} ({existing_device.ip_address}, Cloud ID: {existing_device.cloud_id})")

        return saved_count

    def _save_cloud_users_to_database(self, cloud_users: List[Dict]) -> int:
        """
        Save users from cloud to database.
        Args:
            cloud_users: List of user dictionaries from cloud API
        Returns:
            int: Number of users saved/updated
        """
        # Debug: Check if cloud_users is actually a list
        if not isinstance(cloud_users, list):
            self.logger.error(f"Expected list but got {type(cloud_users)}: {cloud_users}")
            return 0
            
        saved_count = 0
        for user_data in cloud_users:
            self.logger.debug(f"Processing cloud user data: {user_data}")
            # Match user by cloud ID only - user_id field stores cloud ID
            cloud_id_str = str(user_data.get('id', ''))
            existing_user = self.user_repo.get_by_user_id(cloud_id_str)

            # Find the assigned device from local DB based on cloud's device_id
            assigned_device = None
            cloud_device_id = user_data.get('device_id')
            if cloud_device_id:
                assigned_device = self.device_repo.get_by_cloud_id(cloud_device_id)

            # API returns "card" (not "card_number")
            card_value = user_data.get('card') or user_data.get('card_number')

            if not existing_user:
                # Create new user
                user = User(
                    name=user_data.get('name', ''),
                    user_type=user_data.get('type', 'STUDENT'),
                    role=user_data.get('role', 0),
                    password=user_data.get('password', ''),
                    group_id=user_data.get('group_id', ''),
                    user_id=str(user_data.get('id', '')),
                    card=card_value,
                    device_code=user_data.get('device_code'),
                    device=assigned_device,
                    saved_to_device=False
                )
                user.save()
                saved_count += 1
                self.logger.debug(
                    f"Created new user: {user.name} ({user.user_id}) "
                    f"card={card_value} device={assigned_device.ip_address if assigned_device else 'Unassigned'}"
                )
            else:
                # Update existing user
                existing_user.name = user_data.get('name', existing_user.name)
                existing_user.user_type = user_data.get('type', existing_user.user_type)
                existing_user.device = assigned_device
                existing_user.role = user_data.get('role', existing_user.role)
                existing_user.password = user_data.get('password', existing_user.password)
                existing_user.group_id = user_data.get('group_id', existing_user.group_id)
                existing_user.card = card_value if card_value is not None else existing_user.card
                existing_user.device_code = user_data.get('device_code', existing_user.device_code)
                existing_user.user_id = str(user_data.get('id', existing_user.user_id))
                existing_user.save()
                saved_count += 1
                self.logger.debug(f"Updated existing user: {existing_user.name} ({existing_user.user_id}) card={card_value}")
        return saved_count

    def close(self):
        """Close the session to free up resources."""
        if self._session:
            self._session.close()