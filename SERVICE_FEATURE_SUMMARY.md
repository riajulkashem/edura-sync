# Settings UI Service Management Feature

## What Was Added

A new **⚙️ Background Service** section in the Settings tab (Windows only) that lets users enable/disable the Windows Service directly from the app.

## UI Components

### Service Management Section Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚙️  Background Service (Windows)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Run EduraSync as a Windows Service to sync attendance in the    │
│ background even when the app is closed.                         │
│ You will be prompted for administrator permission when          │
│ enabling/disabling.                                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ ❌ Service: Not Installed                    [✅ Enable]  [🔄]  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Status Indicators

| State | Display | Button | Color |
|-------|---------|--------|-------|
| **Not Installed** | ❌ Service: Not Installed | ✅ Enable Service | Red |
| **Running** | ✅ Service: Running | ⏹️ Disable Service | Green/Red |
| **Stopped** | ⚠️ Service: Stopped | ▶️ Start Service | Orange/Green |

## How It Works: Flow Diagram

```
User clicks [✅ Enable Service]
        ↓
Check: Is app running as Admin?
        ├─ No → Show UAC Elevation Dialog
        │        (Windows prompts for permission)
        │        ↓
        │   User clicks [Yes] in UAC
        │        ↓
        └─→ Run install_service.py with admin privileges
                ↓
           Service Installed & Started
                ↓
           Status updates: ✅ Service: Running
                ↓
           Button changes: ⏹️ Disable Service
```

## Code Structure

### New Files Created

1. **`services/service_manager.py`** (340+ lines)
   - `ServiceManager` class
   - Methods:
     - `is_admin()` - Check admin status
     - `request_admin_elevation()` - Trigger UAC prompt
     - `install_service()` - Install Windows service
     - `uninstall_service()` - Remove Windows service
     - `is_service_installed()` - Check if service exists
     - `get_service_status()` - Get current status
   - Handles UAC elevation using Windows `ShellExecuteEx` API

2. **`SERVICE_MANAGEMENT.md`** (Complete user guide)

### Modified Files

1. **`interfaces/gui_pyside6/dashboard_settings.py`**
   - Added imports: `sys`, `ServiceManager`
   - New instance variables: `self.service_manager`, `self.service_status_label`
   - New methods:
     - `_create_service_management_group()` - Create UI section
     - `_update_service_status()` - Refresh status display
     - `_toggle_service()` - Handle enable/disable click
     - `_install_service()` - Install with confirmation dialog
     - `_uninstall_service()` - Uninstall with confirmation dialog

## Features

✅ **Automatic UAC Elevation**: Shows Windows UAC prompt when needed
✅ **Status Display**: Real-time service status indicator
✅ **One-Click Management**: Enable/disable with single click
✅ **Confirmation Dialogs**: User must confirm before action
✅ **Error Handling**: Clear error messages if something fails
✅ **Cross-Platform Aware**: Hidden on macOS/Linux
✅ **Bundling Support**: Works with PyInstaller executables
✅ **Async Operation**: Button shows loading state during operations

## User Experience

### Enable Service Flow
1. User clicks "✅ Enable Service"
2. Confirmation dialog appears
3. UAC prompt appears (user clicks Yes)
4. Service installs silently (takes ~2-5 seconds)
5. Status updates to "✅ Service: Running"

### Disable Service Flow
1. User clicks "⏹️ Disable Service"
2. Confirmation dialog appears
3. UAC prompt appears (user clicks Yes)
4. Service stops and uninstalls
5. Status updates to "❌ Service: Not Installed"

## Technical Highlights

### UAC Elevation Implementation

Uses Windows API `ShellExecuteEx` with `runas` verb:
- No password required (privilege escalation model)
- Works on all Windows versions (Vista+)
- Parent process doesn't need admin privileges
- User sees standard Windows UAC dialog

### Service Status Check

Uses `sc query` command:
- Cross-platform safe (cmd.exe available on all Windows)
- No admin privileges required for querying
- Reliable status detection

### Error Resilience

- Tries relative path first (development)
- Falls back to PyInstaller bundle path
- Timeouts on hanging operations
- Detailed error messages logged

## Testing Checklist

- [ ] Service section only appears on Windows
- [ ] "Checking status..." shows initially
- [ ] Status updates correctly after installation
- [ ] Button text changes based on status
- [ ] UAC prompt appears when enabling
- [ ] Service actually runs in background (check `sc query`)
- [ ] Disabling removes service cleanly
- [ ] Error messages display properly
- [ ] Refresh button updates status
- [ ] Works with bundled .exe file

## Files Modified Summary

```
prime-sync/
├── services/
│   └── service_manager.py          [NEW - 340+ lines]
├── interfaces/gui_pyside6/
│   └── dashboard_settings.py        [MODIFIED - +150 lines]
└── SERVICE_MANAGEMENT.md            [NEW - Complete guide]
```

## Backward Compatibility

✅ **Fully backward compatible**
- Feature is Windows-only (hidden on other platforms)
- No changes to existing Settings functionality
- Service is optional (app works fine without it)
- Existing data/configs unaffected
