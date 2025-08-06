# services/device_manager.py
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from zk import ZK

from core.exceptions import DeviceConnectionError, DeviceOperationError
from interfaces.database.models import Device, User
from interfaces.database.repository import (
    DeviceRepository,
    UserRepository,
    AttendanceRepository,
)
from services.notification import NotificationService


class DeviceConnectionFactory:
    """
    Factory for creating ZKTeco device connections.
    Encapsulates connection logic and configuration.
    """

    @staticmethod
    def create_connection(device: Device, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[ZK]:
        """
        Create a connection to a ZKTeco device with retry logic.
        
        Args:
            device: Device model containing connection details.
            max_retries: Maximum number of connection attempts.
            retry_delay: Delay between retry attempts in seconds.
            
        Returns:
            Optional[ZK]: Connected ZK instance or None if connection fails.
            
        Raises:
            DeviceConnectionError: If connection fails after all retries.
        """
        logger = logging.getLogger(__name__)

        for attempt in range(max_retries):
            try:
                zk = ZK(
                    device.ip_address,
                    port=device.port,
                    password=device.password,
                    timeout=5,
                )
                conn = zk.connect()
                if conn:
                    logger.debug(
                        f"Connected to device {device.ip_address}:{device.port} on attempt {attempt + 1}"
                    )
                    return zk
                else:
                    raise DeviceConnectionError(
                        f"Failed to establish connection to device {device.ip_address}"
                    )
            except DeviceConnectionError:
                # Re-raise device connection errors immediately
                raise
            except Exception as e:
                logger.warning(
                    f"Connection attempt {attempt + 1} failed for {device.ip_address}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    return None
                else:
                    logger.error(
                        f"All connection attempts failed for device {device.ip_address}"
                    )
                    raise DeviceConnectionError(
                        f"Failed to connect to device {device.ip_address} after {max_retries} attempts: {str(e)}"
                    )
        return None


class DeviceManager:
    """
    Manages communication with ZKTeco devices for status checks and data pulling.
    Uses dependency injection for repositories and notification service.
    """

    def __init__(
        self,
        notification_service: NotificationService,
        device_repo: DeviceRepository,
        user_repo: UserRepository,
        attendance_repo: AttendanceRepository,
    ):
        """
        Initialize the device manager with dependencies.
        
        Args:
            notification_service: Service for sending notifications.
            device_repo: Repository for device data.
            user_repo: Repository for user data.
            attendance_repo: Repository for attendance data.
        """
        self.notification_service = notification_service
        self.device_repo = device_repo
        self.user_repo = user_repo
        self.attendance_repo = attendance_repo
        self.logger = logging.getLogger(__name__)

    def _get_all_devices(self) -> List[Device]:
        """Get all configured devices."""
        try:
            devices = self.device_repo.get_all()
            if not devices:
                self.logger.warning("No devices configured")
            return devices
        except Exception as e:
            self.logger.error(f"Failed to get devices: {e}")
            raise DeviceOperationError(f"Failed to get devices: {str(e)}")

    def _update_device_status(self, device: Device, status: str, error_message: str = None) -> None:
        """Update device status in database."""
        try:
            device.status = status
            if error_message:
                device.last_error = error_message
            device.updated_at = datetime.now()
            device.save()
        except Exception as e:
            self.logger.error(f"Failed to update device status for {device.ip_address}: {e}")

    def _process_device_connection(self, device: Device) -> Optional[ZK]:
        """Process device connection with status updates."""
        try:
            zk = DeviceConnectionFactory.create_connection(device)
            self._update_device_status(device, "Online")
            return zk
        except DeviceConnectionError as e:
            self._update_device_status(device, "Offline", str(e))
            self.logger.error(f"Device connection failed: {e.message}")
            return None
        except Exception as e:
            self._update_device_status(device, "Error", str(e))
            self.logger.error(f"Unexpected error connecting to device {device.ip_address}: {e}")
            return None

    def check_devices(self) -> int:
        """
        Check the status of all configured devices.
        
        Returns:
            int: Number of online devices.
        """
        try:
            self.logger.info("Starting device status check")
            devices = self._get_all_devices()
            
            if not devices:
                self.notification_service.notify(
                    "Device Check", "No devices configured", "warning"
                )
                return 0

            online_count = 0
            total_devices = len(devices)

            for device in devices:
                try:
                    zk = self._process_device_connection(device)
                    if zk:
                        online_count += 1
                        zk.disconnect()
                except Exception as e:
                    self.logger.error(f"Error checking device {device.ip_address}: {e}")

            self.logger.info(f"Device check completed: {online_count}/{total_devices} devices online")
            
            # Send notification with results
            if online_count == 0:
                self.notification_service.notify(
                    "Device Check", "All devices are offline", "warning"
                )
            elif online_count < total_devices:
                self.notification_service.notify(
                    "Device Check", 
                    f"{online_count}/{total_devices} devices online", 
                    "warning"
                )
            else:
                self.notification_service.notify(
                    "Device Check", 
                    f"All {total_devices} devices are online", 
                    "info"
                )

            return online_count

        except Exception as e:
            self.logger.error(f"Failed to check devices: {e}")
            self.notification_service.notify(
                "Device Check", f"Failed to check devices: {str(e)}", "error"
            )
            raise DeviceOperationError(f"Failed to check devices: {str(e)}")

    def _extract_device_data(self, zk: ZK, device: Device) -> Dict[str, Any]:
        """Extract data from device."""
        try:
            # Get users
            users = zk.get_users()
            if users is None:
                users = []

            # Get attendance records
            attendance_records = zk.get_attendance()
            if attendance_records is None:
                attendance_records = []

            return {
                "users": users,
                "attendance": attendance_records,
                "device": device
            }
        except Exception as e:
            self.logger.error(f"Failed to extract data from device {device.ip_address}: {e}")
            raise DeviceOperationError(f"Failed to extract data from device {device.ip_address}: {str(e)}")

    def _save_users_to_database(self, users: List, device: Device) -> int:
        """Save users to database."""
        saved_count = 0
        for user in users:
            try:
                # Check if user already exists
                existing_user = self.user_repo.get_by_user_id(user.user_id)
                if not existing_user:
                    # Create new user
                    db_user = User(
                        user_id=user.user_id,
                        name=user.name,
                        privilege=user.privilege,
                        password=user.password,
                        group_id=user.group_id,
                        user_sns=user.user_sns,
                        card=user.card,
                        device=device,
                    )
                    db_user.save()
                    saved_count += 1
                    self.logger.debug(f"Saved new user: {user.name} (ID: {user.user_id})")
                else:
                    # Update existing user
                    existing_user.name = user.name
                    existing_user.privilege = user.privilege
                    existing_user.password = user.password
                    existing_user.group_id = user.group_id
                    existing_user.user_sns = user.user_sns
                    existing_user.card = user.card
                    existing_user.updated_at = datetime.now()
                    existing_user.save()
                    self.logger.debug(f"Updated existing user: {user.name} (ID: {user.user_id})")
            except Exception as e:
                self.logger.error(f"Failed to save user {user.user_id}: {e}")

        return saved_count

    def _save_attendance_to_database(self, attendance_records: List, device: Device) -> int:
        """Save attendance records to database."""
        saved_count = 0
        for record in attendance_records:
            try:
                # Get user for this attendance record
                db_user = self.user_repo.get_by_user_id(record.user_id)
                if not db_user:
                    self.logger.warning(f"User {record.user_id} not found for attendance record")
                    continue

                # Check if attendance record already exists
                existing_attendance = self.attendance_repo.get_by_device_user_timestamp(
                    device, db_user, record.timestamp
                )
                
                if not existing_attendance:
                    # Create new attendance record
                    from interfaces.database.models import Attendance
                    attendance = Attendance(
                        user=db_user,
                        device=device,
                        timestamp=record.timestamp,
                        status=record.status,
                        punch=record.punch,
                        uid=record.uid,
                        posted=False,
                    )
                    attendance.save()
                    saved_count += 1
                    self.logger.debug(f"Saved attendance record for user {db_user.name}")
            except Exception as e:
                self.logger.error(f"Failed to save attendance record: {e}")

        return saved_count

    def pull_data(self) -> None:
        """Pull data from all configured devices."""
        try:
            self.logger.info("Starting data pull from devices")
            devices = self._get_all_devices()
            
            if not devices:
                self.notification_service.notify(
                    "Data Pull", "No devices configured", "warning"
                )
                return

            total_users = 0
            total_attendance = 0
            processed_devices = 0

            for device in devices:
                try:
                    zk = self._process_device_connection(device)
                    if not zk:
                        continue

                    # Extract data from device
                    device_data = self._extract_device_data(zk, device)
                    
                    # Save users
                    users_saved = self._save_users_to_database(device_data["users"], device)
                    total_users += users_saved
                    
                    # Save attendance records
                    attendance_saved = self._save_attendance_to_database(device_data["attendance"], device)
                    total_attendance += attendance_saved
                    
                    processed_devices += 1
                    zk.disconnect()
                    
                    self.logger.info(
                        f"Device {device.ip_address}: {users_saved} users, {attendance_saved} attendance records"
                    )

                except Exception as e:
                    self.logger.error(f"Failed to pull data from device {device.ip_address}: {e}")

            # Send notification with results
            self.logger.info(
                f"Data pull completed: {processed_devices} devices processed, {total_users} users, {total_attendance} attendance records"
            )
            
            self.notification_service.notify(
                "Data Pull", 
                f"Data pulled from {processed_devices} devices: {total_users} users, {total_attendance} attendance records",
                "info"
            )

        except Exception as e:
            self.logger.error(f"Failed to pull data: {e}")
            self.notification_service.notify(
                "Data Pull", f"Failed to pull data: {str(e)}", "error"
            )
            raise DeviceOperationError(f"Failed to pull data: {str(e)}")

    def migrate_user_to_device(self) -> None:
        """Migrate users from database to devices."""
        try:
            self.logger.info("Starting user migration to devices")
            devices = self._get_all_devices()
            
            if not devices:
                self.notification_service.notify(
                    "Sync Users", "No devices found to sync users to", "warning"
                )
                return

            # Get all users from database
            users = self.user_repo.get_all()
            if not users:
                self.notification_service.notify(
                    "Sync Users", "No users found in database", "warning"
                )
                return

            migrated_count = 0
            total_devices = len(devices)

            for device in devices:
                try:
                    zk = self._process_device_connection(device)
                    if not zk:
                        continue

                    # Migrate users to device
                    for user in users:
                        try:
                            zk.set_user(
                                uid=user.user_id,
                                name=user.name,
                                privilege=user.privilege,
                                password=user.password,
                                group_id=user.group_id,
                                card=user.card,
                            )
                            migrated_count += 1
                            self.logger.debug(f"Migrated user {user.name} to device {device.ip_address}")
                        except Exception as e:
                            self.logger.error(f"Failed to migrate user {user.user_id} to device {device.ip_address}: {e}")

                    zk.disconnect()

                except Exception as e:
                    self.logger.error(f"Failed to migrate users to device {device.ip_address}: {e}")

            self.logger.info(f"User migration completed: {migrated_count} users migrated to {total_devices} devices")
            
            self.notification_service.notify(
                "Sync Users", 
                f"Migrated {migrated_count} users to {total_devices} devices",
                "info"
            )

        except Exception as e:
            self.logger.error(f"Failed to migrate users: {e}")
            self.notification_service.notify(
                "Sync Users", f"Failed to migrate users: {str(e)}", "error"
            )
            raise DeviceOperationError(f"Failed to migrate users: {str(e)}")
