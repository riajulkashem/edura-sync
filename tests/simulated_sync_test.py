import logging
from types import SimpleNamespace
from pathlib import Path

logging.basicConfig(level=logging.INFO)

# Prepare in-memory DB and initialize tables
from interfaces.database import models as db_models
from interfaces.database.models import DatabaseFactory, initialize_database
from peewee import SqliteDatabase

# Reset any existing DB and create in-memory DB
db_models.DatabaseFactory._db = None
mem_db = db_models.DatabaseFactory.get_database(':memory:', pragmas={})
db_models.db = mem_db
mem_db.connect()
initialize_database()

# Repositories
from interfaces.database.repository import DeviceRepository, UserRepository, AttendanceRepository

device_repo = DeviceRepository()
user_repo = UserRepository()
attendance_repo = AttendanceRepository()

device = device_repo.create(ip_address='192.168.0.165', port=4370, password='', device_model='ZK Teco', status='Offline')
# Create a device record (avoid duplicate if already exists in file DB)
test_ip = '10.0.0.1'
existing = device_repo.get_by_ip(test_ip)
if existing:
    device = existing
else:
    device = device_repo.create(ip_address=test_ip, port=4370, password='', device_model='ZK Teco', status='Offline')
print(f"Using device id={device.id} ip={device.ip_address}")

# Create DeviceManager and APISync with a fake notification service
class FakeNotification:
    def notify(self, *args, **kwargs):
        pass

from services.device_manager import DeviceManager
from services.api_sync import APISync

fake_notif = FakeNotification()
manager = DeviceManager(fake_notif, device_repo, user_repo, attendance_repo)
api_sync = APISync(fake_notif, None, attendance_repo, user_repo, device_repo, manager)

# Simulate device pull users (these should be saved with device-prefixed user_id)
u1 = SimpleNamespace(user_id='1', uid=1, name='Alice', privilege=0, password='', group_id=None, card='202516')
u2 = SimpleNamespace(user_id='2', uid=2, name='Bob', privilege=0, password='', group_id=None, card='202517')
users = [u1, u2]

saved = manager._save_users_to_database(users, device)
print(f"Device saved users count: {saved}")

print("Users after device pull:")
for u in user_repo.get_all():
    print(f"id={u.id} user_id={u.user_id} device_code={u.device_code} card={u.card} name={u.name}")

# Now simulate cloud users response (matching by card for first entry)
cloud_users = [
    {"id": 7596, "name": "HEMEL MODAK", "device_id": 2, "card_number": "202516", "type": "STUDENT"},
    {"id": 7600, "name": "SAMMO FAGUN DAS", "device_id": 2, "card_number": "202520", "type": "STUDENT"}
]

saved_cloud = api_sync._save_cloud_users_to_database(cloud_users)
print(f"Cloud saved/updated users count: {saved_cloud}")

print("Users after cloud sync:")
all_users = user_repo.get_all()
for u in all_users:
    print(f"id={u.id} user_id={u.user_id} device_code={u.device_code} card={u.card} name={u.name}")

print(f"Total users in DB: {len(all_users)}")

# Now simulate attendance pulled from device for user UIDs 1 and 2
from datetime import datetime, timedelta
rec1 = SimpleNamespace(user_id='1', uid=1, timestamp=datetime.now(), status=1, punch=1, card='202516')
rec2 = SimpleNamespace(user_id='2', uid=2, timestamp=datetime.now() - timedelta(minutes=5), status=1, punch=1, card='202517')
attendance_saved = manager._save_attendance_to_database([rec1, rec2], device)
print(f"Attendance saved count: {attendance_saved}")

print("Attendance rows:")
for a in attendance_repo.get_all():
    print(f"id={a.id} user_id={a.user.user_id} device_id={a.device.id if a.device else None} timestamp={a.timestamp} status={a.status} punch={a.punch}")
