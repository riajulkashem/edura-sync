import logging
from datetime import datetime

import requests

from core.constants import API_ENDPOINTS, STATUS_MESSAGES
from core.security import SecurityManager
from interfaces.database.models import db, User, Device
from interfaces.database.repository import AttendanceRepository, SettingsRepository
from services.device_manager import DeviceManager
from services.notification import NotificationService


class APIClient:
    """
    Handles interactions with the cloud API for syncing attendance data.
    Uses dependency injection for security, notification, and repository services.
    """

    def __init__(
            self,
            security: SecurityManager,
            notification_service: NotificationService,
            settings_repo: SettingsRepository,
            attendance_repo: AttendanceRepository,
            device_manager: DeviceManager
    ):
        """
        Initialize the API client with injected dependencies.

        Args:
            security: SecurityManager for encryption/decryption.
            notification_service: Service for sending notifications.
            settings_repo: Repository for settings data.
            attendance_repo: Repository for attendance data.
        """
        self.logger = logging.getLogger(__name__)
        self.security = security
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.attendance_repo = attendance_repo
        self.device_manager = device_manager
        self.settings = None
        self._load_settings()

    def _load_settings(self) -> None:
        """Load settings from the repository."""
        self.settings = self.settings_repo.get_settings()
        if self.settings:
            self.logger.info("API client settings loaded")
        else:
            self.logger.warning("No settings found in repository")

    def update_settings(self) -> None:
        """Reload settings from the repository."""
        self._load_settings()
        self.logger.info("API client settings updated")

    def _get_auth_token(self) -> str | None:
        """Retrieve or refresh the authentication token."""
        if not self.settings:
            return None

        # Use existing token if available
        if self.settings.auth_token:
            return self.security.decrypt(self.settings.auth_token)

        # Fetch a new token
        try:
            token_url = f"{self.settings.cloud_api_url}{API_ENDPOINTS['TOKEN']}"
            response = requests.post(
                token_url,
                json={
                    "username": self.settings.username,
                    "password": self.security.decrypt(self.settings.password),
                },
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if response.status_code == 200:
                token_data = response.json()
                auth_token = token_data.get("token") or token_data.get("access")
                if auth_token:
                    self.security.save_token_to_settings(auth_token, self.settings_repo)
                    self.logger.info("Auth token refreshed and saved")
                    return auth_token
        except Exception as e:
            self.logger.warning(f"Failed to obtain auth token: {e}")
        return None

    def _make_request(self, method: str, url: str, json_data: dict = None) -> requests.Response | bool:
        """
        Execute an HTTP request with the specified method and parameters.

        Args:
            method: HTTP method ('GET' or 'POST').
            url: Request URL.
            json_data: JSON payload for POST requests.

        Returns:
            Response object.

        Raises:
            requests.RequestException: If the request fails.
        """
        self.logger.info("Starting data post to cloud API")
        if not self.settings:
            self.logger.error(STATUS_MESSAGES["SETTINGS_NOT_FOUND"])
            self.notification_service.notify(
                "Error", STATUS_MESSAGES["SETTINGS_NOT_FOUND"], "error"
            )
            return False

        auth_token = self._get_auth_token()
        if not auth_token:
            self.logger.error("Failed to obtain authentication token")
            self.notification_service.notify("Error", "Authentication failed", "error")
            return False
        else:
            self.logger.info("Authentication token obtained")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {auth_token}",
        }
        institute_id = self.settings.institute_id
        cloud_url = self.settings.cloud_api_url
        reqeust_url = f"{cloud_url}{url}?institute={institute_id}"
        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = requests.request(
                method=method.upper(),
                url=reqeust_url,
                json=json_data,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return False

    def post_to_cloud(self) -> None:
        """Post attendance data to the cloud API."""
        data = self.attendance_repo.cloud_format()
        response = self._make_request(
            "POST", API_ENDPOINTS["ATTENDANCE"], json_data=data
        )
        if response and response.status_code == 200:
            self.attendance_repo.delete_bulk(posted=True)
            self.logger.info("Data posted to cloud successfully")
            self.notification_service.notify(
                "Cloud Sync", "Data posted to cloud successfully", "info"
            )
        else:
            self.logger.error(f"Failed to post data to cloud: {response.text}")
            self.notification_service.notify(
                "Error", f"Failed to post data to cloud: {response.text}", "error"
            )

    def sync_data(self) -> bool:
        """
        Sync users and devices from Django API.

        Returns:
            bool: True if successful, False otherwise
        """

        try:
            sync_response = self._make_request('GET', API_ENDPOINTS['SYNC'])
            if not sync_response:
                self.logger.error(f"Sync failed: HTTP {sync_response.status_code}")
                self.notification_service.notify(
                    "Sync Error",
                    f"Failed to retrieve data: HTTP {sync_response.status_code}",
                    "error",
                )
                return False
            # Process the response data
            sync_data = sync_response.json()
            users_data = sync_data.get("users", [])
            devices_data = sync_data.get("devices", [])
            self.logger.info(f"Received {len(users_data)} users and {len(devices_data)} devices from API")
            with db.atomic():

                devices_created, devices_updated = 0, 0
                for device_data in devices_data:
                    device, created = Device.get_or_create(
                        id=device_data.get("id"),
                        defaults={
                            "ip_address": device_data.get("ip_address"),
                            "port": device_data.get("port", 4370),
                            "password": device_data.get("password", "0"),
                            "device_model": device_data.get("model_name", "ZKTeco"),
                            "status": "Offline",
                            "created_at": datetime.now(),
                        },
                    )
                    if not created:
                        device.ip_address = device_data.get("ip_address")
                        device.port = device_data.get("port", 4370)
                        device.password = device_data.get("password", "0")
                        device.device_model = device_data.get("model_name", "ZKTeco")
                        device.save()
                        devices_updated += 1
                    else:
                        devices_created += 1

                users_created, users_updated = 0, 0
                for user_data in users_data:
                    user, created = User.get_or_create(
                        user_id=user_data.get("device_user_id"),
                        defaults={
                            "name": user_data.get("name"),
                            "role": 0,
                            "user_cloud_id": user_data.get("id"),
                            "created_at": datetime.now(),
                            "updated_at": datetime.now(),
                        },
                    )
                    if not created:
                        user.name = user_data.get("name")
                        user.user_cloud_id = user_data.get("id")
                        user.updated_at = datetime.now()

                        users_updated += 1
                    else:
                        users_created += 1
                    user.saved_to_device = False
                    user.save()
            self.device_manager.migrate_user_to_device()
            # Update sync timestamp
            sync_timestamp = datetime.now()
            setting = self.settings_repo.get_settings()
            setting.last_sync = sync_timestamp
            setting.save()
            sync_message = (
                f"Sync completed: {devices_created} devices created, {devices_updated} updated, "
                f"{users_created} users created, {users_updated} updated, "
            )
            self.logger.info(sync_message)
            self.notification_service.notify("Sync Complete", sync_message, "info")
            return True

        except requests.RequestException as e:
            self.logger.error(f"Failed to sync data: {e}")
            self.notification_service.notify("Error", f"Failed to sync data: {str(e)}", "error")
            return False
        except Exception as e:
            self.logger.error(f"Sync error: {e}")
            self.notification_service.notify("Error", f"Sync failed: {str(e)}", "error")
            return False
