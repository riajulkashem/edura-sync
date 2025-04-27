import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from models import Schedule


class TaskScheduler:
    """Manages periodic tasks for device checks and data syncing."""

    def __init__(self, device_manager, api_client):
        self.logger = logging.getLogger(__name__)
        self.scheduler = BackgroundScheduler()
        self.device_manager = device_manager
        self.api_client = api_client
        self.last_synced_time = None
        self.running = True

    def update_settings(self):
        """Update scheduler with new settings from Schedule model."""
        if not self.running:
            return
        self.scheduler.remove_all_jobs()
        for schedule in Schedule.select().where(Schedule.enabled == True):
            try:
                hour, minute = map(int, schedule.schedule_time.split(":"))
                if schedule.task_type == "pull":
                    self.scheduler.add_job(
                        self.device_manager.pull_data,
                        'cron',
                        hour=hour,
                        minute=minute,
                        id=f"pull_{schedule.id}"
                    )
                    self.logger.info(f"Scheduled pull task at {schedule.schedule_time}")
                elif schedule.task_type == "push":
                    self.scheduler.add_job(
                        self.api_client.post_to_cloud,
                        'cron',
                        hour=hour,
                        minute=minute,
                        id=f"push_{schedule.id}"
                    )
                    self.logger.info(f"Scheduled push task at {schedule.schedule_time}")
            except ValueError as e:
                self.logger.error(f"Invalid schedule time format for {schedule.task_type}: {e}")

        if not self.scheduler.running:
            try:
                self.scheduler.start()
                self.logger.info("Scheduler started")
            except Exception as e:
                self.logger.error(f"Failed to start scheduler: {e}")

    def sync_data(self):
        """Sync data by pulling and pushing data."""
        if not self.running:
            return
        try:
            self.device_manager.pull_data()
            self.api_client.post_to_cloud()
            self.last_synced_time = datetime.now()
            self.logger.info("Full data sync completed")
            self.show_notification("Sync", "Full data sync completed successfully", "info")
        except Exception as e:
            self.logger.error(f"Error during sync: {e}")
            self.show_notification("Error", f"Sync failed: {str(e)}", "error")

    def show_notification(self, title: str, message: str, type: str):
        """Delegate notification to GUI."""
        try:
            from gui import PrimeSyncGUI
            PrimeSyncGUI.show_notification(self, title, message, type)
        except Exception as e:
            self.logger.error(f"Failed to delegate notification: {e}")

    def shutdown(self):
        """Shut down the scheduler."""
        if not self.running:
            return
        self.running = False
        try:
            self.scheduler.shutdown(wait=False)
            self.logger.info("Scheduler shut down")
        except Exception as e:
            self.logger.error(f"Error shutting down scheduler: {e}")