# services/sync_workers.py
"""
QThread workers for all blocking sync operations.

Every operation that touches the network or ZKTeco devices runs here — never
on the Qt main thread.  Each worker emits:
    started()               — operation has begun
    progress(int, str)      — 0-100 percent, human-readable message
    finished(bool, str)     — success flag, summary message
"""
from __future__ import annotations

import logging
from PySide6.QtCore import QThread, Signal


logger = logging.getLogger(__name__)


class _BaseWorker(QThread):
    """Common base for all sync workers."""

    started_op  = Signal()
    progress    = Signal(int, str)   # percent, message
    finished_op = Signal(bool, str)  # success, summary

    def __init__(self, parent=None):
        super().__init__(parent)

    def _emit_progress(self, pct: int, msg: str) -> None:
        self.progress.emit(pct, msg)

    def _emit_done(self, ok: bool, msg: str) -> None:
        self.finished_op.emit(ok, msg)


class CheckDevicesWorker(_BaseWorker):
    """Check connectivity of all configured ZKTeco devices."""

    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self._device_manager = device_manager

    def run(self) -> None:
        self.started_op.emit()
        try:
            self._emit_progress(10, "Connecting to devices…")
            online = self._device_manager.check_devices()
            self._emit_progress(100, "Device check complete")
            self._emit_done(True, f"{online} device(s) online")
        except Exception as e:
            logger.error(f"CheckDevicesWorker error: {e}", exc_info=True)
            self._emit_done(False, f"Device check failed: {e}")


class PullDataWorker(_BaseWorker):
    """Pull attendance and user data from all ZKTeco devices."""

    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self._device_manager = device_manager

    def run(self) -> None:
        self.started_op.emit()
        try:
            self._emit_progress(10, "Connecting to devices…")
            self._device_manager.pull_data()
            self._emit_progress(100, "Device pull complete")
            self._emit_done(True, "Attendance data fetched successfully")
        except Exception as e:
            logger.error(f"PullDataWorker error: {e}", exc_info=True)
            self._emit_done(False, f"Fetch failed: {e}")


class PostToCloudWorker(_BaseWorker):
    """Upload pending attendance records to the cloud API."""

    def __init__(self, api_sync, parent=None):
        super().__init__(parent)
        self._api_sync = api_sync

    def run(self) -> None:
        self.started_op.emit()
        try:
            self._emit_progress(10, "Connecting to cloud API…")
            self._api_sync.post_to_cloud()
            self._emit_progress(100, "Upload complete")
            self._emit_done(True, "Attendance records uploaded successfully")
        except Exception as e:
            logger.error(f"PostToCloudWorker error: {e}", exc_info=True)
            self._emit_done(False, f"Upload failed: {e}")


class SyncUsersWorker(_BaseWorker):
    """Pull users and devices from cloud, save to DB, push to devices."""

    def __init__(self, api_sync, parent=None):
        super().__init__(parent)
        self._api_sync = api_sync

    def run(self) -> None:
        self.started_op.emit()
        try:
            self._emit_progress(10, "Fetching user profiles from cloud…")
            success = self._api_sync.sync_users()
            self._emit_progress(100, "Profile sync complete")
            if success:
                self._emit_done(True, "User profiles synced successfully")
            else:
                self._emit_done(False, "Profile sync failed — check API settings")
        except Exception as e:
            logger.error(f"SyncUsersWorker error: {e}", exc_info=True)
            self._emit_done(False, f"Profile sync failed: {e}")


class FullSyncWorker(_BaseWorker):
    """
    Sync Attendance: pull attendance from devices → upload to cloud.
    This is the everyday operation after users are already configured.
    """

    def __init__(self, device_manager, api_sync, parent=None):
        super().__init__(parent)
        self._device_manager = device_manager
        self._api_sync = api_sync

    def run(self) -> None:
        self.started_op.emit()
        try:
            self._emit_progress(10, "Connecting to devices…")
            self._device_manager.pull_data()
            self._emit_progress(55, "Uploading attendance to cloud…")
            self._api_sync.post_to_cloud()
            self._emit_progress(100, "Attendance sync complete")
            self._emit_done(True, "Attendance synchronization completed successfully")
        except Exception as e:
            logger.error(f"FullSyncWorker error: {e}", exc_info=True)
            self._emit_done(False, f"Attendance sync failed: {e}")


class SetupSyncWorker(_BaseWorker):
    """
    Initial setup sync (run once after installation or credential change):
      1. Sync users & device list from cloud  → save to local DB
      2. Push users to ZKTeco devices
      3. Pull any existing attendance from devices → local DB
      4. Upload attendance to cloud

    This is more thorough than FullSyncWorker and is designed to be run
    from the Settings screen right after the API credentials are configured.
    """

    def __init__(self, device_manager, api_sync, parent=None):
        super().__init__(parent)
        self._device_manager = device_manager
        self._api_sync = api_sync

    def run(self) -> None:
        self.started_op.emit()
        try:
            self._emit_progress(5,  "Step 1 / 4 — Pulling users & devices from cloud…")
            self._api_sync.sync_users()

            self._emit_progress(35, "Step 2 / 4 — Pushing user profiles to devices…")
            self._device_manager.migrate_user_to_device()

            self._emit_progress(60, "Step 3 / 4 — Fetching attendance from devices…")
            self._device_manager.pull_data()

            self._emit_progress(85, "Step 4 / 4 — Uploading attendance to cloud…")
            self._api_sync.post_to_cloud()

            self._emit_progress(100, "Initial sync complete")
            self._emit_done(True, "Initial sync completed — system is fully up to date")
        except Exception as e:
            logger.error(f"SetupSyncWorker error: {e}", exc_info=True)
            self._emit_done(False, f"Initial sync failed: {e}")


class WorkerManager:
    """
    Manages a single active worker at a time.

    Callers pass pre-built worker instances.  The manager connects common
    signals and prevents launching a second worker while one is running.
    """

    def __init__(self, on_started=None, on_progress=None, on_finished=None):
        self._worker: _BaseWorker | None = None
        self._on_started  = on_started
        self._on_progress = on_progress
        self._on_finished = on_finished

    @property
    def is_busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def run(self, worker: _BaseWorker) -> bool:
        """
        Start *worker*.  Returns False (and does nothing) if another worker
        is still running.
        """
        if self.is_busy:
            logger.warning("WorkerManager: ignoring run() — previous worker still active")
            return False

        self._worker = worker

        if self._on_started:
            worker.started_op.connect(self._on_started)
        if self._on_progress:
            worker.progress.connect(self._on_progress)
        if self._on_finished:
            worker.finished_op.connect(self._on_finished)

        # Clean up the thread object after it finishes.
        worker.finished.connect(lambda: self._cleanup())
        worker.start()
        return True

    def _cleanup(self) -> None:
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
