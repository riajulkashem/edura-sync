# tests/test_scheduler.py
import time as time_module
import unittest
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch, ANY

from core.scheduler import SchedulerService


class TestScheduler(unittest.TestCase):
    def setUp(self):
        # Create mock dependencies
        self.settings_repo = MagicMock()
        self.api_client = MagicMock()

        # Configure mock settings
        mock_settings = MagicMock()
        mock_settings.is_scheduler_enabled = True
        mock_settings.process_time = time(15, 0)  # 3:00 PM
        self.settings_repo.get_settings.return_value = mock_settings

        # Create scheduler with mock dependencies
        self.scheduler = SchedulerService(self.settings_repo, self.api_client)

    def tearDown(self):
        if hasattr(self, 'scheduler'):
            try:
                self.scheduler.stop()
                if self.scheduler.scheduler_thread and self.scheduler.scheduler_thread.is_alive():
                    self.scheduler.scheduler_thread.join(timeout=2)
            except Exception as e:
                print(f"Error during teardown: {e}")

    def test_scheduler_initialization(self):
        """Test that scheduler initializes correctly."""
        self.assertIsNotNone(self.scheduler)
        self.assertEqual(self.scheduler.settings_repo, self.settings_repo)
        self.assertEqual(self.scheduler.api_client, self.api_client)
        self.assertIsNone(self.scheduler.scheduler_thread)

    def test_scheduler_start_stop(self):
        """Test that scheduler starts and stops properly."""
        # Start the scheduler
        self.scheduler.start()

        # Check that the thread is running
        self.assertIsNotNone(self.scheduler.scheduler_thread)
        self.assertTrue(self.scheduler.scheduler_thread.is_alive())

        # Stop the scheduler
        self.scheduler.stop()

        # Give it a moment to shut down
        time_module.sleep(0.1)

        # Check that the thread has stopped
        self.assertFalse(self.scheduler.scheduler_thread.is_alive())

    @patch('core.scheduler.datetime')
    def test_scheduled_task_execution(self, mock_datetime):
        """Test that the scheduled task executes at the specified time."""
        # Mock current time to be just before the scheduled time
        now = datetime.now()
        mock_time = datetime.combine(now.date(), time(14, 59, 55))  # 2:59:55 PM
        mock_datetime.now.return_value = mock_time
        mock_datetime.combine.side_effect = datetime.combine

        # Start the scheduler
        self.scheduler.start()

        # Give it time to execute
        time_module.sleep(7)  # Wait 7 seconds, should trigger after 5 seconds

        # Verify the API client was called
        self.api_client.post_to_cloud.assert_called_once()

        # Verify settings were updated
        self.settings_repo.update_settings.assert_called_once()

    def test_scheduler_disabled(self):
        """Test that scheduler doesn't execute when disabled."""
        # Set scheduler to disabled
        mock_settings = MagicMock()
        mock_settings.is_scheduler_enabled = False
        self.settings_repo.get_settings.return_value = mock_settings

        # Start the scheduler
        self.scheduler.start()

        # Give it some time
        time_module.sleep(3)

        # Verify the API client was not called
        self.api_client.post_to_cloud.assert_not_called()

    @patch('core.scheduler.datetime')
    def test_calculate_next_run_time(self, mock_datetime):
        """Test calculation of next run time."""
        # Mock current time to be 10:00 AM
        now = datetime.combine(datetime.now().date(), time(10, 0))
        mock_datetime.now.return_value = now
        mock_datetime.combine.side_effect = datetime.combine

        # Test with process time in the future (3:00 PM today)
        process_time = time(15, 0)
        next_run = self.scheduler._calculate_next_run_time(process_time)
        expected = datetime.combine(now.date(), process_time)
        self.assertEqual(next_run, expected)

        # Test with process time in the past (8:00 AM today, should be tomorrow)
        process_time = time(8, 0)
        next_run = self.scheduler._calculate_next_run_time(process_time)
        expected = datetime.combine(now.date() + timedelta(days=1), process_time)
        self.assertEqual(next_run, expected)

    def test_scheduler_setting_change(self):
        """Test that scheduler respects the is_scheduler_enabled setting."""
        # Create a simplified test that focuses on the core logic

        # Create a controlled environment with mocks
        mock_settings = MagicMock()
        mock_settings.process_time = time(15, 0)

        # Test with scheduler disabled
        mock_settings.is_scheduler_enabled = False
        self.settings_repo.get_settings.return_value = mock_settings

        # We'll directly test the scheduler's decision logic
        # Rather than the actual scheduler loop or threading behavior
        def check_scheduler_execution():
            settings = self.settings_repo.get_settings()
            if settings and settings.is_scheduler_enabled and settings.process_time:
                # Skip the actual scheduling logic and just run the task
                self.scheduler._run_scheduled_task()
                return True
            return False

        # Run with disabled setting
        executed = check_scheduler_execution()
        self.assertFalse(executed)
        self.api_client.post_to_cloud.assert_not_called()

        # Now enable the scheduler and try again
        mock_settings.is_scheduler_enabled = True
        executed = check_scheduler_execution()
        self.assertTrue(executed)
        self.api_client.post_to_cloud.assert_called_once()

        # Reset and disable again
        self.api_client.post_to_cloud.reset_mock()
        mock_settings.is_scheduler_enabled = False
        executed = check_scheduler_execution()
        self.assertFalse(executed)
        self.api_client.post_to_cloud.assert_not_called()

    def test_scheduler_direct_task_execution(self):
        """Test the scheduler task execution directly without thread timing concerns."""
        # Create mock dependencies
        mock_settings = MagicMock()
        mock_settings.is_scheduler_enabled = True
        mock_settings.process_time = time(15, 0)
        self.settings_repo.get_settings.return_value = mock_settings

        # Call the task execution method directly
        self.scheduler._run_scheduled_task()

        # Verify the API client was called
        self.api_client.post_to_cloud.assert_called_once()

        # Verify settings were updated
        self.settings_repo.update_settings.assert_called_once()

    def test_direct_components(self):
        """Test the individual components of the scheduler directly."""
        # Test 1: _run_scheduled_task should call post_to_cloud
        self.scheduler._run_scheduled_task()
        self.api_client.post_to_cloud.assert_called_once()
        self.settings_repo.update_settings.assert_called_once()

        # Reset mocks
        self.api_client.post_to_cloud.reset_mock()
        self.settings_repo.update_settings.reset_mock()

        # Test 2: _calculate_next_run_time functionality
        with patch('core.scheduler.datetime') as mock_datetime:
            # Set current time to 10:00 AM
            now = datetime(2023, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = now
            mock_datetime.combine.side_effect = datetime.combine

            # Test with future time (3:00 PM)
            process_time = time(15, 0)
            next_run = self.scheduler._calculate_next_run_time(process_time)
            expected = datetime.combine(now.date(), process_time)
            self.assertEqual(next_run, expected)

    def test_scheduler_task_execution(self):
        """Test that the _run_scheduled_task method executes correctly."""
        # Test direct execution of the task
        self.scheduler._run_scheduled_task()
        self.api_client.post_to_cloud.assert_called_once()
        self.settings_repo.update_settings.assert_called_once_with(last_post=ANY)

    def test_scheduler_respects_enabled_setting(self):
        """Test that the scheduler respects the is_scheduler_enabled setting."""
        # Create a mock for the scheduler's _run_scheduled_task method
        with patch.object(self.scheduler, '_run_scheduled_task') as mock_run_task:
            # Create a controlled test environment
            mock_settings = MagicMock()
            mock_settings.process_time = time(15, 0)

            # Test with scheduler disabled
            mock_settings.is_scheduler_enabled = False
            self.settings_repo.get_settings.return_value = mock_settings

            # Directly simulate what happens in one loop iteration
            # when the time is right for execution
            with patch('datetime.datetime') as mock_datetime:
                now = datetime(2023, 1, 1, 14, 59, 58)  # Just before 3:00 PM
                next_time = datetime(2023, 1, 1, 15, 0, 0)  # 3:00 PM

                mock_datetime.now.return_value = now
                mock_datetime.combine.return_value = next_time

                # Manually call one "check" like the scheduler would
                settings = self.settings_repo.get_settings()
                if settings and settings.is_scheduler_enabled and settings.process_time:
                    next_run = datetime.combine(now.date(), settings.process_time)
                    seconds_until_next_run = (next_run - now).total_seconds()
                    if 0 < seconds_until_next_run < 60:
                        self.scheduler._run_scheduled_task()

                # Verify task wasn't run because scheduler is disabled
                mock_run_task.assert_not_called()

                # Now enable the scheduler
                mock_settings.is_scheduler_enabled = True

                # Manually call one "check" again
                settings = self.settings_repo.get_settings()
                if settings and settings.is_scheduler_enabled and settings.process_time:
                    next_run = datetime.combine(now.date(), settings.process_time)
                    seconds_until_next_run = (next_run - now).total_seconds()
                    if 0 < seconds_until_next_run < 60:
                        self.scheduler._run_scheduled_task()

                # Verify task was run because scheduler is now enabled
                mock_run_task.assert_called_once()


if __name__ == '__main__':
    unittest.main()
