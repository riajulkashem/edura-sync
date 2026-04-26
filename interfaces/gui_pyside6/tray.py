# interfaces/gui_pyside6/tray.py
"""
System tray icon and context menu.

Design rules:
  • GUI mode  — all sync actions delegate to MainWindow's trigger_*() methods,
    which use the WorkerManager + QThread workers.  No blocking on the main thread.
  • Headless mode — actions run in a plain Python thread so the Qt event loop
    stays responsive even without a visible window.
  • OperationManager guards headless-mode actions so two concurrent background
    jobs cannot run simultaneously.
"""
from __future__ import annotations

import logging
import platform
import threading
from typing import Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction, QCursor
from PySide6.QtCore import QTimer

from core.config import Config
from core.constants import APP_NAME
from core.operation_manager import OperationManager


class SystemTray:
    """Manages the system tray icon, context menu, and background operations."""

    def __init__(
        self,
        app,                   # EduraSync application instance
        config: Config,
        device_manager,
        api_sync,
        dashboard_gui,         # MainWindow or None (headless/service mode)
        notification_service,
    ):
        self.app                  = app
        self.config               = config
        self.device_manager       = device_manager
        self.api_sync             = api_sync
        self.dashboard_gui        = dashboard_gui
        self.notification_service = notification_service
        self.logger               = logging.getLogger(__name__)
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.operation_manager    = OperationManager()

        self.is_tray_supported = QSystemTrayIcon.isSystemTrayAvailable()
        if self.is_tray_supported:
            self._setup_tray()
        else:
            self.logger.info("System tray not available on this platform")

    # ── Tray construction ─────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon()

        icon_path = self.config.ICON_PATH
        if icon_path and icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            self.tray_icon.setIcon(
                QApplication.style().standardIcon(QApplication.StandardPixmap.SP_ComputerIcon)
            )
            self.logger.warning(f"Tray icon not found at {icon_path}, using default")

        self.tray_icon.setToolTip(APP_NAME)

        # Build and keep a reference to the menu.
        self._menu = self._build_menu()

        if platform.system() == "Darwin":
            # macOS: do NOT call setContextMenu(). When setContextMenu is used
            # on macOS, Qt hands click control to the OS which shows only a
            # tiny native "dot" indicator and never fires a Qt popup.
            # Instead we handle every click ourselves in _on_activated().
            pass
        else:
            # Windows / Linux: Qt shows the menu automatically on right-click.
            self.tray_icon.setContextMenu(self._menu)

        self.tray_icon.activated.connect(self._on_activated)

    def _build_menu(self) -> QMenu:
        menu = QMenu()

        # ── Open dashboard ────────────────────────────────────────────────────
        if self.dashboard_gui:
            menu.addAction(self._action(
                "Open Dashboard",
                lambda: self.dashboard_gui.show_dashboard(),
                use_worker=False,
            ))
            menu.addAction(self._action(
                "Open Settings",
                lambda: (self.dashboard_gui.show_dashboard(), self.dashboard_gui._switch_page(3)),
                use_worker=False,
            ))
            menu.addSeparator()

        # ── Sync actions ──────────────────────────────────────────────────────
        if self.dashboard_gui:
            # GUI mode — delegate to MainWindow workers (non-blocking)
            menu.addAction(self._action(
                "⬇  Pull from Devices",
                self.dashboard_gui.trigger_pull_from_devices,
                use_worker=False,  # MainWindow already manages the worker
            ))
            menu.addAction(self._action(
                "⬆  Post to Cloud",
                self.dashboard_gui.trigger_post_to_cloud,
                use_worker=False,
            ))
            menu.addAction(self._action(
                "⬇⬆  Sync Attendance",
                self.dashboard_gui.trigger_sync_attendance,
                use_worker=False,
            ))
            menu.addAction(self._action(
                "↻  Sync Users & Devices",
                self.dashboard_gui.trigger_sync_users,
                use_worker=False,
            ))
            menu.addAction(self._action(
                "●  Check Device Status",
                self.dashboard_gui.trigger_check_devices,
                use_worker=False,
            ))
        else:
            # Headless / service mode — run in a background thread
            menu.addAction(self._action(
                "⬇  Pull from Devices",
                self.device_manager.pull_data,
                description="Pull attendance from devices",
            ))
            menu.addAction(self._action(
                "⬆  Post to Cloud",
                self.api_sync.post_to_cloud,
                description="Upload attendance to cloud",
            ))
            menu.addAction(self._action(
                "⬇⬆  Sync Attendance",
                self._headless_full_sync,
                description="Sync attendance (pull + upload)",
            ))
            menu.addAction(self._action(
                "↻  Sync Users & Devices",
                self.api_sync.sync_users,
                description="Sync user profiles",
            ))
            menu.addAction(self._action(
                "●  Check Device Status",
                self.device_manager.check_devices,
                description="Check device connectivity",
            ))

        # ── App control ───────────────────────────────────────────────────────
        menu.addSeparator()
        menu.addAction(self._action(
            "Quit",
            self.app.exit_app,
            use_worker=False,
        ))

        return menu

    def _action(
        self,
        label: str,
        callback,
        description: str = "",
        use_worker: bool = True,
    ) -> QAction:
        """
        Build a QAction.

        use_worker=False  → callback is called directly on the main thread
                            (safe for navigation / delegating to MainWindow workers).
        use_worker=True   → callback is wrapped in a daemon thread with
                            OperationManager locking (headless mode only).
        """
        if use_worker:
            slot = self._headless_action(callback, description or label)
        else:
            slot = callback

        act = QAction(label)
        act.triggered.connect(slot)
        return act

    # ── Headless-mode thread wrapper ──────────────────────────────────────────

    def _headless_action(self, fn, description: str):
        """Return a callable that runs *fn* in a daemon thread with operation locking."""
        def slot():
            if self.operation_manager.is_operation_in_progress():
                current = self.operation_manager.get_current_operation()
                self.logger.warning(f"Cannot start '{description}' — '{current}' in progress")
                self.notification_service.notify(
                    "Busy",
                    f"Cannot start: another operation is already running ({current}).",
                    "warning",
                )
                return

            def run():
                if not self.operation_manager.acquire_operation_lock(description):
                    return
                try:
                    self.logger.info(f"Tray: starting '{description}'")
                    fn()
                    self.logger.info(f"Tray: completed '{description}'")
                    self.notification_service.notify(description, "Completed successfully.", "info")
                except Exception as e:
                    self.logger.error(f"Tray: '{description}' failed: {e}", exc_info=True)
                    self.notification_service.notify(description, f"Failed: {e}", "error")
                finally:
                    self.operation_manager.release_operation_lock(description)

            t = threading.Thread(target=run, daemon=True, name=f"tray-{description}")
            t.start()

        return slot

    def _headless_full_sync(self):
        """Pull from devices then upload to cloud (headless mode, already in worker thread)."""
        self.device_manager.pull_data()
        self.api_sync.post_to_cloud()

    # ── Activation ────────────────────────────────────────────────────────────

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.dashboard_gui:
                self.dashboard_gui.show_dashboard()

        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            if platform.system() == "Darwin":
                # macOS: single click shows the context menu.
                # exec() creates a proper blocking event loop for the menu so it
                # stays open until the user picks an item or clicks away — unlike
                # popup() which can dismiss instantly on macOS.
                self._menu.exec(QCursor.pos())
            else:
                # Windows / Linux: single-click restores the window.
                if self.dashboard_gui:
                    self.dashboard_gui.show_dashboard()

        elif reason == QSystemTrayIcon.ActivationReason.Context:
            # Right-click (non-macOS) — safety net in case setContextMenu()
            # doesn't fire automatically in some window managers.
            self._menu.exec(QCursor.pos())

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        if self.tray_icon:
            self.tray_icon.show()
        else:
            self.logger.info("No system tray — running in dashboard-only mode")

    def stop(self) -> None:
        if self.tray_icon:
            self.tray_icon.hide()
            self.logger.info("System tray hidden")

    def cleanup(self) -> None:
        self.stop()
        self.logger.info("SystemTray resources cleaned up")
