import logging
from datetime import datetime

import requests

from core.security import SecurityManager
from interfaces.database.models import db
from interfaces.database.repository import (
    AttendanceRepository,
    SettingsRepository,
    ScheduleRepository,
)
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
        schedule_repo: ScheduleRepository,
    ):
        """
        Initialize the API client with injected dependencies.
        Args:
            security: SecurityManager for encryption/decryption.
            notification_service: Service for sending notifications.
            settings_repo: Repository for settings data.
            attendance_repo: Repository for attendance data.
            schedule_repo: Repository for schedule data.
        """
        self.logger = logging.getLogger(__name__)
        self.security = security
        self.notification_service = notification_service
        self.settings_repo = settings_repo
        self.attendance_repo = attendance_repo
        self.schedule_repo = schedule_repo
        self.settings = None
        self._load_settings()
        self.sync_url = '/api/sync/'
        self.token_url = '/api/token/'
        self.attendance_url = '/api/attendance/'

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

    def post_to_cloud(self) -> None:
        """Post attendance data to the cloud API."""
        self.logger.info("Starting data post to cloud API")
        if not self.settings:
            self.logger.error("Settings not configured")
            self.notification_service.notify(
                "Error", "Settings not configured", "error"
            )
            return

        try:
            url = self.settings.cloud_api_url
            username = self.settings.username
            password = self.security.decrypt(self.settings.password)
            institute_id = self.settings.institute_id
            auth_token = self.security.decrypt(self.settings.auth_token)

            # Fetch attendance data
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
            data_count = len(data)
            self.logger.info(
                f"Preparing to send {data_count} attendance records to {url}"
            )

            # First, try to get a token (for Django REST framework)
            auth_token = None
            token_url = f"{url}{self.token_url}"

            try:
                token_response = requests.post(
                    token_url,
                    json={"username": username, "password": password},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )

                if token_response.status_code == 200:
                    token_data = token_response.json()
                    auth_token = token_data.get('token') or token_data.get('access')
                    self.logger.info("Successfully obtained authentication token")
            except Exception as e:
                self.logger.warning(f"Could not obtain token, falling back to basic auth: {e}")

            # Create headers with token if available
            headers = {
                "Content-Type": "application/json"
            }

            if auth_token:
                headers["Authorization"] = f"Token {auth_token}"

                # Send data to cloud using token auth
                attendance_url = f"{url}{self.attendance_url}"

                response = requests.post(
                    attendance_url,
                    json={"data": data, "institute_id": institute_id},
                    headers=headers,
                    timeout=10
                )
            else:
                # Fall back to basic auth if token auth is not available
                response = requests.post(
                    url,
                    json={"data": data, "auth_token": auth_token},
                    auth=(username, password),
                    timeout=10
                )

            response.raise_for_status()

            # Update schedule last run time
            push_schedule = self.schedule_repo.get_by_task_type("push")
            if push_schedule:
                self.schedule_repo.update_last_run(push_schedule.id, datetime.now())
                self.logger.info("Updated push schedule last_run time")

            self.logger.info(f"Data posted to cloud successfully: {data_count} records")
            self.notification_service.notify(
                "Cloud Sync",
                f"Data posted to cloud successfully: {data_count} records",
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
            self.logger.error("Settings not configured")
            self.notification_service.notify(
                "Error", "Settings not configured", "error"
            )
            return False

        try:
            url = self.settings.cloud_api_url
            auth_token = self.security.decrypt(self.settings.auth_token) if self.settings.auth_token else None
            institute_id = self.settings.institute_id
            print(f'preparing for request to {url} with institute_id {institute_id} and auth_token {auth_token}...')
            # If no auth token, try to get one
            if not auth_token:
                username = self.settings.username
                password = self.security.decrypt(self.settings.password)
                
                token_url = f'{url}{self.token_url}'
                token_response = requests.post(
                    token_url,
                    json={"username": username, "password": password},
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if token_response.status_code == 200:
                    token_data = token_response.json()
                    auth_token = token_data.get('token') or token_data.get('access')
                    
                    # Save the token for future use
                    if auth_token:
                        self.security.save_token_to_settings(auth_token, self.settings_repo)
                        self.logger.info("Auth token refreshed and saved")
                        print(f'retrieved new auth token: {auth_token}')
                if not auth_token:
                    self.logger.error("Failed to obtain authentication token")
                    self.notification_service.notify(
                        "Sync Error", "Authentication failed", "error"
                    )
                    return False
            
            # Create headers with token
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Call the sync endpoint
            sync_url = f'{url}{self.sync_url}'
            if "?" in sync_url:
                sync_url += f"&institute={institute_id}"
            else:
                sync_url = f"{sync_url.rstrip('/')}?institute={institute_id}"
                
            self.logger.info(f"Calling sync endpoint: {sync_url}")
            print(f'requesting sync data from {sync_url}...')
            sync_response = requests.get(
                sync_url,
                headers=headers,
                timeout=15  # Longer timeout for sync
            )
            print(f'response status code: {sync_response.status_code}')
            print(f'sync response: {sync_response.text}...end of sync response')
            if sync_response.status_code != 200:
                self.logger.error(f"Sync failed: HTTP {sync_response.status_code}")
                self.notification_service.notify(
                    "Sync Error", 
                    f"Failed to retrieve data: HTTP {sync_response.status_code}", 
                    "error"
                )
                return False
            
            # Process the response data
            sync_data = sync_response.json()
            users_data = sync_data.get('users', [])
            devices_data = sync_data.get('devices', [])
            
            self.logger.info(f"Received {len(users_data)} users and {len(devices_data)} devices from API")
            # Begin database transaction
            with db.atomic():
                # Process devices first
                from interfaces.database.models import Device
                
                devices_created = 0
                devices_updated = 0
                
                for device_data in devices_data:
                    device, created = Device.get_or_create(
                        id=device_data.get('id'),
                        defaults={
                            'ip_address': device_data.get('ip_address'),
                            'port': device_data.get('port', 4370),
                            'password': device_data.get('password', '0'),
                            'device_model': device_data.get('model_name', 'ZKTeco'),
                            'status': 'Offline',
                            'created_at': datetime.now()
                        }
                    )
                    
                    if not created:
                        # Update existing device
                        device.ip_address = device_data.get('ip_address')
                        device.port = device_data.get('port', 4370)
                        device.password = device_data.get('password', '0')
                        device.device_model = device_data.get('model_name', 'ZKTeco')
                        device.save()
                        devices_updated += 1
                    else:
                        devices_created += 1
            
                # Process users
                from interfaces.database.models import User
                
                users_created = 0
                users_updated = 0
                zk_users_created = 0
                
                for user_data in users_data:
                    user, created = User.get_or_create(
                        user_id=user_data.get('device_user_id'),
                        defaults={
                            'name': user_data.get('name'),
                            'role': 0,  # Default role
                            'user_cloud_id': user_data.get('id'),
                            'created_at': datetime.now(),
                            'updated_at': datetime.now()
                        }
                    )
                    
                    if not created:
                        # Update existing user
                        user.name = user_data.get('name')
                        user.user_cloud_id = user_data.get('id')
                        user.updated_at = datetime.now()
                        user.save()
                        users_updated += 1
                    else:
                        users_created += 1
                
                    # Create user in ZKTeco devices
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
                # Create sync schedule if it doesn't exist
                schedule_repo.model.create(
                    task_type='sync', schedule_time='12:00', enabled=True,
                    last_run=datetime.now()
                )
            
            # Log and notify about the sync results
            sync_message = (
                f"Sync completed: {devices_created} devices created, {devices_updated} updated, "
                f"{users_created} users created, {users_updated} updated, "
                f"{zk_users_created} added to physical devices."
            )
            
            self.logger.info(sync_message)
            self.notification_service.notify(
                "Sync Complete", 
                sync_message,
                "info"
            )
            
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Failed to sync data: {e}")
            self.notification_service.notify(
                "Error", f"Failed to sync data: {str(e)}", "error"
            )
            return False
        except Exception as e:
            self.logger.error(f"Sync error: {e}")
            self.notification_service.notify(
                "Error", f"Sync failed: {str(e)}", "error"
            )
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
                # Connect to the device
                zk = DeviceConnectionFactory.create_connection(device)
                conn = zk.connect()
                
                if conn:
                    # Check if user already exists on device
                    device_users = conn.get_users()
                    user_exists = any(u.user_id == user.user_id for u in device_users)
                    
                    if not user_exists:
                        # Create the user in the device
                        conn.set_user(
                            uid=int(user.user_id),  # Might need conversion based on device
                            name=user.name,
                            privilege=user.role,
                            password='',
                            group_id=0,
                            user_id=user.user_id
                        )
                        self.logger.info(f"Created user {user.name} (ID: {user.user_id}) in device {device.ip_address}")
                    
                    # Disconnect from the device
                    conn.disconnect()
            except Exception as e:
                self.logger.error(f"Failed to create user in device {device.ip_address}: {e}")