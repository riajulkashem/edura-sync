# Windows Service Management Guide

## Overview

EduraSync now includes an integrated Windows Service management feature in the Settings UI. This allows users to enable/disable the background service directly from the application without needing to run command-line scripts.

## What is the Windows Service?

The **EduraSync Windows Service** runs in the background as a system service, continuously synchronizing attendance data from ZKTeco devices to the cloud, even when:
- The GUI application is closed
- No user is logged into Windows
- The computer is locked

This is useful for:
- **Production servers** needing 24/7 synchronization
- **Automated deployments** without user interaction
- **Headless operations** (no desktop environment)

## How to Enable the Service from the App

### Step 1: Open EduraSync Settings

1. Launch the EduraSync application
2. Click the **Settings** tab

### Step 2: Find the Service Management Section

On Windows only, you'll see the **⚙️ Background Service** section showing:
- Current service status (Not Installed / Running / Stopped)
- An **Enable Service** button (or **Disable Service** if already running)

### Step 3: Enable the Service

1. Click the **✅ Enable Service** button
2. You will see a confirmation dialog explaining that you need administrator permission
3. Click **Yes** to proceed

### Step 4: Authorize with Administrator Permission

Windows will show the **User Account Control (UAC)** prompt asking for administrator permission.

```
Do you want to allow this app to make changes to your device?

[     EduraSync     ]
```

Click **Yes** to grant permission and install the service.

### Step 5: Confirm Installation

Once the service is installed and started, you'll see:
- Service status changes to: **✅ Service: Running** (green)
- Button changes to: **⏹️ Disable Service** (red)

## How to Disable the Service

1. Open Settings → **⚙️ Background Service** section
2. If the service is running, click **⏹️ Disable Service**
3. Confirm in the dialog
4. Authorize with administrator permission when the UAC prompt appears
5. The service will be uninstalled and stopped

## Checking Service Status

Click the **🔄 Refresh** button to manually check the current service status at any time.

### Service Status Meanings

| Status | Icon | Color | Meaning |
|--------|------|-------|---------|
| **Not Installed** | ❌ | Red | Service is not installed on this system |
| **Running** | ✅ | Green | Service is installed and actively syncing |
| **Stopped** | ⚠️ | Orange | Service is installed but not running (may need restart) |
| **Unknown** | ❓ | Gray | Unable to determine service status |

## Administrator Permission Requirements

The service management feature requires **administrator privileges** because Windows Service installation is a privileged operation.

### How It Works

When you click Enable/Disable, the app:
1. Checks if it has admin privileges
2. If **NOT admin**: Shows Windows UAC (User Account Control) prompt
3. If **YES**: User grants permission in the UAC dialog
4. The service operation is then executed with elevated privileges

### No Password Required

On Windows, UAC uses the **privilege escalation model**, not password authentication. You simply need to confirm the action, not enter a password (unless your organization uses strict group policies).

## Usage Scenarios

### Scenario 1: Desktop User (No Service Needed)

```
User opens EduraSync normally → Uses GUI → Syncs data when app is running
Service Status: Not Installed ✅ (This is fine)
```

### Scenario 2: Server/Always-On Sync

```
Admin runs EduraSync once → Enables Service via Settings → Closes app
Service continues syncing in background 24/7
Status: ✅ Service: Running
```

### Scenario 3: Disable Service Later

```
Open EduraSync → Settings → Click Disable Service → Authorize UAC
Service stops and is removed
Status: ❌ Service: Not Installed
```

## Troubleshooting

### "Service Installation Failed" Error

**Possible Causes:**
- UAC prompt was canceled or timed out
- Pywin32 dependencies not installed
- Script path not found (bundling issue)

**Solution:**
- Try again and ensure you click **Yes** in the UAC prompt
- Check logs in `%APPDATA%\EduraSync\edurasync.log`
- Run from administrator command prompt manually:
  ```cmd
  python scripts\install_service.py install
  ```

### Service Status Shows "Unknown"

**Possible Causes:**
- Windows Service manager is having issues
- Script execution failed silently

**Solution:**
- Click **🔄 Refresh** to re-check status
- Open Windows Services manager:
  - Press `Win + R`
  - Type `services.msc`
  - Look for "EduraSync Attendance Service"

### Service Installed but Shows as "Stopped"

**Possible Causes:**
- Service crashed during startup
- Missing dependencies in background mode
- File permissions issue

**Solution:**
1. Check logs: `%APPDATA%\EduraSync\edurasync.log`
2. Try restarting the service:
   - Open `services.msc`
   - Right-click "EduraSync Attendance Service"
   - Click "Restart"
3. If restart fails, disable and re-enable from the app

## Manual Service Management

If you need to manage the service manually without the GUI:

### Install Service (Command Prompt as Admin)
```cmd
cd path\to\edurasync
python scripts\install_service.py install
python scripts\install_service.py start
```

### Uninstall Service (Command Prompt as Admin)
```cmd
python scripts\install_service.py stop
python scripts\install_service.py remove
```

### Check Service Status (Command Prompt)
```cmd
sc query EduraSyncService
```

### Via Windows Services Manager
1. Press `Win + R` and type `services.msc`
2. Find "EduraSync Attendance Service"
3. Right-click to:
   - **Start** service
   - **Stop** service
   - **Restart** service
   - **Delete** service (requires admin, use `sc delete` command)

## What Happens When Service is Running

When the service is active:

1. **EduraSync.exe runs in background** with `--service` flag
2. **No GUI or system tray** (headless mode)
3. **Minimal resource usage** (optimized for background operation)
4. **Periodic sync tasks** execute automatically based on settings
5. **Logs written to:** `%APPDATA%\EduraSync\edurasync.log`

The service continues syncing even if:
- The app window is closed
- The user logs out
- The screen is locked
- No one is using the computer

## Implementation Details

### Service Manager Class

The `ServiceManager` class (`services/service_manager.py`) handles:

```python
from services.service_manager import ServiceManager

manager = ServiceManager()

# Check if running as admin
is_admin = manager.is_admin()

# Install service (requests UAC if needed)
success, message = manager.install_service()

# Uninstall service (requests UAC if needed)
success, message = manager.uninstall_service()

# Check service status
status = manager.get_service_status()  # Returns: "running", "stopped", "not_installed", "unknown"

# Check if service is installed
installed = manager.is_service_installed()
```

### UAC Elevation

The `request_admin_elevation()` method uses Windows `ShellExecuteEx` API with the `runas` verb to trigger UAC without needing the parent process to be admin.

### Service Implementation

See [scripts/install_service.py](scripts/install_service.py) for the actual service class definition. It:
- Inherits from `win32serviceutil.ServiceFramework`
- Runs `EduraSync.exe --service` as a subprocess
- Handles Windows service events (start, stop)
- Logs to Windows Event Viewer

## Security Considerations

1. **UAC Protects Installation**: Service installation is protected by Windows UAC
2. **Admin Elevation Only When Needed**: UAC prompt only shows when necessary
3. **No Credential Storage**: Service runs under Local System account (no password needed)
4. **Logs Accessible**: Service logs written to user-accessible directory

## Supported Platforms

- **Windows**: ✅ Full support (with UAC elevation)
- **macOS**: ⚠️ Service section hidden (not applicable)
- **Linux**: ⚠️ Service section hidden (systemd would be used instead)

## Notes

- Service management is **Windows-only** due to platform differences
- The GUI app and service can run simultaneously (they sync independently)
- Service automatically restarts on Windows startup if set to "Automatic" (currently set to "Manual")
- Uninstalling the app does NOT automatically remove the service—must be uninstalled from Settings first
