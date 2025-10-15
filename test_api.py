#!/usr/bin/env python3
"""
Test script to verify API functionality without GUI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from interfaces.database.models import DatabaseFactory, db, initialize_database
from interfaces.database.repository import (
    DeviceRepository,
    UserRepository,
    AttendanceRepository,
    SettingsRepository,
)
from services.api_sync import APISync  # Changed from APIClient to APISync
from services.device_manager import DeviceManager
from services.notification import NotificationService

def test_api_functionality():
    """Test API functionality without GUI"""
    print("Testing API functionality...")
    
    try:
        # Initialize database
        config = Config()
        db_instance = DatabaseFactory.get_database(str(config.DB_PATH))
        db_instance.connect()
        initialize_database()
        print("✓ Database initialized")
        
        # Initialize repositories
        device_repo = DeviceRepository()
        user_repo = UserRepository()
        attendance_repo = AttendanceRepository()
        settings_repo = SettingsRepository()
        print("✓ Repositories initialized")
        
        # Initialize services
        notification_service = NotificationService(config)
        device_manager = DeviceManager(
            notification_service,
            device_repo,
            user_repo,
            attendance_repo,
        )
        api_client = APISync(  # Changed from APIClient to APISync
            notification_service,
            settings_repo,
            attendance_repo,
            user_repo,
            device_repo,
            device_manager,
        )
        print("✓ Services initialized")
        
        # Test settings loading
        api_client.load_settings()  # Changed from update_settings to load_settings
        print("✓ Settings loaded")
        
        print("API functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ API functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_functionality()
    sys.exit(0 if success else 1)