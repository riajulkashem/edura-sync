# EduraSync

A comprehensive attendance synchronization system for ZKTeco fingerprint devices. EduraSync manages device connections, pulls attendance data, syncs users with cloud APIs, and provides a modern GUI dashboard with system tray integration.

## Features

- **Device Management**: Connect and manage multiple ZKTeco fingerprint devices
- **User Synchronization**: Sync users from cloud API to local database and devices
- **Attendance Data Sync**: Pull attendance logs from devices and push to cloud API
- **Modern GUI**: PySide6-based dashboard with device management, user management, and status monitoring
- **System Tray Integration**: Background operation with system tray access
- **Headless Mode**: Run with minimal resources (tray only, no dashboard)
- **Service Mode**: Run as Windows service for automated scheduled tasks
- **Automated Builds**: GitHub Actions for Windows installer creation
- **Real-time Notifications**: System notifications for device status, sync operations, and errors
- **Database Management**: SQLite database with optimized queries and caching

## Prerequisites

- **Python**: 3.13.2 or higher
- **Operating System**: Windows 10/11 or macOS
- **ZKTeco Device**: Compatible fingerprint attendance device (e.g., K40, ZK Teco)
- **Network**: Device must be accessible on the network
- **Cloud API**: Backend API endpoint for user and attendance synchronization

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/riajulkashem/edura-sync.git
   cd edura-sync
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python main.py
   ```

### Windows Installer (Recommended)

Download the latest Windows installer from [GitHub Releases](https://github.com/riajulkashem/edura-sync/releases).

#### ⚠️ Security Note (SmartScreen)

Because this application is not signed with a paid Microsoft Developer Certificate, Windows will display a blue "Windows protected your PC" warning when you run the installer.

**To bypass this and install:**
1. Click **"More info"** on the blue dialog box.
2. Click **"Run anyway"**.

#### 🛡️ Verifying the Download

To ensure the file hasn't been tampered with, you can verify the SHA256 checksum provided in the release assets.

**Using PowerShell:**
1. Open PowerShell in your download folder.
2. Run the following command:
   ```powershell
   Get-FileHash ./EduraSync-Setup-1.0.x.exe -Algorithm SHA256
   ```
3. Compare the output hash with the content of the `.sha256` file downloaded from the release page.

The installer includes:
- Pre-built executable
- Automatic startup configuration
- Desktop shortcut (optional)
- All required dependencies

## Configuration

### Initial Setup

1. **Configure Cloud API Settings**:
   - Open the application
   - Navigate to Settings
   - Enter your Cloud API URL
   - Enter your Sync ID (provided by your institution)

2. **Sync Users from Cloud**:
   - Use "Sync Users" from the system tray menu or dashboard
   - This will pull users and devices from the cloud API
   - Users will be automatically migrated to connected devices

3. **Add Devices**:
   - Devices are automatically added when syncing from cloud
   - Or manually add devices through the Device Management tab
   - Configure IP address, port (default: 4370), and password

### Device Configuration

Devices are configured with the following information:
- **IP Address**: Device's network IP (e.g., `192.168.0.165`)
- **Port**: Default is `4370` for ZKTeco devices
- **Password**: Device password (usually empty or `0`)
- **Cloud ID**: Automatically assigned when syncing from cloud

## Usage

### Running Modes

1. **Full GUI Mode** (default):
   ```bash
   python main.py
   ```
   - Dashboard window
   - System tray icon
   - Full feature access

2. **Headless Mode** (tray only):
   ```bash
   python main.py --headless
   ```
   - System tray only
   - Reduced resource usage
   - Background operation

3. **Service Mode** (Windows):
   ```bash
   python main.py --service
   ```
   - No GUI
   - Scheduled tasks only
   - Minimal resource usage

### System Tray Menu

- **Check Device Status**: Verify connectivity to all configured devices
- **Sync Users**: Pull users and devices from cloud API
- **Upload Attendance**: Push pending attendance records to cloud
- **Fetch New Logs**: Pull latest attendance data from devices
- **Open Dashboard**: Launch the main GUI window
- **App Settings**: Configure API credentials and schedules
- **Quit Application**: Exit the application

### Dashboard Features

- **Device Management**: View and manage connected devices
- **User Management**: View users synced from cloud
- **Status Monitoring**: Real-time device and sync status
- **Settings**: Configure API endpoints and sync schedules

## API Integration

EduraSync integrates with a Django REST Framework backend:

### Endpoints

- **Users List**: `GET /api/attendance/fingerprint-device/users-list/`
  - Returns users and devices assigned to the sync ID
  - Format: `{"users": [...], "devices": [...]}`

- **Attendance Log**: `POST /api/attendance/attendance-log/`
  - Sends attendance records to cloud
  - Format: `[{"device": 2, "user_id": "7596", "timestamp": "...", ...}]`

- **Test Connection**: `GET /api/attendance/fingerprint-device/test/`
  - Validates sync ID and connection

### Authentication

All API requests use the `X-Sync-Id` header for authentication.

## Building

### Automated Builds

Builds are automated via GitHub Actions:
- **Trigger**: Push to `main` or `headless` branch
- **Output**: Windows installer (`.exe`) with SHA256 checksum
- **Artifacts**: Available in GitHub Actions tab

### Manual Build

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build using the spec file:
   ```bash
   pyinstaller --clean --noconfirm edurasync.spec
   ```

3. Output location:
   - **Windows**: `dist/EduraSync/` directory containing `EduraSync.exe`

## Project Structure

```
EduraSync/
├── core/                 # Core functionality
│   ├── config.py        # Configuration management
│   ├── constants.py     # Application constants
│   └── validation.py    # Input validation
├── interfaces/          # Interface layers
│   ├── database/       # Database models and repositories
│   └── gui_pyside6/    # GUI components
├── services/            # Business logic
│   ├── api_sync.py     # Cloud API synchronization
│   ├── device_manager.py # Device communication
│   └── notification.py # System notifications
├── assets/             # Application assets
├── scripts/            # Utility scripts
├── tests/              # Test files
└── main.py             # Application entry point
```

## Troubleshooting

### Device Connection Issues

- **Device Not Found**:
  - Verify device IP address and port
  - Check network connectivity: `ping <device-ip>`
  - Test port accessibility: `telnet <device-ip> 4370`
  - Verify device password

- **Users Not Syncing to Device**:
  - Ensure users are synced from cloud first
  - Check device connectivity
  - Verify device has sufficient storage

### Cloud API Issues

- **Connection Failed**:
  - Verify Cloud API URL is correct
  - Check Sync ID is valid
  - Test connection using "Test Connection" in settings

- **Users Not Found**:
  - Ensure users are synced from cloud before fetching device logs
  - Check that cloud user IDs match device user IDs

### Application Issues

- **Application Won't Start**:
  - Check Python version: `python --version` (requires 3.13.2+)
  - Verify all dependencies are installed
  - Check logs (see Log File Locations below)

### Log File Locations

After installing on Windows, log files are stored in:

**Windows (Installed Application):**
- Primary location: `C:\Program Files\EduraSync\data\logs\edurasync.log`
- Fallback location: `%APPDATA%\EduraSync\logs\edurasync.log`
  - Full path: `C:\Users\<YourUsername>\AppData\Roaming\EduraSync\logs\edurasync.log`

**To find your log file:**
1. Press `Win + R` to open Run dialog
2. Type: `%APPDATA%\EduraSync\logs` and press Enter
3. Open `edurasync.log` in a text editor

**Windows (Running from Source):**
- Log file: `logs/edurasync.log` (in the project directory)

**macOS:**
- Log file: `~/Library/Application Support/EduraSync/logs/edurasync.log`

- **Database Errors**:
  - Database file: `edurasync.db` in project root
  - Check file permissions
  - Verify database is not corrupted

### Build Issues

- **PyInstaller Fails**:
  - Ensure all dependencies are installed
  - Check `edurasync.spec` file is valid
  - Review build logs for missing modules

## Development

### Setting Up Development Environment

1. Clone and install dependencies (see Installation)
2. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run in development mode:
   ```bash
   python main.py
   ```

### Code Structure

- **Models**: Database models in `interfaces/database/models.py`
- **Repositories**: Data access layer in `interfaces/database/repository.py`
- **Services**: Business logic in `services/`
- **GUI**: PySide6 components in `interfaces/gui_pyside6/`

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add your feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Developer

**Riajul Kashem** - Software Engineer

- GitHub: [@riajulkashem](https://github.com/riajulkashem)
- LinkedIn: [riajulkashem](https://linkedin.com/in/riajulkashem)

## Support

For issues, feature requests, or questions:
- Open an issue on [GitHub Issues](https://github.com/riajulkashem/edura-sync/issues)
- Check logs in `logs/edurasync.log` for error details

---

**Note**: This application requires a compatible cloud API backend. Ensure your backend implements the required endpoints as described in the API Integration section.
