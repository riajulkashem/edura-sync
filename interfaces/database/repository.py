from peewee import DoesNotExist, fn
from interfaces.database.models import Device, User, Attendance, Settings
from interfaces.database.base_repository import BaseRepository
from core.exceptions import DatabaseError
from typing import List, Dict, Optional
import logging


class DeviceRepository(BaseRepository):
    """Repository for Device model operations."""
    
    def __init__(self):
        super().__init__(Device)
        self.logger = logging.getLogger(__name__)
    
    def get_by_ip(self, ip_address: str) -> Optional[Device]:
        """
        Get device by IP address with index optimization.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            return self.model.get(self.model.ip_address == ip_address)
        except DoesNotExist:
            return None
        except Exception as e:
            raise DatabaseError(f"Error getting device by IP {ip_address}: {e}")

    def get_online_devices(self) -> List[Device]:
        """
        Get all online devices using status index.
        
        Returns:
            List of online devices
        """
        try:
            return list(
                self.model.select()
                .where(self.model.status == "Online")
                .order_by(self.model.ip_address)
            )
        except Exception as e:
            raise DatabaseError(f"Error getting online devices: {e}")

    def get_device_stats(self) -> Dict[str, int]:
        """
        Get device statistics efficiently.
        
        Returns:
            Dictionary with device counts by status
        """
        try:
            stats = (
                self.model.select(
                    self.model.status,
                    fn.COUNT(self.model.id).alias('count')
                )
                .group_by(self.model.status)
            )
            
            result = {"total": 0, "online": 0, "offline": 0, "error": 0}
            for stat in stats:
                result["total"] += stat.count
                if stat.status.lower() == "online":
                    result["online"] = stat.count
                elif stat.status.lower() == "offline":
                    result["offline"] = stat.count
                elif stat.status.lower() == "error":
                    result["error"] = stat.count
                    
            return result
        except Exception as e:
            raise DatabaseError(f"Error getting device stats: {e}")

    def update_device_status_bulk(self, device_statuses: Dict[int, str]) -> int:
        """
        Update multiple device statuses efficiently.
        
        Args:
            device_statuses: Dictionary of device_id: status
            
        Returns:
            int: Number of devices updated
        """
        try:
            updated_count = 0
            for device_id, status in device_statuses.items():
                updated_count += self.update_bulk(
                    data={"status": status},
                    ids=[device_id]
                )
            return updated_count
        except Exception as e:
            raise DatabaseError(f"Error updating device statuses: {e}")


class UserRepository(BaseRepository):
    """Repository for User model operations."""
    
    def __init__(self):
        super().__init__(User)
        self.logger = logging.getLogger(__name__)
    
    def get_by_user_id(self, user_id: str) -> Optional[User]:
        """
        Get user by user_id field with index optimization.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            return self.model.get(self.model.user_id == user_id)
        except DoesNotExist:
            return None
        except Exception as e:
            raise DatabaseError(f"Error getting user by user_id {user_id}: {e}")

    def get_unsaved_to_device(self, device_id: Optional[int] = None) -> List[User]:
        """
        Get users not yet saved to device(s).
        Uses composite index for performance.
        
        Args:
            device_id: Optional device ID to filter by
            
        Returns:
            List of users not saved to device
        """
        try:
            query = self.model.select().where(self.model.saved_to_device == False)
            if device_id:
                query = query.where(self.model.device_id == device_id)
            return list(query)
        except Exception as e:
            raise DatabaseError(f"Error getting unsaved users: {e}")

    def get_by_device(self, device_id: int) -> List[User]:
        """
        Get all users for a specific device.
        Uses device_id index for performance.
        """
        try:
            return list(
                self.model.select()
                .where(self.model.device_id == device_id)
                .order_by(self.model.name)
            )
        except Exception as e:
            raise DatabaseError(f"Error getting users by device {device_id}: {e}")

    def mark_as_saved_to_device(self, user_ids: List[int]) -> int:
        """
        Mark multiple users as saved to device efficiently.
        
        Args:
            user_ids: List of user IDs
            
        Returns:
            int: Number of users updated
        """
        try:
            return self.update_bulk(
                data={"saved_to_device": True},
                ids=user_ids
            )
        except Exception as e:
            raise DatabaseError(f"Error marking users as saved: {e}")


class AttendanceRepository(BaseRepository):
    """Repository for Attendance model operations."""
    
    def __init__(self):
        super().__init__(Attendance)
        self.logger = logging.getLogger(__name__)

    def get_pending(self) -> List[Attendance]:
        """
        Get all pending attendance records with optimized query.
        Uses index on (posted, timestamp) for better performance.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            return list(
                self.model.select()
                .where(self.model.posted == False)
                .order_by(self.model.timestamp.desc())
            )
        except Exception as e:
            raise DatabaseError(f"Error getting pending attendance: {e}")

    def get_pending_count(self) -> int:
        """
        Get count of pending attendance records efficiently.
        Returns:
            int: Number of pending records
        """
        try:
            return (
                self.model.select(fn.COUNT(self.model.id))
                .where(self.model.posted == False)
                .scalar()
            )
        except Exception as e:
            raise DatabaseError(f"Error counting pending attendance: {e}")

    def get_by_device_user_timestamp(self, device, user, timestamp) -> Optional[Attendance]:
        """
        Get attendance record by device, user, and timestamp.
        Uses composite index for performance.
        """
        try:
            return self.model.get(
                (self.model.user == user) & 
                (self.model.timestamp == timestamp)
            )
        except DoesNotExist:
            return None
        except Exception as e:
            raise DatabaseError(f"Error getting attendance by device/user/timestamp: {e}")

    def mark_as_posted(self, attendance_ids: List[int]) -> int:
        """
        Mark multiple attendance records as posted efficiently.
        
        Args:
            attendance_ids: List of attendance record IDs
            
        Returns:
            int: Number of records updated
        """
        try:
            return self.update_bulk(
                data={"posted": True},
                ids=attendance_ids
            )
        except Exception as e:
            raise DatabaseError(f"Error marking attendance as posted: {e}")

    def cloud_format(self) -> List[Dict]:
        """
        Format attendance data for cloud API with optimized query.
        Uses joins to reduce database queries.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            # Use join to get user data in single query
            pending_records = (
                self.model.select(self.model, User)
                .join(User)
                .where(self.model.posted == False)
                .order_by(self.model.timestamp.desc())
            )
            
            formatted_data = []
            for record in pending_records:
                formatted_record = {
                    "id": record.id,
                    "user_id": record.user.user_id,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                    "status": record.status,
                    "punch": record.punch,
                    "uid": record.uid
                }
                formatted_data.append(formatted_record)
                
            return formatted_data
        except Exception as e:
            raise DatabaseError(f"Error formatting attendance data: {e}")


class SettingsRepository(BaseRepository):
    """Repository for Settings model operations."""
    
    def __init__(self):
        super().__init__(Settings)

    def get_settings(self):
        """
        Get the first (and only) settings record.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            return self.get()
        except Exception as e:
            raise DatabaseError(f"Error getting settings: {e}")

    def save_settings(self, **data):
        """
        Save settings, creating a new record if none exists.
        Raises:
            DatabaseError: If a database error occurs.
        """
        from datetime import datetime
        try:
            settings = self.get_settings()
            if settings:
                return self.update(settings, **data)
            else:
                # Ensure created_at and updated_at are set for new records
                data['created_at'] = data.get('created_at', datetime.now())
                data['updated_at'] = data.get('updated_at', datetime.now())
                return self.create(**data)
        except Exception as e:
            raise DatabaseError(f"Error saving settings: {e}")
