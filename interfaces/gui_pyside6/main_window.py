# interfaces/gui_pyside6/main_window.py
"""
New MainWindow shell.

Architecture:
    QMainWindow
    └── central QWidget
        └── QHBoxLayout
            ├── SidebarWidget       ← navigation
            └── QStackedWidget      ← page container
                ├── DashboardScreen (0)
                ├── DevicesScreen   (1)
                ├── AttendanceScreen(2)
                ├── SettingsScreen  (3)
                └── AboutScreen     (4)

All blocking operations (device ↔ cloud sync) run in QThread workers via
WorkerManager so the UI never freezes.
"""
from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QStackedWidget, QLabel, QProgressBar,
    QStatusBar, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap

from core.config import Config
from core.constants import APP_NAME

from interfaces.database.repository import (
    DeviceRepository, UserRepository,
    AttendanceRepository, SettingsRepository,
)
from interfaces.gui_pyside6.theme import (
    tokens, apply_theme, WINDOW_MIN_W, WINDOW_MIN_H, SPACE_SM
)
from interfaces.gui_pyside6.widgets import SidebarWidget, Spinner
from interfaces.gui_pyside6.screens import (
    DashboardScreen, DevicesScreen,
    AttendanceScreen, SettingsScreen, AboutScreen,
)
from services.sync_workers import (
    CheckDevicesWorker, PullDataWorker,
    PostToCloudWorker, SyncUsersWorker,
    FullSyncWorker, SetupSyncWorker, WorkerManager,
)

# Page indexes matching SidebarWidget.NAV_ITEMS + BOTTOM_ITEMS
PAGE_DASHBOARD  = 0
PAGE_DEVICES    = 1
PAGE_ATTENDANCE = 2
PAGE_SETTINGS   = 3
PAGE_ABOUT      = 4


class MainWindow(QMainWindow):
    """
    Top-level application window.

    Instantiated by EduraSync.__init__ instead of DashboardGUI.
    Provides the same public interface that main.py + tray.py expect:
        show_dashboard(first_run=False)
        hide_dashboard()
        cleanup()
        show_status_log(message, level)
        start_periodic_refresh(interval_ms)
        stop_periodic_refresh()
        set_device_manager(dm)
    """

    # Kept for API compatibility — same as old DashboardGUI.TAB_SETTINGS
    TAB_SETTINGS = PAGE_SETTINGS

    def __init__(
        self,
        app_ref,            # EduraSync instance
        device_repo:     DeviceRepository,
        user_repo:       UserRepository,
        notification_service,
        settings_repo:   SettingsRepository | None = None,
        api_sync=None,
    ):
        super().__init__()
        self.logger              = logging.getLogger(__name__)
        self.app_ref             = app_ref
        self.device_repo         = device_repo
        self.user_repo           = user_repo
        self.notification_service = notification_service
        self.settings_repo       = settings_repo or SettingsRepository()
        self.api_sync            = api_sync
        self.attendance_repo     = AttendanceRepository()
        self.device_manager      = None  # set later via set_device_manager()

        self._refresh_timer: QTimer | None = None
        self._worker_manager = WorkerManager(
            on_started=self._on_worker_started,
            on_progress=self._on_worker_progress,
            on_finished=self._on_worker_finished,
        )

        self._setup_window()
        self._setup_ui()
        self._connect_dashboard_actions()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        t = tokens()
        self.setWindowTitle(f"{APP_NAME}")
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.resize(1120, 720)
        self._set_icon()

    def _set_icon(self) -> None:
        try:
            icon_path = Config().ICON_PATH
            if icon_path and icon_path.exists():
                self.setWindowIcon(QIcon(QPixmap(str(icon_path))))
        except Exception as e:
            self.logger.warning(f"Could not set window icon: {e}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        t = tokens()

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self._sidebar = SidebarWidget()
        self._sidebar.page_changed.connect(self._switch_page)
        root.addWidget(self._sidebar)

        # ── Pages ─────────────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        self._dashboard_screen = DashboardScreen(
            self.device_repo,
            self.user_repo,
            self.attendance_repo,
            self.settings_repo,
        )
        self._devices_screen    = DevicesScreen()
        self._attendance_screen = AttendanceScreen()
        self._settings_screen   = SettingsScreen(self.api_sync, self.app_ref)
        self._about_screen      = AboutScreen()

        for screen in [
            self._dashboard_screen,
            self._devices_screen,
            self._attendance_screen,
            self._settings_screen,
            self._about_screen,
        ]:
            self._stack.addWidget(screen)

        # ── Status bar ────────────────────────────────────────────────────────
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 11px; background: transparent;")
        self._statusbar.addWidget(self._status_label, stretch=1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setMaximumHeight(10)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setVisible(False)
        self._statusbar.addPermanentWidget(self._progress_bar)

        self._spinner = Spinner(14)
        self._statusbar.addPermanentWidget(self._spinner)

        tray_btn = QPushButton("Minimize to Tray")
        tray_btn.setProperty("variant", "ghost")
        tray_btn.setMaximumHeight(24)
        tray_btn.clicked.connect(self._minimize_to_tray)
        self._statusbar.addPermanentWidget(tray_btn)

    # ── Page switching ────────────────────────────────────────────────────────

    def _switch_page(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        if index == PAGE_ATTENDANCE:
            self._attendance_screen.refresh()
        elif index == PAGE_SETTINGS:
            self._settings_screen.refresh()
        elif index == PAGE_DEVICES:
            self._devices_screen.load_devices()

    # ── Wire dashboard action buttons → workers ───────────────────────────────

    def _connect_dashboard_actions(self) -> None:
        ds = self._dashboard_screen
        ds.sig_check_devices.connect(self._run_check_devices)
        ds.sig_pull_from_devices.connect(self._run_fetch_logs)
        ds.sig_post_to_cloud.connect(self._run_upload)
        ds.sig_sync_attendance.connect(self._run_full_sync)
        ds.sig_sync_users.connect(self._run_sync_users)

        # Settings screen signals
        self._settings_screen.settings_saved.connect(self._on_settings_saved)
        self._settings_screen.sig_initial_sync.connect(self._run_setup_sync)

    # ── Worker launch helpers ─────────────────────────────────────────────────

    def _ensure_device_manager(self) -> bool:
        if self.device_manager is None:
            QMessageBox.warning(self, "Not Ready", "Device manager is not initialised yet.")
            return False
        return True

    def _ensure_api_sync(self) -> bool:
        if self.api_sync is None:
            QMessageBox.warning(self, "Not Ready", "API sync is not initialised yet.")
            return False
        return True

    def _run_check_devices(self) -> None:
        if not self._ensure_device_manager():
            return
        self._worker_manager.run(CheckDevicesWorker(self.device_manager, parent=self))

    def _run_fetch_logs(self) -> None:
        if not self._ensure_device_manager():
            return
        self._worker_manager.run(PullDataWorker(self.device_manager, parent=self))

    def _run_upload(self) -> None:
        if not self._ensure_api_sync():
            return
        self._worker_manager.run(PostToCloudWorker(self.api_sync, parent=self))

    def _run_sync_users(self) -> None:
        if not self._ensure_api_sync():
            return
        self._worker_manager.run(SyncUsersWorker(self.api_sync, parent=self))

    def _run_full_sync(self) -> None:
        if not self._ensure_device_manager() or not self._ensure_api_sync():
            return
        self._worker_manager.run(FullSyncWorker(self.device_manager, self.api_sync, parent=self))

    def _run_setup_sync(self) -> None:
        if not self._ensure_device_manager() or not self._ensure_api_sync():
            return
        self._worker_manager.run(SetupSyncWorker(self.device_manager, self.api_sync, parent=self))

    # ── Worker signal handlers ────────────────────────────────────────────────

    def _on_worker_started(self) -> None:
        self._spinner.start()
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._dashboard_screen.set_busy(True)
        self._status_label.setText("Working…")
        t = tokens()
        self._status_label.setStyleSheet(f"color: {t['warning']}; font-size: 11px; background: transparent;")

    def _on_worker_progress(self, pct: int, msg: str) -> None:
        self._progress_bar.setValue(pct)
        self._status_label.setText(msg)

    def _on_worker_finished(self, success: bool, message: str) -> None:
        self._spinner.stop()
        self._progress_bar.setVisible(False)
        self._dashboard_screen.set_busy(False)
        t = tokens()

        if success:
            self._status_label.setText(f"✓  {message}")
            self._status_label.setStyleSheet(f"color: {t['success']}; font-size: 11px; background: transparent;")
            self.notification_service.notify("Sync", message, "info")
        else:
            self._status_label.setText(f"✗  {message}")
            self._status_label.setStyleSheet(f"color: {t['danger']}; font-size: 11px; background: transparent;")
            self.notification_service.notify("Sync Error", message, "error")

        # Refresh visible screen data
        self._dashboard_screen.refresh()
        if self._stack.currentIndex() == PAGE_ATTENDANCE:
            self._attendance_screen.refresh()

        # Reset status colour after 8 s
        QTimer.singleShot(8000, self._reset_status_style)

    def _reset_status_style(self) -> None:
        t = tokens()
        self._status_label.setText("Ready")
        self._status_label.setStyleSheet(f"color: {t['text_secondary']}; font-size: 11px; background: transparent;")

    # ── Tray + window events ──────────────────────────────────────────────────

    def _minimize_to_tray(self) -> None:
        self.hide()
        self.notification_service.notify(
            APP_NAME,
            "Minimized to system tray. Click the tray icon to restore.",
            "info",
        )

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()

    # ── Settings changed ──────────────────────────────────────────────────────

    def _on_settings_saved(self) -> None:
        if self.app_ref and hasattr(self.app_ref, "_start_periodic_tasks"):
            self.app_ref._start_periodic_tasks()

    # ── Public API expected by main.py / tray.py ──────────────────────────────

    # ── Public trigger methods (used by SystemTray in GUI mode) ──────────────

    def trigger_check_devices(self)     -> None: self._run_check_devices()
    def trigger_pull_from_devices(self) -> None: self._run_fetch_logs()
    def trigger_post_to_cloud(self)     -> None: self._run_upload()
    def trigger_sync_attendance(self)   -> None: self._run_full_sync()
    def trigger_sync_users(self)        -> None: self._run_sync_users()

    def show_dashboard(self, first_run: bool = False) -> None:
        """Show (or restore) the window. Navigate to Settings on first run."""
        self.show()
        self.raise_()
        self.activateWindow()
        if first_run:
            self._switch_page(PAGE_SETTINGS)
            self._sidebar.set_active(PAGE_SETTINGS)

    def hide_dashboard(self) -> None:
        self.hide()

    def show_status_log(self, message: str, level: str = "info") -> None:
        """Update the status bar. Compatible with old DashboardGUI.show_status_log."""
        t = tokens()
        colour = {
            "info":    t["text_secondary"],
            "success": t["success"],
            "warning": t["warning"],
            "error":   t["danger"],
        }.get(level, t["text_secondary"])
        self._status_label.setText(message)
        self._status_label.setStyleSheet(f"color: {colour}; font-size: 11px; background: transparent;")

    def set_device_manager(self, device_manager) -> None:
        self.device_manager = device_manager

    def start_periodic_refresh(self, interval_ms: int = 30_000) -> None:
        if self._refresh_timer is None:
            self._refresh_timer = QTimer(self)
            self._refresh_timer.timeout.connect(self._dashboard_screen.refresh)
        if not self._refresh_timer.isActive():
            self._refresh_timer.start(interval_ms)

    def stop_periodic_refresh(self) -> None:
        if self._refresh_timer and self._refresh_timer.isActive():
            self._refresh_timer.stop()

    def cleanup(self) -> None:
        self.stop_periodic_refresh()
        if self._refresh_timer:
            self._refresh_timer.deleteLater()
            self._refresh_timer = None
        self._dashboard_screen.cleanup()
        self.deleteLater()
        self.logger.info("MainWindow resources cleaned up")
