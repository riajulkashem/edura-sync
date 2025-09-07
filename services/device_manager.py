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
        Create a connection to a ZKTeco device with enhanced retry logic and exponential backoff.
        
        Args:
            device: Device model containing connection details.
            max_retries: Maximum number of connection attempts.
            retry_delay: Initial delay between retry attempts in seconds.
            
        Returns:
            Optional[ZK]: Connected ZK instance or None if connection fails.
            
        Raises:
            DeviceConnectionError: If connection fails after all retries.
        """
        logger = logging.getLogger(__name__)
        last_exception = None

        for attempt in range(max_retries):
            try:
                # Calculate exponential backoff delay
                current_delay = retry_delay * (2 ** attempt)
                
                logger.debug(
                    f"Connection attempt {attempt + 1}/{max_retries} for {device.ip_address}:{device.port}"
                )
                
                zk = ZK(
                    device.ip_address,
                    port=device.port,
                    password=device.password,
                    timeout=10,  # Increased timeout for better reliability
                )
                
                conn = zk.connect()
                if conn:
                    logger.info(
                        f"Successfully connected to device {device.ip_address}:{device.port} on attempt {attempt + 1}"
                    )
                    return zk
                else:
                    raise DeviceConnectionError(
                        f"Failed to establish connection to device {device.ip_address}"
                    )
                    
            except DeviceConnectionError as e:
                last_exception = e
                logger.warning(f"Device connection error on attempt {attempt + 1}: {e.message}")
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Connection attempt {attempt + 1} failed for {device.ip_address}: {str(e)}"
                )
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                logger.debug(f"Waiting {current_delay:.1f}s before retry...")
                time.sleep(current_delay)
        
        # All attempts failed
        error_msg = f"Failed to connect to device {device.ip_address} after {max_retries} attempts"
        if last_exception:
            error_msg += f": {str(last_exception)}"
            
        logger.error(error_msg)
        raise DeviceConnectionError(error_msg)


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
        """Process device connection with status updates and proper resource management."""
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

    def _safe_disconnect(self, zk: ZK, device_ip: str) -> None:
        """Safely disconnect from device with error handling."""
        try:
            if zk:
                zk.disconnect()
                self.logger.debug(f"Disconnected from device {device_ip}")
        except Exception as e:
            self.logger.warning(f"Error disconnecting from device {device_ip}: {e}")

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
                zk = None
                try:
                    zk = self._process_device_connection(device)
                    if zk:
                        online_count += 1
                except Exception as e:
                    self.logger.error(f"Error checking device {device.ip_address}: {e}")
                finally:
                    self._safe_disconnect(zk, device.ip_address)

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
        """Save users to database with batch processing for better performance."""
        if not users:
            return 0
            
        saved_count = 0
        batch_size = 100  # Process users in batches
        
        try:
            # Process users in batches for better performance
            for i in range(0, len(users), batch_size):
                batch = users[i:i + batch_size]
                batch_users = []
                update_users = []
                
                for user in batch:
                    try:
                        # Check if user already exists
                        existing_user = self.user_repo.get_by_user_id(user.user_id)
                        if not existing_user:
                            # Prepare for batch insert
                            user_data = {
                                'uid': getattr(user, 'uid', 0),
                                'user_id': user.user_id,
                                'name': getattr(user, 'name', ''),
                                'role': getattr(user, 'privilege', 0),
                                'password': getattr(user, 'password', ''),
                                'group_id': getattr(user, 'group_id', None),
                                'card': getattr(user, 'card', None),
                                'device': device,
                                'saved_to_device': False
                            }
                            batch_users.append(user_data)
                        else:
                            # Update existing user
                            update_data = {
                                'name': getattr(user, 'name', existing_user.name),
                                'role': getattr(user, 'privilege', existing_user.role),
                                'password': getattr(user, 'password', existing_user.password),
                                'group_id': getattr(user, 'group_id', existing_user.group_id),
                                'card': getattr(user, 'card', existing_user.card),
                            }
                            self.user_repo.update(existing_user, **update_data)
                            update_users.append(existing_user)
                            
                    except Exception as e:
                        self.logger.error(f"Error processing user {getattr(user, 'user_id', 'unknown')}: {e}")
                        continue
                
                # Bulk insert new users
                if batch_users:
                    try:
                        saved_count += self.user_repo.create_bulk(batch_users)
                        self.logger.debug(f"Batch inserted {len(batch_users)} users")
                    except Exception as e:
                        self.logger.error(f"Error in batch insert: {e}")
                        # Fallback to individual inserts
                        for user_data in batch_users:
                            try:
                                self.user_repo.create(**user_data)
                                saved_count += 1
                            except Exception as e2:
                                self.logger.error(f"Error inserting user {user_data.get('user_id')}: {e2}")
                
                saved_count += len(update_users)
                
            self.logger.info(f"Processed {len(users)} users: {saved_count} saved/updated")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"Error in batch user processing: {e}")
            raise DeviceOperationError(f"Failed to save users to database: {str(e)}")

    def _save_attendance_to_database(self, attendance_records: List, device: Device) -> int:
        """Save attendance records to database with batch processing and duplicate prevention."""
        if not attendance_records:
            return 0
            
        saved_count = 0
        batch_size = 200  # Process attendance in larger batches
        
        try:
            # Process attendance in batches for better performance
            for i in range(0, len(attendance_records), batch_size):
                batch = attendance_records[i:i + batch_size]
                batch_attendance = []
                
                for record in batch:
                    try:
                        # Get user for this attendance record
                        db_user = self.user_repo.get_by_user_id(str(getattr(record, 'user_id', '')))
                        if not db_user:
                            self.logger.warning(f"User {getattr(record, 'user_id', 'unknown')} not found for attendance record")
                            continue

                        # Check for duplicate attendance record (basic deduplication)
                        record_timestamp = getattr(record, 'timestamp', None)
                        if record_timestamp:
                            existing_attendance = self.attendance_repo.get_by_device_user_timestamp(
                                device, db_user, record_timestamp
                            )
                            if existing_attendance:
                                continue  # Skip duplicate
                        
                        # Prepare attendance data for batch insert
                        attendance_data = {
                            'user': db_user,
                            'timestamp': record_timestamp,
                            'status': getattr(record, 'status', ''),
                            'punch': getattr(record, 'punch', ''),
                            'uid': getattr(record, 'uid', None),
                            'posted': False,
                        }
                        batch_attendance.append(attendance_data)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing attendance record: {e}")
                        continue
                
                # Bulk insert attendance records
                if batch_attendance:
                    try:
                        saved_count += self.attendance_repo.create_bulk(batch_attendance)
                        self.logger.debug(f"Batch inserted {len(batch_attendance)} attendance records")
                    except Exception as e:
                        self.logger.error(f"Error in batch attendance insert: {e}")
                        # Fallback to individual inserts
                        for att_data in batch_attendance:
                            try:
                                self.attendance_repo.create(**att_data)
                                saved_count += 1
                            except Exception as e2:
                                self.logger.error(f"Error inserting attendance record: {e2}")
            
            self.logger.info(f"Processed {len(attendance_records)} attendance records: {saved_count} saved")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"Error in batch attendance processing: {e}")
            raise DeviceOperationError(f"Failed to save attendance to database: {str(e)}")

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
                zk = None
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
                    
                    self.logger.info(
                        f"Device {device.ip_address}: {users_saved} users, {attendance_saved} attendance records"
                    )

                except Exception as e:
                    self.logger.error(f"Failed to pull data from device {device.ip_address}: {e}")
                finally:
                    self._safe_disconnect(zk, device.ip_address)

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
                zk = None
                try:
                    zk = self._process_device_connection(device)
                    if not zk:
                        continue

                    # Migrate users to device
                    device_migrated = 0
                    for user in users:
                        try:
                            zk.set_user(
                                uid=user.uid,
                                name=user.name,
                                privilege=user.role,
                                password=user.password,
                                group_id=user.group_id,
                                card=user.card,
                            )
                            device_migrated += 1
                            self.logger.debug(f"Migrated user {user.name} to device {device.ip_address}")
                        except Exception as e:
                            self.logger.error(f"Failed to migrate user {user.user_id} to device {device.ip_address}: {e}")

                    migrated_count += device_migrated
                    self.logger.info(f"Migrated {device_migrated} users to device {device.ip_address}")

                except Exception as e:
                    self.logger.error(f"Failed to migrate users to device {device.ip_address}: {e}")
                finally:
                    self._safe_disconnect(zk, device.ip_address)

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
