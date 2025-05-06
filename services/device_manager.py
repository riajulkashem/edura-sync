import logging
from datetime import datetime
from typing import List

from zk import ZK

from core.exceptions import DeviceConnectionError
from interfaces.database.models import Device
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
    def create_connection(device: Device) -> ZK:
        """
        Create and return a live connection to a ZKTeco device.
        Raises DeviceConnectionError on failure.
        """
        logger = logging.getLogger(__name__)
        try:
            zk = ZK(
                device.ip_address,
                port=device.port,
                password=device.password,
                timeout=5,
            )
            conn = zk.connect()
            if not conn:
                raise DeviceConnectionError(
                    f"Failed to connect to device {device.ip_address}:{device.port}"
                )
            logger.debug(f"Connected to device {device.ip_address}:{device.port}")
            return conn
        except Exception as e:
            logger.error(f"Device connection error for {device.ip_address}: {e}")
            raise DeviceConnectionError(
                f"Failed to connect to device {device.ip_address}:{e}"
            )


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
        self.notification_service = notification_service
        self.device_repo = device_repo
        self.user_repo = user_repo
        self.attendance_repo = attendance_repo
        self.logger = logging.getLogger(__name__)
        self.logger.info("DeviceManager initialized")

    def check_devices(self) -> int:
        """
        Check the status of all registered devices and update their status in the DB.
        Returns the number of online devices.
        """
        self.logger.info("Starting device status check")
        online_count = 0
        try:
            devices: List[Device] = self.device_repo.get_all()
            for device in devices:
                try:
                    conn = DeviceConnectionFactory.create_connection(device)
                    self.device_repo.update(device, status="Online")
                    online_count += 1
                    conn.disconnect()
                    self.logger.debug(
                        f"Checked device {device.ip_address}: Online"
                    )
                except DeviceConnectionError:
                    self.device_repo.update(device, status="Offline")
                    self.logger.info(
                        f"Checked device {device.ip_address}: Offline"
                    )

            self.logger.info(f"Device status check completed: {online_count} online")
            return online_count
        except Exception as e:
            self.logger.error(f"Error checking devices: {e}")
            self.notification_service.notify(
                "Error", f"Failed to check devices: {e}", "error"
            )
            return 0

    def pull_data(self) -> None:
        """Pull attendance data from all registered devices."""
        self.logger.info("Starting data pull from devices")
        try:
            devices: List[Device] = self.device_repo.get_all()
            for device in devices:
                try:
                    conn = DeviceConnectionFactory.create_connection(device)
                    conn.disable_device()

                    attendances = conn.get_attendance()
                    total = len(attendances)
                    print(f'device pull attendances: {attendances} length: {len(attendances)}')
                    for att in attendances:
                        existing = self.attendance_repo.filter(
                            user_id=att.user_id,
                            timestamp=att.timestamp,
                            status=att.status,
                        )
                        print(f'existing: {existing} for attendance: {att} length: {len(existing)}')
                        if not existing:
                            self.attendance_repo.create(
                                user_id=att.user_id,
                                timestamp=att.timestamp,
                                status=att.status,
                                punch=att.punch,
                                created_at=datetime.now(),
                                device_id=device.cloud_id,
                            )

                    conn.enable_device()
                    conn.disconnect()
                    self.logger.info(
                        f"Pulled {total} attendance records from {device.ip_address}"
                    )
                except DeviceConnectionError as e:
                    self.logger.error(
                        f"Failed to pull data from {device.ip_address}: {e}"
                    )
                    continue

            self.logger.info("Data pull completed successfully")
            self.notification_service.notify(
                "Data Pull", "Data pulled from devices successfully", "info"
            )
        except Exception as e:
            self.logger.error(f"Error pulling data: {e}")
            self.notification_service.notify(
                "Error", f"Failed to pull data: {e}", "error"
            )

    def migrate_user_to_device(self) -> None:
        """Migrate users from the database to connected devices."""
        self.logger.info("Starting user migration to devices")
        devices = self.device_repo.get_all()
        total_users = 0
        devices_updated = 0

        for device in devices:
            try:
                conn = DeviceConnectionFactory.create_connection(device)
                conn.disable_device()
                self.logger.debug(f"Device connected: {device.ip_address}")

                # Fetch users not yet saved to this device
                users = self.user_repo.filter(
                    saved_to_device=False,
                    device=device.id,
                )

                self.logger.debug(f"{users.count()} users to migrate for device {device.ip_address}")

                migrated = 0
                for user in users:
                    conn.set_user(
                        uid=int(user.user_id),
                        name=user.name,
                        privilege=user.role,
                        password=user.password,
                        group_id=user.group_id,
                        user_id=user.user_id,
                        card=user.card,
                    )
                    self.user_repo.update(user, saved_to_device=True)
                    migrated += 1
                    self.logger.info(
                        f"Migrated user {user.user_id} to {device.ip_address}"
                    )

                conn.enable_device()
                conn.disconnect()

                if migrated:
                    total_users += migrated
                    devices_updated += 1
                    self.logger.info(
                        f"Successfully migrated {migrated} users to {device.ip_address}"
                    )
                else:
                    self.logger.info(
                        f"No new users for {device.ip_address}"
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to sync users to {device.ip_address}: {e}"
                )

        if total_users:
            self.notification_service.notify(
                "Users Synced",
                f"Migrated {total_users} users across {devices_updated} devices",
                "info",
            )
        else:
            self.notification_service.notify(
                "Sync Complete",
                "No new users needed syncing",
                "info",
            )

        self.logger.info(
            f"User migration completed: {total_users} users -> {devices_updated} devices"
        )

    def clear_device_logs(self, device: Device) -> bool:
        zk = ZK(device.ip_address, port=device.port, password=device.password, timeout=5)
        conn = None
        try:
            conn = zk.connect()
            conn.disable_device()
            success = conn.clear_attendance()
            conn.enable_device()
            return success
        except Exception as e:
            raise DeviceConnectionError(f"Failed to clear logs: {e}")
        finally:
            if conn:
                conn.disconnect()

    def clear_all_device_logs(self) -> int:
        """
        Clear attendance logs on all registered devices.
        Returns the number of devices successfully cleared.
        """
        devices = self.device_repo.get_all()
        total_cleared = 0
        for device in devices:
            try:
                success = self.clear_device_logs(device)
                if success:
                    total_cleared += 1
                    self.logger.info(f"Cleared logs for {device.ip_address}")
                else:
                    self.logger.warning(f"Failed to clear logs for {device.ip_address}")
            except DeviceConnectionError as e:
                self.logger.error(f"Failed to clear logs for {device.ip_address}: {e}")
        self.notification_service.notify(
            "Clear Logs",
            f"Cleared attendance logs on {total_cleared}/{len(devices)} devices",
            "info"
        )
        return total_cleared

    def clear_all_user_logs(self) -> int:
        """
        Clear all user data (users & templates) on all registered devices.
        Returns the number of devices successfully cleared.
        """
        devices = self.device_repo.get_all()
        total_cleared = 0
        for device in devices:
            conn = None
            try:
                conn = DeviceConnectionFactory.create_connection(device)
                conn.disable_device()
                success = conn.clear_data()
                conn.enable_device()
                if success:
                    total_cleared += 1
                    self.logger.info(f"Cleared user data for {device.ip_address}")
                else:
                    self.logger.warning(f"Failed to clear user data for {device.ip_address}")
            except Exception as e:
                self.logger.error(f"Failed to clear user data for {device.ip_address}: {e}")
            finally:
                if conn:
                    conn.disconnect()
        self.notification_service.notify(
            "Clear Users",
            f"Cleared user data on {total_cleared}/{len(devices)} devices",
            "info"
        )
        return total_cleared
