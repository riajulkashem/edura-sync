# Service Management Feature - Architecture & Diagrams

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EduraSync Application                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ PySide6 GUI Layer                                                    │   │
│  │ ┌────────────────────────────────────────────────────────────────┐   │   │
│  │ │ Dashboard UI                                                   │   │   │
│  │ │  ├─ Settings Tab                                              │   │   │
│  │ │  │  ├─ Cloud API Settings                                     │   │   │
│  │ │  │  ├─ Sync Time Configuration                                │   │   │
│  │ │  │  └─ ⚙️ SERVICE MANAGEMENT (NEW)                            │   │   │
│  │ │  │     ├─ Status Display                                      │   │   │
│  │ │  │     ├─ Enable/Disable Button                               │   │   │
│  │ │  │     └─ Refresh Status Button                               │   │   │
│  │ └────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              ↓ (user clicks)                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ServiceManager Layer (NEW)                                           │   │
│  │ services/service_manager.py                                          │   │
│  │                                                                        │   │
│  │  Methods:                                                            │   │
│  │  • is_admin()              ← Check privilege level                  │   │
│  │  • request_admin_elevation() ← Trigger Windows UAC                 │   │
│  │  • install_service()       ← Install with auto-elevation          │   │
│  │  • uninstall_service()     ← Remove with auto-elevation           │   │
│  │  • get_service_status()    ← Query current status                 │   │
│  │  • is_service_installed()  ← Check if exists                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              ↓                                               │
│                    Windows APIs / Subprocess                               │
│                              ↓                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                        Windows Operating System                             │
│                                                                              │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────┐    │
│  │  Windows Service Control (sc.exe)    │  │  Windows UAC Dialog      │    │
│  │                                      │  │                          │    │
│  │  sc create EduraSyncService          │  │  "Do you want to allow   │    │
│  │  sc start EduraSyncService           │  │  this app to make        │    │
│  │  sc stop EduraSyncService            │  │  changes to your device?"│    │
│  │  sc delete EduraSyncService          │  │                          │    │
│  │  sc query EduraSyncService           │  │  [Yes] [No] [Cancel]     │    │
│  └──────────────────────────────────────┘  └──────────────────────────┘    │
│                              ↓                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │              EduraSync Windows Service (Optional)                    │   │
│  │                                                                        │   │
│  │  • Service Name: EduraSyncService                                    │   │
│  │  • Display Name: EduraSync Attendance Service                        │   │
│  │  • Executable: EduraSync.exe --service                               │   │
│  │  • Mode: Headless (no GUI)                                           │   │
│  │  • Startup: Manual                                                   │   │
│  │  • Account: Local System                                             │   │
│  │  • Function: Background sync 24/7                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## User Interaction Flow

```
START: User opens EduraSync
  │
  └─→ [Settings Tab]
        │
        └─→ [⚙️ Service Management Section]
              │
              ├─→ Status Check: "Checking status..."
              │   └─→ Shows: "❌ Service: Not Installed"
              │
              └─→ User clicks [✅ Enable Service]
                    │
                    ├─→ Confirmation Dialog appears
                    │   "Install service for background sync?"
                    │   [Yes] [No]
                    │
                    ├─→ User clicks [Yes]
                    │   │
                    │   └─→ ServiceManager.install_service() called
                    │       │
                    │       ├─→ Check: is_admin() ?
                    │       │   │
                    │       │   ├─ Yes → Run install directly
                    │       │   │         (subprocess.run)
                    │       │   │
                    │       │   └─ No → request_admin_elevation()
                    │       │         │
                    │       │         └─→ Windows UAC Dialog
                    │       │             "Do you want to allow..."
                    │       │             │
                    │       │             ├─→ User clicks [Yes]
                    │       │             │   └─→ Elevated process runs
                    │       │             │
                    │       │             └─→ User clicks [No]
                    │       │                 └─→ Cancel operation
                    │       │
                    │       ├─→ Run install_service.py install
                    │       ├─→ Run install_service.py start
                    │       └─→ Return (success, message)
                    │
                    ├─→ UI Updates:
                    │   └─→ Status: "✅ Service: Running" (green)
                    │   └─→ Button: "⏹️ Disable Service" (red)
                    │   └─→ Success notification shown
                    │
                    └─→ END: Service active in background
```

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   DashboardSettings (UI)                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ _create_service_management_group()                       │   │
│  │  ├─ Creates QGroupBox                                    │   │
│  │  ├─ Creates Status Label                                 │   │
│  │  ├─ Creates Toggle Button                                │   │
│  │  └─ Creates Refresh Button                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Event Handlers                                           │   │
│  │  ├─ _update_service_status()  [Called on init & refresh] │   │
│  │  ├─ _toggle_service()         [Toggle button clicked]    │   │
│  │  ├─ _install_service()        [Install flow]            │   │
│  │  └─ _uninstall_service()      [Uninstall flow]          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                           │
                  Uses ServiceManager
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   ServiceManager (Backend)                      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Status Checking                                          │   │
│  │  ├─ is_admin()         ← ctypes.windll.shell check      │   │
│  │  ├─ is_service_installed() ← subprocess sc query        │   │
│  │  └─ get_service_status()   ← Parse sc query output      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Service Management                                       │   │
│  │  ├─ install_service()                                    │   │
│  │  │   ├─ Check admin status                               │   │
│  │  │   ├─ If not admin: request_admin_elevation()         │   │
│  │  │   └─ subprocess.run(python install_service.py...)    │   │
│  │  │                                                       │   │
│  │  └─ uninstall_service()                                  │   │
│  │      ├─ Check admin status                               │   │
│  │      ├─ If not admin: request_admin_elevation()         │   │
│  │      └─ subprocess.run(python install_service.py...)    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ UAC Elevation                                            │   │
│  │  └─ request_admin_elevation()                            │   │
│  │      └─ Uses ctypes.windll.shell.ShellExecuteEx()       │   │
│  │         with runas verb (triggers UAC)                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           ↓
                           │
                 Subprocess / Windows API
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Windows System                                │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Command Line (sc.exe, python.exe)                        │   │
│  │  └─ python scripts/install_service.py [action]          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Windows Service Control Manager                          │   │
│  │  └─ Manages EduraSyncService                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ EduraSync Windows Service (When Running)                 │   │
│  │  └─ EduraSync.exe --service                              │   │
│  │     └─ Headless sync in background                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Status State Machine

```
                    [NOT_INSTALLED]
                           ↑
                           │
                 user clicks "Enable Service"
                 shows confirmation dialog
                 UAC prompts
                 install_service.py runs
                           │
                           ↓
                 ┌─────────────────────┐
                 │   INSTALLING...     │
                 │ (progress state)    │
                 └─────────────────────┘
                           │
                           ↓
                        [RUNNING] ←─────────────┐
                           ↑                    │
                           │                    │
           no action       │                    │
           (auto-start)    │                    │
                           │            user clicks "Disable Service"
                           │            shows confirmation dialog
                           │            UAC prompts
                           │            install_service.py remove runs
                           │                    │
                     [STOPPED] ←────────────────┘
                    (rare state)

Legend:
[STATE] = stable state
PROCESS... = transitional state
→ = user action or automatic transition
```

## Files and Dependencies

```
prime-sync/
│
├── services/
│   ├── __init__.py
│   ├── service_manager.py              ← NEW (340+ lines)
│   │   └── ServiceManager class
│   │       └── Windows Service API
│   │
│   ├── api_sync.py                     (unchanged)
│   ├── device_manager.py               (unchanged)
│   └── notification.py                 (unchanged)
│
├── interfaces/gui_pyside6/
│   ├── dashboard_settings.py           ← MODIFIED (+150 lines)
│   │   └── DashboardSettings class
│   │       └── Service UI integration
│   │
│   ├── dashboard.py                    (unchanged)
│   ├── device_management.py            (unchanged)
│   └── tray.py                         (unchanged)
│
├── scripts/
│   ├── install_service.py              (unchanged)
│   ├── install_service.bat             (unchanged)
│   └── uninstall_service.bat           (unchanged)
│
├── core/
│   ├── config.py                       (unchanged)
│   ├── constants.py                    (unchanged)
│   └── ... (other modules unchanged)
│
└── Documentation (NEW)
    ├── SERVICE_MANAGEMENT.md           ← User guide
    ├── SERVICE_FEATURE_SUMMARY.md      ← Overview
    ├── SERVICE_MANAGER_API.md          ← Developer guide
    └── SERVICE_FEATURE_IMPLEMENTATION.md ← Implementation details
```

## Request/Response Flow

### Enable Service Flow

```
1. User clicks "Enable Service" button
   │
   ├─ Request: _toggle_service() called
   │
   └─ Response: Confirmation dialog shown
   
2. User clicks "Yes" in confirmation
   │
   ├─ Request: _install_service() called
   │
   └─ Response: UI shows "⏳ Installing..."

3. ServiceManager.install_service() called
   │
   ├─ Request 1: Check is_admin()
   │   └─ Response: bool (True/False)
   │
   ├─ Request 2a: If not admin, request_admin_elevation()
   │   └─ Response: UAC prompt appears → user clicks Yes
   │
   ├─ Request 2b: If admin, skip UAC
   │   └─ Response: (continue directly)
   │
   ├─ Request 3: subprocess.run(install_service.py install)
   │   └─ Response: (success, message) tuple
   │
   └─ Return: (True, "Service installed and started successfully")

4. Update UI
   │
   ├─ _update_service_status() called
   │
   └─ Display: "✅ Service: Running" + "⏹️ Disable Service"

5. Show Success Notification
   │
   └─ User sees: "Service installed and started successfully"
```

### Check Status Flow

```
User clicks "Refresh" button
   │
   ├─ Request: _update_service_status() called
   │
   ├─ Request: ServiceManager.get_service_status()
   │   │
   │   ├─ Request: is_service_installed()
   │   │   │
   │   │   └─ subprocess.run(["sc", "query", "EduraSyncService"])
   │   │       └─ Response: returncode 0 if exists
   │   │
   │   ├─ If installed:
   │   │   └─ subprocess.run(["sc", "query", "EduraSyncService"])
   │   │       └─ Parse stdout for status
   │   │           └─ Response: "running" | "stopped" | "unknown"
   │   │
   │   └─ If not installed:
   │       └─ Response: "not_installed"
   │
   └─ Update UI:
       ├─ Status label color
       ├─ Status label text
       └─ Button text and state
```

## UI Layout Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     Settings Tab                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Cloud API Settings Group]                                     │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Cloud API URL:     [________________________]               │ │
│  │ Sync ID:           [________________________]               │ │
│  │ Daily Sync Time:   [HH:MM▼]                                │ │
│  │                                                            │ │
│  │ [Save Settings] [Test Connection] [Reset]                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [⚙️ Background Service (Windows)] ← NEW SECTION              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Run EduraSync as a Windows Service to sync attendance in  │ │
│  │ the background even when the app is closed. You will be   │ │
│  │ prompted for administrator permission when enabling/      │ │
│  │ disabling.                                                │ │
│  │                                                            │ │
│  │ ❌ Service: Not Installed      [✅ Enable Service] [🔄]    │ │
│  │ (status label)                  (action button)   (refresh)│ │
│  │                                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  [🔧 Advanced Maintenance]                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ ... (existing maintenance options)                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Security Model                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Normal Execution (no service management)                    │
│     ┌────────────────────────────────────────────┐             │
│     │ EduraSync.exe                              │             │
│     │ Privilege Level: User                      │             │
│     │ Can: Read/write user files, sync data      │             │
│     │ Cannot: Install Windows services           │             │
│     └────────────────────────────────────────────┘             │
│                          ↓ (Service install requested)          │
│                                                                  │
│  2. Service Installation (with UAC)                             │
│     ┌────────────────────────────────────────────┐             │
│     │ EduraSync.exe → request_admin_elevation()  │             │
│     │       ↓                                    │             │
│     │ [Windows UAC Dialog]                       │             │
│     │ "Do you want to allow this app..."         │             │
│     │       ↓ (user clicks Yes)                  │             │
│     │ Elevated Process Created                   │             │
│     │ Privilege Level: Administrator             │             │
│     │ Can: Install services, modify system       │             │
│     │       ↓                                    │             │
│     │ install_service.py runs (elevated)         │             │
│     │       ↓                                    │             │
│     │ Service installed, elevated process ends   │             │
│     └────────────────────────────────────────────┘             │
│                          ↓                                      │
│  3. Service Runtime (after installation)                        │
│     ┌────────────────────────────────────────────┐             │
│     │ EduraSyncService (Windows Service)         │             │
│     │ Privilege Level: Local System              │             │
│     │ Account: NT AUTHORITY\SYSTEM               │             │
│     │ Can: Read/write all files, run as service  │             │
│     │ Runtime: 24/7 in background               │             │
│     └────────────────────────────────────────────┘             │
│                                                                  │
│  4. Key Security Points                                          │
│     • UAC elevation only when necessary                         │
│     • No password storage or transmission                       │
│     • No credential passing between processes                   │
│     • Service runs under predefined system account              │
│     • Service can be uninstalled anytime                        │
│     • All operations logged to file                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
Try to install service
    │
    ├─→ Catch TimeoutExpired
    │   └─→ Return (False, "Service installation timed out")
    │
    ├─→ Catch FileNotFoundError
    │   └─→ Return (False, "Service script not found: [path]")
    │
    ├─→ Catch subprocess error
    │   └─→ Parse stderr
    │   └─→ Return (False, f"Installation failed: {error}")
    │
    └─→ Catch Generic Exception
        └─→ Log exception
        └─→ Return (False, f"Error: {str(e)}")

In UI:
    ├─→ If success:
    │   └─→ Show info notification
    │   └─→ Log to INFO level
    │   └─→ Update UI status
    │
    └─→ If failure:
        └─→ Show warning/error notification
        └─→ Log to ERROR level
        └─→ Keep UI status unchanged
        └─→ Display error message to user
```

---

## Summary

The service management feature creates a complete ecosystem for Windows Service control:

1. **User Interface** → Clean, intuitive Settings UI section
2. **Service Manager** → Python API with admin elevation
3. **Windows Integration** → UAC elevation, service control
4. **Error Handling** → Comprehensive error reporting
5. **Documentation** → Complete guides for users and developers

All layers communicate seamlessly with proper error handling, logging, and user feedback at each stage.
