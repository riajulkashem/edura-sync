from peewee import DoesNotExist, fn
from interfaces.database.models import Device, User, Attendance, Settings
from interfaces.database.base_repository import BaseRepository
from core.exceptions import DatabaseError  # noqa: F401
from typing import List, Dict, Optional
import logging


class DeviceRepository(BaseRepository):
    """Repository for Device model operations."""
    
    def __init__(self):
        super().__init__(Device)
        self.logger = logging.getLogger(__name__)
        self._cache = {}  # Simple cache for frequently accessed data
    
    def get_by_ip(self, ip_address: str) -> Optional[Device]:
        """
        Get device by IP address with index optimization.
        Raises:
            DatabaseError: If a database error occurs.
        """
        return self.get(ip_address=ip_address)

    def get_by_cloud_id(self, cloud_id: int) -> Optional[Device]:
        """
        Get device by cloud_id field.
        """
        return self.get(cloud_id=cloud_id)

    def clear_cache(self):
        """Clear the device cache."""
        self._cache.clear()

    def get_online_devices(self) -> List[Device]:
        """
        Get all online devices using status index.
        
        Returns:
            List of online devices
        """
        return list(
            self.model.select()
            .where(self.model.status == "Online")
            .order_by(self.model.ip_address)
        )

    def get_device_stats(self) -> Dict[str, int]:
        """
        Get device statistics efficiently.
        
        Returns:
            Dictionary with device counts by status
        """
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

    def update_device_status_bulk(self, device_statuses: Dict[int, str]) -> int:
        """
        Update multiple device statuses efficiently.
        
        Args:
            device_statuses: Dictionary of device_id: status
            
        Returns:
            int: Number of devices updated
        """
        updated_count = 0
        for device_id, status in device_statuses.items():
            updated_count += self.update_bulk(
                data={"status": status},
                ids=[device_id]
            )
        return updated_count


class UserRepository(BaseRepository):
    """Repository for User model operations."""
    
    def __init__(self):
        super().__init__(User)
        self.logger = logging.getLogger(__name__)
        self._user_cache = {}  # Cache for user lookups
        self._cache_timestamps = {}  # Track when entries were cached
        self._cache_ttl = 300  # 5-minute TTL in seconds
        self._max_cache_size = 1000  # Maximum cache entries
    
    def get_by_user_id(self, user_id: str) -> Optional[User]:
        """
        Get user by user_id field with index optimization.
        Uses caching with TTL for frequently accessed users.
        Raises:
            DatabaseError: If a database error occurs.
        """
        from datetime import datetime
        
        # Check cache first
        if user_id in self._user_cache:
            # Check if entry is still valid (within TTL)
            cache_time = self._cache_timestamps.get(user_id)
            if cache_time and (datetime.now() - cache_time).total_seconds() < self._cache_ttl:
                return self._user_cache[user_id]
            else:
                # Expired, remove from cache
                del self._user_cache[user_id]
                del self._cache_timestamps[user_id]
        
        # Fetch from database
        user = self.get(user_id=user_id)
        
        # Cache the result
        if user:
            # Enforce max cache size
            if len(self._user_cache) >= self._max_cache_size:
                # Remove oldest entry
                if self._cache_timestamps:
                    oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
                    del self._user_cache[oldest_key]
                    del self._cache_timestamps[oldest_key]
            
            self._user_cache[user_id] = user
            self._cache_timestamps[user_id] = datetime.now()
        
        return user

    def get_unsaved_to_device(self, device_id: Optional[int] = None) -> List[User]:
        """
        Get users not yet saved to device(s).
        Uses composite index for performance.
        
        Args:
            device_id: Optional device ID to filter by
            
        Returns:
            List of users not saved to device
        """
        query = self.model.select().where(~self.model.saved_to_device)
        if device_id:
            query = query.where(self.model.device_id == device_id)
        return list(query)

    def get_by_device(self, device_id: int) -> List[User]:
        """
        Get all users for a specific device.
        Uses device_id index for performance.
        """
        return list(
            self.model.select()
            .where(self.model.device_id == device_id)
            .order_by(self.model.name)
        )

    def get_user_stats(self) -> Dict[str, int]:
        """
        Get user statistics efficiently.
        
        Returns:
            Dictionary with user counts by type and status
        """
        # Get total users
        total_users = self.model.select().count()
        
        # Get users by type
        user_types = (
            self.model.select(
                self.model.user_type,
                fn.COUNT(self.model.id).alias('count')
            )
            .group_by(self.model.user_type)
        )
        
        # Get users by saved status
        saved_count = (
            self.model.select(fn.COUNT(self.model.id))
            .where(self.model.saved_to_device)
            .scalar()
        )
        
        unsaved_count = (
            self.model.select(fn.COUNT(self.model.id))
            .where(~self.model.saved_to_device)
            .scalar()
        )
        
        result = {
            "total": total_users,
            "students": 0,
            "teachers": 0,
            "staff": 0,
            "saved_to_device": saved_count or 0,
            "unsaved_to_device": unsaved_count or 0
        }
        
        # Count by user type
        for user_type in user_types:
            if user_type.user_type == 'STUDENT':
                result["students"] = user_type.count
            elif user_type.user_type == 'TEACHER':
                result["teachers"] = user_type.count
            elif user_type.user_type == 'STAFF':
                result["staff"] = user_type.count
        
        return result

    def mark_as_saved_to_device(self, user_ids: List[int]) -> int:
        """
        Mark multiple users as saved to device efficiently.
        
        Args:
            user_ids: List of user IDs
            
        Returns:
            int: Number of users updated
        """
        return self.update_bulk(
            data={"saved_to_device": True},
            ids=user_ids
        )

    def count_by_device(self, device: Device) -> int:
        """
        Count all users associated with a device.
        Returns total users for the device, regardless of saved_to_device status.
        """
        return (
            self.model.select()
            .where(self.model.device == device)
            .count()
        )
    
    def clear_cache(self):
        """Clear the user cache and timestamps."""
        self._user_cache.clear()
        self._cache_timestamps.clear()


class AttendanceRepository(BaseRepository):
    """Repository for Attendance model operations."""
    
    def __init__(self):
        super().__init__(Attendance)
        self.logger = logging.getLogger(__name__)
        self._pending_cache = None
        self._pending_cache_time = None

    def get_pending(self) -> List[Attendance]:
        """
        Get all pending attendance records with optimized query.
        Uses index on (posted, timestamp) for better performance.
        Implements caching for better performance.
        Raises:
            DatabaseError: If a database error occurs.
        """
        return list(
            self.model.select()
            .where(~self.model.posted)
            .order_by(self.model.timestamp.desc())
        )

    def get_pending_count(self) -> int:
        """
        Get count of pending attendance records efficiently.
        Returns:
            int: Number of pending records
        """
        return (
            self.model.select(fn.COUNT(self.model.id))
            .where(~self.model.posted)
            .scalar()
        )

    def get_by_device_user_timestamp(self, device, user, timestamp) -> Optional[Attendance]:
        """
        Get attendance record by device, user, and timestamp.
        Uses composite index for performance.
        """
        try:
            return self.model.get(
                (self.model.device == device) &
                (self.model.user == user) & 
                (self.model.timestamp == timestamp)
            )
        except DoesNotExist:
            return None

    def mark_as_posted(self, attendance_ids: List[int]) -> int:
        """
        Mark multiple attendance records as posted efficiently.
        
        Args:
            attendance_ids: List of attendance record IDs
            
        Returns:
            int: Number of records updated
        """
        result = self.update_bulk(
            data={"posted": True},
            ids=attendance_ids
        )
        # Clear cache when data changes
        self._pending_cache = None
        return result

    def cloud_format(self) -> List[Dict]:
        """
        Format attendance data for cloud API with optimized query.
        Uses joins to reduce database queries and includes readable status/punch values.
        Raises:
            DatabaseError: If a database error occurs.
        """
        # Use join to get user data in single query
        pending_records = (
            self.model.select(self.model, User)
            .join(User)
            .where(~self.model.posted)
            .order_by(self.model.timestamp.desc())
        )
        
        formatted_data = []
        for record in pending_records:
            user = record.user
            device = record.device
            
            # Use cloud_id for device, fallback to local id if cloud_id is not set
            device_id = device.cloud_id if device.cloud_id is not None else device.id
            if device.cloud_id is None:
                self.logger.warning(
                    f"Device {device.ip_address} (id={device.id}) has no cloud_id. Using local id {device.id}."
                )
            
            # Format timestamp safely
            ts = record.timestamp
            if isinstance(ts, str):
                try:
                    from dateutil import parser
                    ts = parser.parse(ts)
                except ImportError:
                    from datetime import datetime
                    try:
                        ts = datetime.fromisoformat(ts.split('.')[0]) # Basic fallback
                    except Exception:
                        pass

            formatted_record = {
                "device": device_id,
                "user_id": user.user_id,  # This should be the cloud ID (numeric string like "7596")
                "timestamp": ts.strftime('%Y-%m-%d %H:%M:%S'),
                "status": str(record.status),
                "punch": str(record.punch),
                "is_student": user.user_type == 'STUDENT',
                "is_teacher": user.user_type == 'TEACHER',
                "is_staff": user.user_type == 'STAFF',
                # Internal ID for post-processing
                "id": record.id
            }
            self.logger.debug(f"Formatted attendance record: {formatted_record}")
            formatted_data.append(formatted_record)
            
        return formatted_data

    def cleanup_posted_attendance(self, days_old=1) -> int:
        """
        Delete posted attendance records older than N days.
        Args:
            days_old: Number of days to keep records for reference.
        Returns:
            int: Number of records deleted.
        """
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days_old)
        
        deleted = (
            self.model.delete()
            .where(
                (self.model.posted) & 
                (self.model.timestamp < cutoff)
            )
            .execute()
        )
        return deleted


class SettingsRepository(BaseRepository):
    """Repository for Settings model operations."""
    
    def __init__(self):
        super().__init__(Settings)
        self._settings_cache = None

    def get_settings(self):
        """
        Get the first (and only) settings record.
        Implements caching for better performance.
        Raises:
            DatabaseError: If a database error occurs.
        """
        # Return cached settings if available
        if self._settings_cache:
            return self._settings_cache
            
        settings = self.get()
        # Cache the result
        self._settings_cache = settings
        return settings

    def save_settings(self, **data):
        """
        Save settings, creating a new record if none exists.
        Clears cache when settings are updated.
        Raises:
            DatabaseError: If a database error occurs.
        """
        settings = self.get_settings()
        if settings:
            result = self.update(settings, **data)
        else:
            # Remove timestamp fields from data if they're None, let the model handle them
            if 'created_at' in data and data['created_at'] is None:
                del data['created_at']
            if 'updated_at' in data and data['updated_at'] is None:
                del data['updated_at']
            result = self.create(**data)
        
        # Clear cache when settings are updated
        self._settings_cache = None
        return result