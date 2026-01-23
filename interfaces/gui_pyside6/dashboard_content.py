# interfaces/gui_pyside6/dashboard_content.py
"""
Dashboard content manager for the EduraSync application using PySide6.
"""

import logging
from PySide6.QtWidgets import (
    QLabel, QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton
)
from PySide6.QtCore import Qt
from interfaces.gui_pyside6.gui_utils import GUIHelpers


class DashboardContent:
    """Content manager for the PySide6 dashboard."""

    def __init__(self, dashboard_gui):
        self.dashboard_gui = dashboard_gui
        self.logger = logging.getLogger(__name__)

    def update_dashboard_content(self, layout):
        """Update dashboard content with current data."""
        # Clear existing content with shared helper
        GUIHelpers.clear_layout(layout)

        # Add header
        header_label = QLabel("EduraSync Dashboard")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Add action buttons
        self._create_action_buttons(layout)

        # Add statistics section
        self._create_statistics_section(layout)

        # Add device status section
        self._create_device_status_section(layout)

        # Add recent activity section
        self._create_recent_activity_section(layout)

        # Add some spacing at the bottom
        layout.addStretch()

    def _create_action_buttons(self, parent_layout):
        """Create action buttons section."""
        group_box = QGroupBox("Quick Actions")
        group_layout = QHBoxLayout(group_box)

        # Check Devices button
        check_btn = QPushButton("🔍 Check Device Status")
        check_btn.clicked.connect(self.dashboard_gui._check_devices)
        check_btn.setToolTip("Scan all biometric machines and check if they are online")
        group_layout.addWidget(check_btn)

        # Pull Data button
        pull_btn = QPushButton("⬇️ Fetch Device Logs")
        pull_btn.clicked.connect(self.dashboard_gui._pull_data)
        pull_btn.setToolTip("Download new attendance logs from your biometric machines")
        group_layout.addWidget(pull_btn)

        # Sync Users button
        sync_users_btn = QPushButton("👥 Sync Profiles")
        sync_users_btn.clicked.connect(self.dashboard_gui._sync_users)
        sync_users_btn.setToolTip("Synchronize student and staff profiles with the cloud")
        group_layout.addWidget(sync_users_btn)

        # Sync to Cloud button
        sync_cloud_btn = QPushButton("☁️ Upload to Cloud")
        sync_cloud_btn.clicked.connect(self.dashboard_gui._sync_to_cloud)
        sync_cloud_btn.setToolTip("Upload all pending attendance records to your website")
        group_layout.addWidget(sync_cloud_btn)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.dashboard_gui._refresh_dashboard)
        refresh_btn.setToolTip("Refresh dashboard data and statistics")
        group_layout.addWidget(refresh_btn)

        parent_layout.addWidget(group_box)

    def _create_statistics_section(self, parent_layout):
        """Create statistics section."""
        group_box = QGroupBox("Statistics")
        group_layout = QGridLayout(group_box)

        # Get statistics
        device_stats = self._get_device_statistics()
        attendance_stats = self._get_attendance_statistics()
        user_stats = self._get_user_statistics()

        # Device statistics
        group_layout.addWidget(QLabel("Total Devices:"), 0, 0)
        group_layout.addWidget(QLabel(str(device_stats.get("total", 0))), 0, 1)
        
        group_layout.addWidget(QLabel("Online Devices:"), 1, 0)
        group_layout.addWidget(QLabel(str(device_stats.get("online", 0))), 1, 1)
        
        group_layout.addWidget(QLabel("Offline Devices:"), 2, 0)
        group_layout.addWidget(QLabel(str(device_stats.get("offline", 0))), 2, 1)

        # User statistics
        group_layout.addWidget(QLabel("Total Users:"), 0, 2)
        group_layout.addWidget(QLabel(str(user_stats.get("total", 0))), 0, 3)
        
        group_layout.addWidget(QLabel("Students:"), 1, 2)
        group_layout.addWidget(QLabel(str(user_stats.get("students", 0))), 1, 3)
        
        group_layout.addWidget(QLabel("Teachers:"), 2, 2)
        group_layout.addWidget(QLabel(str(user_stats.get("teachers", 0))), 2, 3)
        
        group_layout.addWidget(QLabel("Staff:"), 3, 2)
        group_layout.addWidget(QLabel(str(user_stats.get("staff", 0))), 3, 3)

        # Attendance statistics
        group_layout.addWidget(QLabel("Pending Attendance:"), 0, 4)
        group_layout.addWidget(QLabel(str(attendance_stats.get("pending", 0))), 0, 5)
        
        group_layout.addWidget(QLabel("Total Attendance:"), 1, 4)
        group_layout.addWidget(QLabel(str(attendance_stats.get("total", 0))), 1, 5)
        
        # User sync status
        group_layout.addWidget(QLabel("Saved to Device:"), 2, 4)
        group_layout.addWidget(QLabel(str(user_stats.get("saved_to_device", 0))), 2, 5)
        
        group_layout.addWidget(QLabel("Not Saved to Device:"), 3, 4)
        group_layout.addWidget(QLabel(str(user_stats.get("unsaved_to_device", 0))), 3, 5)

        parent_layout.addWidget(group_box)

    def _create_device_status_section(self, parent_layout):
        """Create device status section."""
        group_box = QGroupBox("Device Status")
        group_layout = QVBoxLayout(group_box)

        devices = self.dashboard_gui.device_repo.get_all()
        if devices:
            for device in devices:
                status_text = f"{device.ip_address}:{device.port} - {device.status}"
                if device.last_error:
                    status_text += f" (Error: {device.last_error})"
                device_label = QLabel(status_text)
                group_layout.addWidget(device_label)
        else:
            group_layout.addWidget(QLabel("No devices configured"))

        parent_layout.addWidget(group_box)

    def _create_recent_activity_section(self, parent_layout):
        """Create recent activity section."""
        group_box = QGroupBox("Recent Activity")
        group_layout = QVBoxLayout(group_box)

        # Get recent activity (last 10 records)
        # Use existing attendance repo method for formatted data
        try:
            # We want pending records first as they are "active"
            attendance_data = self.dashboard_gui.attendance_repo.cloud_format()[:10]
        except Exception:
            attendance_data = []

        if not attendance_data:
            activity_label = QLabel("No recent activity")
            activity_label.setAlignment(Qt.AlignCenter)
            group_layout.addWidget(activity_label)
        else:
            from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
            
            # Create table
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Cloud ID", "Date", "User", "Status", "Device"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.verticalHeader().setVisible(False)
            table.setRowCount(len(attendance_data))
            
            for row, record in enumerate(attendance_data):
                table.setItem(row, 0, QTableWidgetItem(str(record.get('user_id', ''))))
                table.setItem(row, 1, QTableWidgetItem(record.get('timestamp', '')))
                
                # Format user info
                user_info = "Unknown"
                if record.get('is_student'):
                    user_info = "Student"
                elif record.get('is_teacher'):
                    user_info = "Teacher" 
                elif record.get('is_staff'):
                    user_info = "Staff"
                table.setItem(row, 2, QTableWidgetItem(user_info))
                
                table.setItem(row, 3, QTableWidgetItem(record.get('status', '')))
                table.setItem(row, 4, QTableWidgetItem(str(record.get('device', ''))))
                
            group_layout.addWidget(table)

        parent_layout.addWidget(group_box)

        parent_layout.addWidget(group_box)

    def _get_device_statistics(self):
        """Get device statistics."""
        try:
            return self.dashboard_gui.device_repo.get_device_stats()
        except Exception as e:
            self.logger.error(f"Failed to get device statistics: {e}")
            return {"total": 0, "online": 0, "offline": 0}

    def _get_attendance_statistics(self):
        """Get attendance statistics."""
        try:
            pending_count = self.dashboard_gui.attendance_repo.get_pending_count()
            total_count = self.dashboard_gui.attendance_repo.count()
            return {"pending": pending_count, "total": total_count}
        except Exception as e:
            self.logger.error(f"Failed to get attendance statistics: {e}")
            return {"pending": 0, "total": 0}

    def _get_user_statistics(self):
        """Get user statistics."""
        try:
            return self.dashboard_gui.user_repo.get_user_stats()
        except Exception as e:
            self.logger.error(f"Failed to get user statistics: {e}")
            return {
                "total": 0, 
                "students": 0, 
                "teachers": 0, 
                "staff": 0,
                "saved_to_device": 0,
                "unsaved_to_device": 0
            }