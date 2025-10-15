# interfaces/gui/dashboard_settings.py
"""
Settings management component for the dashboard.
Handles settings form creation, validation, and persistence.
"""

import logging
from datetime import datetime
from tkinter import ttk

from core.constants import UI_CONFIG, DEFAULT_SETTING
from core.exceptions import ConfigurationError
from interfaces.gui.base_component import BaseComponent
from interfaces.gui.form_manager import FormManager
from interfaces.gui.ui_utils import (
    create_label,
    create_button,
    show_error_dialog,
    show_info_dialog,
)


class DashboardSettings(BaseComponent):
    """Manages settings tab and form functionality."""

    def __init__(self, dashboard_gui):
        """Initialize settings manager with dashboard reference."""
        super().__init__(parent=dashboard_gui, logger_name="DashboardSettings")
        self.dashboard = dashboard_gui
        
        # Initialize form manager
        self.form_manager = FormManager(
            parent=self.parent,
            notification_service=self.dashboard.notification_service
        )
        
        # Setup form configuration
        self._setup_form_config()

    def _setup_form_config(self):
        """Setup the form configuration with all fields."""
        # API Settings
        self.form_manager.add_field(
            name="cloud_api_url",
            label="Cloud API URL:",
            field_type="entry",
            required=True,
            default="",
            kwargs={"width": 40}
        )
        self.form_manager.add_field(
            name="sync_id",
            label="Sync ID:",
            field_type="entry",
            required=True,
            default="",
            kwargs={"width": 40}
        )
        # Time Settings
        self.form_manager.add_field(
            name="in_time_process",
            label="In Time Process:",
            field_type="entry",
            required=False,
            default="",
            kwargs={"width": 40}
        )
        self.form_manager.add_field(
            name="out_time_process",
            label="Out Time Process:",
            field_type="entry",
            required=False,
            default="",
            kwargs={"width": 40}
        )

    def create_settings_tab(self, frame):
        """Create the settings tab with configuration options."""
        try:
            if not self.dashboard.settings_repo:
                self.logger.error("settings_repo not available for settings tab")
                raise ConfigurationError("Settings repository not available")

            # Load current settings
            settings = self.dashboard.settings_repo.get_settings()
            if not settings:
                settings = self.dashboard.settings_repo.model()

            # Create API settings section
            self._create_api_settings_section(frame, settings, 0)
            
            # Create time settings section
            self._create_time_settings_section(frame, settings, 6)

            # Add status label for connection feedback
            self.dashboard.connection_status_label = create_label(
                frame, 
                text="Ready to configure API settings", 
                font=("TkDefaultFont", 10)
            )
            self.dashboard.connection_status_label.grid(
                row=11, column=0, columnspan=2, pady=(10, 0), sticky="w"
            )

            # Add action buttons
            self._create_settings_buttons(frame, 12)

        except ConfigurationError as e:
            self.logger.error(f"Configuration error in settings tab: {e.message}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating settings tab: {e}")
            raise

    def _create_api_settings_section(self, parent, settings, row_start):
        """Create API settings section."""
        try:
            # API Settings Section
            api_label = create_label(
                parent, text="API Configuration", font=UI_CONFIG["HEADER_FONT"]
            )
            api_label.grid(
                row=row_start, column=0, columnspan=2, pady=(0, 10), sticky="w"
            )

            # Create form fields for API settings
            api_fields = [
                ("cloud_api_url", "Cloud API URL:", settings.cloud_api_url or ""),
                ("username", "Username:", settings.username or ""),
                ("password", "Password:", settings.password or ""),
                ("sync_id", "Sync ID:", settings.sync_id or ""),
            ]

            for i, (field_name, label_text, default_value) in enumerate(api_fields):
                # Create label
                label = create_label(parent, text=label_text)
                label.grid(row=row_start + 1 + i, column=0, pady=2, sticky="w")

                # Create entry field
                entry = ttk.Entry(parent, width=40)
                entry.insert(0, default_value)
                entry.grid(row=row_start + 1 + i, column=1, pady=2, padx=(10, 0), sticky="w")

                # Store reference to form field
                self.form_manager.form_fields[field_name] = entry

        except Exception as e:
            self.logger.error(f"Error creating API settings section: {e}")
            raise

    def _create_time_settings_section(self, parent, settings, row_start):
        """Create time settings section."""
        try:
            # Time Settings Section
            time_label = create_label(
                parent, text="Time Settings", font=UI_CONFIG["HEADER_FONT"]
            )
            time_label.grid(
                row=row_start, column=0, columnspan=2, pady=(20, 10), sticky="w"
            )

            # In Time Process
            in_time_label = create_label(parent, text="In Time Process:")
            in_time_label.grid(row=row_start + 1, column=0, pady=2, sticky="w")

            in_time_entry = ttk.Entry(parent, width=40)
            if settings.in_time_process:
                in_time_entry.insert(0, settings.in_time_process.strftime("%H:%M"))
            in_time_entry.grid(row=row_start + 1, column=1, pady=2, padx=(10, 0), sticky="w")
            self.form_manager.form_fields["in_time_process"] = in_time_entry

            # Out Time Process
            out_time_label = create_label(parent, text="Out Time Process:")
            out_time_label.grid(row=row_start + 2, column=0, pady=2, sticky="w")

            out_time_entry = ttk.Entry(parent, width=40)
            if settings.out_time_process:
                out_time_entry.insert(0, settings.out_time_process.strftime("%H:%M"))
            out_time_entry.grid(row=row_start + 2, column=1, pady=2, padx=(10, 0), sticky="w")
            self.form_manager.form_fields["out_time_process"] = out_time_entry

        except Exception as e:
            self.logger.error(f"Error creating time settings section: {e}")
            raise

    def _create_settings_buttons(self, parent, row):
        """Create settings action buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)

        buttons = [
            ("Save Settings", self._save_settings),
            ("Test Connection", self._check_api_connection),
            ("Reset", self._reset_settings),
            ("Load Settings", self._load_settings)
        ]

        for text, command in buttons:
            btn = create_button(button_frame, text=text, command=command)
            btn.pack(side="left", padx=5)

    def _save_settings(self):
        """Save the current settings with authentication validation."""
        try:
            if not self.dashboard.settings_repo or not self.dashboard.security:
                raise ConfigurationError(
                    "Settings repository or security manager not available"
                )

            # Validate required fields
            required_fields = ["cloud_api_url", "username", "password", "sync_id"]
            if not self.form_manager.validate_form(required_fields):
                return

            # Show saving status
            self.dashboard._update_connection_status("Saving settings and authenticating...", "info")
            self.dashboard.show_status_log("Saving settings and authenticating...", "info")

            # Get form values
            values = self.form_manager.get_values()
            
            # Encrypt password
            encrypted_password = self.dashboard.security.encrypt(values["password"])

            # Authenticate with the API to get token and institute_id
            try:
                # Test authentication to get token and institute info
                if self.dashboard.api_client:
                    login_success = self.dashboard.api_client.test_connection(
                        values["cloud_api_url"],
                        values["username"],
                        values["password"],
                        values["sync_id"]
                    )
                    
                    if not login_success:
                        self.dashboard._update_connection_status("❌ Authentication failed! Settings not saved.", "error")
                        self.dashboard.show_status_log("Authentication failed - settings not saved", "error")
                        self.dashboard.notification_service.notify(
                            "Settings", "Authentication failed. Please check your credentials.", "error"
                        )
                        return
                    
                    # Get the authentication token and institute info from token manager
                    token_manager = self.dashboard.api_client.get_auth_manager().token_manager
                    institute_info = token_manager.get_institute_info()
                    
                    # Save settings (auth_token and institute_id already saved by test_connection)
                    settings_data = {
                        "cloud_api_url": values["cloud_api_url"],
                        "username": values["username"],
                        "password": encrypted_password,
                        "sync_id": values["sync_id"],
                        "institute_id": institute_info["institute_id"],
                        "in_time_process": values.get("in_time_process"),
                        "out_time_process": values.get("out_time_process"),
                        "updated_at": datetime.now(),
                    }
                    
                    self.logger.info(f"Saving settings with institute_id: {institute_info.get('institute_id', 'N/A')} (auth_token saved by test_connection)")
                else:
                    # Save without authentication data if API client not available
                    settings_data = {
                        "cloud_api_url": values["cloud_api_url"],
                        "username": values["username"],
                        "password": encrypted_password,
                        "sync_id": values["sync_id"],
                        "in_time_process": values.get("in_time_process"),
                        "out_time_process": values.get("out_time_process"),
                        "updated_at": datetime.now(),
                    }
                    self.logger.warning("API client not available - saving settings without authentication")
                    
            except Exception as auth_error:
                self.logger.error(f"Authentication error during save: {auth_error}")
                self.dashboard._update_connection_status(f"❌ Authentication failed: {str(auth_error)}", "error")
                self.dashboard.show_status_log(f"Authentication failed: {str(auth_error)}", "error")
                self.dashboard.notification_service.notify(
                    "Settings", f"Authentication failed: {str(auth_error)}", "error"
                )
                return

            # Save settings to database
            self.dashboard.settings_repo.save_settings(**settings_data)

            # Update API client settings
            if self.dashboard.api_client:
                self.dashboard.api_client.update_settings()

            # Show success status
            success_msg = "✅ Settings saved successfully!"
            if institute_info.get("institute_id"):
                success_msg += f" Institute: {institute_info.get('institute_name', institute_info['institute_id'])}"
                
            self.dashboard._update_connection_status(success_msg, "success")
            self.dashboard.show_status_log("Settings saved successfully with authentication", "success")
            self.dashboard.notification_service.notify(
                "Settings", "Settings saved successfully with authentication", "info"
            )

        except ConfigurationError as e:
            self.logger.error(f"Configuration error saving settings: {e.message}")
            self.dashboard._update_connection_status(f"Configuration error: {e.message}", "error")
            self.dashboard.show_status_log(f"Configuration error: {e.message}", "error")
            self.dashboard.notification_service.notify(
                "Error", f"Configuration error: {e.message}", "error"
            )
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            self.dashboard._update_connection_status(f"Failed to save settings: {str(e)}", "error")
            self.dashboard.show_status_log(f"Failed to save settings: {str(e)}", "error")
            self.dashboard.notification_service.notify(
                "Error", f"Failed to save settings: {str(e)}", "error"
            )

    def _load_settings(self):
        """Load settings from repository into form."""
        try:
            if not self.dashboard.settings_repo:
                raise ConfigurationError("Settings repository not available")

            settings = self.dashboard.settings_repo.get_settings()
            if not settings:
                self.dashboard.notification_service.notify("Info", "No settings found", "info")
                return

            # Clear existing form fields
            self.form_manager.clear_form()

            # Populate form fields
            if settings.cloud_api_url:
                self.form_manager.set_field_value("cloud_api_url", settings.cloud_api_url)
            if settings.username:
                self.form_manager.set_field_value("username", settings.username)
            if settings.password:
                decrypted_password = self.dashboard.security.decrypt(settings.password)
                self.form_manager.set_field_value("password", decrypted_password)
            if settings.sync_id:
                self.form_manager.set_field_value("sync_id", settings.sync_id)
            if settings.in_time_process:
                self.form_manager.set_field_value("in_time_process", settings.in_time_process.strftime("%H:%M"))
            if settings.out_time_process:
                self.form_manager.set_field_value("out_time_process", settings.out_time_process.strftime("%H:%M"))

            self.dashboard._update_connection_status("✅ Settings loaded successfully!", "success")
            self.dashboard.show_status_log("Settings loaded successfully", "success")
            self.dashboard.notification_service.notify(
                "Settings", "Settings loaded successfully", "info"
            )

        except ConfigurationError as e:
            self.logger.error(f"Configuration error loading settings: {e.message}")
            self.dashboard._update_connection_status(f"Configuration error: {e.message}", "error")
            self.dashboard.show_status_log(f"Configuration error: {e.message}", "error")
            self.dashboard.notification_service.notify(
                "Error", f"Configuration error: {e.message}", "error"
            )
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            self.dashboard._update_connection_status(f"Failed to load settings: {str(e)}", "error")
            self.dashboard.show_status_log(f"Failed to load settings: {str(e)}", "error")
            self.dashboard.notification_service.notify(
                "Error", f"Failed to load settings: {str(e)}", "error"
            )

    def _check_api_connection(self):
        """Test API connection with current settings."""
        try:
            if not self.dashboard.api_client:
                raise ConfigurationError("API client not available")

            # Validate required fields
            required_fields = ["cloud_api_url", "username", "password", "sync_id"]
            if not self.form_manager.validate_form(required_fields):
                return

            # Get form values
            values = self.form_manager.get_values()

            # Show testing status
            self.dashboard._update_connection_status("Testing API connection...", "info")
            self.dashboard.show_status_log("Testing API connection...", "info")

            # Test connection
            success = self.dashboard.api_client.test_connection(
                values["cloud_api_url"],
                values["username"],
                values["password"],
                values["sync_id"]
            )

            if success:
                self.dashboard._update_connection_status("✅ API connection successful!", "success")
                self.dashboard.show_status_log("API connection successful", "success")
                self.dashboard.notification_service.notify(
                    "Connection Test", "API connection successful", "info"
                )
            else:
                self.dashboard._update_connection_status("❌ API connection failed!", "error")
                self.dashboard.show_status_log("API connection failed", "error")
                self.dashboard.notification_service.notify(
                    "Connection Test", "API connection failed", "error"
                )

        except ConfigurationError as e:
            self.logger.error(f"Configuration error testing connection: {e.message}")
            self.dashboard._update_connection_status(f"Configuration error: {e.message}", "error")
            self.dashboard.show_status_log(f"Configuration error: {e.message}", "error")
            self.dashboard.notification_service.notify(
                "Error", f"Configuration error: {e.message}", "error"
            )
        except Exception as e:
            self.logger.error(f"Error testing API connection: {e}")
            self.dashboard._update_connection_status(f"Connection test failed: {str(e)}", "error")
            self.dashboard.show_status_log(f"Connection test failed: {str(e)}", "error")
            self.dashboard.notification_service.notify(
                "Error", f"Connection test failed: {str(e)}", "error"
            )

    def _reset_settings(self, clear_status=True):
        """Reset all settings form fields."""
        try:
            # Clear all form fields
            self.form_manager.clear_form()

            # Clear status if requested
            if clear_status:
                self.dashboard._update_connection_status("Settings form reset", "info")

            self.dashboard.show_status_log("Settings form reset", "info")
            self.dashboard.notification_service.notify("Info", "Settings form reset", "info")

        except Exception as e:
            self.logger.error(f"Error resetting settings form: {e}")
            self.dashboard.notification_service.notify(
                "Error", f"Failed to reset form: {str(e)}", "error"
            ) 