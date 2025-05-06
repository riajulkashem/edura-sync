import logging
from datetime import datetime

import requests

from core.constants import API_ENDPOINTS, STATUS_MESSAGES
from core.security import SecurityManager
from interfaces.database.models import db
from interfaces.database.repository import (
    AttendanceRepository,
    SettingsRepository,
)
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
        device_manager: DeviceManager,
    ):
        self.logger = logging.getLogger(__name__)
        self.security = security
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.attendance_repo = attendance_repo
        self.device_manager = device_manager
        # expose repos from device_manager
        self.device_repo = self.device_manager.device_repo
        self.user_repo = self.device_manager.user_repo

        # load and cache settings
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

        # existing token
        if self.settings.auth_token:
            return self.security.decrypt(self.settings.auth_token)

        # fetch new token
        try:
            url = f"{self.settings.cloud_api_url}{API_ENDPOINTS['TOKEN']}"
            payload = {
                "username": self.settings.username,
                "password": self.security.decrypt(self.settings.password),
            }
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            token = data.get("token") or data.get("access")
            if token:
                self.security.save_token_to_settings(token, self.settings_repo)
                self.logger.info("Auth token refreshed and saved")
                return token
        except Exception as e:
            self.logger.warning(f"Failed to obtain auth token: {e}")
        return None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
    ) -> requests.Response | bool:
        """Execute an HTTP request with the specified method and parameters."""
        if not self.settings:
            self.logger.error(STATUS_MESSAGES["SETTINGS_NOT_FOUND"])
            self.notification_service.notify(
                "Error", STATUS_MESSAGES["SETTINGS_NOT_FOUND"], "error"
            )
            return False

        token = self._get_auth_token()
        if not token:
            self.logger.error("Authentication failed: no token")
            self.notification_service.notify("Error", "Authentication failed", "error")
            return False

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {token}",
        }
        url = f"{self.settings.cloud_api_url}{endpoint}?institute={self.settings.institute_id}"
        try:
            resp = requests.request(
                method=method.upper(),
                url=url,
                json=json_data,
                headers=headers,
                timeout=10,
            )
            json_resp = resp.json()
            if 'detail' in json_resp and json_resp['detail'] == 'Invalid token.':
                self._get_auth_token()
            print(f'response: {resp}')
            print(f'response json: {resp.json()}')

            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            self.logger.error(f"Request failed ({method} {endpoint}): {e}")
            return False

    def post_to_cloud(self) -> None:
        """Pull local data and post attendance records to the cloud."""
        self.device_manager.pull_data()
        payload = self.attendance_repo.cloud_format()
        print(f'payload: {payload} length: {len(payload)}')
        resp = self._make_request("POST", API_ENDPOINTS["ATTENDANCE"], json_data=payload)
        if resp and getattr(resp, 'status_code', None) == 200:
            # clear posted records
            self.attendance_repo.update_bulk({'posted': True}, filters={'posted': False})
            payload = self.attendance_repo.cloud_format()
            print(f'attendance after cleared: {payload} length: {len(payload)}')
            self.logger.info("Data posted to cloud successfully")
            self.notification_service.notify(
                "Cloud Sync", "Data posted to cloud successfully", "info"
            )
        else:
            msg = getattr(resp, 'text', 'No response')
            self.logger.error(f"Failed to post data to cloud: {msg}")
            self.notification_service.notify(
                "Error", f"Failed to post data to cloud: {msg}", "error"
            )

    def sync_data(self) -> bool:
        """Sync devices and users from the cloud into the local database."""
        try:
            resp = self._make_request("GET", API_ENDPOINTS["SYNC"] )
            if not resp:
                self.logger.error("Sync request failed or returned no response")
                self.notification_service.notify(
                    "Sync Error", "Failed to retrieve sync data", "error"
                )
                return False

            data = resp.json()
            users_data = data.get("users", [])
            devices_data = data.get("devices", [])
            self.logger.info(
                f"Sync data received: {len(users_data)} users, {len(devices_data)} devices"
            )

            with db.atomic():
                created_d, updated_d = 0, 0
                for d in devices_data:
                    existing = self.device_repo.get(cloud_id=d.get("id"))
                    if existing:
                        self.device_repo.update(
                            existing,
                            ip_address=d.get("ip_address"),
                            port=d.get("port", 4370),
                            password=d.get("password", "0"),
                            name=d.get("name", "ZKTeco"),
                            cloud_id=d.get("id"),
                        )
                        updated_d += 1
                    else:
                        self.device_repo.create(
                            ip_address=d.get("ip_address"),
                            port=d.get("port", 4370),
                            password=d.get("password", "0"),
                            name=d.get("name", "ZKTeco"),
                            status="Offline",
                            created_at=datetime.now(),
                            cloud_id=d.get("id"),
                        )
                        created_d += 1

                created_u, updated_u = 0, 0
                now = datetime.now()
                for u in users_data:
                    if existing:
                        self.user_repo.update(
                            existing,
                            name=u.get("name"),
                            user_cloud_id=u.get("id"),
                            updated_at=now,
                            saved_to_device=False,
                            device=self.device_repo.get(cloud_id=u.get("device")),
                            card=u.get("card"),
                        )
                        updated_u += 1
                    else:
                        self.user_repo.create(
                            name=u.get("name"),
                            role=0,
                            password="",
                            group_id="",
                            user_id=u.get("device_user_id"),
                            user_cloud_id=u.get("id"),
                            saved_to_device=False,
                            created_at=now,
                            updated_at=now,
                            device=self.device_repo.get(cloud_id=u.get("device")),
                            device_cloud_id=u.get("device"),
                            card=u.get("card"),
                        )
                        created_u += 1

            self.device_manager.migrate_user_to_device()

            # update last_sync in settings
            now = datetime.now()
            settings = self.settings_repo.get_settings()
            if settings:
                self.settings_repo.update(settings, last_sync=now)

            summary = (
                f"Sync complete: {created_d} devices created, {updated_d} updated; "
                f"{created_u} users created, {updated_u} updated"
            )
            self.logger.info(summary)
            self.notification_service.notify("Sync Complete", summary, "info")
            return True

        except Exception as e:
            self.logger.error(f"Sync error: {e}")
            self.notification_service.notify("Error", f"Sync failed: {e}", "error")
            return False
