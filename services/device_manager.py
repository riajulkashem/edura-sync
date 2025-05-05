# services/device_manager.py
import logging
from datetime import datetime
from typing import List, Optional

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
    def create_connection(device: Device) -> Optional[ZK]:
        """
        Create a connection to a ZKTeco device.
        Args:
            device: Device model containing connection details.
        Returns:
            Optional[ZK]: Connected ZK instance or None if connection fails.
        Raises:
            DeviceConnectionError: If connection fails.
        """
        logger = logging.getLogger(__name__)
        try:
            zk = ZK(
                device.ip_address, port=device.port, password=device.password, timeout=5
            )
            conn = zk.connect()
            if conn:
                logger.debug(f"Connected to device {device.ip_address}:{device.port}")
                return zk
            else:
                raise DeviceConnectionError(
                    f"Failed to connect to device {device.ip_address}"
                )
        except Exception as e:
            logger.error(f"Device connection error for {device.ip_address}: {e}")
            raise DeviceConnectionError(
                f"Failed to connect to device {device.ip_address}: {str(e)}"
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
        self.logger.info("DeviceManager initialized")

    def check_devices(self) -> int:
        """
        Check the status of all registered devices and update their status.
        Returns:
            int: Number of online devices.
        """
        self.logger.info("Starting device status check")
        online_count = 0
        try:
            devices: List[Device] = self.device_repo.get_all()
            for device in devices:
                try:
                    zk = DeviceConnectionFactory.create_connection(device)
                    device.status = "Online"
                    online_count += 1
                    zk.disconnect()
                except DeviceConnectionError:
                    device.status = "Offline"
                finally:
                    self.device_repo.model.update(status=device.status).where(
                        self.device_repo.model.id == device.id
                    ).execute()
                    self.logger.info(
                        f"Checked device {device.ip_address}: {device.status}"
                    )

            self.logger.info(f"Device status check completed: {online_count} online")
            self.notification_service.notify(
                "Device Check",
                f"Checked {len(devices)} devices. {online_count} online.",
                "info",
            )
            return online_count
        except Exception as e:
            self.logger.error(f"Error checking devices: {e}")
            self.notification_service.notify(
                "Error", f"Failed to check devices: {str(e)}", "error"
            )
            return 0

    def pull_data(self) -> None:
        """Pull user and attendance data from all registered devices."""
        self.logger.info("Starting data pull from devices")
        try:
            devices: List[Device] = self.device_repo.get_all()
            for device in devices:
                try:
                    zk = DeviceConnectionFactory.create_connection(device)
                    # Pull users
                    users = zk.get_users()
                    user_count = len(users)
                    for zk_user in users:
                        self.user_repo.model.get_or_create(
                            uid=zk_user.uid,
                            defaults={
                                "name": zk_user.name,
                                "role": zk_user.privilege,
                                "password": zk_user.password,
                                "group_id": zk_user.group_id,
                                "user_id": zk_user.user_id,
                                "card": zk_user.card,
                                "device": device,
                                "created_at": datetime.now(),
                                "updated_at": datetime.now(),
                            },
                        )

                    # Pull attendance records
                    attendances = zk.get_attendance()
                    attendance_count = len(attendances)
                    for att in attendances:
                        user = self.user_repo.get_by_id(att.user_id)
                        if user:
                            self.attendance_repo.model.create(
                                user=user,
                                timestamp=att.timestamp,
                                status=att.status,
                                punch=att.punch,
                                uid=att.user_id,
                                created_at=datetime.now(),
                            )

                    zk.disconnect()
                    self.logger.info(
                        f"Pulled data from device {device.ip_address}: "
                        f"{user_count} users, {attendance_count} attendance records"
                    )
                except DeviceConnectionError as e:
                    self.logger.error(
                        f"Failed to pull data from device {device.ip_address}: {e}"
                    )
                    continue

            self.logger.info("Data pull completed successfully")
            self.notification_service.notify(
                "Data Pull", "Data pulled from devices successfully", "info"
            )
        except Exception as e:
            self.logger.error(f"Error pulling data: {e}")
            self.notification_service.notify(
                "Error", f"Failed to pull data: {str(e)}", "error"
            )
