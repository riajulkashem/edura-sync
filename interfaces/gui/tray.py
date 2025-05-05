import logging
from typing import Optional, Callable, Any
import pystray
from PIL import Image


class SystemTray:
    """
    Manages the system tray icon and menu for the PrimeSync application.
    Provides quick access to application actions.
    """

    def __init__(
        self,
        app,
        config,
        device_manager,
        api_client,
        dashboard_gui,
        notification_service,
    ):
        """
        Initialize the system tray with dependencies.
        Args:
            app: Reference to the main PrimeSync application.
            config: Application configuration.
            device_manager: Service for device management.
            api_client: Service for cloud API interactions.
            dashboard_gui: Dashboard GUI component.
            notification_service: Service for sending notifications.
        """
        self.app = app
        self.config = config
        self.device_manager = device_manager
        self.api_client = api_client
        self.dashboard_gui = dashboard_gui
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
        self.icon: Optional[pystray.Icon] = None
        self._setup_tray()

    def _run_action(self, action: Callable, description: str) -> Callable:
        """
        Creates a wrapper function for tray menu actions with error handling.
        
        Args:
            action: The function to run
            description: Description of the action for logging
            
        Returns:
            Callable: Wrapped function that handles errors
        """
        def wrapper(icon, item):
            try:
                self.logger.info(f"Running action: {description}")
                action()
                self.logger.info(f"Completed action: {description}")
            except Exception as e:
                self.logger.error(f"Error in {description}: {e}")
                self.notification_service.notify(
                    "Error", f"Failed to {description.lower()}: {str(e)}", "error"
                )
        return wrapper

    def _setup_tray(self) -> None:
        """Set up the system tray icon and menu."""
        try:
            icon_path = self.config.ICON_PATH
            if icon_path and icon_path.exists() and icon_path.is_file():
                image = Image.open(icon_path)
                self.logger.info(f"Loaded tray icon from {icon_path}")
            else:
                self.logger.warning(
                    f"Icon file not available at {icon_path}, using default"
                )
                image = Image.new("RGB", (64, 64), color="blue")

            menu = (
                pystray.MenuItem(
                    "Devices Status",
                    self._run_action(
                        self.device_manager.check_devices, "Check Devices Status"
                    ),
                ),
                pystray.MenuItem(
                    "Sync Data", self._run_action(self.api_client.sync_data, "Sync Data")
                ),
                pystray.MenuItem(
                    "Post Cloud",
                    self._run_action(
                        self.api_client.post_to_cloud, "Post Data to Cloud"
                    ),
                ),
                pystray.MenuItem(
                    "Pull Machine",
                    self._run_action(
                        self.device_manager.pull_data, "Pull Data from Machine"
                    ),
                ),
                pystray.MenuItem(
                    "Dashboard",
                    self._run_action(
                        self.dashboard_gui.show_dashboard, "Show Dashboard"
                    ),
                ),
                pystray.MenuItem(
                    "Exit", self._run_action(self.app.exit_app, "Exit Application")
                ),
            )

            self.icon = pystray.Icon("PrimeSync", image, "PrimeSync Manager", menu)
            self.logger.info("System tray initialized")
        except Exception as e:
            self.logger.error(f"Failed to setup system tray: {e}")
            # Just log errors, don't use notification during setup

    def run(self) -> None:
        """Start the system tray icon."""
        if self.icon:
            try:
                self.icon.run()
                self.logger.info("System tray running")
            except Exception as e:
                self.logger.error(f"Failed to run system tray: {e}")
                self.notification_service.notify(
                    "Error", f"Failed to run system tray: {str(e)}", "error"
                )

    def stop(self) -> None:
        """Stop the system tray icon."""
        if self.icon:
            try:
                self.icon.stop()
                self.icon = None
                self.logger.info("System tray stopped")
            except Exception as e:
                self.logger.error(f"Failed to stop system tray: {e}")
                self.notification_service.notify(
                    "Error", f"Failed to stop system tray: {str(e)}", "error"
                )