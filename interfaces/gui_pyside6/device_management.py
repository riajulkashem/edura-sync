# interfaces/gui_pyside6/device_management.py
"""
Comprehensive Device Management Interface for EduraSync.
Provides stunning UI for managing ZKTeco devices, users, fingerprints, and attendance.
"""

import logging
from typing import List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QComboBox, QTextEdit, QFrame, QSplitter,
    QAbstractItemView, QMessageBox, QDialog, QDialogButtonBox,
    QFormLayout, QSpinBox, QProgressBar, QStatusBar, QInputDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import (
    QFont, QColor,
)

from interfaces.database.models import Device
from interfaces.database.repository import DeviceRepository, UserRepository, AttendanceRepository
from services.device_utils import DeviceConnectionManager
from interfaces.gui_pyside6.gui_utils import handle_gui_errors
from zk import ZK


class DeviceConnectionThread(QThread):
    """Thread for device connection operations to prevent UI blocking."""
    
    connection_result = Signal(bool, str, object)  # success, message, device_data
    progress_update = Signal(int, str)  # progress, message
    
    def __init__(self, device: Device, operation: str, **kwargs):
        super().__init__()
        self.device = device
        self.operation = operation
        self.kwargs = kwargs
        self.connection_manager = DeviceConnectionManager()
        
    def run(self):
        """Execute device operation in background thread."""
        try:
            self.progress_update.emit(10, f"Connecting to {self.device.ip_address}...")
            
            zk = self.connection_manager.create_connection(self.device)
            if not zk:
                self.connection_result.emit(False, "Failed to connect to device", None)
                return
                
            self.progress_update.emit(30, "Connected successfully")
            
            # Execute specific operation
            if self.operation == "get_users":
                self._get_users(zk)
            elif self.operation == "get_attendance":
                self._get_attendance(zk)
            elif self.operation == "add_user":
                self._add_user(zk)
            elif self.operation == "delete_user":
                self._delete_user(zk)
            elif self.operation == "test_connection":
                self._test_connection(zk)
            elif self.operation == "reset_device":
                self._reset_device(zk)
                
            self.connection_manager.safe_disconnect(zk, self.device.ip_address)
            self.progress_update.emit(100, "Operation completed")
            
        except Exception as e:
            self.connection_result.emit(False, str(e), None)
            
    def _get_users(self, zk: ZK):
        """Get users from device."""
        self.progress_update.emit(50, "Retrieving users...")
        users = zk.get_users() or []
        self.progress_update.emit(80, f"Found {len(users)} users")
        self.connection_result.emit(True, f"Retrieved {len(users)} users", {"users": users})
        
    def _get_attendance(self, zk: ZK):
        """Get attendance records from device."""
        self.progress_update.emit(50, "Retrieving attendance...")
        attendance = zk.get_attendance() or []
        self.progress_update.emit(80, f"Found {len(attendance)} records")
        self.connection_result.emit(True, f"Retrieved {len(attendance)} attendance records", {"attendance": attendance})
        

    def _add_user(self, zk: ZK):
        """Add user to device."""
        user_data = self.kwargs.get('user_data')
        if not user_data:
            self.connection_result.emit(False, "No user data provided", None)
            return
            
        # Map dialog fields to pyzk set_user signature
        # set_user(uid, name, privilege=0, password='', group_id='', user_id='', card=0)
        uid = int(user_data.get('uid') or 0)
        # Ensure string fields are str to avoid .encode errors in pyzk
        name = str(user_data.get('name', '') or '')
        privilege = int(user_data.get('role') or user_data.get('privilege') or 0)
        password = str(user_data.get('password', '') or '')
        # group_id is expected as string in many firmware; keep as string
        group_id_val = user_data.get('group_id')
        group_id = str(group_id_val) if group_id_val is not None else ''
        user_id = str(user_data.get('user_id') or '')
        card_raw = user_data.get('card')
        try:
            card = int(card_raw) if card_raw not in (None, '') else 0
        except Exception:
            card = 0

        self.progress_update.emit(40, "Preparing user add...")
        try:
            # Some firmwares require disabling the device while writing
            try:
                zk.disable_device()
            except Exception:
                pass

            # Auto-generate UID if not provided or is zero
            if uid <= 0:
                try:
                    existing = zk.get_users() or []
                    used = [int(getattr(u, 'uid', 0)) for u in existing if getattr(u, 'uid', 0)]
                    next_uid = max(used) + 1 if used else 1
                    uid = next_uid
                except Exception:
                    uid = 1

            self.progress_update.emit(60, "Adding user to device...")
            result = zk.set_user(uid=uid, name=name, privilege=privilege, password=password, group_id=group_id, user_id=user_id, card=card)
            if result is False:
                self.connection_result.emit(False, "Failed to add user", None)
                return
            self.connection_result.emit(True, "User added successfully", {"user": {**user_data, 'uid': uid}})
        except Exception as e:
            self.connection_result.emit(False, f"Failed to add user: {e}", None)
        finally:
            try:
                zk.enable_device()
            except Exception:
                pass
            
    def _reset_device(self, zk: ZK):
        """Clear all data from device."""
        self.progress_update.emit(40, "Clearing attendance logs...")
        try:
            zk.clear_attendance()
            self.progress_update.emit(70, "Clearing user data...")
            zk.clear_data()
            self.connection_result.emit(True, "Device reset successfully", None)
        except Exception as e:
            self.connection_result.emit(False, f"Failed to reset device: {e}", None)

    def _delete_user(self, zk: ZK):
        """Delete user from device."""
        user_id = self.kwargs.get('user_id')
        if user_id is None or user_id == "":
            self.connection_result.emit(False, "No user ID provided", None)
            return
            
        self.progress_update.emit(50, "Deleting user...")
        # pyzk delete_user expects uid (int)
        try:
            uid = int(user_id)
        except Exception:
            self.connection_result.emit(False, "Device requires numeric UID to delete user", None)
            return
        try:
            try:
                zk.disable_device()
            except Exception:
                pass
            result = zk.delete_user(uid)
        finally:
            try:
                zk.enable_device()
            except Exception:
                pass
        # Some firmwares return None on success; treat non-False as success
        if result is not False:
            self.connection_result.emit(True, "User deleted successfully", {"user_id": user_id})
        else:
            self.connection_result.emit(False, "Failed to delete user", None)
            
    def _test_connection(self, zk: ZK):
        """Test device connection."""
        self.progress_update.emit(50, "Testing connection...")
        # Collect safe device info if available
        info = {}
        for attr_name in ("get_firmware_version", "get_platform", "get_serialnumber"):
            try:
                method = getattr(zk, attr_name, None)
                if callable(method):
                    info[attr_name.replace("get_", "")] = method()
            except Exception:
                pass
        # If nothing available, still consider connection successful
        self.connection_result.emit(True, "Connection test successful", {"device_info": info or {"status": "online"}})


class UserDialog(QDialog):
    """Dialog for adding/editing users."""
    
    def __init__(self, parent=None, user_data: Dict = None, is_edit: bool = False):
        super().__init__(parent)
        self.user_data = user_data or {}
        self.is_edit = is_edit
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user dialog UI."""
        self.setWindowTitle("Edit User" if self.is_edit else "Add New User")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # User ID
        self.user_id_edit = QLineEdit()
        self.user_id_edit.setText(self.user_data.get('user_id', ''))
        form_layout.addRow("User ID:", self.user_id_edit)
        
        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.user_data.get('name', ''))
        form_layout.addRow("Name:", self.name_edit)
        
        # Role/Privilege
        self.role_combo = QComboBox()
        self.role_combo.addItems(["User (0)", "Admin (14)", "Super Admin (15)"])
        current_role = self.user_data.get('role', 0)
        self.role_combo.setCurrentIndex(current_role)
        form_layout.addRow("Role:", self.role_combo)
        
        # Password
        self.password_edit = QLineEdit()
        self.password_edit.setText(self.user_data.get('password', ''))
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.password_edit)
        
        # Card
        self.card_edit = QLineEdit()
        self.card_edit.setText(str(self.user_data.get('card', '')))
        form_layout.addRow("Card Number:", self.card_edit)
        
        # Group ID
        self.group_id_edit = QSpinBox()
        self.group_id_edit.setRange(0, 999)
        self.group_id_edit.setValue(self.user_data.get('group_id', 0))
        form_layout.addRow("Group ID:", self.group_id_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_user_data(self) -> Dict:
        """Get user data from form."""
        return {
            'user_id': self.user_id_edit.text().strip(),
            'name': self.name_edit.text().strip(),
            'role': self.role_combo.currentIndex(),
            'password': self.password_edit.text(),
            'card': self.card_edit.text().strip(),
            'group_id': self.group_id_edit.value()
        }


class DeviceDialog(QDialog):
    """Dialog for adding/editing a device."""
    def __init__(self, parent=None, device_data: Dict = None, is_edit: bool = False):
        super().__init__(parent)
        self.device_data = device_data or {}
        self.is_edit = is_edit
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("Edit Device" if self.is_edit else "Add New Device")
        self.setModal(True)
        self.resize(380, 260)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("192.168.1.100")
        self.ip_edit.setText(self.device_data.get('ip_address', ''))
        form.addRow("IP Address:", self.ip_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.device_data.get('port', 4370))
        form.addRow("Port:", self.port_spin)
        
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setText(self.device_data.get('password', '0'))
        form.addRow("Password:", self.pass_edit)
        
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("ZKTeco Model")
        self.model_edit.setText(self.device_data.get('device_model', 'ZKTeco'))
        form.addRow("Model:", self.model_edit)
        
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_device_data(self) -> Dict:
        return {
            'ip_address': self.ip_edit.text().strip(),
            'port': self.port_spin.value(),
            'password': self.pass_edit.text().strip() or '0',
            'device_model': self.model_edit.text().strip() or 'ZKTeco',
        }

class DeviceManagementWidget(QWidget):
    """Main device management widget with stunning UI."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Repositories
        self.device_repo = DeviceRepository()
        self.user_repo = UserRepository()
        self.attendance_repo = AttendanceRepository()
        
        # Current device and data
        self.current_device = None
        self.current_users = []
        self.current_attendance = []
        
        # Connection thread
        self.connection_thread = None
        
        self.setup_ui()
        self.load_devices()
        
    def setup_ui(self):
        """Setup the main UI."""
        self.setObjectName("deviceManagementWidget")
        self.setStyleSheet(self._get_stylesheet())
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header
        self._create_header(main_layout)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Device list
        self._create_device_panel(splitter)
        
        # Right panel - Device details
        self._create_details_panel(splitter)
        
        # Status bar
        self._create_status_bar(main_layout)
        
        # Set splitter proportions
        splitter.setSizes([300, 700])
        
    def _create_header(self, parent_layout):
        """Create a slim, modern header."""
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setFixedHeight(60) # Slimmer header
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # Title and Icon
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel("🛠️")
        icon_label.setStyleSheet("font-size: 20px;")
        title_layout.addWidget(icon_label)
        
        title_label = QLabel("Device Management")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)
        header_layout.addWidget(title_container)
        
        header_layout.addStretch()
        
        # Action buttons Container
        actions_container = QWidget()
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setObjectName("headerActionButton")
        self.refresh_btn.clicked.connect(self.load_devices)
        actions_layout.addWidget(self.refresh_btn)
        
        header_layout.addWidget(actions_container)
        parent_layout.addWidget(header_frame)
        
    def _create_device_panel(self, parent_splitter):
        """Create device list panel."""
        device_widget = QWidget()
        device_layout = QVBoxLayout(device_widget)
        
        # Device list header
        device_header_container = QWidget()
        device_header_layout = QHBoxLayout(device_header_container)
        device_header_layout.setContentsMargins(0, 5, 0, 5)

        device_header = QLabel("Biometric Machines")
        device_header.setObjectName("sectionHeader")
        device_header_layout.addWidget(device_header)
        device_header_layout.addStretch()
        
        self.add_device_btn = QPushButton("➕ Add Machine")
        self.add_device_btn.setObjectName("addMachineButton")
        self.add_device_btn.clicked.connect(self.add_device)
        device_header_layout.addWidget(self.add_device_btn)
        
        device_layout.addWidget(device_header_container)
        
        # Device table
        self.device_table = QTableWidget()
        self.device_table.setObjectName("deviceTable")
        self.device_table.setColumnCount(4)
        self.device_table.setHorizontalHeaderLabels(["IP Address", "Model", "Status", "Users"])
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setAlternatingRowColors(True)
        self.device_table.itemSelectionChanged.connect(self.on_device_selected)
        device_layout.addWidget(self.device_table)
        
        # Device actions
        device_actions_layout = QHBoxLayout()
        device_actions_layout.setSpacing(5)
        
        self.connect_btn = QPushButton("🔗 Connect")
        self.connect_btn.setObjectName("deviceActionButton")
        self.connect_btn.clicked.connect(self.connect_device)
        device_actions_layout.addWidget(self.connect_btn)
        
        self.test_btn = QPushButton("🧪 Test")
        self.test_btn.setObjectName("deviceActionButton")
        self.test_btn.clicked.connect(self.test_device)
        device_actions_layout.addWidget(self.test_btn)
        
        self.reset_machine_btn = QPushButton("🧹 Reset")
        self.reset_machine_btn.setObjectName("deviceActionButtonLine")
        self.reset_machine_btn.setToolTip("Clear all data from the selected machine")
        self.reset_machine_btn.clicked.connect(self.reset_device_data)
        device_actions_layout.addWidget(self.reset_machine_btn)

        self.disconnect_btn = QPushButton("🔌 Offline")
        self.disconnect_btn.setObjectName("deviceActionButtonLine")
        self.disconnect_btn.clicked.connect(self.disconnect_device)
        device_actions_layout.addWidget(self.disconnect_btn)

        self.remove_btn = QPushButton("🗑️ Remove")
        self.remove_btn.setObjectName("deviceActionButtonLine")
        self.remove_btn.clicked.connect(self.delete_device)
        device_actions_layout.addWidget(self.remove_btn)
        
        device_layout.addLayout(device_actions_layout)
        
        parent_splitter.addWidget(device_widget)
        
    def _create_details_panel(self, parent_splitter):
        """Create device details panel with tabs."""
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        # Details header
        self.details_header = QLabel("Select a device to view details")
        self.details_header.setObjectName("sectionHeader")
        details_layout.addWidget(self.details_header)
        
        # Tab widget
        self.details_tabs = QTabWidget()
        self.details_tabs.setObjectName("detailsTabs")
        details_layout.addWidget(self.details_tabs)
        
        # Users tab
        self._create_users_tab()
        
        # Attendance tab
        self._create_attendance_tab()
        
        # Device info tab
        self._create_device_info_tab()
        
        parent_splitter.addWidget(details_widget)
        
    def _create_users_tab(self):
        """Create users management tab."""
        users_widget = QWidget()
        users_layout = QVBoxLayout(users_widget)
        
        # Users header with actions
        users_header_layout = QHBoxLayout()
        
        users_title = QLabel("Users")
        users_title.setObjectName("tabTitle")
        users_header_layout.addWidget(users_title)
        
        users_header_layout.addStretch()
        
        self.add_user_btn = QPushButton("➕ Add User")
        self.add_user_btn.setObjectName("actionButton")
        self.add_user_btn.clicked.connect(self.add_user)
        users_header_layout.addWidget(self.add_user_btn)
        
        self.edit_user_btn = QPushButton("✏️ Edit")
        self.edit_user_btn.setObjectName("actionButton")
        self.edit_user_btn.clicked.connect(self.edit_user)
        users_header_layout.addWidget(self.edit_user_btn)
        
        self.delete_user_btn = QPushButton("🗑️ Delete")
        self.delete_user_btn.setObjectName("actionButton")
        self.delete_user_btn.clicked.connect(self.delete_user)
        users_header_layout.addWidget(self.delete_user_btn)
        
        self.refresh_users_btn = QPushButton("🔄 Refresh")
        self.refresh_users_btn.setObjectName("actionButton")
        self.refresh_users_btn.clicked.connect(self.refresh_users)
        users_header_layout.addWidget(self.refresh_users_btn)
        
        users_layout.addLayout(users_header_layout)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setObjectName("dataTable")
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels(["Cloud ID", "Device UID", "Name", "Role", "Card", "Group", "Actions"])
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setAlternatingRowColors(True)
        users_layout.addWidget(self.users_table)
        
        self.details_tabs.addTab(users_widget, "👥 Users")
        
    def _create_attendance_tab(self):
        """Create attendance management tab."""
        attendance_widget = QWidget()
        attendance_layout = QVBoxLayout(attendance_widget)
        
        # Attendance header
        attendance_header_layout = QHBoxLayout()
        
        attendance_title = QLabel("Attendance Records")
        attendance_title.setObjectName("tabTitle")
        attendance_header_layout.addWidget(attendance_title)
        
        attendance_header_layout.addStretch()
        
        self.refresh_attendance_btn = QPushButton("🔄 Refresh")
        self.refresh_attendance_btn.setObjectName("actionButton")
        self.refresh_attendance_btn.clicked.connect(self.refresh_attendance)
        attendance_header_layout.addWidget(self.refresh_attendance_btn)
        
        attendance_layout.addLayout(attendance_header_layout)
        
        # Attendance table
        self.attendance_table = QTableWidget()
        self.attendance_table.setObjectName("dataTable")
        self.attendance_table.setColumnCount(5)
        self.attendance_table.setHorizontalHeaderLabels(["Cloud ID", "User ID", "Timestamp", "Status", "Punch"])
        self.attendance_table.horizontalHeader().setStretchLastSection(True)
        self.attendance_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.attendance_table.setAlternatingRowColors(True)
        attendance_layout.addWidget(self.attendance_table)
        
        self.details_tabs.addTab(attendance_widget, "📊 Attendance")
        
    def _create_device_info_tab(self):
        """Create device information tab."""
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        # Device info
        self.device_info_text = QTextEdit()
        self.device_info_text.setObjectName("infoText")
        self.device_info_text.setReadOnly(True)
        info_layout.addWidget(self.device_info_text)
        
        self.details_tabs.addTab(info_widget, "ℹ️ Device Info")
        
    def _create_status_bar(self, parent_layout):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("statusBar")
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        parent_layout.addWidget(self.status_bar)
        
    def _get_stylesheet(self) -> str:
        """Get the redesigned modern stylesheet for the widget."""
        return """
        QWidget#deviceManagementWidget {
            background-color: #ffffff;
        }
        
        QFrame#headerFrame {
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        
        QLabel#titleLabel {
            color: #212529;
            font-size: 16px;
            font-weight: 600;
        }
        
        QLabel#sectionHeader {
            font-size: 13px;
            font-weight: 600;
            color: #495057;
            padding-left: 5px;
        }
        
        QLabel#tabTitle {
            font-size: 12px;
            font-weight: 600;
            color: #495057;
        }
        
        QPushButton#headerActionButton {
            background-color: white;
            color: #495057;
            border: 1px solid #ced4da;
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 12px;
        }
        
        QPushButton#headerActionButton:hover {
            background-color: #f1f3f5;
            border-color: #adb5bd;
        }
        
        QPushButton#addMachineButton {
            background-color: #228be6;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }
        
        QPushButton#addMachineButton:hover {
            background-color: #1c7ed6;
        }
        
        QPushButton#deviceActionButton {
            background-color: #228be6;
            color: white;
            border: none;
            padding: 6px 10px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }
        
        QPushButton#deviceActionButton:hover {
            background-color: #1c7ed6;
        }

        QPushButton#deviceActionButtonLine {
            background-color: white;
            color: #495057;
            border: 1px solid #ced4da;
            padding: 6px 10px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }

        QPushButton#deviceActionButtonLine:hover {
            background-color: #f1f3f5;
        }
        
        QPushButton#actionButton {
            background-color: #228be6;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }
        
        QPushButton#actionButton:hover {
            background-color: #1c7ed6;
        }
        
        QTableWidget#deviceTable, QTableWidget#dataTable {
            gridline-color: #e9ecef;
            background-color: white;
            alternate-background-color: #f8f9fa;
            selection-background-color: #e7f5ff;
            selection-color: #228be6;
            border: 1px solid #dee2e6;
            border-radius: 8px;
        }
        
        QHeaderView::section {
            background-color: #f8f9fa;
            color: #495057;
            padding: 10px;
            border: none;
            border-bottom: 1px solid #dee2e6;
            font-weight: 600;
            font-size: 11px;
        }
        
        QTabWidget#detailsTabs::pane {
            border: 1px solid #dee2e6;
            background-color: white;
            border-radius: 8px;
            margin-top: -1px;
        }
        
        QTabBar::tab {
            background-color: transparent;
            color: #868e96;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 12px;
            border-bottom: 2px solid transparent;
        }
        
        QTabBar::tab:selected {
            color: #228be6;
            border-bottom: 2px solid #228be6;
        }
        
        QTabBar::tab:hover:!selected {
            color: #495057;
        }
        
        QTextEdit#infoText {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Segoe UI', system-ui, -apple-system;
            line-height: 1.5;
        }
        
        QStatusBar#statusBar {
            background-color: #ffffff;
            border-top: 1px solid #dee2e6;
            color: #868e96;
            font-size: 11px;
        }
        
        QProgressBar {
            border: 1px solid #dee2e6;
            border-radius: 4px;
            text-align: center;
            height: 12px;
            font-size: 9px;
            background-color: #f1f3f5;
        }
        
        QProgressBar::chunk {
            background-color: #228be6;
            border-radius: 3px;
        }
        """
        
    @handle_gui_errors
    def load_devices(self):
        """Load devices from database."""
        try:
            devices = self.device_repo.get_all()
            self.device_table.setRowCount(len(devices))
            
            for row, device in enumerate(devices):
                self.device_table.setItem(row, 0, QTableWidgetItem(device.ip_address))
                self.device_table.setItem(row, 1, QTableWidgetItem(device.device_model))
                
                # Status with color coding
                status_item = QTableWidgetItem(device.status)
                if device.status == "Online":
                    status_item.setBackground(QColor(200, 255, 200))
                else:
                    status_item.setBackground(QColor(255, 200, 200))
                self.device_table.setItem(row, 2, status_item)
                
                # User count
                user_count = self.user_repo.count_by_device(device)
                self.device_table.setItem(row, 3, QTableWidgetItem(str(user_count)))
                
            self.status_bar.showMessage(f"Loaded {len(devices)} devices")
            
        except Exception as e:
            self.logger.error(f"Failed to load devices: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load devices: {e}")
            
    @handle_gui_errors
    def on_device_selected(self):
        """Handle device selection."""
        current_row = self.device_table.currentRow()
        if current_row >= 0:
            device_ip = self.device_table.item(current_row, 0).text()
            self.current_device = self.device_repo.get_by_ip(device_ip)
            
            if self.current_device:
                self.details_header.setText(f"Device Details: {self.current_device.ip_address}")
                self._update_device_info()
                self.refresh_users()
                
    @handle_gui_errors
    def connect_device(self):
        """Connect to selected device."""
        if not self.current_device:
            QMessageBox.warning(self, "Warning", "Please select a device first")
            return
            
        self._start_connection_thread("test_connection")
        
    @handle_gui_errors
    def disconnect_device(self):
        """Disconnect from selected device."""
        if not self.current_device:
            QMessageBox.warning(self, "Warning", "Please select a device first")
            return
            
        # Update device status to offline
        self.current_device.status = "Offline"
        self.current_device.save()
        self.load_devices()
        self.status_bar.showMessage("Device disconnected")
        
    @handle_gui_errors
    def reset_device_data(self):
        """Clear all data from selected device with Reset Key verification."""
        if not self.current_device:
            QMessageBox.warning(self, "Warning", "Please select a device first")
            return
            
        settings = UserRepository().model._meta.database.execute_sql("SELECT sync_id FROM settings LIMIT 1").fetchone()
        actual_sync_id = settings[0] if settings else ""

        reply = QMessageBox.warning(
            self, "Reset Device",
            f"Are you sure you want to clear ALL data (users and logs) from {self.current_device.ip_address}?\n"
            "This action cannot be undone on the device.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 2. Reset Key verification
            key, ok = QInputDialog.getText(
                self, "SECURITY CHECK", 
                "Enter Sync ID as RESET KEY to authorize hardware reset:", 
                QLineEdit.Password
            )
            
            if not ok or key != actual_sync_id:
                QMessageBox.warning(self, "Access Denied", "Incorrect Reset Key.")
                return
                
            self._start_connection_thread("reset_device")

    @handle_gui_errors
    def test_device(self):
        """Test device connection."""
        if not self.current_device:
            QMessageBox.warning(self, "Warning", "Please select a device first")
            return
            
        self._start_connection_thread("test_connection")
        
    @handle_gui_errors
    def delete_device(self):
        """Delete selected device from database."""
        if not self.current_device:
            QMessageBox.warning(self, "Warning", "Please select a device first")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to remove machine '{self.current_device.device_model}' ({self.current_device.ip_address})?\n\nThis will remove the machine from the list but won't delete data from the machine itself.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Remove from database (cascading deletes for users if configured, though we might want to keep users)
                self.device_repo.delete(self.current_device)
                self.current_device = None
                self.load_devices()
                self.details_header.setText("Select a device to view details")
                self.users_table.setRowCount(0)
                self.attendance_table.setRowCount(0)
                self.device_info_text.clear()
                self.status_bar.showMessage("Machine removed successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove machine: {e}")

    @handle_gui_errors
    def add_device(self):
        """Add new device dialog."""
        dialog = DeviceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_device_data()
            if not data['ip_address']:
                QMessageBox.warning(self, "Warning", "IP Address is required")
                return
            # Persist device
            try:
                # ensure not duplicate
                existing = self.device_repo.get_by_ip(data['ip_address'])
                if existing:
                    # update existing
                    self.device_repo.update(existing, **data)
                else:
                    self.device_repo.create(**data)
                self.load_devices()
                self.status_bar.showMessage("Device saved")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save device: {e}")
        
    @handle_gui_errors
    def refresh_users(self):
        """Refresh users from selected device."""
        if not self.current_device:
            return
            
        self._start_connection_thread("get_users")
        
    @handle_gui_errors
    def refresh_attendance(self):
        """Refresh attendance from selected device."""
        if not self.current_device:
            return
            
        self._start_connection_thread("get_attendance")
        
    @handle_gui_errors
    def add_user(self):
        """Add new user to device."""
        if not self.current_device:
            QMessageBox.warning(self, "Warning", "Please select a device first")
            return
            
        dialog = UserDialog(self)
        if dialog.exec() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            if user_data['user_id'] and user_data['name']:
                # --- DATABASE SAVE ---
                try:
                    # Check if user already exists
                    existing = self.user_repo.get_by_user_id(str(user_data['user_id']))
                    if not existing:
                        self.user_repo.create(
                            user_id=str(user_data['user_id']),
                            name=str(user_data['name']),
                            role=int(user_data['role']),
                            password=str(user_data['password']),
                            card=str(user_data['card']),
                            group_id=str(user_data['group_id']),
                            device=self.current_device  # Associate with current machine
                        )
                except Exception as e:
                    self.logger.error(f"Failed to save new user to database: {e}")

                # --- DEVICE PUSH ---
                self._start_connection_thread("add_user", user_data=user_data)
            else:
                QMessageBox.warning(self, "Warning", "User ID and Name are required")
                
    @handle_gui_errors
    def edit_user(self):
        """Edit selected user."""
        current_row = self.users_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a user to edit")
            return
            
        # Get user data from table
        user_id = self.users_table.item(current_row, 0).text()
        name = self.users_table.item(current_row, 1).text()
        # role text not used here; privilege will be chosen in dialog
        card = self.users_table.item(current_row, 3).text()
        
        user_data = {
            'user_id': user_id,
            'name': name,
            'role': 0,  # Default role
            'card': card,
            'group_id': 0
        }
        
        dialog = UserDialog(self, user_data, is_edit=True)
        if dialog.exec() == QDialog.Accepted:
            updated = dialog.get_user_data()
            
            # --- DATABASE UPDATE ---
            try:
                # Find user in database by user_id
                user_record = self.user_repo.get_by_user_id(str(user_id))
                if user_record:
                    self.user_repo.update(
                        user_record,
                        name=updated['name'],
                        role=updated['role'],
                        password=updated['password'],
                        card=updated['card'],
                        group_id=updated['group_id']
                    )
            except Exception as e:
                self.logger.error(f"Failed to update user in database: {e}")
            
            # --- DEVICE UPDATE ---
            # send update via set_user (must include uid or user_id)
            # Ensure proper types; keep group as string, card int if possible
            uid_val = int(user_id) if user_id.isdigit() else 0
            card_val = 0
            try:
                card_val = int(updated['card']) if str(updated['card']).isdigit() else 0
            except Exception:
                card_val = 0
            self._start_connection_thread("add_user", user_data={
                'uid': uid_val,
                'user_id': str(updated['user_id']),
                'name': str(updated['name']),
                'role': int(updated['role']),
                'password': str(updated['password']),
                'group_id': str(updated['group_id']),
                'card': card_val,
            })
            
    @handle_gui_errors
    def delete_user(self):
        """Delete selected user from device."""
        current_row = self.users_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a user to delete")
            return
            
        user_id = self.users_table.item(current_row, 0).text()
        user_name = self.users_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete user '{user_name}' (ID: {user_id})?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Deleting by uid (preferred), fallback to user_id
            uid = int(user_id) if user_id.isdigit() else None
            self._start_connection_thread("delete_user", user_id=uid or user_id)
            
    def _start_connection_thread(self, operation: str, **kwargs):
        """Start connection thread for device operation."""
        if self.connection_thread and self.connection_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Another operation is in progress")
            return
            
        self.connection_thread = DeviceConnectionThread(self.current_device, operation, **kwargs)
        self.connection_thread.connection_result.connect(self._on_connection_result)
        self.connection_thread.progress_update.connect(self._on_progress_update)
        self.connection_thread.finished.connect(self._on_thread_finished)
        self.connection_thread.start()
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
    def _on_connection_result(self, success: bool, message: str, data: Any):
        """Handle connection thread result."""
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_bar.showMessage(message)
            
            if data:
                if 'users' in data:
                    self._update_users_table(data['users'])
                elif 'attendance' in data:
                    self._update_attendance_table(data['attendance'])
                elif 'device_info' in data:
                    self._update_device_info_display(data['device_info'])
            # Always decide on post-op refresh based on operation
            operation = getattr(self.connection_thread, 'operation', None)
            if operation in ("add_user", "delete_user"):
                # Slight delay to let device settle before pulling users
                QTimer.singleShot(300, self.refresh_users)
                    
            # Update device status
            if self.current_device:
                self.current_device.status = "Online"
                self.current_device.save()
                self.load_devices()
        else:
            self.status_bar.showMessage(f"Error: {message}")
            QMessageBox.critical(self, "Error", message)
            
            # Update device status
            if self.current_device:
                self.current_device.status = "Offline"
                self.current_device.last_error = message
                self.current_device.save()
                self.load_devices()
                
    def _on_progress_update(self, progress: int, message: str):
        """Handle progress updates."""
        self.progress_bar.setValue(progress)
        self.status_bar.showMessage(message)

    def _on_thread_finished(self):
        """Cleanup after thread finishes to allow new operations."""
        self.connection_thread = None
        
    def _update_users_table(self, users: List):
        """Update users table with data."""
        self.current_users = users
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            # Get raw device UID and device-side card (if present)
            device_uid = str(getattr(user, 'user_id', ''))
            device_card = getattr(user, 'card', None) or getattr(user, 'card_number', None)
            user_name = str(getattr(user, 'name', ''))

            # Match with local DB to get Cloud ID
            cloud_id = "N/A"

            # 1) Try direct match by cloud user_id
            db_user = self.user_repo.get_by_user_id(device_uid)

            # 2) Fallback: Search by device_code (device UID stored in DB)
            if not db_user and device_uid.isdigit():
                try:
                    db_user = self.user_repo.get(device_code=int(device_uid))
                except Exception:
                    db_user = None

            # 3) Fallback: Search by card number (match card on DB)
            if not db_user and device_card:
                try:
                    db_user = self.user_repo.get(card=str(device_card))
                except Exception:
                    db_user = None

            if db_user:
                cloud_id = db_user.user_id
                # Prefer local name if ZK name is empty
                if not user_name:
                    user_name = db_user.name

            # Prefer showing the card stored in DB (authoritative), fallback to device-reported card
            display_card = db_user.card if db_user and getattr(db_user, 'card', None) else (device_card or '')

            self.users_table.setItem(row, 0, QTableWidgetItem(str(cloud_id)))
            self.users_table.setItem(row, 1, QTableWidgetItem(str(device_uid)))
            self.users_table.setItem(row, 2, QTableWidgetItem(str(user_name)))
            self.users_table.setItem(row, 3, QTableWidgetItem(str(getattr(user, 'privilege', 0))))
            self.users_table.setItem(row, 4, QTableWidgetItem(str(display_card)))
            self.users_table.setItem(row, 5, QTableWidgetItem(str(getattr(user, 'group_id', 0))))
            # Actions column placeholder (future context menu)
            action_btn = QPushButton("⋯")
            action_btn.clicked.connect(lambda checked, r=row: self._show_user_actions(r))
            self.users_table.setCellWidget(row, 6, action_btn)
            
    def _update_attendance_table(self, attendance: List):
        """Update attendance table with data."""
        self.current_attendance = attendance
        self.attendance_table.setRowCount(len(attendance))
        
        for row, record in enumerate(attendance):
            # Match with local user to get Cloud ID and Name
            user_id = str(getattr(record, 'user_id', ''))
            record_card = getattr(record, 'card', None) or getattr(record, 'card_number', None)
            cloud_id = "N/A"
            name = "Unknown"

            # Lookup user in DB using several fallbacks
            user_rec = self.user_repo.get_by_user_id(user_id)
            if not user_rec and user_id.isdigit():
                try:
                    user_rec = self.user_repo.get(device_code=int(user_id))
                except Exception:
                    user_rec = None

            if not user_rec and record_card:
                try:
                    user_rec = self.user_repo.get(card=str(record_card))
                except Exception:
                    user_rec = None

            if user_rec:
                cloud_id = user_rec.user_id
                name = user_rec.name

            self.attendance_table.setItem(row, 0, QTableWidgetItem(str(cloud_id)))
            user_cell = QTableWidgetItem(str(user_id))
            user_cell.setToolTip(name)
            self.attendance_table.setItem(row, 1, user_cell)

            # Format timestamp - 12-hour format with AM/PM
            timestamp = getattr(record, 'timestamp', None)
            if timestamp:
                try:
                    timestamp_str = timestamp.strftime("%b %d, %Y %I:%M:%S %p")
                except Exception:
                    timestamp_str = str(timestamp)
            else:
                timestamp_str = "Unknown"
            self.attendance_table.setItem(row, 2, QTableWidgetItem(timestamp_str))
            
            # Status - Convert to human-readable
            from interfaces.database.models import Attendance as AttendanceModel
            status_code = getattr(record, 'status', 0)
            status_display = AttendanceModel.STATUS_MAP.get(status_code, f'Unknown ({status_code})')
            self.attendance_table.setItem(row, 3, QTableWidgetItem(status_display))
            
            # Punch - Convert to human-readable
            punch_code = getattr(record, 'punch', 0)
            punch_display = AttendanceModel.PUNCH_MAP.get(punch_code, f'Unknown ({punch_code})')
            self.attendance_table.setItem(row, 4, QTableWidgetItem(punch_display))
            
    def _update_device_info(self):
        """Update device information display."""
        if not self.current_device:
            return
            
        info_text = f"""
Device Information:
IP Address: {self.current_device.ip_address}
Port: {self.current_device.port}
Model: {self.current_device.device_model}
Status: {self.current_device.status}
Last Updated: {self.current_device.updated_at}
"""
        
        if self.current_device.last_error:
            info_text += f"Last Error: {self.current_device.last_error}\n"
            
        self.device_info_text.setPlainText(info_text)
        
    def _update_device_info_display(self, device_info: Dict):
        """Update device info with live data."""
        info_text = f"""
    Live Device Information:
    {device_info}
    """
        self.device_info_text.setPlainText(info_text)
        
    def _show_user_actions(self, row: int):
        """Show user actions menu."""
        # This would show a context menu with user actions
        QMessageBox.information(self, "Info", f"User actions for row {row} will be implemented")
