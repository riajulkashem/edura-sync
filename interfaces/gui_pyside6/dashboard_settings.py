# interfaces/gui_pyside6/dashboard_settings.py
"""
Settings tab for the EduraSync dashboard using PySide6.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QTimeEdit, QMessageBox, QGroupBox, QInputDialog,
    QComboBox
)
from PySide6.QtCore import QTime

from core.constants import DEFAULT_SETTING, APP_NAME
from core.exceptions import ValidationError
from interfaces.gui_pyside6.gui_utils import GUIHelpers


class DashboardSettings:
    """Settings manager for the PySide6 dashboard."""

    def __init__(self, dashboard_gui):
        self.dashboard_gui = dashboard_gui
        self.logger = logging.getLogger(__name__)
        self.form_fields = {}

    def create_settings_tab(self, tab_widget):
        """Create the settings tab."""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)

        # Create a group box for settings
        settings_group = QGroupBox(f"{APP_NAME} Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Create form layout
        form_layout = QFormLayout()

        # Cloud API URL
        self.form_fields['cloud_api_url'] = QLineEdit()
        form_layout.addRow("Cloud API URL:", self.form_fields['cloud_api_url'])

        # Sync ID
        self.form_fields['sync_id'] = QLineEdit()
        form_layout.addRow("Sync ID:", self.form_fields['sync_id'])

        # Daily Sync Time
        self.form_fields['sync_time'] = QTimeEdit()
        self.form_fields['sync_time'].setDisplayFormat("HH:mm")
        self.form_fields['sync_time'].setToolTip("Daily time to pull data and post to cloud automatically")
        form_layout.addRow("Daily Sync Time:", self.form_fields['sync_time'])

        settings_layout.addLayout(form_layout)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(save_btn)

        # Test Connection button
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        buttons_layout.addWidget(test_btn)

        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_form)
        buttons_layout.addWidget(reset_btn)

        settings_layout.addLayout(buttons_layout)

        layout.addWidget(settings_group)
        
        # --- MAINTENANCE SECTION ---
        maint_group = QGroupBox("🔧 Advanced Maintenance")
        maint_layout = QVBoxLayout(maint_group)
        
        maint_info = QLabel("These actions are irreversible. Enter Sync ID as Reset Key to authorize.")
        maint_info.setStyleSheet("color: #666; font-style: italic;")
        maint_info.setWordWrap(True)
        maint_layout.addWidget(maint_info)
        
        # --- Device Hardware Reset ---
        maint_layout.addSpacing(10)
        hw_label = QLabel("<b>Hardware Reset</b> (Selected Machine)")
        maint_layout.addWidget(hw_label)
        
        hw_control_layout = QHBoxLayout()
        self.device_selector = QComboBox()
        self.device_selector.setPlaceholderText("Select Machine...")
        hw_control_layout.addWidget(self.device_selector, 3)
        
        reset_device_btn = QPushButton("🧹 Reset Machine")
        reset_device_btn.setStyleSheet("background-color: #fff3f3; color: #cc0000;")
        reset_device_btn.clicked.connect(self._reset_selected_device)
        hw_control_layout.addWidget(reset_device_btn, 1)
        maint_layout.addLayout(hw_control_layout)
        
        maint_layout.addSpacing(15)
        db_label = QLabel("<b>Data Cleanup</b> (Entire Application)")
        maint_layout.addWidget(db_label)
        
        # Flush DB Button
        flush_btn = QPushButton("🗑️ Flush Local Database")
        flush_btn.setStyleSheet("color: #ff4d4d; font-weight: bold; padding: 5px;")
        flush_btn.clicked.connect(self.dashboard_gui._flush_database)
        maint_layout.addWidget(flush_btn)
        
        layout.addWidget(maint_group)

        # Add some spacing
        layout.addStretch()

        # Add tab
        tab_widget.addTab(settings_widget, "Settings")

        # Load existing settings
        self._load_settings()

    def _load_settings(self):
        """Load settings from repository into form."""
        settings = self.dashboard_gui.settings_repo.get_settings()
        if settings:
            self.form_fields['cloud_api_url'].setText(settings.cloud_api_url or "")
            self.form_fields['sync_id'].setText(settings.sync_id or "")
            
            if settings.sync_time:
                time_val = QTime(settings.sync_time.hour, settings.sync_time.minute)
                self.form_fields['sync_time'].setTime(time_val)
        else:
            # Load default settings
            self.form_fields['cloud_api_url'].setText(DEFAULT_SETTING['cloud_api_url'])
            self.form_fields['sync_id'].setText(DEFAULT_SETTING['sync_id'])

    def _save_settings(self):
        """Save settings from form to repository."""
        try:
            # Get form values
            cloud_api_url = self.form_fields['cloud_api_url'].text().strip()
            sync_id = self.form_fields['sync_id'].text().strip()
            
            sync_time_val = self.form_fields['sync_time'].time()
            sync_time = sync_time_val.toPython() if not sync_time_val.isNull() else None

            # Save to repository
            self.dashboard_gui.settings_repo.save_settings(
                cloud_api_url=cloud_api_url,
                sync_id=sync_id,
                sync_time=sync_time
            )

            # Update API sync with new settings
            self.dashboard_gui.api_sync.load_settings()

            # Restart periodic tasks with new settings
            self.dashboard_gui.app._start_periodic_tasks()

            # Show success message
            GUIHelpers.show_message(
                self.dashboard_gui.main_window,
                "Success",
                "Settings saved successfully!",
                "info"
            )

            self.logger.info("Settings saved successfully")

        except ValidationError as e:
            self.logger.error(f"Validation error saving settings: {e.message}")
            GUIHelpers.show_message(
                self.dashboard_gui.main_window,
                "Validation Error",
                f"Validation error: {e.message}",
                "warning"
            )
        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            GUIHelpers.show_message(
                self.dashboard_gui.main_window,
                "Error",
                f"Failed to save settings: {str(e)}",
                "error"
            )

    def _test_connection(self):
        """Test connection to cloud API."""
        # Get form values
        cloud_api_url = self.form_fields['cloud_api_url'].text().strip()
        sync_id = self.form_fields['sync_id'].text().strip()

        if not cloud_api_url or not sync_id:
            GUIHelpers.show_message(
                self.dashboard_gui.main_window,
                "Validation Error",
                "Please enter both Cloud API URL and Sync ID",
                "warning"
            )
            return

        # Test connection
        success = self.dashboard_gui.api_sync.test_connection(cloud_api_url, sync_id)

        if success:
            GUIHelpers.show_message(
                self.dashboard_gui.main_window,
                "Connection Test",
                "Connection successful!",
                "info"
            )
        else:
            GUIHelpers.show_message(
                self.dashboard_gui.main_window,
                "Connection Test",
                "Connection failed!",
                "error"
            )

    def _reset_form(self):
        """Reset form to default values."""
        self.form_fields['cloud_api_url'].setText(DEFAULT_SETTING['cloud_api_url'])
        self.form_fields['sync_id'].setText(DEFAULT_SETTING['sync_id'])
        self.form_fields['sync_time'].setTime(QTime(0, 0))

        GUIHelpers.show_message(
            self.dashboard_gui.main_window,
            "Reset",
            "Form reset to default values",
            "info"
        )

    def _update_device_list(self):
        """Update the device selector with current devices."""
        self.device_selector.clear()
        devices = self.dashboard_gui.device_repo.get_all()
        for device in devices:
            self.device_selector.addItem(f"{device.device_model} ({device.ip_address})", device.id)
            
    def _reset_selected_device(self):
        """Reset the hardware for the selected device."""
        device_id = self.device_selector.currentData()
        if not device_id:
            GUIHelpers.show_message(self.dashboard_gui.main_window, "Wait", "Please select a machine first", "warning")
            return
            
        # Switch to device, then reset
        device = self.dashboard_gui.device_repo.get(id=device_id)
        if device:
            if hasattr(self.dashboard_gui, 'device_management_widget'):
                self.dashboard_gui.device_management_widget.current_device = device
                self.dashboard_gui.device_management_widget.reset_device_data()
            else:
                GUIHelpers.show_message(self.dashboard_gui.main_window, "Error", "Device Management system not ready", "error")