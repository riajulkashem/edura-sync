import logging
from datetime import datetime
from zk import ZK
from models import Device, User, Attendance, Schedule


class DeviceManager:
    """Manages communication with ZKTeco devices."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def check_devices(self):
        """Check status of all devices."""
        try:
            online_count = 0
            for device in Device.select():
                try:
                    zk = ZK(device.ip_address, port=device.port, password=device.password, timeout=5)
                    conn = zk.connect()
                    if conn:
                        device.status = "Online"
                        online_count += 1
                        conn.disconnect()
                    else:
                        device.status = "Offline"
                    device.save()
                    self.logger.info(f"Checked device {device.ip_address}: {device.status}")
                except Exception as e:
                    device.status = "Offline"
                    device.save()
                    self.logger.error(f"Failed to connect to device {device.ip_address}: {e}")
            self.logger.info(f"Device status check completed: {online_count} online")
            self.show_notification("Device Check", f"Checked {Device.select().count()} devices. {online_count} online.",
                                   "info")
            return online_count
        except Exception as e:
            self.logger.error(f"Error checking devices: {e}")
            self.show_notification("Error", "Failed to check devices.", "error")
            return 0

    def pull_data(self):
        """Pull attendance data from devices."""
        try:
            for device in Device.select():
                try:
                    zk = ZK(device.ip_address, port=device.port, password=device.password, timeout=5)
                    conn = zk.connect()
                    if conn:
                        users = zk.get_users()
                        for user in users:
                            User.get_or_create(
                                uid=user.uid,
                                defaults={
                                    "name": user.name,
                                    "role": user.privilege,
                                    "password": user.password,
                                    "group_id": user.group_id,
                                    "user_id": user.user_id,
                                    "card": user.card,
                                    "device": device,
                                    "created_at": datetime.now(),
                                    "updated_at": datetime.now()
                                }
                            )

                        attendances = zk.get_attendance()
                        for att in attendances:
                            user = User.get_or_none(User.uid == att.user_id)
                            if user:
                                Attendance.create(
                                    user=user,
                                    timestamp=att.timestamp,
                                    status=att.status,
                                    punch=att.punch,
                                    uid=att.user_id,
                                    created_at=datetime.now()
                                )
                        conn.disconnect()
                        self.logger.info(f"Pulled data from device {device.ip_address}")
                except Exception as e:
                    self.logger.error(f"Failed to pull data from device {device.ip_address}: {e}")

            pull_schedule = Schedule.get_or_none(task_type="pull")
            if pull_schedule:
                pull_schedule.last_run = datetime.now()
                pull_schedule.save()

            self.logger.info("Data pull completed")
            self.show_notification("Data Pull", "Data pulled from devices successfully", "info")
        except Exception as e:
            self.logger.error(f"Error pulling data: {e}")
            self.show_notification("Error", "Failed to pull data.", "error")

    def show_notification(self, title: str, message: str, type: str):
        """Delegate notification to GUI."""
        try:
            from gui import PrimeSyncGUI
            PrimeSyncGUI.show_notification(self, title, message, type)
        except Exception as e:
            self.logger.error(f"Failed to delegate notification: {e}")