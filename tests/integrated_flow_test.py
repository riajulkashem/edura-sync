import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from interfaces.database.models import Device, User, Attendance, Settings, db
from interfaces.database.repository import DeviceRepository, UserRepository, AttendanceRepository, SettingsRepository
from services.api_sync import APISync
from services.device_manager import DeviceManager

class MockZK:
    """Mock ZKTeco Device."""
    def __init__(self, ip, port=4370, timeout=5, password='0', force_udp=False, **kwargs):
        self.ip = ip
        self.users = []
        self.attendance = []

    def connect(self):
        return True

    def disconnect(self):
        return True

    def disable_device(self):
        pass

    def enable_device(self):
        pass

    def get_users(self):
        return self.users

    def set_user(self, uid, name, privilege, password, group_id, card):
        user_mock = MagicMock()
        user_mock.uid = uid
        user_mock.name = name
        user_mock.privilege = privilege
        user_mock.password = password
        user_mock.group_id = group_id
        user_mock.card = card
        self.users.append(user_mock)

    def get_attendance(self):
        return self.attendance

class TestIntegratedFlow(unittest.TestCase):
    def setUp(self):
        """Set up temporary in-memory database and repositories."""
        # Use in-memory SQLite for testing
        db.init(':memory:')
        db.create_tables([Device, User, Attendance, Settings], safe=True)
        
        self.device_repo = DeviceRepository()
        self.user_repo = UserRepository()
        self.attendance_repo = AttendanceRepository()
        self.settings_repo = SettingsRepository()
        
        self.notification_service = MagicMock()
        
        # Initialize services
        self.device_manager = DeviceManager(
            self.notification_service,
            self.device_repo,
            self.user_repo,
            self.attendance_repo
        )
        
        self.api_sync = APISync(
            self.notification_service,
            self.settings_repo,
            self.attendance_repo,
            self.user_repo,
            self.device_repo,
            self.device_manager
        )
        
        # Setup basic settings
        self.settings_repo.create(
            cloud_api_url="http://mock-api.com",
            sync_id="test-sync-id"
        )
        self.api_sync.load_settings()

    @patch('services.device_utils.ZK')
    @patch('time.sleep', return_value=None)
    def test_full_targeted_sync_flow(self, mock_sleep, mock_zk_class):
        """Test the entire flow: Cloud -> Local DB -> Targeted Device Sync -> Attendance Pull -> Cloud Post."""
        
        # Setup ZK mock factory
        devices_mocks = {}
        def zk_side_effect(ip, **kwargs):
            if ip not in devices_mocks:
                devices_mocks[ip] = MockZK(ip)
            return devices_mocks[ip]
        mock_zk_class.side_effect = zk_side_effect

        # 1. Mock Cloud API Response for Users and Devices
        mock_response_data = {
            "users": [
                {
                    "id": 101,
                    "name": "John Doe",
                    "device_id": 1, # Assigned to Cloud Device 1
                    "device_code": 5001,
                    "user_type": "STUDENT",
                    "role": 0,
                    "password": "",
                    "group_id": "1",
                    "card": "12345"
                },
                {
                    "id": 12,
                    "name": "Robert Brown",
                    "device_id": 2, # Assigned to Cloud Device 2
                    "device_code": 3003,
                    "user_type": "STAFF",
                    "role": 0,
                    "password": "",
                    "group_id": "1",
                    "card": "67890"
                }
            ],
            "devices": [
                {
                    "id": 1,
                    "name": "Main Gate",
                    "ip": "192.168.1.100",
                    "port": 4370,
                    "password": "0"
                },
                {
                    "id": 2,
                    "name": "Office",
                    "ip": "192.168.1.101",
                    "port": 4370,
                    "password": "0"
                }
            ]
        }

        # Mock the session inside api_sync
        self.api_sync._session = MagicMock()
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_response_data
        self.api_sync._session.get.return_value = mock_res
        
        # Step A: Pull from Cloud
        result = self.api_sync.sync_users()
        self.assertTrue(result)
        
        # Step B: Verify Devices saved with cloud_id
        devices = self.device_repo.get_all()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].cloud_id, 1)
        self.assertEqual(devices[1].cloud_id, 2)
        
        # Step C: Verify Users mapped to correct Device
        users = self.user_repo.get_all()
        self.assertEqual(len(users), 2)
        
        john = self.user_repo.get_by_user_id("101")
        robert = self.user_repo.get_by_user_id("12")
        
        self.assertEqual(john.device.cloud_id, 1)
        self.assertEqual(robert.device.cloud_id, 2)

        # 2. Verify Targeted Sync (Automatically triggered by sync_users)
        # Verify targeted upload
        # John (device_id 1) should be in Device 1 (192.168.1.100)
        # Robert (device_id 2) should be in Device 2 (192.168.1.101)
        self.assertEqual(len(devices_mocks["192.168.1.100"].users), 1)
        self.assertEqual(devices_mocks["192.168.1.100"].users[0].name, "John Doe")
        
        self.assertEqual(len(devices_mocks["192.168.1.101"].users), 1)
        self.assertEqual(devices_mocks["192.168.1.101"].users[0].name, "Robert Brown")

        # 3. Pull Attendance
        mock_attendance_record = MagicMock()
        mock_attendance_record.user_id = "101"
        mock_attendance_record.timestamp = datetime(2026, 1, 22, 12, 0, 0)
        mock_attendance_record.status = 0
        mock_attendance_record.punch = 0
        
        # Add attendance to Device 1
        devices_mocks["192.168.1.100"].attendance = [mock_attendance_record]
        
        # Step E: Pull attendance
        self.device_manager.pull_data()
        
        # Verify attendance saved in local DB
        attendance = self.attendance_repo.get_all()
        self.assertEqual(len(attendance), 1)
        self.assertEqual(attendance[0].user.user_id, "101")
        self.assertEqual(attendance[0].device.ip_address, "192.168.1.100")

        # 4. Post to Cloud
        mock_res_post = MagicMock()
        mock_res_post.status_code = 200
        self.api_sync._session.post.return_value = mock_res_post
        
        # Step F: Post to Cloud
        self.api_sync.post_to_cloud()
        
        # Verify correct payload structure
        self.assertTrue(self.api_sync._session.post.called)
        args, kwargs = self.api_sync._session.post.call_args
        posted_data = kwargs.get('json', [])
        
        self.assertEqual(len(posted_data), 1)
        self.assertEqual(posted_data[0]['user_id'], 101)
        self.assertEqual(posted_data[0]['device'], 1) # Mapped to cloud device ID

        # Verify marked as posted
        self.assertEqual(self.attendance_repo.get_pending_count(), 0)

    def tearDown(self):
        db.close()

if __name__ == '__main__':
    unittest.main()
