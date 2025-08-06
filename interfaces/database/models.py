import os
from datetime import datetime
import logging
from pathlib import Path

from peewee import *

from core.constants import DEFAULT_DB_NAME, DB_PRAGMAS, TABLE_NAMES, DEVICE_DEFAULTS
from core.validation import Validator, ValidationError


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

    def save(self, *args, **kwargs):
        """Override save to add validation."""
        self.validate()
        return super().save(*args, **kwargs)

    def validate(self):
        """Base validation method - override in subclasses."""
        pass


class Device(BaseModel):
    id = AutoField()
    ip_address = CharField(
        max_length=15, help_text="IPv4 address of the device", index=True
    )
    port = IntegerField(default=DEVICE_DEFAULTS["PORT"])
    password = CharField(max_length=32, default=DEVICE_DEFAULTS["PASSWORD"])
    device_model = CharField(max_length=50, index=True)
    status = CharField(max_length=20, default=DEVICE_DEFAULTS["STATUS"], index=True)
    created_at = DateTimeField(default=datetime.now, index=True)

    class Meta:
        table_name = TABLE_NAMES["DEVICES"]
        indexes = (
            (("ip_address", "port"), True),  # Unique index on IP and port combination
        )

    def validate(self):
        """Validate device data before saving."""
        try:
            Validator.validate_ip_address(self.ip_address)
            Validator.validate_port(self.port)
            Validator.validate_device_model(self.device_model)
        except ValidationError as e:
            raise ValidationError(f"Device validation failed: {e.message}")


class User(BaseModel):
    uid = IntegerField(primary_key=True)
    name = CharField(max_length=100)
    user_type = CharField(
        max_length=20,
        choices=[('STUDENT', 'Student'), ('TEACHER', 'Teacher'), ('STAFF', 'Staff')],
        default='STUDENT',
        help_text="User type: STUDENT, TEACHER, or STAFF",
        index=True
    )
    role = IntegerField(help_text="Privilege level on the device")
    password = CharField(max_length=128, null=True)
    group_id = IntegerField(null=True)
    user_id = CharField(
        max_length=50, unique=True, help_text="Application-specific user ID", index=True
    )
    card = CharField(max_length=50, null=True, help_text="ID card number if applicable")
    device_code = IntegerField(
        null=True, help_text="User ID on the device", index=True
    )
    device = ForeignKeyField(Device, backref="users", null=True, index=True)
    saved_to_device = BooleanField(default=False, index=True)
    created_at = DateTimeField(default=datetime.now, index=True)
    updated_at = DateTimeField(default=datetime.now, index=True)

    class Meta:
        table_name = TABLE_NAMES["USERS"]
        indexes = (
            (("user_id", "device"), False),  # Non-unique index for queries
            (("saved_to_device", "device"), False),  # Index for migration queries
        )

    def validate(self):
        """Validate user data before saving."""
        try:
            Validator.validate_user_id(self.user_id)
            if self.name and len(self.name.strip()) == 0:
                raise ValidationError("User name cannot be empty")
            if self.user_type not in ['STUDENT', 'TEACHER', 'STAFF']:
                raise ValidationError("User type must be STUDENT, TEACHER, or STAFF")
        except ValidationError as e:
            raise ValidationError(f"User validation failed: {e.message}")


class Attendance(BaseModel):
    id = AutoField()
    user = ForeignKeyField(User, backref="attendances", index=True)
    timestamp = DateTimeField(index=True)
    status = CharField(max_length=20, help_text="Attendance status code", index=True)
    punch = CharField(max_length=20, help_text="Punch type (e.g., IN, OUT)", index=True)
    uid = IntegerField(null=True, help_text="Device-specific user identifier at punch")
    created_at = DateTimeField(default=datetime.now, index=True)
    posted = BooleanField(default=False, index=True)

    class Meta:
        table_name = TABLE_NAMES["ATTENDANCE"]
        indexes = (
            (("user", "timestamp"), False),  # Index for user attendance queries
            (("timestamp", "posted"), False),  # Index for sync queries
            (
                ("user", "timestamp", "posted"),
                False,
            ),  # Composite index for complex queries
        )

    def validate(self):
        """Validate attendance data before saving."""
        if not self.user:
            raise ValidationError("Attendance record must have an associated user")
        if not self.timestamp:
            raise ValidationError("Attendance record must have a timestamp")


class Settings(BaseModel):
    cloud_api_url = CharField(default="", index=True)
    username = CharField(default="")
    password = CharField(default="", help_text="Encrypted password")
    institute_id = CharField(default="", index=True)
    auth_token = CharField(default="", null=True)
    in_time_process = TimeField(null=True)
    out_time_process = TimeField(null=True)
    last_sync = DateTimeField(null=True, index=True)
    last_post = DateTimeField(null=True, index=True)
    attendance_pending = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now, index=True)

    class Meta:
        table_name = TABLE_NAMES["SETTINGS"]

    def validate(self):
        """Validate settings data before saving."""
        try:
            if self.cloud_api_url:
                Validator.validate_url(self.cloud_api_url)
            if self.username:
                Validator.validate_username(self.username)
            if self.password:
                Validator.validate_password(self.password)
            if self.institute_id:
                Validator.validate_institute_id(self.institute_id)
        except ValidationError as e:
            raise ValidationError(f"Settings validation failed: {e.message}")


def create_indexes():
    """Create additional indexes for performance optimization."""
    try:
        # Create indexes for common query patterns
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_attendance_user_timestamp ON attendance_logs (user_id, timestamp)"
        )
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_attendance_posted ON attendance_logs (posted)"
        )
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_user_device ON users (device_id)"
        )
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_user_saved ON users (saved_to_device)"
        )
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_device_status ON devices (status)"
        )
        db.execute_sql(
            "CREATE INDEX IF NOT EXISTS idx_settings_sync ON settings (last_sync)"
        )

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create database indexes: {e}")


def initialize_database():
    """Initialize database with tables and indexes."""
    try:
        # Create tables
        db.create_tables([Device, User, Attendance, Settings], safe=True)

        # Create indexes
        create_indexes()

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
