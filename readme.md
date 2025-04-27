# PrimeSync Tray App

A system tray application for managing ZKTeco devices, pulling attendance data, and syncing with a cloud API. This application supports both Windows and macOS, with automated builds via GitHub Actions.

## Features

- System tray interface for easy access.
- Manage ZKTeco devices (e.g., K40) to pull attendance data.
- Sync data with a cloud API.
- Configurable settings for API credentials and schedules.
- System notifications for key actions (device checks, data pull/push).
- Automated builds for Windows and macOS.

## Prerequisites

- Python 3.9 or 3.10.
- ZKTeco device (e.g., K40 at IP `192.168.0.201`, port `4370`).
- A 64x64 PNG icon file at `assets/icon.png`.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/prime-sync.git
   cd prime-sync
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure `assets/icon.png` exists (create a 64x64 PNG if missing).

4. Run the application:
   ```bash
   python main.py
   ```

## Building

Builds are automated via GitHub Actions. Artifacts are available in the Actions tab after a push to the `main` branch.

### Manual Build

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build using the provided spec file:
   ```bash
   pyinstaller --noconfirm --clean primesync.spec
   ```

3. Find outputs in the `dist/` directory:
   - **Windows**: `PrimeSyncTrayApp/` (contains `PrimeSyncTrayApp.exe`)
   - **macOS**: `PrimeSyncTrayApp.app`

4. For macOS, move the app to Applications and optionally sign it:
   ```bash
   mv dist/PrimeSyncTrayApp.app /Applications/
   codesign --force --deep --sign - /Applications/PrimeSyncTrayApp.app
   ```

## Device Configuration

Configure your ZKTeco K40 device in the application or database:

- **IP**: `192.168.0.201`
- **Port**: `4370`
- **Password**: `0` (default)
- **Model**: `K40`

To add the device manually to the database:
```python
from models import Device, db
db.connect()
Device.create(
    ip_address="192.168.0.201",
    port=4370,
    password="0",
    device_model="K40",
    status="Offline"
)
db.close()
```

## Usage

1. On first run, configure settings (Cloud API URL, username, password, client key).
2. Use the system tray menu to:
   - Check device status.
   - Pull attendance data from devices.
   - Push data to the cloud.
   - View the dashboard or adjust settings.
3. Notifications will appear for successful operations or errors.
4. Logs are saved to `logs/zkteco.log`.

## GitHub Actions

Automated builds run on push or pull request to the `main` branch:
- **Windows**: Produces `PrimeSyncTrayApp-Windows` artifact.
- **macOS**: Produces `PrimeSyncTrayApp-macOS` artifact.

Download artifacts from the GitHub Actions tab.

## Troubleshooting

- **macOS Crashes**:
  - Check `logs/zkteco.log` for errors.
  - Run `python main.py` in terminal for console output.
  - Verify Python 3.9/3.10 compatibility.
  - Check crash reports in macOS Console.app.

- **Notifications Not Showing**:
  - Ensure `PrimeSync Manager` is enabled in macOS System Preferences > Notifications.
  - Test `plyer` notifications:
    ```python
    from plyer import notification
    notification.notify(title="Test", message="Test", app_name="PrimeSync Manager")
    ```
  - Check fallback logs in `logs/primesync.log`.

- **Device Connectivity Issues**:
  - Verify device is reachable:
    ```bash
    ping 192.168.0.201
    telnet 192.168.0.201 4370
    ```
  - Check macOS firewall:
    ```bash
    sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
    ```
  - Test with ZKAccess software to confirm device functionality.

- **Build Failures**:
  - Review GitHub Actions logs for missing dependencies.
  - Ensure `zk` library is installed (may require manual inclusion).

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License

MIT License. See LICENSE file for details.