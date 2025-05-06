# core/scheduler.py
import logging
import threading
import time
from datetime import datetime, timedelta


class SchedulerService:
    """Service for scheduling background tasks."""

    def __init__(self, settings_repo, api_client):
        """Initialize scheduler with required dependencies.

        Args:
            settings_repo: Repository for accessing settings
            api_client: Client for cloud API operations
        """
        self.logger = logging.getLogger(__name__)
        self.settings_repo = settings_repo
        self.api_client = api_client
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        self.logger.info("Scheduler service initialized")

    def start(self):
        """Start the scheduler thread."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.logger.warning("Scheduler is already running")
            return

        self.stop_event.clear()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Scheduler thread started")

    def stop(self):
        """Stop the scheduler thread."""
        if not self.scheduler_thread or not self.scheduler_thread.is_alive():
            self.logger.warning("Scheduler is not running")
            return

        self.stop_event.set()
        self.scheduler_thread.join(timeout=5)
        self.logger.info("Scheduler thread stopped")

    def _scheduler_loop(self):
        """Main scheduler loop that runs continuously."""
        self.logger.info("Scheduler loop started")

        # Use shorter check intervals for more responsive testing
        check_interval = 10  # Start with checking every 10 seconds

        while not self.stop_event.is_set():
            try:
                # Get current settings
                settings = self.settings_repo.get_settings()

                # Check if scheduler is enabled and process time is set
                if settings and settings.is_scheduler_enabled and settings.process_time:
                    # Calculate time until next run
                    next_run = self._calculate_next_run_time(settings.process_time)
                    seconds_until_next_run = (next_run - datetime.now()).total_seconds()

                    if 0 < seconds_until_next_run < 60:  # If next run is less than a minute away
                        self.logger.info(f"Scheduled task will run in {seconds_until_next_run:.2f} seconds")

                        # Wait until the exact time
                        self.stop_event.wait(seconds_until_next_run)

                        # Run the task if we didn't get stopped during the wait
                        if not self.stop_event.is_set():
                            self.logger.info("Running scheduled cloud post task")
                            self._run_scheduled_task()

                # Use a shorter check interval for more responsive testing
                self.stop_event.wait(check_interval)
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                # Wait before retrying
                self.stop_event.wait(check_interval)

    def _calculate_next_run_time(self, process_time):
        """Calculate the next run time based on the specified process time.

        Args:
            process_time: The time of day to run the task (TimeField)

        Returns:
            datetime: The next run datetime
        """
        now = datetime.now()
        next_run = datetime.combine(now.date(), process_time)

        # If the time has already passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run

    def _run_scheduled_task(self):
        """Run the scheduled post to cloud task."""
        try:
            if self.api_client:
                self.logger.info("Running scheduled post_to_cloud")
                self.api_client.post_to_cloud()

                # Update last_post time in settings
                self.settings_repo.update_settings(last_post=datetime.now())
                self.logger.info("Scheduled post_to_cloud completed")
            else:
                self.logger.error("Cannot run scheduled task: API client not available")
        except Exception as e:
            self.logger.error(f"Error running scheduled task: {e}")
