import logging

class TaskScheduler:
    """
    Dummy scheduler class that replaces the real scheduler.
    This class provides the same interface but doesn't actually schedule any tasks.
    """

    def __init__(self, device_manager, api_client, notification_service, schedule_repo):
        """
        Initialize the dummy scheduler with dependencies.
        """
        self.device_manager = device_manager
        self.api_client = api_client
        self.notification_service = notification_service
        self.schedule_repo = schedule_repo
        self.logger = logging.getLogger(__name__)
        self.logger.info("Dummy TaskScheduler initialized (scheduler functionality disabled)")

    def update_settings(self) -> None:
        """
        Dummy method for compatibility.
        """
        self.logger.info("Scheduler disabled, ignoring update_settings call")
        pass

    def sync_data(self) -> None:
        """
        Perform a full data sync by pulling and pushing data.
        """
        self.logger.info("Starting full data sync (manual)")
        try:
            self.device_manager.pull_data()
            self.api_client.post_to_cloud()
            self.logger.info("Full data sync completed successfully")
            self.notification_service.notify(
                "Sync", "Full data sync completed successfully", "info"
            )
        except Exception as e:
            self.logger.error(f"Error during sync: {e}")
            self.notification_service.notify("Error", f"Sync failed: {str(e)}", "error")

    def shutdown(self) -> None:
        """
        Dummy method for compatibility.
        """
        self.logger.info("Scheduler disabled, nothing to shut down")
        pass