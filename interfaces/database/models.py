import os
from datetime import datetime
import logging
from pathlib import Path

from peewee import (
    SqliteDatabase,
    Model,
    AutoField,
    CharField,
    IntegerField,
    DateTimeField,
    ForeignKeyField,
    BooleanField,
    TimeField,
)

from core.constants import DEFAULT_DB_NAME, DB_PRAGMAS, TABLE_NAMES, DEVICE_DEFAULTS


# Create a logger
logger = logging.getLogger(__name__)


class DatabaseFactory:
    """Factory for creating and configuring the database connection."""

    _db = None

    @classmethod
    def get_database(cls, db_path: str = DEFAULT_DB_NAME) -> SqliteDatabase:
        """
        Get or create a database connection.
        Args:
            db_path: Path to the SQLite database file.
        Returns:
            SqliteDatabase: Configured database instance.
        """
        if cls._db is None:
            logger.info(f"Initializing database with path: {db_path}")

            # If path is relative, use current directory
            if not os.path.isabs(db_path):
                # Get the project root directory (current working directory)
                project_dir = Path.cwd()
                db_path = str(project_dir / db_path)
                logger.info(f"Using absolute path: {db_path}")

            # Ensure parent directory exists
            db_dir = os.path.dirname(db_path)
            if db_dir:  # Only create directory if there is a path
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Ensured database directory exists: {db_dir}")

            cls._db = SqliteDatabase(db_path, pragmas=DB_PRAGMAS)
            logger.info(f"Database created at {db_path}")
        return cls._db


# Initialize with a default path - this will be replaced in main.py
db = DatabaseFactory.get_database()


class BaseModel(Model):
    class Meta:
        database = db


class Device(BaseModel):
    id = AutoField()
    ip_address = CharField(max_length=15, help_text="IPv4 address of the device")
    port = IntegerField(default=DEVICE_DEFAULTS["PORT"])
    password = CharField(max_length=32, default=DEVICE_DEFAULTS["PASSWORD"])
    name = CharField(max_length=50)
    status = CharField(max_length=20, default=DEVICE_DEFAULTS["STATUS"])
    created_at = DateTimeField(default=datetime.now)
    cloud_id = IntegerField(null=True)

    class Meta:
        table_name = TABLE_NAMES["DEVICES"]


class User(BaseModel):
    uid = IntegerField(primary_key=True)
    name = CharField(max_length=100)
    role = IntegerField(help_text="Privilege level on the device", default=0)
    password = CharField(max_length=128, null=True, default="")
    group_id = CharField(null=True, default="")
    user_id = CharField(
        max_length=50, unique=True, help_text="Application-specific user ID"
    )
    card = CharField(max_length=50, null=True, help_text="ID card number if applicable")
    user_cloud_id = IntegerField(null=True, help_text="Link to user record in cloud")
    device = ForeignKeyField(Device, backref="users", null=True)
    saved_to_device = BooleanField(default=False)
    device_cloud_id = IntegerField(null=True, help_text="Link to user record in cloud")
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = TABLE_NAMES["USERS"]


class Attendance(BaseModel):
    id = AutoField()
    user_id = IntegerField(help_text="User ID")
    device_id = IntegerField(help_text="Device ID")
    timestamp = DateTimeField()
    status = CharField(max_length=20, help_text="Attendance status code")
    punch = CharField(max_length=20, help_text="Punch type (e.g., IN, OUT)")
    uid = IntegerField(null=True, help_text="Device-specific user identifier at punch")
    created_at = DateTimeField(default=datetime.now)
    posted = BooleanField(default=False)

    class Meta:
        table_name = TABLE_NAMES["ATTENDANCE"]


class Settings(BaseModel):
    cloud_api_url = CharField(default="")
    username = CharField(default="")
    password = CharField(default="", help_text="Encrypted password")
    institute_id = CharField(default="")
    auth_token = CharField(default="", null=True)
    process_time = TimeField(null=True)
    is_scheduler_enabled = BooleanField(default=False)
    last_sync = DateTimeField(null=True)
    last_post = DateTimeField(null=True)
    attendance_pending = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = TABLE_NAMES["SETTINGS"]
