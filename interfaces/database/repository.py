from peewee import DoesNotExist
from interfaces.database.models import Device, User, Attendance, Settings
from interfaces.database.base_repository import BaseRepository
from core.exceptions import DatabaseError


class DeviceRepository(BaseRepository):
    """Repository for Device model operations."""
    
    def __init__(self):
        super().__init__(Device)
    
    def get_by_ip(self, ip_address: str):
        """
        Get device by IP address.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            return self.model.get(self.model.ip_address == ip_address)
        except DoesNotExist:
            return None
        except Exception as e:
            raise DatabaseError(f"Error getting device by IP {ip_address}: {e}")


class UserRepository(BaseRepository):
    """Repository for User model operations."""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_user_id(self, user_id: str):
        """
        Get user by user_id field.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            return self.model.get(self.model.user_id == user_id)
        except DoesNotExist:
            return None
        except Exception as e:
            raise DatabaseError(f"Error getting user by user_id {user_id}: {e}")


class AttendanceRepository(BaseRepository):
    """Repository for Attendance model operations."""
    
    def __init__(self):
        super().__init__(Attendance)

    def get_pending(self):
        """
        Get all pending attendance records.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            return list(self.model.select().where(self.model.posted == False))
        except Exception as e:
            raise DatabaseError(f"Error getting pending attendance: {e}")

    def cloud_format(self):
        """
        Format attendance data for cloud API.
        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            pending_records = self.get_pending()
            formatted_data = []
            
            for record in pending_records:
                formatted_record = {
                    "user_id": record.user_id,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                    "device_id": record.device_id,
                    "status": record.status,
                    "type": record.type
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
