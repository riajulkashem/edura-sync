# interfaces/gui_pyside6/device_management.py
"""
Low-level device helpers used by the DevicesScreen:
  - DeviceConnectionThread  – QThread wrapper for ZKTeco device operations
  - UserDialog              – dialog for adding / editing a device user
  - DeviceDialog            – dialog for adding / editing a device entry
"""

from typing import Dict

from PySide6.QtWidgets import (
    QVBoxLayout, QDialog, QDialogButtonBox,
    QFormLayout, QSpinBox, QLineEdit, QComboBox,
)
from PySide6.QtCore import QThread, Signal

from interfaces.database.models import Device
from services.device_utils import DeviceConnectionManager
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

