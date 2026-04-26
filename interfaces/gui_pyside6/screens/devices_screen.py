# interfaces/gui_pyside6/screens/devices_screen.py
"""Devices screen — manage ZKTeco machines and inspect live data."""
from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget, QTextEdit,
    QFrame, QMessageBox, QDialog, QProgressBar, QStatusBar
)
from PySide6.QtCore import Qt, QTimer

from interfaces.gui_pyside6.theme import tokens, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL, RADIUS_LG
from interfaces.gui_pyside6.widgets import StatusBadge, ConfirmDialog
from interfaces.database.repository import DeviceRepository, UserRepository, AttendanceRepository, SettingsRepository
from interfaces.database.models import Device
# Re-use the existing threaded device operations
from interfaces.gui_pyside6.device_management import DeviceConnectionThread, UserDialog, DeviceDialog


class DevicesScreen(QWidget):
    """Two-column split: machine list (left) + detail panel (right)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)

        self.device_repo     = DeviceRepository()
        self.user_repo       = UserRepository()
        self.attendance_repo = AttendanceRepository()
        self.settings_repo   = SettingsRepository()

        self.current_device: Device | None = None
        self.connection_thread: DeviceConnectionThread | None = None

        self._setup_ui()
        self.load_devices()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        t = tokens()
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)
        root.setSpacing(SPACE_MD)

        # Page title + Add button
        hdr = QHBoxLayout()
        title = QLabel("Devices")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {t['text_primary']}; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._add_btn = QPushButton("+ Add Machine")
        self._add_btn.setProperty("variant", "primary")
        self._add_btn.clicked.connect(self._add_device)
        hdr.addWidget(self._add_btn)
        root.addLayout(hdr)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        root.addWidget(splitter, stretch=1)

        # Left panel
        left = QWidget()
        left.setMinimumWidth(260)
        left.setMaximumWidth(320)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(SPACE_SM)

        machines_lbl = QLabel("Biometric Machines")
        machines_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {t['text_secondary']}; background: transparent;")
        lv.addWidget(machines_lbl)

        self._machine_table = QTableWidget()
        self._machine_table.setColumnCount(3)
        self._machine_table.setHorizontalHeaderLabels(["IP Address", "Model", "Status"])
        self._machine_table.horizontalHeader().setStretchLastSection(True)
        self._machine_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._machine_table.verticalHeader().setVisible(False)
        self._machine_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._machine_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._machine_table.setAlternatingRowColors(True)
        self._machine_table.itemSelectionChanged.connect(self._on_device_selected)
        lv.addWidget(self._machine_table)

        splitter.addWidget(left)

        # Right panel
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(SPACE_LG, 0, 0, 0)
        rv.setSpacing(SPACE_MD)

        # Device header
        self._detail_header = QLabel("Select a machine to view details")
        self._detail_header.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {t['text_primary']}; background: transparent;")
        self._detail_status = StatusBadge("No device selected", "neutral")
        hdr2 = QHBoxLayout()
        hdr2.addWidget(self._detail_header, stretch=1)
        hdr2.addWidget(self._detail_status)
        rv.addLayout(hdr2)

        # Action buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(SPACE_SM)
        self._connect_btn = self._mk_btn("Connect",         self._connect_device, "primary")
        self._test_btn    = self._mk_btn("Test",            self._test_device,    "secondary")
        self._reset_btn   = self._mk_btn("Reset Device",    self._reset_device,   "danger")
        self._remove_btn  = self._mk_btn("Remove",          self._delete_device,  "danger")
        for b in [self._connect_btn, self._test_btn, self._reset_btn, self._remove_btn]:
            action_row.addWidget(b)
        action_row.addStretch()
        rv.addLayout(action_row)

        # Progress bar (hidden when idle)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(6)
        rv.addWidget(self._progress)

        # Detail tabs
        self._tabs = QTabWidget()
        rv.addWidget(self._tabs, stretch=1)

        self._users_tab     = self._build_users_tab()
        self._attendance_tab = self._build_attendance_tab()
        self._info_tab      = self._build_info_tab()

        self._tabs.addTab(self._users_tab,      "Users")
        self._tabs.addTab(self._attendance_tab, "Attendance")
        self._tabs.addTab(self._info_tab,       "Device Info")

        # Status bar
        self._status_bar = QStatusBar()
        rv.addWidget(self._status_bar)

        splitter.addWidget(right)
        splitter.setSizes([280, 680])

        self._set_detail_enabled(False)

    def _mk_btn(self, label: str, slot, variant: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setProperty("variant", variant)
        btn.clicked.connect(slot)
        return btn

    def _build_users_tab(self) -> QWidget:
        w = QWidget()
        lv = QVBoxLayout(w)
        lv.setContentsMargins(0, SPACE_SM, 0, 0)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Users"))
        hdr.addStretch()
        add_user_btn = QPushButton("+ Add User")
        add_user_btn.setProperty("variant", "primary")
        add_user_btn.clicked.connect(self._add_user)
        self._edit_user_btn   = QPushButton("Edit")
        self._delete_user_btn = QPushButton("Delete")
        self._delete_user_btn.setProperty("variant", "danger")
        refresh_users_btn = QPushButton("Refresh")
        refresh_users_btn.clicked.connect(self._refresh_users)
        for b in [add_user_btn, self._edit_user_btn, self._delete_user_btn, refresh_users_btn]:
            hdr.addWidget(b)
        self._edit_user_btn.clicked.connect(self._edit_user)
        self._delete_user_btn.clicked.connect(self._delete_user)
        lv.addLayout(hdr)

        self._users_table = QTableWidget()
        self._users_table.setColumnCount(6)
        self._users_table.setHorizontalHeaderLabels(["Cloud ID", "Device UID", "Name", "Role", "Card", "Group"])
        self._users_table.horizontalHeader().setStretchLastSection(True)
        self._users_table.verticalHeader().setVisible(False)
        self._users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._users_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._users_table.setAlternatingRowColors(True)
        lv.addWidget(self._users_table)
        return w

    def _build_attendance_tab(self) -> QWidget:
        w = QWidget()
        lv = QVBoxLayout(w)
        lv.setContentsMargins(0, SPACE_SM, 0, 0)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Attendance Records"))
        hdr.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_attendance)
        hdr.addWidget(refresh_btn)
        lv.addLayout(hdr)

        self._attendance_table = QTableWidget()
        self._attendance_table.setColumnCount(5)
        self._attendance_table.setHorizontalHeaderLabels(["Cloud ID", "User ID", "Timestamp", "Method", "Punch"])
        self._attendance_table.horizontalHeader().setStretchLastSection(True)
        self._attendance_table.verticalHeader().setVisible(False)
        self._attendance_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._attendance_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._attendance_table.setAlternatingRowColors(True)
        lv.addWidget(self._attendance_table)
        return w

    def _build_info_tab(self) -> QWidget:
        w = QWidget()
        lv = QVBoxLayout(w)
        lv.setContentsMargins(0, SPACE_SM, 0, 0)
        self._info_text = QTextEdit()
        self._info_text.setReadOnly(True)
        self._info_text.setPlaceholderText("Connect to the device to fetch live info.")
        lv.addWidget(self._info_text)
        return w

    # ── Logic ─────────────────────────────────────────────────────────────────

    def load_devices(self) -> None:
        devices = self.device_repo.get_all()
        self._machine_table.setRowCount(len(devices))
        for row, dev in enumerate(devices):
            self._machine_table.setItem(row, 0, QTableWidgetItem(dev.ip_address))
            self._machine_table.setItem(row, 1, QTableWidgetItem(dev.device_model))
            tone = "success" if dev.status == "Online" else "danger"
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(4, 2, 4, 2)
            hl.addWidget(StatusBadge(dev.status, tone))
            hl.addStretch()
            self._machine_table.setCellWidget(row, 2, w)
        self._machine_table.resizeRowsToContents()
        self._status_bar.showMessage(f"{len(devices)} machine(s) loaded")

    def _on_device_selected(self) -> None:
        row = self._machine_table.currentRow()
        if row < 0:
            return
        item = self._machine_table.item(row, 0)
        if not item:
            return
        dev = self.device_repo.get_by_ip(item.text())
        if dev:
            self.current_device = dev
            self._detail_header.setText(f"{dev.ip_address}  —  {dev.device_model}")
            tone = "success" if dev.status == "Online" else "danger"
            self._detail_status.update_badge(dev.status, tone)
            self._update_info_tab()
            self._set_detail_enabled(True)
            self._refresh_users()

    def _set_detail_enabled(self, enabled: bool) -> None:
        for btn in [self._connect_btn, self._test_btn, self._reset_btn, self._remove_btn,
                    self._edit_user_btn, self._delete_user_btn]:
            btn.setEnabled(enabled)

    def _update_info_tab(self) -> None:
        if not self.current_device:
            return
        dev = self.current_device
        lines = [
            f"IP Address   : {dev.ip_address}",
            f"Port         : {dev.port}",
            f"Model        : {dev.device_model}",
            f"Status       : {dev.status}",
            f"Cloud ID     : {dev.cloud_id or 'Not assigned'}",
            f"Last Updated : {dev.updated_at}",
        ]
        if dev.last_error:
            lines.append(f"Last Error   : {dev.last_error}")
        self._info_text.setPlainText("\n".join(lines))

    # ── Device thread operations ───────────────────────────────────────────────

    def _start_thread(self, operation: str, **kwargs) -> None:
        if self.connection_thread and self.connection_thread.isRunning():
            QMessageBox.warning(self, "Busy", "Another operation is in progress. Please wait.")
            return
        if not self.current_device:
            return
        self.connection_thread = DeviceConnectionThread(self.current_device, operation, **kwargs)
        self.connection_thread.connection_result.connect(self._on_result)
        self.connection_thread.progress_update.connect(self._on_progress)
        self.connection_thread.finished.connect(self._on_thread_done)
        self.connection_thread.start()
        self._progress.setVisible(True)
        self._progress.setValue(0)

    def _on_result(self, success: bool, message: str, data) -> None:
        self._progress.setVisible(False)
        self._status_bar.showMessage(message)
        if success:
            if data:
                if "users" in data:
                    self._populate_users_table(data["users"])
                elif "attendance" in data:
                    self._populate_attendance_table(data["attendance"])
                elif "device_info" in data:
                    self._info_text.setPlainText(str(data["device_info"]))
            if self.current_device:
                self.current_device.status = "Online"
                self.current_device.save()
                self.load_devices()
        else:
            QMessageBox.critical(self, "Error", message)
            if self.current_device:
                self.current_device.status = "Offline"
                self.current_device.last_error = message
                self.current_device.save()
                self.load_devices()

    def _on_progress(self, pct: int, msg: str) -> None:
        self._progress.setValue(pct)
        self._status_bar.showMessage(msg)

    def _on_thread_done(self) -> None:
        self.connection_thread = None

    def _connect_device(self)    -> None: self._start_thread("test_connection")
    def _test_device(self)       -> None: self._start_thread("test_connection")
    def _refresh_users(self)     -> None:
        if self.current_device:
            self._start_thread("get_users")
    def _refresh_attendance(self) -> None:
        if self.current_device:
            self._start_thread("get_attendance")

    def _reset_device(self) -> None:
        if not self.current_device:
            return
        settings = self.settings_repo.get_settings()
        sync_id = settings.sync_id if settings else ""
        dlg = ConfirmDialog(
            self,
            title="Reset Device",
            message=f"This will erase ALL users and attendance logs from {self.current_device.ip_address}. This cannot be undone on the device.",
            confirm_label="Reset Device",
            danger=True,
            require_key=True,
            key_hint="Enter Sync ID to authorise hardware reset",
            expected_key=sync_id,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._start_thread("reset_device")

    def _delete_device(self) -> None:
        if not self.current_device:
            return
        dlg = ConfirmDialog(
            self,
            title="Remove Machine",
            message=(
                f"Remove '{self.current_device.device_model}' ({self.current_device.ip_address}) "
                f"from the list?\n\n"
                f"All locally stored users and attendance records linked to this machine "
                f"will also be removed from the local database. "
                f"Data on the physical device is NOT affected."
            ),
            confirm_label="Remove",
            danger=True,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.device_repo.delete_cascade(self.current_device)
            except Exception as exc:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Failed to remove machine:\n{exc}")
                return
            self.current_device = None
            self._detail_header.setText("Select a machine to view details")
            self._detail_status.update_badge("No device selected", "neutral")
            self._users_table.setRowCount(0)
            self._attendance_table.setRowCount(0)
            self._info_text.clear()
            self._set_detail_enabled(False)
            self.load_devices()

    def _add_device(self) -> None:
        dlg = DeviceDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_device_data()
            if not data["ip_address"]:
                QMessageBox.warning(self, "Warning", "IP Address is required")
                return
            try:
                existing = self.device_repo.get_by_ip(data["ip_address"])
                if existing:
                    self.device_repo.update(existing, **data)
                else:
                    self.device_repo.create(**data)
                self.load_devices()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save device: {e}")

    def _add_user(self) -> None:
        if not self.current_device:
            QMessageBox.warning(self, "Warning", "Select a device first")
            return
        dlg = UserDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            user_data = dlg.get_user_data()
            if user_data["user_id"] and user_data["name"]:
                try:
                    if not self.user_repo.get_by_user_id(str(user_data["user_id"])):
                        self.user_repo.create(
                            user_id=str(user_data["user_id"]),
                            name=str(user_data["name"]),
                            role=int(user_data["role"]),
                            password=str(user_data["password"]),
                            card=str(user_data["card"]),
                            group_id=str(user_data["group_id"]),
                            device=self.current_device,
                        )
                except Exception as e:
                    self.logger.error(f"DB save error: {e}")
                self._start_thread("add_user", user_data=user_data)
            else:
                QMessageBox.warning(self, "Warning", "User ID and Name are required")

    def _edit_user(self) -> None:
        row = self._users_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Select a user to edit")
            return
        # Columns: Cloud ID(0), Device UID(1), Name(2), Role(3), Card(4), Group(5)
        cloud_id = self._users_table.item(row, 0).text()
        name     = self._users_table.item(row, 2).text()
        card     = self._users_table.item(row, 4).text()
        user_data = {"user_id": cloud_id, "name": name, "role": 0, "card": card, "group_id": 0}
        dlg = UserDialog(self, user_data, is_edit=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.get_user_data()
            try:
                rec = self.user_repo.get_by_user_id(str(cloud_id))
                if rec:
                    self.user_repo.update(rec, name=updated["name"], role=updated["role"],
                                          password=updated["password"], card=updated["card"],
                                          group_id=updated["group_id"])
            except Exception as e:
                self.logger.error(f"DB update error: {e}")
            uid_val = int(cloud_id) if cloud_id.isdigit() else 0
            self._start_thread("add_user", user_data={**updated, "uid": uid_val})

    def _delete_user(self) -> None:
        row = self._users_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Select a user to delete")
            return
        cloud_id = self._users_table.item(row, 0).text()
        name     = self._users_table.item(row, 2).text()
        dlg = ConfirmDialog(self, f"Delete User", f"Delete '{name}' (ID: {cloud_id}) from this device?", "Delete", danger=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            uid = int(cloud_id) if cloud_id.isdigit() else cloud_id
            self._start_thread("delete_user", user_id=uid)

    # ── Table population ──────────────────────────────────────────────────────

    def _populate_users_table(self, users: list) -> None:
        from interfaces.database.models import Attendance as AttModel
        self._users_table.setRowCount(len(users))
        for row, user in enumerate(users):
            device_uid = str(getattr(user, "user_id", ""))
            name = str(getattr(user, "name", ""))
            db_user = self.user_repo.get_by_user_id(device_uid)
            cloud_id = db_user.user_id if db_user else "N/A"
            if not name and db_user:
                name = db_user.name
            card = db_user.card if db_user else (getattr(user, "card", "") or "")
            self._users_table.setItem(row, 0, QTableWidgetItem(str(cloud_id)))
            self._users_table.setItem(row, 1, QTableWidgetItem(device_uid))
            self._users_table.setItem(row, 2, QTableWidgetItem(name))
            self._users_table.setItem(row, 3, QTableWidgetItem(str(getattr(user, "privilege", 0))))
            self._users_table.setItem(row, 4, QTableWidgetItem(str(card or "")))
            self._users_table.setItem(row, 5, QTableWidgetItem(str(getattr(user, "group_id", 0))))
        self._users_table.resizeRowsToContents()

    def _populate_attendance_table(self, records: list) -> None:
        from interfaces.database.models import Attendance as AttModel
        self._attendance_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            user_id = str(getattr(rec, "user_id", ""))
            db_user = self.user_repo.get_by_user_id(user_id)
            cloud_id = db_user.user_id if db_user else "N/A"
            ts = getattr(rec, "timestamp", None)
            ts_str = ts.strftime("%b %d, %Y  %I:%M %p") if ts else "Unknown"
            status_code = getattr(rec, "status", 0)
            punch_code  = getattr(rec, "punch", 0)
            self._attendance_table.setItem(row, 0, QTableWidgetItem(str(cloud_id)))
            self._attendance_table.setItem(row, 1, QTableWidgetItem(user_id))
            self._attendance_table.setItem(row, 2, QTableWidgetItem(ts_str))
            self._attendance_table.setItem(row, 3, QTableWidgetItem(AttModel.STATUS_MAP.get(status_code, str(status_code))))
            self._attendance_table.setItem(row, 4, QTableWidgetItem(AttModel.PUNCH_MAP.get(punch_code, str(punch_code))))
        self._attendance_table.resizeRowsToContents()
