import logging
from datetime import datetime

import requests

from core.constants import API_ENDPOINTS, STATUS_MESSAGES
from core.security import SecurityManager
from interfaces.database.models import db
from interfaces.database.repository import AttendanceRepository, SettingsRepository
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

    def post_to_cloud(self) -> None:
        """Post attendance data to the cloud API."""
        self.logger.info("Starting data post to cloud API")
        if not self.settings:
            self.logger.error(STATUS_MESSAGES["SETTINGS_NOT_FOUND"])
            self.notification_service.notify(
                "Error", STATUS_MESSAGES["SETTINGS_NOT_FOUND"], "error"
            )
            return

        auth_token = self._get_auth_token()
        if not auth_token:
            self.logger.error("Failed to obtain authentication token")
            self.notification_service.notify("Error", "Authentication failed", "error")
            return

        try:
            url = self.settings.cloud_api_url
            institute_id = self.settings.institute_id
            attendances = self.attendance_repo.get_all()
            data = [
                {
                    "user_id": att.user.user_id,
                    "timestamp": att.timestamp.isoformat(),
                    "status": att.status,
                    "punch": att.punch,
                }
                for att in attendances
            ]
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}",
            }
            attendance_url = f"{url}{API_ENDPOINTS['ATTENDANCE']}"
            response = requests.post(
                attendance_url,
                json={"data": data, "institute_id": institute_id},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            self.logger.info(f"Data posted to cloud successfully: {len(data)} records")
            self.notification_service.notify(
                "Cloud Sync",
                f"Data posted to cloud successfully: {len(data)} records",
                "info",
            )
        except requests.RequestException as e:
            self.logger.error(f"Failed to post data to cloud: {e}")
            self.notification_service.notify(
                "Error", f"Failed to post data to cloud: {str(e)}", "error"
            )

    def sync_data(self) -> bool:
        """
        Sync users and devices from Django API.

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.info("Starting data sync from cloud API")
        if not self.settings:
            self.logger.error(STATUS_MESSAGES["SETTINGS_NOT_FOUND"])
            self.notification_service.notify(
                "Error", STATUS_MESSAGES["SETTINGS_NOT_FOUND"], "error"
            )
            return False

        auth_token = self._get_auth_token()
        if not auth_token:
            self.logger.error("Failed to obtain authentication token")
            self.notification_service.notify("Sync Error", "Authentication failed", "error")
            return False

        try:
            url = self.settings.cloud_api_url
            institute_id = self.settings.institute_id
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}",
            }
            sync_url = f"{url}{API_ENDPOINTS['SYNC']}?institute={institute_id}"
            sync_response = requests.get(sync_url, headers=headers, timeout=15)
            if sync_response.status_code != 200:
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
                from interfaces.database.models import Device, User

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

                users_created, users_updated, zk_users_created = 0, 0, 0
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
                        user.save()
                        users_updated += 1
                    else:
                        users_created += 1
                    try:
                        self._create_user_in_devices(user)
                        zk_users_created += 1
                    except Exception as e:
                        self.logger.error(f"Failed to create user {user.name} in devices: {e}")

            # Update sync timestamp
            from interfaces.database.repository import ScheduleRepository

            schedule_repo = ScheduleRepository()
            sync_schedule = schedule_repo.get_by_task_type("sync")
            if sync_schedule:
                schedule_repo.update_last_run(sync_schedule.id, datetime.now())
            else:
                schedule_repo.model.create(
                    task_type="sync",
                    schedule_time="12:00",
                    enabled=True,
                    last_run=datetime.now(),
                )

            sync_message = (
                f"Sync completed: {devices_created} devices created, {devices_updated} updated, "
                f"{users_created} users created, {users_updated} updated, "
                f"{zk_users_created} added to physical devices."
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

    def _create_user_in_devices(self, user) -> None:
        """
        Create a user in all ZKTeco devices.

        Args:
            user: User model to create in devices
        """
        from interfaces.database.models import Device
        from services.device_manager import DeviceConnectionFactory

        devices = Device.select()
        for device in devices:
            try:
                zk = DeviceConnectionFactory.create_connection(device)
                conn = zk.connect()
                if conn:
                    device_users = conn.get_users()
                    user_exists = any(u.user_id == user.user_id for u in device_users)
                    if not user_exists:
                        conn.set_user(
                            uid=int(user.user_id),
                            name=user.name,
                            privilege=user.role,
                            password="",
                            group_id=0,
                            user_id=user.user_id,
                        )
                        self.logger.info(f"Created user {user.name} (ID: {user.user_id}) in device {device.ip_address}")
                    conn.disconnect()
            except Exception as e:
                self.logger.error(f"Failed to create user in device {device.ip_address}: {e}")