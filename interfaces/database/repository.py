from peewee import DoesNotExist, fn
from interfaces.database.models import Device, User, Attendance, Settings, db
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

    def delete_cascade(self, device: Device) -> bool:
        """
        Delete a device and all of its dependent records in the correct order:
          1. Attendance rows that reference this device directly
          2. Attendance rows that belong to users of this device
          3. User rows that belong to this device
          4. The device itself

        All steps run inside a single atomic transaction so the DB is never left
        in a partially-deleted state.

        Returns:
            True if the device was deleted, False otherwise.
        """
        with db.atomic():
            # 1. Attendance rows linked to this device via their own device FK
            att_del = Attendance.delete().where(Attendance.device == device).execute()
            self.logger.info(f"Cascade-deleted {att_del} attendance rows (device FK) for device {device.ip_address}")

            # 2. Attendance rows belonging to users of this device
            user_ids = [u.id for u in User.select(User.id).where(User.device == device)]
            if user_ids:
                att_usr_del = Attendance.delete().where(Attendance.user.in_(user_ids)).execute()
                self.logger.info(f"Cascade-deleted {att_usr_del} attendance rows (user FK) for device {device.ip_address}")

            # 3. Users belonging to this device
            usr_del = User.delete().where(User.device == device).execute()
            self.logger.info(f"Cascade-deleted {usr_del} users for device {device.ip_address}")

            # 4. The device itself
            deleted = device.delete_instance()
            self.logger.info(f"Deleted device {device.ip_address} (rows affected: {deleted})")
            return deleted == 1

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
        Negative lookups (user not found) are also cached to avoid repeated DB hits
        during attendance processing when many device records have no matching cloud user.
        Raises:
            DatabaseError: If a database error occurs.
        """
        from datetime import datetime

        _MISSING = object.__new__(object)  # sentinel stored once at module level would be cleaner
        # Use a module-level sentinel to distinguish "cached None" from "not cached".
        # We store None directly and use the timestamps dict as the presence indicator.
        if user_id in self._cache_timestamps:
            cache_time = self._cache_timestamps[user_id]
            if (datetime.now() - cache_time).total_seconds() < self._cache_ttl:
                return self._user_cache.get(user_id)  # returns None for negative cache entries
            # Expired — evict
            self._user_cache.pop(user_id, None)
            del self._cache_timestamps[user_id]

        # Fetch from database
        user = self.get(user_id=user_id)

        # Enforce max cache size (evict oldest)
        if len(self._cache_timestamps) >= self._max_cache_size:
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            self._user_cache.pop(oldest_key, None)
            del self._cache_timestamps[oldest_key]

        # Cache both hits AND misses (None) so repeated lookups for unknown users are cheap.
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
        Get user statistics in two queries instead of the previous four.

        Query 1: GROUP BY user_type to get per-type counts and a total.
        Query 2: COUNT saved_to_device = True.

        Returns:
            Dictionary with user counts by type and status
        """
        result = {
            "total": 0,
            "students": 0,
            "teachers": 0,
            "staff": 0,
            "saved_to_device": 0,
            "unsaved_to_device": 0,
        }

        # Single GROUP BY query covers total + per-type counts.
        for row in (
            self.model.select(
                self.model.user_type,
                fn.COUNT(self.model.id).alias("count"),
            ).group_by(self.model.user_type)
        ):
            result["total"] += row.count
            if row.user_type == "STUDENT":
                result["students"] = row.count
            elif row.user_type == "TEACHER":
                result["teachers"] = row.count
            elif row.user_type == "STAFF":
                result["staff"] = row.count

        # Single query for saved/unsaved split.
        saved = (
            self.model.select(fn.COUNT(self.model.id))
            .where(self.model.saved_to_device)
            .scalar() or 0
        )
        result["saved_to_device"] = saved
        result["unsaved_to_device"] = result["total"] - saved

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

    def _format_record(self, record) -> Optional[Dict]:
        """
        Convert a single Attendance ORM record to the cloud API payload dict.
        Returns None if the record cannot be formatted (e.g. missing device).
        """
        user = record.user
        device = record.device

        if device is None:
            self.logger.warning(
                f"Attendance record id={record.id} has no associated device. Skipping."
            )
            return None

        # Use cloud_id for device; fallback to local id with a warning.
        if device.cloud_id is not None:
            device_id = device.cloud_id
        else:
            device_id = device.id
            self.logger.warning(
                f"Device {device.ip_address} (id={device.id}) has no cloud_id. Using local id {device.id}."
            )

        # Normalise timestamp to datetime if it arrived as a string.
        ts = record.timestamp
        if isinstance(ts, str):
            try:
                from dateutil import parser as _dp
                ts = _dp.parse(ts)
            except ImportError:
                from datetime import datetime as _dt
                try:
                    ts = _dt.fromisoformat(ts.split(".")[0])
                except Exception:
                    pass

        return {
            "device": device_id,
            "user_id": user.user_id,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "status": str(record.status),
            "punch": str(record.punch),
            "is_student": user.user_type == "STUDENT",
            "is_teacher": user.user_type == "TEACHER",
            "is_staff": user.user_type == "STAFF",
            "id": record.id,
        }

    def cloud_format(self) -> List[Dict]:
        """
        Format ALL pending attendance records for the cloud API.
        Uses a JOIN to fetch user data in a single query.
        Raises:
            DatabaseError: If a database error occurs.
        """
        pending_records = (
            self.model.select(self.model, User)
            .join(User)
            .where(~self.model.posted)
            .order_by(self.model.timestamp.desc())
        )

        formatted_data = []
        for record in pending_records:
            item = self._format_record(record)
            if item is not None:
                self.logger.debug(f"Formatted attendance record: {item}")
                formatted_data.append(item)

        return formatted_data

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """
        Return the most recent *pending* attendance records formatted for display.
        Applies LIMIT at the SQL level so the full table is never loaded for UI purposes.
        """
        recent_records = (
            self.model.select(self.model, User)
            .join(User)
            .where(~self.model.posted)
            .order_by(self.model.timestamp.desc())
            .limit(limit)
        )

        result = []
        for record in recent_records:
            item = self._format_record(record)
            if item is not None:
                result.append(item)
        return result

    def get_all_with_user(self) -> list:
        """
        Return all attendance records with user data pre-fetched (single JOIN query).
        Used by the Attendance screen for the full filterable table.
        """
        return list(
            self.model.select(self.model, User)
            .join(User)
            .order_by(self.model.timestamp.desc())
        )

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


_SETTINGS_NOT_CACHED = object()  # Sentinel distinguishing "no cache" from "cached None"


class SettingsRepository(BaseRepository):
    """Repository for Settings model operations."""

    def __init__(self):
        super().__init__(Settings)
        self._settings_cache = _SETTINGS_NOT_CACHED  # Use sentinel, not None

    def get_settings(self):
        """
        Get the first (and only) settings record.
        Implements caching for better performance.
        Both a found record AND a missing record (None) are cached so that
        repeated calls before default settings are created don't hit the DB.
        Raises:
            DatabaseError: If a database error occurs.
        """
        if self._settings_cache is not _SETTINGS_NOT_CACHED:
            return self._settings_cache

        settings = self.get()
        self._settings_cache = settings  # Cache hit or None
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
            if "created_at" in data and data["created_at"] is None:
                del data["created_at"]
            if "updated_at" in data and data["updated_at"] is None:
                del data["updated_at"]
            result = self.create(**data)

        # Reset cache so the next read fetches the fresh record.
        self._settings_cache = _SETTINGS_NOT_CACHED
        return result