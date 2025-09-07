# interfaces/gui/dashboard_content.py
"""
Dashboard content management component.
Handles building and updating dashboard sections (status, devices, actions).
"""

import logging
from tkinter import ttk

from core.exceptions import ConfigurationError
from interfaces.gui.ui_utils import (
    create_label,
    create_button,
    create_treeview,
)


class DashboardContent:
    """Manages dashboard content sections and updates."""

    def __init__(self, dashboard_gui):
        """Initialize content manager with dashboard reference."""
        self.dashboard = dashboard_gui
        self.logger = logging.getLogger(__name__)

    def update_dashboard_content(self):
        """Update the dashboard content with current data."""
        try:
            if not self.dashboard.device_repo:
                self.logger.error("device_repo not available for dashboard update")
                raise ConfigurationError("Device repository not available")

            # Clear existing content
            for widget in self.dashboard.dashboard_content.winfo_children():
                widget.destroy()

            # Get current data
            devices = self.dashboard.device_repo.get_all()

            # Build dashboard sections
            self._build_status_section(devices)
            self._build_devices_section(devices)
            self._build_actions_section()

        except ConfigurationError as e:
            self.logger.error(f"Configuration error updating dashboard: {e.message}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to update dashboard content: {e}")
            raise

    def _build_status_section(self, devices):
        """Build the status overview section."""
        # Status Overview
        status_frame = ttk.LabelFrame(
            self.dashboard.dashboard_content, text="Status Overview", padding=10
        )
        status_frame.pack(fill="x", padx=10, pady=5)

        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.status == "Online")
        offline_devices = total_devices - online_devices

        # Users in DB
        users_in_db = self.dashboard.user_repo.count() if self.dashboard.user_repo else 0
        # Users in Device
        users_in_device = 0
        if self.dashboard.user_repo:
            try:
                users_in_device = self.dashboard.user_repo.model.select().where(self.dashboard.user_repo.model.saved_to_device == True).count()
            except Exception as e:
                self.logger.error(f"Error counting users in device: {e}")
                users_in_device = 0

        status_text = (
            f"Total Devices: {total_devices} | Online: {online_devices} | Offline: {offline_devices} | "
            f"Users in DB: {users_in_db} | Users in Device: {users_in_device}"
        )
        self.dashboard.status_label = create_label(status_frame, text=status_text)
        self.dashboard.status_label.pack()

    def _build_devices_section(self, devices):
        """Build the devices list section."""
        # Devices List
        devices_frame = ttk.LabelFrame(
            self.dashboard.dashboard_content, text="Devices", padding=10
        )
        devices_frame.pack(fill="both", expand=True, padx=10, pady=5)

        if not devices:
            create_label(devices_frame, text="No devices configured").pack()
            return

        # Create treeview for devices
        columns = ("IP Address", "Port", "Model", "Status", "Last Check")
        tree = create_treeview(devices_frame, columns=columns, height=5)

        for device in devices:
            tree.insert(
                "",
                "end",
                values=(
                    device.ip_address,
                    device.port,
                    device.device_model,
                    device.status,
                    device.created_at.strftime("%Y-%m-%d %H:%M")
                    if device.created_at
                    else "N/A",
                ),
            )

        tree.pack(fill="both", expand=True)

    def _build_actions_section(self):
        """Build the actions section."""
        # Actions
        actions_frame = ttk.LabelFrame(
            self.dashboard.dashboard_content, text="Actions", padding=10
        )
        actions_frame.pack(fill="x", padx=10, pady=5)

        # Action buttons
        button_frame = ttk.Frame(actions_frame)
        button_frame.pack()

        actions = [
            ("Check Devices", self.dashboard._check_devices),
            ("Pull Data", self.dashboard._pull_data),
            ("Sync Users", self.dashboard._sync_users),
            ("Sync to Cloud", self.dashboard._sync_to_cloud),
            ("Refresh", self.dashboard._refresh_dashboard),
        ]

        self.action_buttons = []
        for text, command in actions:
            btn = create_button(button_frame, text=text, command=None)
            self.action_buttons.append(btn)
            btn.pack(side="left", padx=5)

        def make_action_callback(cmd, btn_ref, orig_text):
            def callback():
                # Disable all buttons
                for b in self.action_buttons:
                    try:
                        if b.winfo_exists():
                            b.config(state="disabled")
                    except:
                        pass
                # Change only clicked button text
                try:
                    if btn_ref.winfo_exists():
                        btn_ref.config(text="Processing...")
                        self.dashboard.dashboard_content.update_idletasks()
                except:
                    pass
                try:
                    cmd()
                finally:
                    # Restore all buttons safely
                    for b in self.action_buttons:
                        try:
                            if b.winfo_exists():
                                b.config(state="normal")
                        except:
                            pass
                    # Restore clicked button text safely
                    try:
                        if btn_ref.winfo_exists():
                            btn_ref.config(text=orig_text)
                    except:
                        pass
            return callback

        for btn, (text, command) in zip(self.action_buttons, actions):
            btn.config(command=make_action_callback(command, btn, text))