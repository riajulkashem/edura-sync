import logging
from peewee import *
from interfaces.database.models import db, Settings, Device, User, Attendance

class BaseRepository:
    """Base repository with common functionality for all repositories."""
    
    def __init__(self):
        """Initialize the repository with a logger."""
        self.logger = logging.getLogger(self.__class__.__name__)


class SettingsRepository(BaseRepository):
    """Repository for settings data."""

    def __init__(self):
        """Initialize with Settings model."""
        super().__init__()
        self.model = Settings

    def get_settings(self):
        """Get application settings."""
        try:
            with db.atomic():
                return self.model.get_or_none(id=1)
        except Exception as e:
            self.logger.error(f"Failed to retrieve settings: {e}")
            return None

    def save_settings(self, data):
        """Save application settings."""
        print(f'save settings called: {data}')
        try:
            with db.atomic():
                try:
                    # Attempt to retrieve the settings object with id=1
                    settings = self.model.get(id=1)
                    print(f'retrieved existing settings: {settings}')
                except self.model.DoesNotExist:
                    # If it doesn’t exist, create a new object with id=1 and the provided data
                    settings = self.model.create(id=1, **data)
                    print(f'created new settings: {settings}')
                else:
                    # If it exists, update its fields with the provided data
                    for key, value in data.items():
                        if hasattr(settings, key):
                            setattr(settings, key, value)
                    settings.save()
                    print(f'updated existing settings: {settings}')
            print(f'after saved settings: {settings}')
            return settings
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            raise

class DeviceRepository(BaseRepository):
    """Repository for device data."""
    
    def __init__(self):
        """Initialize with Device model."""
        super().__init__()
        self.model = Device
    
    def get_all(self):
        """Get all devices."""
        try:
            return list(self.model.select())
        except Exception as e:
            self.logger.error(f"Failed to get all devices: {e}")
            return []
    
    def get_by_id(self, device_id):
        """Get device by ID."""
        try:
            return self.model.get_or_none(self.model.id == device_id)
        except Exception as e:
            self.logger.error(f"Failed to get device by ID {device_id}: {e}")
            return None
    
    def count_online(self):
        """Count online devices."""
        try:
            return self.model.select().where(self.model.status == "Online").count()
        except Exception as e:
            self.logger.error(f"Failed to count online devices: {e}")
            return 0
    
    def count_total(self):
        """Count total devices."""
        try:
            return self.model.select().count()
        except Exception as e:
            self.logger.error(f"Failed to count total devices: {e}")
            return 0

class UserRepository(BaseRepository):
    """Repository for user data."""
    
    def __init__(self):
        """Initialize with User model."""
        super().__init__()
        self.model = User
    
    def get_all(self):
        """Get all users."""
        try:
            return list(self.model.select())
        except Exception as e:
            self.logger.error(f"Failed to get all users: {e}")
            return []
    
    def get_by_id(self, user_id):
        """Get user by ID."""
        try:
            return self.model.get_or_none(self.model.user_id == user_id)
        except Exception as e:
            self.logger.error(f"Failed to get user by ID {user_id}: {e}")
            return None
    
    def count_total(self):
        """Count total users."""
        try:
            return self.model.select().count()
        except Exception as e:
            self.logger.error(f"Failed to count total users: {e}")
            return 0

class AttendanceRepository(BaseRepository):
    """Repository for attendance data."""
    
    def __init__(self):
        """Initialize with Attendance model."""
        super().__init__()
        self.model = Attendance
    
    def get_all(self):
        """Get all attendance records."""
        try:
            return list(self.model.select().join(User))
        except Exception as e:
            self.logger.error(f"Failed to get all attendance records: {e}")
            return []