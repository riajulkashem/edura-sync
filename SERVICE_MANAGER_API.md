# Service Manager API Examples

This document shows how to use the `ServiceManager` class programmatically.

## Basic Usage

### Import the Service Manager

```python
from services.service_manager import ServiceManager

manager = ServiceManager()
```

## Common Operations

### 1. Check If Running as Administrator

```python
if manager.is_admin():
    print("Running with administrator privileges")
else:
    print("Not running as administrator")
```

### 2. Get Service Status

```python
status = manager.get_service_status()

if status == "running":
    print("✅ Service is actively syncing")
elif status == "stopped":
    print("⚠️ Service is installed but stopped")
elif status == "not_installed":
    print("❌ Service not installed")
else:
    print("❓ Unknown status")
```

### 3. Check If Service Is Installed

```python
if manager.is_service_installed():
    print("Service is installed on this system")
else:
    print("Service is not installed")
```

### 4. Install Service (With Auto UAC)

```python
success, message = manager.install_service()

if success:
    print(f"✅ {message}")
else:
    print(f"❌ {message}")
```

### 5. Uninstall Service (With Auto UAC)

```python
success, message = manager.uninstall_service()

if success:
    print(f"✅ {message}")
else:
    print(f"❌ {message}")
```

## Advanced Usage

### Check Service and Update Status Display

```python
def update_ui_status():
    status = manager.get_service_status()
    
    status_map = {
        "not_installed": {
            "text": "❌ Service: Not Installed",
            "color": "#cc0000",
            "button": "✅ Enable Service"
        },
        "running": {
            "text": "✅ Service: Running",
            "color": "#00aa00",
            "button": "⏹️ Disable Service"
        },
        "stopped": {
            "text": "⚠️ Service: Stopped",
            "color": "#ff9900",
            "button": "▶️ Start Service"
        }
    }
    
    info = status_map.get(status, {
        "text": "❓ Unknown",
        "color": "#666",
        "button": "Refresh"
    })
    
    label.setText(info["text"])
    label.setStyleSheet(f"color: {info['color']};")
    button.setText(info["button"])
```

### Handle Service Installation with Error Feedback

```python
def enable_service_with_feedback():
    button.setEnabled(False)
    original_text = button.text()
    button.setText("⏳ Installing...")
    
    try:
        success, message = manager.install_service()
        
        if success:
            # Show success message
            show_message(
                title="Success",
                message=message,
                type="info"
            )
            # Log to file
            logger.info(f"Service installed: {message}")
        else:
            # Show error message
            show_message(
                title="Installation Failed",
                message=message,
                type="error"
            )
            # Log error
            logger.error(f"Service installation failed: {message}")
    
    except Exception as e:
        show_message(
            title="Error",
            message=f"Unexpected error: {str(e)}",
            type="error"
        )
        logger.exception("Service installation exception")
    
    finally:
        button.setEnabled(True)
        button.setText(original_text)
        # Refresh status after operation
        update_ui_status()
```

### Periodically Check and Update Service Status

```python
from PySide6.QtCore import QTimer

def setup_status_refresh():
    timer = QTimer()
    timer.timeout.connect(lambda: update_ui_status())
    timer.start(5000)  # Check every 5 seconds
    return timer
```

## Platform Awareness

### Safe Multi-Platform Usage

```python
import sys
from services.service_manager import ServiceManager

def manage_service():
    manager = ServiceManager()
    
    # Check if Windows
    if not sys.platform.startswith('win'):
        print("Service management only available on Windows")
        return False
    
    # Proceed with service operations
    success, msg = manager.install_service()
    return success
```

### Show Service Section Only on Windows

```python
import sys

if sys.platform.startswith('win'):
    service_group = create_service_management_group()
    layout.addWidget(service_group)
else:
    print("Service management section hidden (non-Windows platform)")
```

## Integration with GUI

### Minimal Integration (Like in dashboard_settings.py)

```python
class DashboardSettings:
    def __init__(self, dashboard_gui):
        self.dashboard_gui = dashboard_gui
        self.service_manager = None
    
    def create_settings_tab(self, tab_widget):
        # ... other UI code ...
        
        if sys.platform.startswith('win'):
            self.service_manager = ServiceManager()
            service_group = self._create_service_management_group()
            layout.addWidget(service_group)
    
    def _create_service_management_group(self):
        # Creates the UI group
        # Uses self.service_manager for operations
        pass
```

## Troubleshooting with Service Manager

### Debugging Service Installation

```python
import logging

logger = logging.getLogger(__name__)

def debug_service_install():
    manager = ServiceManager()
    
    logger.info(f"Running as admin: {manager.is_admin()}")
    logger.info(f"Is Windows: {manager.is_windows}")
    logger.info(f"Service installed: {manager.is_service_installed()}")
    logger.info(f"Current status: {manager.get_service_status()}")
    
    # Attempt installation
    success, message = manager.install_service()
    logger.info(f"Install result: success={success}, message={message}")
```

### Timeout Handling

The service manager has 30-second timeouts on subprocess operations. If a timeout occurs:

```python
success, message = manager.install_service()

if "timed out" in message.lower():
    print("Service operation timed out. Try again or check Windows Service manually.")
    # Suggest manual alternative
    print("Alternative: python scripts\\install_service.py install")
```

## Class Reference

### ServiceManager

**Attributes:**
```python
SERVICE_NAME = "EduraSyncService"
DISPLAY_NAME = "EduraSync Attendance Service"
DESCRIPTION = "Synchronizes attendance data from ZKTeco devices to the cloud."
```

**Methods:**

```python
class ServiceManager:
    def is_admin(self) -> bool
        """Check if current process has admin privileges"""
    
    def request_admin_elevation(script_path: str, args: list) -> Tuple[bool, str]
        """Request UAC elevation to run a script"""
    
    def install_service(self) -> Tuple[bool, str]
        """Install service (auto-elevates if needed)"""
    
    def uninstall_service(self) -> Tuple[bool, str]
        """Uninstall service (auto-elevates if needed)"""
    
    def is_service_installed(self) -> bool
        """Check if service exists"""
    
    def get_service_status(self) -> str
        """Get status: "running", "stopped", "not_installed", "unknown", "not_applicable" """
```

## Return Values

### Service Status Codes

```python
"running"          # Service is installed and actively running
"stopped"          # Service is installed but not running
"not_installed"    # Service doesn't exist on this system
"unknown"          # Unable to determine status (error occurred)
"not_applicable"   # Non-Windows platform
```

### Install/Uninstall Returns

```python
(True, "Service installed and started successfully")
(True, "Service uninstalled successfully")

(False, "Service installation only available on Windows")
(False, "Service installation timed out")
(False, "Installation failed: [error details]")
(False, "Error: [exception message]")
```

## Security Notes

1. **UAC Elevation**: Only triggered when necessary (not already admin)
2. **No Password Storage**: Service runs under Local System account
3. **No Credential Passing**: Uses privilege escalation, not authentication
4. **Error Messages**: Don't expose sensitive paths in user-facing errors
5. **Logging**: Sensitive operations logged to user-accessible log file

## Performance Considerations

- `is_service_installed()` takes ~1-2 seconds (runs `sc query`)
- `get_service_status()` takes ~1-2 seconds
- `install_service()` takes ~3-5 seconds (including subprocess execution)
- `uninstall_service()` takes ~3-5 seconds
- UAC prompt may add additional user wait time
- Use threading for GUI to avoid freezing during operations

## Examples in the Codebase

See [interfaces/gui_pyside6/dashboard_settings.py](../interfaces/gui_pyside6/dashboard_settings.py) for complete integration example:

- `_create_service_management_group()` - Full UI creation
- `_update_service_status()` - Status refresh logic
- `_toggle_service()` - Entry point for enable/disable
- `_install_service()` - Installation flow with confirmation
- `_uninstall_service()` - Uninstallation flow with confirmation
