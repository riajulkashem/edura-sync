# interfaces/database/repository.py
from typing import List, Optional
from datetime import datetime
from peewee import ModelSelect
from .models import Device, User, Attendance, Settings, Schedule, db


class BaseRepository:
    """Base repository class for database operations."""

    def __init__(self, model):
        self.model = model

    def get_all(self) -> List:
        """Retrieve all records."""
        with db.atomic():
            return list(self.model.select())

    def get_by_id(self, id: int) -> Optional[ModelSelect]:
        """Retrieve a record by ID."""
        with db.atomic():
            return self.model.get_or_none(id=id)


class DeviceRepository(BaseRepository):
    """Repository for Device model operations."""

    def __init__(self):
        super().__init__(Device)

    def count_online(self) -> int:
        """Count online devices."""
        with db.atomic():
            return self.model.select().where(self.model.status == "Online").count()

    def count_total(self) -> int:
        """Count total devices."""
        with db.atomic():
            return self.model.select().count()


class UserRepository(BaseRepository):
    """Repository for User model operations."""

    def __init__(self):
        super().__init__(User)

    def count_total(self) -> int:
        """Count total users."""
        with db.atomic():
            return self.model.select().count()


class AttendanceRepository(BaseRepository):
    """Repository for Attendance model operations."""

    def __init__(self):
        super().__init__(Attendance)


class SettingsRepository(BaseRepository):
    """Repository for Settings model operations."""

    def __init__(self):
        super().__init__(Settings)

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
        try:
            with db.atomic():
                settings, created = self.model.get_or_create(id=1)
                for key, value in data.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
                settings.save()
            return settings
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            raise


class ScheduleRepository(BaseRepository):
    """Repository for Schedule model operations."""

    def __init__(self):
        super().__init__(Schedule)

    def get_by_task_type(self, task_type: str) -> Optional[Schedule]:
        """Retrieve schedule by task type."""
        with db.atomic():
            return self.model.get_or_none(task_type=task_type)

    def update_last_run(self, schedule_id: int, last_run: datetime) -> None:
        """Update the last run time for a schedule."""
        with db.atomic():
            schedule = self.model.get_or_none(id=schedule_id)
            if schedule:
                schedule.last_run = last_run
                schedule.save()