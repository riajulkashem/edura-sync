# interfaces/gui_pyside6/tray.py
"""
System tray icon and context menu.

Design rules:
  • GUI mode    — all sync actions delegate to MainWindow's trigger_*() methods,
                  which use the WorkerManager + QThread workers.  No blocking
                  on the main thread.
  • Headless mode — actions run in a plain Python thread so the Qt event loop
                  stays responsive even without a visible window.
  • OperationManager guards headless-mode actions so two concurrent background
                  jobs cannot run simultaneously.

Fix notes (vs. previous version):
  • setContextMenu() is NEVER called — on macOS it hands control to the OS
    which renders a native "dot" indicator and never fires a proper Qt popup.
  • Every QAction created by _build_menu() is appended to self._actions so
    Python's garbage collector cannot destroy them while the menu is alive.
  • self._menu is an instance attribute (not a local) so the QMenu itself is
    also protected from GC.
  • The popup is always deferred through QTimer.singleShot(0) so it executes
    outside the activated-signal handler — required on both macOS and Windows
    for the menu to paint and stay open reliably.
"""
from __future__ import annotations

import logging
import platform
import threading
from typing import List, Optional

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
        app,                    # EduraSync application instance
        config: Config,
        device_manager,
        api_sync,
        dashboard_gui,          # MainWindow or None (headless / service mode)
        notification_service,
    ) -> None:
        self.app                  = app
        self.config               = config
        self.device_manager       = device_manager
        self.api_sync             = api_sync
        self.dashboard_gui        = dashboard_gui
        self.notification_service = notification_service
        self.logger               = logging.getLogger(__name__)
        self.operation_manager    = OperationManager()

        # These are kept as instance attributes so neither the QMenu nor any
        # QAction inside it can be garbage-collected while the tray is alive.
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self._menu:     Optional[QMenu]           = None
        self._actions:  List[QAction]             = []   # GC anchor for every action

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
                QApplication.style().standardIcon(
                    QApplication.StandardPixmap.SP_ComputerIcon
                )
            )
            self.logger.warning(
                f"Tray icon not found at {icon_path}, using default"
            )

        self.tray_icon.setToolTip(APP_NAME)

        # Build the menu and keep a hard reference on self so Python GC never
        # destroys it.  Do NOT call setContextMenu() — see module docstring.
        self._menu = self._build_menu()

        self.tray_icon.activated.connect(self._on_activated)

    def _build_menu(self) -> QMenu:
        """
        Construct the context menu.

        Every QAction is appended to self._actions so it has a Python-level
        owner and cannot be garbage-collected between menu builds.
        """
        # Clear any previously stored actions (e.g. if menu is rebuilt).
        self._actions.clear()

        menu = QMenu()

        def add_action(action: QAction) -> QAction:
            """Append to GC-anchor list, add to menu, return for chaining."""
            self._actions.append(action)
            menu.addAction(action)
            return action

        # ── Open dashboard ────────────────────────────────────────────────────
        if self.dashboard_gui:
            add_action(self._make_action(
                "Open Dashboard",
                lambda: self.dashboard_gui.show_dashboard(),
            ))
            add_action(self._make_action(
                "Open Settings",
                lambda: (
                    self.dashboard_gui.show_dashboard(),
                    self.dashboard_gui._switch_page(3),
                ),
            ))
            menu.addSeparator()

        # ── Sync actions ──────────────────────────────────────────────────────
        if self.dashboard_gui:
            # GUI mode — delegate to MainWindow workers (non-blocking).
            add_action(self._make_action(
                "⬇  Pull from Devices",
                self.dashboard_gui.trigger_pull_from_devices,
            ))
            add_action(self._make_action(
                "⬆  Post to Cloud",
                self.dashboard_gui.trigger_post_to_cloud,
            ))
            add_action(self._make_action(
                "⬇⬆  Sync Attendance",
                self.dashboard_gui.trigger_sync_attendance,
            ))
            add_action(self._make_action(
                "↻  Sync Users & Devices",
                self.dashboard_gui.trigger_sync_users,
            ))
            add_action(self._make_action(
                "●  Check Device Status",
                self.dashboard_gui.trigger_check_devices,
            ))
        else:
            # Headless / service mode — run each action in a daemon thread.
            add_action(self._make_action(
                "⬇  Pull from Devices",
                self._headless_action(
                    self.device_manager.pull_data,
                    "Pull attendance from devices",
                ),
            ))
            add_action(self._make_action(
                "⬆  Post to Cloud",
                self._headless_action(
                    self.api_sync.post_to_cloud,
                    "Upload attendance to cloud",
                ),
            ))
            add_action(self._make_action(
                "⬇⬆  Sync Attendance",
                self._headless_action(
                    self._headless_full_sync,
                    "Sync attendance (pull + upload)",
                ),
            ))
            add_action(self._make_action(
                "↻  Sync Users & Devices",
                self._headless_action(
                    self.api_sync.sync_users,
                    "Sync user profiles",
                ),
            ))
            add_action(self._make_action(
                "●  Check Device Status",
                self._headless_action(
                    self.device_manager.check_devices,
                    "Check device connectivity",
                ),
            ))

        # ── App control ───────────────────────────────────────────────────────
        menu.addSeparator()
        add_action(self._make_action("Quit", self.app.exit_app))

        return menu

    @staticmethod
    def _make_action(label: str, slot) -> QAction:
        """
        Create a QAction with the given label and connect *slot* to triggered.

        The action is intentionally created without a parent widget so it can
        be owned exclusively by self._actions (our GC anchor).  Passing a
        parent here would let Qt try to manage lifetime independently, which
        can conflict with our explicit ownership model.
        """
        action = QAction(label)
        action.triggered.connect(slot)
        return action

    # ── Headless-mode thread wrapper ──────────────────────────────────────────

    def _headless_action(self, fn, description: str):
        """
        Return a *callable* that runs *fn* in a daemon thread with operation
        locking.  Suitable for passing directly to _make_action as the slot.
        """
        def slot() -> None:
            if self.operation_manager.is_operation_in_progress():
                current = self.operation_manager.get_current_operation()
                self.logger.warning(
                    f"Cannot start '{description}' — '{current}' in progress"
                )
                self.notification_service.notify(
                    "Busy",
                    f"Cannot start: another operation is already running ({current}).",
                    "warning",
                )
                return

            def run() -> None:
                if not self.operation_manager.acquire_operation_lock(description):
                    return
                try:
                    self.logger.info(f"Tray: starting '{description}'")
                    fn()
                    self.logger.info(f"Tray: completed '{description}'")
                    self.notification_service.notify(
                        description, "Completed successfully.", "info"
                    )
                except Exception as exc:
                    self.logger.error(
                        f"Tray: '{description}' failed: {exc}", exc_info=True
                    )
                    self.notification_service.notify(
                        description, f"Failed: {exc}", "error"
                    )
                finally:
                    self.operation_manager.release_operation_lock(description)

            thread = threading.Thread(
                target=run,
                daemon=True,
                name=f"tray-{description}",
            )
            thread.start()

        return slot

    def _headless_full_sync(self) -> None:
        """Pull from devices then upload to cloud (headless mode, already in worker thread)."""
        self.device_manager.pull_data()
        self.api_sync.post_to_cloud()

    # ── Activation ────────────────────────────────────────────────────────────

    def _show_menu(self) -> None:
        """
        Popup the context menu at the current cursor position.

        Always invoked via QTimer.singleShot(0) so it executes *outside* the
        activated-signal handler.  This is required on both macOS and Windows
        for the menu to paint correctly and stay open until the user dismisses
        it.  popup() is non-blocking, keeping the Qt event loop alive.
        """
        if self._menu is not None:
            self._menu.popup(QCursor.pos())

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        is_mac = platform.system() == "Darwin"

        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double-click always opens / raises the dashboard window.
            if self.dashboard_gui:
                self.dashboard_gui.show_dashboard()

        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            if is_mac:
                # macOS: single left-click on the menu-bar icon shows the
                # context menu (standard macOS behaviour for tray apps).
                QTimer.singleShot(0, self._show_menu)
            else:
                # Windows / Linux: single left-click restores the main window.
                if self.dashboard_gui:
                    self.dashboard_gui.show_dashboard()

        elif reason == QSystemTrayIcon.ActivationReason.Context:
            # Right-click on ALL platforms shows the context menu.
            QTimer.singleShot(0, self._show_menu)

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
        self._actions.clear()
        self._menu = None
        self.logger.info("SystemTray resources cleaned up")