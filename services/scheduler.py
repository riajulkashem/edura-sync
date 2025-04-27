# services/scheduler.py
import logging
from typing import Optional, List
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from core.exceptions import SchedulerError
from interfaces.database.repository import ScheduleRepository
from services.device_manager import DeviceManager
from services.api_client import APIClient
from services.notification import NotificationService
from interfaces.database.models import Schedule


class TaskScheduler:
    """
    Manages periodic tasks for device checks and data syncing.
    Uses APScheduler for scheduling and dependency injection for services.
    """

    def __init__(
        self,
        device_manager: DeviceManager,
        api_client: APIClient,
        notification_service: NotificationService,
        schedule_repo: ScheduleRepository,
    ):
        """
        Initialize the scheduler with dependencies.
        Args:
            device_manager: Service for device management.
            api_client: Service for cloud API interactions.
            notification_service: Service for sending notifications.
            schedule_repo: Repository for schedule data.
        """
        self.device_manager = device_manager
        self.api_client = api_client
        self.notification_service = notification_service
        self.schedule_repo = schedule_repo
        self.scheduler = BackgroundScheduler()
        self.logger = logging.getLogger(__name__)
        self.last_synced_time: Optional[datetime] = None
        self.running: bool = True
        self.logger.info("TaskScheduler initialized")

    def update_settings(self) -> None:
        """Update scheduler with new settings from the Schedule model."""
        if not self.running:
            self.logger.debug("Scheduler not running, skipping settings update")
            return

        self.logger.info("Updating scheduler settings")
        try:
            self.scheduler.remove_all_jobs()
            self.logger.info("Removed all existing scheduled jobs")

            schedules: List[Schedule] = self.schedule_repo.get_all()
            for schedule in schedules:
                if not schedule.enabled:
                    continue
                try:
                    hour, minute = map(int, schedule.schedule_time.split(":"))
                    job_id = f"{schedule.task_type}_{schedule.id}"
                    if schedule.task_type == "pull":
                        self.scheduler.add_job(
                            self.device_manager.pull_data,
                            "cron",
                            hour=hour,
                            minute=minute,
                            id=job_id,
                        )
                        self.logger.info(
                            f"Scheduled pull task at {schedule.schedule_time} with job ID {job_id}"
                        )
                    elif schedule.task_type == "push":
                        self.scheduler.add_job(
                            self.api_client.post_to_cloud,
                            "cron",
                            hour=hour,
                            minute=minute,
                            id=job_id,
                        )
                        self.logger.info(
                            f"Scheduled push task at {schedule.schedule_time} with job ID {job_id}"
                        )
                except ValueError as e:
                    self.logger.error(
                        f"Invalid schedule time format for {schedule.task_type}: {e}"
                    )
                    continue

            if not self.scheduler.running:
                self.scheduler.start()
                self.logger.info("Scheduler started")

            self.logger.info("Scheduler settings updated successfully")
        except Exception as e:
            self.logger.error(f"Failed to update scheduler settings: {e}")
            raise SchedulerError(f"Failed to update scheduler settings: {str(e)}")

    def sync_data(self) -> None:
        """Perform a full data sync by pulling and pushing data."""
        if not self.running:
            self.logger.debug("Scheduler not running, skipping data sync")
            return

        self.logger.info("Starting full data sync")
        try:
            self.device_manager.pull_data()
            self.api_client.post_to_cloud()
            self.last_synced_time = datetime.now()
            self.logger.info("Full data sync completed successfully")
            self.notification_service.notify(
                "Sync", "Full data sync completed successfully", "info"
            )
            # Update dashboard last synced time
            if hasattr(self, "app") and hasattr(self.app, "dashboard_gui"):
                self.app.dashboard_gui.update_last_synced(self.last_synced_time)
        except Exception as e:
            self.logger.error(f"Error during sync: {e}")
            self.notification_service.notify("Error", f"Sync failed: {str(e)}", "error")

    def shutdown(self) -> None:
        """Shut down the scheduler gracefully."""
        if not self.running:
            self.logger.debug("Scheduler already shut down")
            return

        self.running = False
        self.logger.info("Initiating scheduler shutdown")
        try:
            self.scheduler.shutdown(wait=True)
            self.logger.info("Scheduler shut down successfully")
        except Exception as e:
            self.logger.error(f"Error shutting down scheduler: {e}")
            raise SchedulerError(f"Failed to shut down scheduler: {str(e)}")
