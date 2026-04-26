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
    def reset(cls) -> None:
        """Reset the singleton so a new database path can be used (e.g. fallback path)."""
        cls._db = None

    @classmethod
    def _build_db(cls, db_path: str, pragmas: dict) -> SqliteDatabase:
        """Create and configure a new SqliteDatabase instance."""
        logger.info(f"Initializing database with path: {db_path}")

        # Special-case in-memory DB: keep ':memory:' as-is so SQLite uses an actual
        # in-memory database rather than creating a file named ':memory:' in cwd.
        if db_path == ':memory:' or db_path.startswith('file:'):
            logger.info(f"Using special database path: {db_path}")
        else:
            # If path is relative, resolve against the current working directory.
            if not os.path.isabs(db_path):
                project_dir = Path.cwd()
                db_path = str(project_dir / db_path)
                logger.info(f"Using absolute path: {db_path}")

            # Ensure parent directory exists.
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
                logger.info(f"Ensured database directory exists: {db_dir}")

        db_pragmas = pragmas if pragmas is not None else DB_PRAGMAS
        instance = SqliteDatabase(db_path, pragmas=db_pragmas)
        logger.info(f"Database created at {db_path} with pragmas: {db_pragmas}")
        return instance

    @classmethod
    def get_database(cls, db_path: str = DEFAULT_DB_NAME, pragmas: dict = None) -> SqliteDatabase:
        """
        Get or create a database connection.

        If called with a different path after reset() the factory will create a
        new instance, allowing main.py's fallback path logic to work correctly.

        Args:
            db_path: Path to the SQLite database file.
            pragmas: Custom database pragmas.
        Returns:
            SqliteDatabase: Configured database instance.
        """
        if cls._db is None:
            cls._db = cls._build_db(db_path, pragmas if pragmas is not None else DB_PRAGMAS)
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
    cloud_id = IntegerField(null=True, index=True, help_text="Primary key of the device in the cloud backend")
    ip_address = CharField(
        max_length=15, help_text="IPv4 address of the device", index=True
    )
    port = IntegerField(default=DEVICE_DEFAULTS["PORT"])
    password = CharField(max_length=32, default=DEVICE_DEFAULTS["PASSWORD"])
    device_model = CharField(max_length=50, index=True)
    status = CharField(max_length=20, default=DEVICE_DEFAULTS["STATUS"], index=True)
    last_error = TextField(null=True, help_text="Last error message")
    created_at = DateTimeField(default=datetime.now, index=True)
    updated_at = DateTimeField(default=datetime.now, index=True)

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
    id = BigAutoField(primary_key=True)
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
    # pyzk status codes - verification method used
    STATUS_MAP = {
        0: 'Fingerprint',
        1: 'Password',
        2: 'RFID Card',
        3: 'Face',
        4: 'Palm',
        5: 'Vein',
    }

    # pyzk punch codes - check in/out type
    PUNCH_MAP = {
        0: 'Check IN',
        1: 'Check OUT',
        2: 'Break OUT',
        3: 'Break IN',
        4: 'Overtime IN',
        5: 'Overtime OUT',
    }
    
    id = AutoField()
    user = ForeignKeyField(User, backref="attendances", index=True)
    device = ForeignKeyField(Device, backref="attendances", null=True, index=True)
    timestamp = DateTimeField(index=True)
    status = IntegerField(help_text="Verification method: 0=Fingerprint, 1=Password, 2=Card, 3=Face", index=True)
    punch = IntegerField(help_text="Check type: 0=IN, 1=OUT, 2=Break OUT, 3=Break IN, 4=OT IN", index=True)
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
    
    @property
    def status_display(self) -> str:
        """Get human-readable status (verification method)."""
        return self.STATUS_MAP.get(self.status, f'Unknown ({self.status})')
    
    @property
    def punch_display(self) -> str:
        """Get human-readable punch type."""
        return self.PUNCH_MAP.get(self.punch, f'Unknown ({self.punch})')
    
    def to_dict(self) -> dict:
        """Convert attendance to dictionary with readable values."""
        return {
            'id': self.id,
            'user_id': self.user.user_id if self.user else None,
            'user_name': self.user.name if self.user else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status,
            'status_display': self.status_display,
            'punch': self.punch,
            'punch_display': self.punch_display,
            'posted': self.posted,
        }

    def validate(self):
        """Validate attendance data before saving."""
        if not self.user:
            raise ValidationError("Attendance record must have an associated user")
        if not self.timestamp:
            raise ValidationError("Attendance record must have a timestamp")


class Settings(BaseModel):
    cloud_api_url = CharField(default="", index=True)
    sync_id = CharField(default="", index=True, help_text="Sync ID for all API requests")
    sync_time = TimeField(null=True)
    is_sync_enabled = BooleanField(default=True, help_text="Enable/disable the daily automatic sync schedule")
    last_sync = DateTimeField(null=True, index=True)
    last_post = DateTimeField(null=True, index=True)
    attendance_pending = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = TABLE_NAMES["SETTINGS"]

    def validate(self):
        """Validate settings data before saving."""
        try:
            if self.cloud_api_url:
                Validator.validate_url(self.cloud_api_url)
        except ValidationError as e:
            raise ValidationError(f"Settings validation failed: {e.message}")

    def save(self, *args, **kwargs):
        """Override save to update timestamps."""
        # Update the updated_at timestamp
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)


def create_indexes():
    """Create additional indexes for performance optimization."""
    try:
        # Use constants for table names
        attendance_table = TABLE_NAMES["ATTENDANCE"]
        users_table = TABLE_NAMES["USERS"]
        devices_table = TABLE_NAMES["DEVICES"]
        settings_table = TABLE_NAMES["SETTINGS"]
        # Create indexes for common query patterns with improved performance
        # Only attempt index creation if the table exists. This avoids "no such table"
        # errors in transient contexts (in-memory DBs or early init runs).
        def try_index(table_name: str, sql: str):
            if db.table_exists(table_name):
                try:
                    db.execute_sql(sql)
                except Exception as e:
                    logger.warning(f"Failed to create index on {table_name}: {e}")
            else:
                logger.debug(f"Skipping index creation: table {table_name} does not exist")

        try_index(attendance_table, f"CREATE INDEX IF NOT EXISTS idx_attendance_user_timestamp_posted ON {attendance_table} (user_id, timestamp, posted)")
        try_index(attendance_table, f"CREATE INDEX IF NOT EXISTS idx_attendance_posted_timestamp ON {attendance_table} (posted, timestamp)")
        try_index(users_table, f"CREATE INDEX IF NOT EXISTS idx_user_device_saved ON {users_table} (device_id, saved_to_device)")
        try_index(users_table, f"CREATE INDEX IF NOT EXISTS idx_user_type_device ON {users_table} (user_type, device_id)")
        try_index(devices_table, f"CREATE INDEX IF NOT EXISTS idx_device_status_model ON {devices_table} (status, device_model)")
        try_index(settings_table, f"CREATE INDEX IF NOT EXISTS idx_settings_sync_status ON {settings_table} (last_sync, last_post)")
        # Add covering indexes for better query performance (partial indexes may not be supported everywhere)
        try_index(attendance_table, f"CREATE INDEX IF NOT EXISTS idx_attendance_user_status_timestamp ON {attendance_table} (user_id, status, timestamp) WHERE posted = 0")
        try_index(users_table, f"CREATE INDEX IF NOT EXISTS idx_user_active_device ON {users_table} (user_id, device_id) WHERE saved_to_device = 1")

        logger.info("Database indexes created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database indexes: {e}")


def migrate_database():
    """Migrate database schema for existing databases."""
    try:
        # Check if last_error column exists in devices
        if db.table_exists('devices'):
            cursor = db.execute_sql("PRAGMA table_info(devices)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'last_error' not in columns:
                # Add last_error column
                db.execute_sql("ALTER TABLE devices ADD COLUMN last_error TEXT NULL")
                logger.info("Added last_error column to devices table")
            
            if 'cloud_id' not in columns:
                # Add cloud_id column
                db.execute_sql("ALTER TABLE devices ADD COLUMN cloud_id INTEGER NULL")
                # Add index separately to avoid UNIQUE constraint issues with existing rows
                db.execute_sql("CREATE INDEX IF NOT EXISTS idx_device_cloud_id ON devices (cloud_id)")
                logger.info("Added cloud_id column to devices table")
                
        # Check if sync_time / is_sync_enabled columns exist in settings
        if db.table_exists('settings'):
            cursor = db.execute_sql("PRAGMA table_info(settings)")
            settings_columns = [row[1] for row in cursor.fetchall()]
            if 'sync_time' not in settings_columns:
                db.execute_sql("ALTER TABLE settings ADD COLUMN sync_time TEXT NULL")
                logger.info("Added sync_time column to settings table")
            if 'is_sync_enabled' not in settings_columns:
                db.execute_sql("ALTER TABLE settings ADD COLUMN is_sync_enabled INTEGER NOT NULL DEFAULT 1")
                logger.info("Added is_sync_enabled column to settings table")
        
        # Check if device column exists in attendance
        if db.table_exists('attendance'):
            cursor = db.execute_sql("PRAGMA table_info(attendance)")
            attendance_columns = [row[1] for row in cursor.fetchall()]
            if 'device_id' not in attendance_columns:
                db.execute_sql("ALTER TABLE attendance ADD COLUMN device_id INTEGER NULL REFERENCES devices(id)")
                logger.info("Added device_id column to attendance table")
            
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")


def initialize_database():
    """Initialize database with tables and indexes."""
    try:
        # Create tables
        db.create_tables([Device, User, Attendance, Settings], safe=True)
        
        # Migrate existing databases
        migrate_database()

        # Create indexes
        create_indexes()

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def flush_database():
    """Clear all data from Device, User and Attendance tables."""
    try:
        with db.atomic():
            # Delete in correct order for foreign keys
            Attendance.delete().execute()
            User.delete().execute()
            Device.delete().execute()
        logger.info("Database flushed successfully - all devices, users and attendance cleared")
        return True
    except Exception as e:
        logger.error(f"Failed to flush database: {e}")
        return False