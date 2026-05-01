# interfaces/gui_pyside6/screens/settings_screen.py
"""Settings screen — cloud API config, sync schedule, maintenance."""
from __future__ import annotations

import logging
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QTimeEdit, QComboBox,
    QGroupBox, QCheckBox, QMessageBox, QFrame, QScrollArea, QSizePolicy,
    QAbstractScrollArea
)
from PySide6.QtCore import Qt, QTime, Signal
from PySide6.QtWidgets import QDialog

from core.constants import DEFAULT_SETTING
from core.exceptions import ValidationError
from interfaces.gui_pyside6.theme import tokens, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL
from interfaces.database.repository import SettingsRepository, DeviceRepository
from interfaces.gui_pyside6.widgets import ConfirmDialog


class SettingsScreen(QWidget):
    """
    Settings screen with two-column layout for the config boxes.
    Signals:
      settings_saved — emitted after successful save so main window can reschedule tasks.
    """

    settings_saved   = Signal()
    sig_initial_sync = Signal()  # Triggers SetupSyncWorker from main_window

    def __init__(self, api_sync, app_ref, settings_repo=None, device_repo=None, parent=None):
        super().__init__(parent)
        self.logger        = logging.getLogger(__name__)
        self.api_sync      = api_sync
        self.app_ref       = app_ref
        self.settings_repo = settings_repo or SettingsRepository()
        self.device_repo   = device_repo or DeviceRepository()

        self._form: dict[str, QWidget] = {}

        # Windows service management (None on non-Windows)
        self._service_manager = None
        self._service_status_lbl: QLabel | None = None
        self._service_toggle_btn: QPushButton | None = None

        self._setup_ui()
        self._load_settings()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        t = tokens()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        outer.setSpacing(SPACE_LG)

        title = QLabel("Settings")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {t['text_primary']}; background: transparent;"
        )
        outer.addWidget(title)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, SPACE_MD, 0)
        layout.setSpacing(SPACE_XL)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        # ── Two config boxes side by side ─────────────────────────────────────
        cols_row = QHBoxLayout()
        cols_row.setSpacing(SPACE_LG)

        # Left column — Cloud API
        cloud_group = QGroupBox("Cloud API Configuration")
        cloud_form  = QFormLayout(cloud_group)
        cloud_form.setSpacing(SPACE_MD)
        cloud_form.setContentsMargins(SPACE_MD, SPACE_LG, SPACE_MD, SPACE_MD)
        cloud_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        cloud_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._form["cloud_api_url"] = QLineEdit()
        self._form["cloud_api_url"].setPlaceholderText("https://api.example.com")
        self._form["cloud_api_url"].setMinimumWidth(280)
        self._form["cloud_api_url"].setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cloud_form.addRow("API URL:", self._form["cloud_api_url"])

        self._form["sync_id"] = QLineEdit()
        self._form["sync_id"].setPlaceholderText("Organisation sync token")
        self._form["sync_id"].setMinimumWidth(280)
        self._form["sync_id"].setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cloud_form.addRow("Sync ID:", self._form["sync_id"])

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        cloud_form.addRow("", test_btn)

        cols_row.addWidget(cloud_group)

        # Right column — Sync Schedule
        sched_group = QGroupBox("Sync Schedule")
        sched_form  = QFormLayout(sched_group)
        sched_form.setSpacing(SPACE_MD)
        sched_form.setContentsMargins(SPACE_MD, SPACE_LG, SPACE_MD, SPACE_MD)
        sched_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        sched_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._form["is_sync_enabled"] = QCheckBox("Enable daily automatic sync")
        self._form["is_sync_enabled"].setToolTip(
            "When checked, the app will automatically pull from devices and upload to cloud at the configured time."
        )
        self._form["is_sync_enabled"].stateChanged.connect(self._on_sync_enabled_changed)
        sched_form.addRow("", self._form["is_sync_enabled"])

        self._form["sync_time"] = QTimeEdit()
        self._form["sync_time"].setDisplayFormat("HH:mm")
        self._form["sync_time"].setMinimumWidth(120)
        self._form["sync_time"].setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._form["sync_time"].setToolTip("Daily time to pull from devices and push to cloud automatically")
        sched_form.addRow("Daily Sync Time:", self._form["sync_time"])

        cols_row.addWidget(sched_group)

        layout.addLayout(cols_row)

        # ── Save / Reset row ──────────────────────────────────────────────────
        save_row = QHBoxLayout()
        reset_defaults_btn = QPushButton("Reset to Defaults")
        reset_defaults_btn.clicked.connect(self._reset_form)
        save_btn = QPushButton("Save Settings")
        save_btn.setProperty("variant", "primary")
        save_btn.setMinimumHeight(34)
        save_btn.clicked.connect(self._save_settings)
        save_row.addStretch()
        save_row.addWidget(reset_defaults_btn)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        # ── Initial Setup / Sync Everything card ──────────────────────────────
        setup_card = QFrame()
        setup_card.setStyleSheet(
            f"QFrame {{ background-color: {t['accent_muted']}; border: none;"
            f" border-radius: 8px; }}"
        )
        setup_layout = QHBoxLayout(setup_card)
        setup_layout.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, SPACE_MD)
        setup_layout.setSpacing(SPACE_LG)

        setup_text_col = QVBoxLayout()
        setup_text_col.setSpacing(2)
        setup_title = QLabel("Sync Everything")
        setup_title.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {t['accent']}; background: transparent;"
        )
        setup_desc = QLabel(
            "Run this once after installation or after changing your API credentials. "
            "It will: pull users & device list from cloud → push users to machines → "
            "fetch attendance from devices → upload to cloud."
        )
        setup_desc.setWordWrap(True)
        setup_desc.setStyleSheet(
            f"font-size: 11px; color: {t['text_secondary']}; background: transparent;"
        )
        setup_text_col.addWidget(setup_title)
        setup_text_col.addWidget(setup_desc)
        setup_layout.addLayout(setup_text_col, stretch=1)

        sync_all_btn = QPushButton("⬇⬆  Sync Everything")
        sync_all_btn.setProperty("variant", "primary")
        sync_all_btn.setMinimumHeight(40)
        sync_all_btn.setMinimumWidth(160)
        sync_all_btn.setToolTip(
            "Sync users from cloud, push to devices, pull attendance, upload to cloud"
        )
        sync_all_btn.clicked.connect(self.sig_initial_sync)
        setup_layout.addWidget(sync_all_btn)

        layout.addWidget(setup_card)

        # ── Windows Background Service (Windows only) ─────────────────────────
        if sys.platform.startswith("win"):
            layout.addWidget(self._build_service_group())

        # ── Separator ─────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {t['border']}; border: none; max-height: 1px;")
        layout.addWidget(sep)

        # ── Advanced Maintenance (single flat row) ────────────────────────────
        maint_group = QGroupBox("Advanced Maintenance")
        maint_layout = QVBoxLayout(maint_group)
        maint_layout.setSpacing(SPACE_SM)
        maint_layout.setContentsMargins(SPACE_MD, SPACE_LG, SPACE_MD, SPACE_MD)

        info_lbl = QLabel(
            "These operations are irreversible — authorise with your Sync ID."
        )
        info_lbl.setStyleSheet(
            f"color: {t['text_secondary']}; font-size: 11px; background: transparent;"
        )
        info_lbl.setWordWrap(True)
        maint_layout.addWidget(info_lbl)

        # Single row: combo + Reset + Flush
        maint_row = QHBoxLayout()
        maint_row.setSpacing(SPACE_SM)

        self._device_combo = QComboBox()
        self._device_combo.setPlaceholderText("Select Machine…")
        self._device_combo.setToolTip("Select the biometric machine to reset")
        maint_row.addWidget(self._device_combo, stretch=1)

        reset_device_btn = QPushButton("Reset Machine")
        reset_device_btn.setProperty("variant", "danger")
        reset_device_btn.setToolTip("Erase all users and logs from the selected device")
        reset_device_btn.clicked.connect(self._reset_selected_device)
        maint_row.addWidget(reset_device_btn)

        flush_btn = QPushButton("Flush Local Database")
        flush_btn.setProperty("variant", "danger")
        flush_btn.setToolTip("Delete all local attendance, user and device records")
        flush_btn.clicked.connect(self._flush_database)
        maint_row.addWidget(flush_btn)

        maint_layout.addLayout(maint_row)
        layout.addWidget(maint_group)
        layout.addStretch()

        self._refresh_device_combo()

    # ── Windows Service helpers ───────────────────────────────────────────────

    def _build_service_group(self) -> QGroupBox:
        """Build the Windows Service management group (Windows-only)."""
        from services.service_manager import ServiceManager
        self._service_manager = ServiceManager()

        t = tokens()
        group = QGroupBox("Background Service  (Windows)")
        lv = QVBoxLayout(group)
        lv.setContentsMargins(SPACE_MD, SPACE_LG, SPACE_MD, SPACE_MD)
        lv.setSpacing(SPACE_MD)

        desc = QLabel(
            "Run EduraSync as a Windows Service so attendance syncs in the background "
            "even when the app window is closed. You will be prompted for administrator "
            "permission when enabling or disabling."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"font-size: 11px; color: {t['text_secondary']}; background: transparent;"
        )
        lv.addWidget(desc)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(SPACE_SM)

        self._service_status_lbl = QLabel("Checking…")
        self._service_status_lbl.setStyleSheet(
            f"font-weight: 600; font-size: 12px; color: {t['text_secondary']}; background: transparent;"
        )
        ctrl.addWidget(self._service_status_lbl, stretch=1)

        self._service_toggle_btn = QPushButton("Enable Service")
        self._service_toggle_btn.setMinimumWidth(140)
        self._service_toggle_btn.clicked.connect(self._toggle_service)
        ctrl.addWidget(self._service_toggle_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setMaximumWidth(80)
        refresh_btn.setToolTip("Re-check service status")
        refresh_btn.clicked.connect(self._update_service_status)
        ctrl.addWidget(refresh_btn)

        lv.addLayout(ctrl)
        self._update_service_status()
        return group

    def _update_service_status(self) -> None:
        """Refresh the service status label and toggle-button text/style."""
        if self._service_manager is None or self._service_status_lbl is None:
            return
        t = tokens()
        status = self._service_manager.get_service_status()

        if status == "not_installed":
            self._service_status_lbl.setText("❌  Service: Not Installed")
            self._service_status_lbl.setStyleSheet(
                f"font-weight: 600; font-size: 12px; color: {t['danger']}; background: transparent;"
            )
            self._service_toggle_btn.setText("Enable Service")
            self._service_toggle_btn.setProperty("variant", "primary")
        elif status == "running":
            self._service_status_lbl.setText("✅  Service: Running")
            self._service_status_lbl.setStyleSheet(
                f"font-weight: 600; font-size: 12px; color: {t['success']}; background: transparent;"
            )
            self._service_toggle_btn.setText("Disable Service")
            self._service_toggle_btn.setProperty("variant", "danger")
        elif status == "stopped":
            self._service_status_lbl.setText("⚠  Service: Stopped")
            self._service_status_lbl.setStyleSheet(
                f"font-weight: 600; font-size: 12px; color: {t['warning']}; background: transparent;"
            )
            self._service_toggle_btn.setText("Enable Service")
            self._service_toggle_btn.setProperty("variant", "primary")
        else:
            self._service_status_lbl.setText("❓  Service: Unknown")
            self._service_status_lbl.setStyleSheet(
                f"font-weight: 600; font-size: 12px; color: {t['text_secondary']}; background: transparent;"
            )
            self._service_toggle_btn.setText("Enable Service")
            self._service_toggle_btn.setEnabled(False)

        # Force Qt to re-apply the variant style
        self._service_toggle_btn.style().unpolish(self._service_toggle_btn)
        self._service_toggle_btn.style().polish(self._service_toggle_btn)

    def _toggle_service(self) -> None:
        if self._service_manager is None:
            return
        status = self._service_manager.get_service_status()
        if status == "not_installed" or status == "stopped":
            self._install_service()
        else:
            self._uninstall_service()

    def _install_service(self) -> None:
        reply = QMessageBox.question(
            self,
            "Enable Background Service",
            "Install EduraSync as a Windows Service?\n\n"
            "You will be prompted for administrator permission.\n"
            "The service will sync attendance data automatically in the background.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._service_toggle_btn.setEnabled(False)
        self._service_toggle_btn.setText("Installing…")
        try:
            success, message = self._service_manager.install_service()
            if success:
                QMessageBox.information(self, "Service Enabled", message)
                self.logger.info(f"Service installed: {message}")
            else:
                QMessageBox.warning(self, "Installation Failed", message)
                self.logger.error(f"Service installation failed: {message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.logger.error(f"Service install exception: {e}")
        finally:
            self._service_toggle_btn.setEnabled(True)
            self._update_service_status()

    def _uninstall_service(self) -> None:
        reply = QMessageBox.question(
            self,
            "Disable Background Service",
            "Remove the EduraSync Windows Service?\n\n"
            "You will be prompted for administrator permission.\n"
            "Attendance will no longer sync automatically in the background.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._service_toggle_btn.setEnabled(False)
        self._service_toggle_btn.setText("Removing…")
        try:
            success, message = self._service_manager.uninstall_service()
            if success:
                QMessageBox.information(self, "Service Disabled", message)
                self.logger.info(f"Service removed: {message}")
            else:
                QMessageBox.warning(self, "Removal Failed", message)
                self.logger.error(f"Service removal failed: {message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.logger.error(f"Service uninstall exception: {e}")
        finally:
            self._service_toggle_btn.setEnabled(True)
            self._update_service_status()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _on_sync_enabled_changed(self, state: int) -> None:
        """Enable/disable the time picker to reflect the checkbox state."""
        enabled = state == Qt.CheckState.Checked.value
        self._form["sync_time"].setEnabled(enabled)

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _load_settings(self) -> None:
        settings = self.settings_repo.get_settings()
        if settings:
            self._form["cloud_api_url"].setText(settings.cloud_api_url or "")
            self._form["sync_id"].setText(settings.sync_id or "")
            if settings.sync_time:
                self._form["sync_time"].setTime(
                    QTime(settings.sync_time.hour, settings.sync_time.minute)
                )
            is_enabled = getattr(settings, "is_sync_enabled", True)
            self._form["is_sync_enabled"].setChecked(bool(is_enabled))
            self._form["sync_time"].setEnabled(bool(is_enabled))
        else:
            self._form["cloud_api_url"].setText(DEFAULT_SETTING.get("cloud_api_url", ""))
            self._form["sync_id"].setText(DEFAULT_SETTING.get("sync_id", ""))
            self._form["is_sync_enabled"].setChecked(True)

    def _save_settings(self) -> None:
        try:
            url        = self._form["cloud_api_url"].text().strip()
            sync_id    = self._form["sync_id"].text().strip()
            qt_time    = self._form["sync_time"].time()
            sync_time  = qt_time.toPython() if not qt_time.isNull() else None
            is_enabled = self._form["is_sync_enabled"].isChecked()

            self.settings_repo.save_settings(
                cloud_api_url=url,
                sync_id=sync_id,
                sync_time=sync_time,
                is_sync_enabled=is_enabled,
            )
            if hasattr(self.api_sync, "load_settings"):
                self.api_sync.load_settings()
            if self.app_ref and hasattr(self.app_ref, "_start_periodic_tasks"):
                self.app_ref._start_periodic_tasks()

            self.settings_saved.emit()
            QMessageBox.information(self, "Saved", "Settings saved successfully.")
            self.logger.info("Settings saved")
        except ValidationError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")

    def _test_connection(self) -> None:
        url     = self._form["cloud_api_url"].text().strip()
        sync_id = self._form["sync_id"].text().strip()
        if not url or not sync_id:
            QMessageBox.warning(self, "Missing Fields", "Enter both API URL and Sync ID first.")
            return
        try:
            ok = self.api_sync.test_connection(url, sync_id)
            if ok:
                QMessageBox.information(self, "Connection Test", "Connection successful!")
            else:
                QMessageBox.warning(self, "Connection Test", "Connection failed. Check URL and Sync ID.")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))

    def _reset_form(self) -> None:
        self._form["cloud_api_url"].setText(DEFAULT_SETTING.get("cloud_api_url", ""))
        self._form["sync_id"].setText(DEFAULT_SETTING.get("sync_id", ""))
        self._form["sync_time"].setTime(QTime(0, 0))
        self._form["is_sync_enabled"].setChecked(True)

    def _refresh_device_combo(self) -> None:
        self._device_combo.clear()
        for dev in self.device_repo.get_all():
            self._device_combo.addItem(f"{dev.device_model}  ({dev.ip_address})", dev.id)

    def _reset_selected_device(self) -> None:
        device_id = self._device_combo.currentData()
        if not device_id:
            QMessageBox.warning(self, "No Machine", "Select a machine to reset.")
            return
        settings = self.settings_repo.get_settings()
        sync_id  = settings.sync_id if settings else ""
        device   = self.device_repo.get(id=device_id)
        dlg = ConfirmDialog(
            self,
            title="Hardware Reset",
            message=(
                f"Erase ALL users and logs from "
                f"{getattr(device, 'ip_address', '')}?\n"
                "This cannot be undone on the device."
            ),
            confirm_label="Reset",
            danger=True,
            require_key=True,
            key_hint="Enter Sync ID to authorise",
            expected_key=sync_id,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from interfaces.gui_pyside6.device_management import DeviceConnectionThread
                self._reset_thread = DeviceConnectionThread(device, "reset_device")
                self._reset_thread.connection_result.connect(
                    lambda ok, msg, _: (
                        QMessageBox.information(self, "Reset Complete", msg)
                        if ok else
                        QMessageBox.critical(self, "Reset Failed", msg)
                    )
                )
                self._reset_thread.start()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _flush_database(self) -> None:
        settings = self.settings_repo.get_settings()
        sync_id  = settings.sync_id if settings else ""
        dlg = ConfirmDialog(
            self,
            title="Flush Local Database",
            message=(
                "This will permanently delete ALL local attendance records, "
                "user data, and device configurations.\n"
                "Cloud data is NOT affected."
            ),
            confirm_label="Flush",
            danger=True,
            require_key=True,
            key_hint="Enter Sync ID to authorise",
            expected_key=sync_id,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                from interfaces.database.models import Attendance, User, Device, Settings
                Attendance.delete().execute()
                User.delete().execute()
                Device.delete().execute()
                Settings.delete().execute()
                # Reset the settings cache so the next read hits the DB
                from interfaces.database.repository import _SETTINGS_NOT_CACHED
                self.settings_repo._settings_cache = _SETTINGS_NOT_CACHED
                QMessageBox.information(self, "Flushed", "Local database cleared successfully.")
                self.logger.warning("Local database flushed by user")
            except Exception as e:
                self.logger.error(f"Flush error: {e}")
                QMessageBox.critical(self, "Error", f"Flush failed:\n{e}")

    def refresh(self) -> None:
        self._load_settings()
        self._refresh_device_combo()
