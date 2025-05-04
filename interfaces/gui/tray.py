# interfaces/gui/tray.py
import logging
from typing import Optional

import pystray
from PIL import Image

from core.config import Config
from interfaces.gui.dashboard import DashboardGUI
from interfaces.gui.settings import SettingsGUI
from services.api_client import APIClient
from services.device_manager import DeviceManager
from services.notification import NotificationService
from services.scheduler import TaskScheduler


class SystemTray:
    """
    Manages the system tray icon and menu for the PrimeSync application.
    Provides quick access to application actions.
    """

    def __init__(
        self,
        app: "PrimeSync",
        config: Config,
        device_manager: DeviceManager,
        scheduler: TaskScheduler,
        api_client: APIClient,
        dashboard_gui: DashboardGUI,
        settings_gui: SettingsGUI,
        notification_service: NotificationService,
    ):
        """
        Initialize the system tray with dependencies.
        Args:
            app: Reference to the main PrimeSync application.
            config: Application configuration.
            device_manager: Service for device management.
            scheduler: Service for task scheduling.
            api_client: Service for cloud API interactions.
            dashboard_gui: Dashboard GUI component.
            settings_gui: Settings GUI component.
            notification_service: Service for sending notifications.
        """
        self.app = app
        self.config = config
        self.device_manager = device_manager
        self.scheduler = scheduler
        self.api_client = api_client
        self.dashboard_gui = dashboard_gui
        self.settings_gui = settings_gui
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
        self.icon: Optional[pystray.Icon] = None
        self._setup_tray()

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
                    "Sync Data", self._run_action(self.scheduler.sync_data, "Sync Data")
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
                    "Settings",
                    self._run_action(self.settings_gui.show_settings, "Show Settings"),
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
            # self.notification_service.notify(
            #     "Error", f"Failed to setup system tray: {str(e)}", "error"
            # )

    def _run_action(self, func, action_name: str):
        """
        Wrap an action to log and handle exceptions.
        Args:
            func: The function to execute.
            action_name: Name of the action for logging.
        Returns:
            Callable: Wrapped function.
        """

        def wrapper():
            self.logger.info(f"System tray action triggered: {action_name}")

            # For GUI-related actions, ensure they run on the main thread
            if action_name in ["Show Settings", "Show Dashboard"]:
                try:
                    # Schedule the function to run on the main thread
                    self.app.root.after(10, func)
                    self.logger.info(f"Scheduled {action_name} on main thread")
                    return
                except Exception as e:
                    self.logger.error(f"Failed to schedule {action_name}: {e}")
                    # Fall through to try direct execution

            # For non-GUI actions or if scheduling failed
            try:
                result = func()
                self.logger.info(f"System tray action completed: {action_name}")
                return result
            except Exception as e:
                self.logger.error(f"System tray action failed: {action_name} - {e}")
                # Use logger instead of notification to avoid potential recursive errors
                self.logger.error(f"Action failed: {action_name} - {str(e)}")

        return wrapper

    def _create_desktop_shortcut(self) -> None:
        """Create a desktop shortcut to the application."""
        try:
            from pathlib import Path
            from win32com.client import Dispatch

            desktop = Path.home() / "Desktop"
            shortcut_path = desktop / "PrimeSyncTrayApp.lnk"
            target_path = Path(
                r"C:\Program Files\PrimeSyncTrayApp\PrimeSyncTrayApp.exe"
            )
            icon_path = self.config.ICON_PATH

            if shortcut_path.exists():
                self.notification_service.notify(
                    "Desktop Shortcut", "Shortcut already exists on desktop", "info"
                )
                self.logger.info("Desktop shortcut already exists")
                return

            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.Targetpath = str(target_path)
            shortcut.WorkingDirectory = str(target_path.parent)
            shortcut.IconLocation = (
                str(icon_path) if icon_path and icon_path.exists() else str(target_path)
            )
            shortcut.Description = "PrimeSync Tray App for device management"
            shortcut.save()

            self.notification_service.notify(
                "Desktop Shortcut", "Desktop shortcut created successfully", "info"
            )
            self.logger.info(f"Created desktop shortcut at {shortcut_path}")
        except Exception as e:
            self.logger.error(f"Failed to create desktop shortcut: {e}")
            self.notification_service.notify(
                "Error", f"Failed to create desktop shortcut: {str(e)}", "error"
            )

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