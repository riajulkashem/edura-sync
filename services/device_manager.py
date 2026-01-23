# services/device_manager.py
import logging
from typing import List, Optional

from zk import ZK

# Removed ConnectionError import as try-catch blocks were removed
from interfaces.database.models import Device
from interfaces.database.repository import (
    DeviceRepository,
    UserRepository,
    AttendanceRepository,
)
from services.notification import NotificationService
from services.device_utils import DeviceConnectionManager, extract_device_data
from interfaces.database.models import User

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
        self.connection_manager = DeviceConnectionManager()
        self.background_mode = False  # Set to True for minimal resource usage

    def _get_all_devices(self) -> List[Device]:
        """Get all configured devices."""
        devices = self.device_repo.get_all()
        if not devices:
            self.logger.warning("No devices configured")
        return devices

    def _process_device_connection(self, device: Device) -> Optional[ZK]:
        """Process device connection with status updates and proper resource management."""
        try:
            zk = self.connection_manager.create_connection(device)
            self.connection_manager.update_device_status(device, "Online")
            return zk
        except Exception as e:
            # Update device status to offline and clear any previous error
            self.connection_manager.update_device_status(device, "Offline", str(e))
            return None

    def _safe_disconnect(self, zk: ZK, device_ip: str) -> None:
        """Safely disconnect from device with error handling."""
        self.connection_manager.safe_disconnect(zk, device_ip)


    def check_devices(self) -> int:
        """
        Check the status of all configured devices.
        
        Returns:
            int: Number of online devices.
        """
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
            zk = self._process_device_connection(device)
            if zk:
                online_count += 1
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

    def _save_users_to_database(self, users: List, device: Device) -> int:
        """Save users to database with batch processing for better performance."""
        if not users:
            return 0
            
        saved_count = 0
        batch_size = 100  # Process users in batches
        
        # Process users in batches for better performance
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            batch_users = []
            update_users = []
            
            for user in batch:
                # Match user by user_id (cloud ID) - device returns user_id which should be cloud ID
                user_id_str = str(user.user_id).strip()
                existing_user = self.user_repo.get_by_user_id(user_id_str)

                if not existing_user:
                    # User not found - skip creating new user from device
                    # Users should be synced from cloud first to get proper cloud ID
                    self.logger.warning(
                        f"User with cloud ID '{user_id_str}' not found in database. "
                        f"User should be synced from cloud first. Skipping user from device."
                    )
                    continue
                else:
                    # Update existing user with device data
                    update_data = {
                        'name': getattr(user, 'name', existing_user.name),
                        'role': getattr(user, 'privilege', existing_user.role),
                        'password': getattr(user, 'password', existing_user.password),
                        'group_id': getattr(user, 'group_id', existing_user.group_id),
                        'card': getattr(user, 'card', existing_user.card),
                        'device_code': getattr(user, 'uid', existing_user.device_code),  # Store device UID for reference
                        'saved_to_device': True  # Mark as saved since it's on device
                    }
                    self.user_repo.update(existing_user, **update_data)
                    update_users.append(existing_user)
            
            # Bulk insert new users
            if batch_users:
                saved_count += self.user_repo.create_bulk(batch_users)
                self.logger.debug(f"Batch inserted {len(batch_users)} users")
            
            saved_count += len(update_users)
        
        # Clear user cache after updates to prevent stale data
        if saved_count > 0:
            self.user_repo.clear_cache()
            
        self.logger.info(f"Processed {len(users)} users: {saved_count} saved/updated")
        return saved_count

    def _save_attendance_to_database(self, attendance_records: List, device: Device) -> int:
        """Save attendance records to database with batch processing and duplicate prevention."""
        if not attendance_records:
            return 0
        
        from datetime import timezone
            
        saved_count = 0
        batch_size = 200  # Process attendance in larger batches
        
        # Process attendance in batches for better performance
        for i in range(0, len(attendance_records), batch_size):
            batch = attendance_records[i:i + batch_size]
            batch_attendance = []
            
            for record in batch:
                # Match user by user_id (cloud ID) - device returns user_id which should be cloud ID
                raw_user_id = str(getattr(record, 'user_id', ''))
                db_user = self.user_repo.get_by_user_id(raw_user_id)

                if not db_user:
                    self.logger.warning(
                        f"User with cloud ID '{raw_user_id}' not found for attendance record. "
                        f"User should be synced from cloud first. Skipping attendance record."
                    )
                    continue

                # Check for duplicate attendance record (basic deduplication)
                record_timestamp = getattr(record, 'timestamp', None)
                if record_timestamp:
                    # Ensure timezone aware - assume UTC if naive
                    if record_timestamp.tzinfo is None:
                        record_timestamp = record_timestamp.replace(tzinfo=timezone.utc)
                    
                    existing_attendance = self.attendance_repo.get_by_device_user_timestamp(
                        device, db_user, record_timestamp
                    )
                    if existing_attendance:
                        continue  # Skip duplicate
                
                # Prepare attendance data for batch insert
                attendance_data = {
                    'user': db_user,
                    'device': device,
                    'timestamp': record_timestamp,
                    'status': getattr(record, 'status', ''),
                    'punch': getattr(record, 'punch', ''),
                    'uid': getattr(record, 'uid', None),
                    'posted': False,
                }
                batch_attendance.append(attendance_data)
            
            # Bulk insert attendance records
            if batch_attendance:
                saved_count += self.attendance_repo.create_bulk(batch_attendance)
                self.logger.debug(f"Batch inserted {len(batch_attendance)} attendance records")
        
        self.logger.info(f"Processed {len(attendance_records)} attendance records: {saved_count} saved")
        return saved_count

    def pull_data(self) -> None:
        """Pull data from all configured devices."""
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
            zk = self._process_device_connection(device)
            if not zk:
                continue

            # Extract data from device - limit to 14 days in background mode to save memory/cpu
            days_limit = 14 if self.background_mode else None
            device_data = extract_device_data(zk, device, days_limit=days_limit)
            
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

    def migrate_user_to_device(self) -> None:
        """Migrate users from database to devices."""
        self.logger.info("Starting user migration to devices")
        devices = self._get_all_devices()
        
        # Debug: Check if devices is actually a list
        if not isinstance(devices, list):
            self.logger.error(f"Expected list but got {type(devices)}: {devices}")
            self.notification_service.notify(
                "Sync Users", "Invalid device data type", "error"
            )
            return
        
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
            # Get users assigned to THIS specific device
            users = self.user_repo.get_by_device(device.id)
            if not users:
                self.logger.info(f"No users assigned to device {device.ip_address}, skipping upload.")
                continue

            zk = None
            zk = self._process_device_connection(device)
            if not zk:
                continue

            # Migrate users to device
            device_migrated_ids = []
            for user in users:
                # Handle None values for optional fields
                card_value = user.card if user.card is not None else 0
                group_id_value = user.group_id if user.group_id is not None else 0
                
                try:
                    zk.set_user(
                        uid=user.id,  # Use local DB id for device uid
                        name=user.name,
                        privilege=user.role,
                        password=user.password,
                        group_id=group_id_value,
                        card=card_value,
                        user_id=user.user_id,  # Use cloud ID for device user_id
                    )
                    device_migrated_ids.append(user.id)
                    self.logger.debug(f"Migrated user {user.name} (cloud ID: {user.user_id}) to device {device.ip_address}")
                except Exception as e:
                    self.logger.error(f"Failed to migrate user {user.name}: {e}")

            if device_migrated_ids:
                migrated_count += len(device_migrated_ids)
                # Mark users as saved in database
                self.user_repo.mark_as_saved_to_device(device_migrated_ids)
                self.logger.info(f"Migrated {len(device_migrated_ids)} users to device {device.ip_address}")

            self._safe_disconnect(zk, device.ip_address)

        self.logger.info(f"User migration completed: {migrated_count} users migrated to {total_devices} devices")
        
        self.notification_service.notify(
            "Sync Users", 
            f"Migrated {migrated_count} users to {total_devices} devices",
            "info"
        )

    def reset_device(self, device: Device) -> bool:
        """Clear all data from a device."""
        self.logger.info(f"Attempting to reset device {device.ip_address}")
        zk = self._process_device_connection(device)
        if not zk:
            return False
            
        try:
            zk.disable_device()
            # Clear logs
            zk.clear_attendance()
            # Clear users (clear_data clears users and other records)
            zk.clear_data()
            self.logger.info(f"Successfully reset device {device.ip_address}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset device {device.ip_address}: {e}")
            return False
        finally:
            try:
                zk.enable_device()
                self._safe_disconnect(zk, device.ip_address)
            except Exception:
                pass

    def upload_user_to_device(self, device: Device, user: User) -> bool:
        """Upload a single user profile to a specific device."""
        self.logger.info(f"Uploading user {user.name} to device {device.ip_address}")
        zk = self._process_device_connection(device)
        if not zk:
            return False
            
        try:
            zk.disable_device()
            # Handle numeric values for ZK
            card_value = int(user.card) if user.card and str(user.card).isdigit() else 0
            group_id_value = int(user.group_id) if user.group_id is not None else 0
            
            zk.set_user(
                uid=user.id,  # Use local DB id for device uid
                name=user.name,
                privilege=user.role,
                password=user.password or '',
                group_id=group_id_value,
                card=card_value,
                user_id=user.user_id  # Use cloud ID for device user_id
            )
            
            # Mark user as saved to device
            self.user_repo.mark_as_saved_to_device([user.id])
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload user {user.name} to {device.ip_address}: {e}")
            return False
        finally:
            try:
                zk.enable_device()
                self._safe_disconnect(zk, device.ip_address)
            except Exception:
                pass