# interfaces/database/models.py
from datetime import datetime

from peewee import *


class DatabaseFactory:
    """Factory for creating and configuring the database connection."""

    _db = None

    @classmethod
    def get_database(cls, db_path: str) -> SqliteDatabase:
        """
        Get or create a database connection.
        Args:
            db_path: Path to the SQLite database file.
        Returns:
            SqliteDatabase: Configured database instance.
        """
        if cls._db is None:
            cls._db = SqliteDatabase(db_path)
        return cls._db


db = DatabaseFactory.get_database("primesync.db")


class BaseModel(Model):
    """Base model with database configuration."""

    class Meta:
        database = db


class Device(BaseModel):
    """
    Model representing a ZKTeco device.
    Stores device connection details and status.
    """

    id = AutoField()
    ip_address = CharField(max_length=15, help_text="IPv4 address of the device")
    port = IntegerField(default=4370)
    password = CharField(max_length=32, default="0")
    device_model = CharField(max_length=50)
    status = CharField(max_length=20, default="Offline")
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "devices"


class User(BaseModel):
    """
    Model representing a user registered on a device.
    Stores user details and links to a device.
    """

    uid = IntegerField(primary_key=True)
    name = CharField(max_length=100)
    role = IntegerField(help_text="Privilege level on the device")
    password = CharField(max_length=128, null=True)
    group_id = IntegerField(null=True)
    user_id = CharField(
        max_length=50, unique=True, help_text="Application-specific user ID"
    )
    card = CharField(max_length=50, null=True, help_text="ID card number if applicable")
    user_cloud_id = IntegerField(null=True, help_text="Link to user record in cloud")
    device = ForeignKeyField(Device, backref="users", null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "users"


class Attendance(BaseModel):
    """
    Model representing an attendance record.
    Links to a user and stores punch details.
    """

    id = AutoField()
    user = ForeignKeyField(User, backref="attendances")
    timestamp = DateTimeField()
    status = CharField(max_length=20, help_text="Attendance status code")
    punch = CharField(max_length=20, help_text="Punch type (e.g., IN, OUT)")
    uid = IntegerField(null=True, help_text="Device-specific user identifier at punch")
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "attendance_logs"


class Settings(BaseModel):
    """
    Model for storing application settings.
    Includes cloud API credentials and configuration.
    """

    id = AutoField()
    cloud_api_url = CharField(max_length=255)
    username = CharField(max_length=100)
    password = CharField(max_length=256)  # Encrypted
    client_key = CharField(max_length=100)

    class Meta:
        table_name = "settings"


class Schedule(BaseModel):
    """
    Model for storing scheduled tasks (pull/push).
    Includes timing and status information.
    """

    id = AutoField()
    task_type = CharField(max_length=20, choices=(("pull", "Pull"), ("push", "Push")))
    schedule_time = CharField(max_length=5)  # Format: HH:MM
    enabled = BooleanField(default=True)
    last_run = DateTimeField(null=True)

    class Meta:
        table_name = "schedules"
