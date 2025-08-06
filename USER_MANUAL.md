# PrimeSync User Manual

## Table of Contents
1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [First-Time Setup](#first-time-setup)
5. [Using the Application](#using-the-application)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Features](#advanced-features)
9. [Support](#support)

## Overview

PrimeSync is a system tray application designed to manage ZKTeco attendance devices and synchronize attendance data with cloud-based systems. The application provides a user-friendly interface for monitoring device status, pulling attendance records, and syncing data with external APIs.

### Key Features
- **System Tray Interface**: Quick access to all functions from the system tray
- **Device Management**: Monitor and manage ZKTeco devices (e.g., K40)
- **Data Synchronization**: Pull attendance data from devices and sync to cloud APIs
- **User Management**: Manage users across devices
- **Real-time Notifications**: Get notified of important events and errors
- **Dashboard Interface**: Comprehensive GUI for monitoring and configuration

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11 or macOS 10.15+
- **Python**: 3.9 or 3.10 (for development)
- **Memory**: 512 MB RAM
- **Storage**: 100 MB free space
- **Network**: Internet connection for cloud sync

### Hardware Requirements
- **ZKTeco Device**: Compatible attendance device (e.g., K40)
- **Network**: Device must be accessible via TCP/IP

### Supported Devices
- ZKTeco K40 (tested)
- Other ZKTeco devices with ZK protocol support

## Installation

### Option 1: Pre-built Executable (Recommended)

1. **Download**: Get the latest release from the project's GitHub releases page
2. **Windows**: Run the installer and follow the setup wizard
3. **macOS**: 
   - Download the `.app` file
   - Move to Applications folder
   - Right-click and select "Open" (first time only)

### Option 2: Source Code Installation

1. **Clone Repository**:
   ```bash
   git clone https://github.com/your-username/prime-sync.git
   cd prime-sync
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   python main.py
   ```

## First-Time Setup

### 1. Initial Launch
When you first launch PrimeSync, the application will:
- Create necessary directories and database
- Show the dashboard with default settings
- Display a notification about configuring settings

### 2. Configure Settings
1. **Open Dashboard**: Right-click the system tray icon and select "Dashboard"
2. **Navigate to Settings Tab**: Click the "Settings" tab
3. **Fill in API Configuration**:
   - **Cloud API URL**: Your cloud service endpoint (e.g., `https://api.yourcompany.com`)
   - **Username**: Your API username
   - **Password**: Your API password
   - **Institute ID**: Your organization identifier
4. **Set Time Processing**:
   - **In Time Process**: Default check-in time (e.g., 09:00)
   - **Out Time Process**: Default check-out time (e.g., 17:00)
5. **Save Settings**: Click "Save Settings" button

### 3. Add Devices
1. **In Dashboard**: Go to the "Dashboard" tab
2. **Add Device**: Click "Add Device" button
3. **Configure Device**:
   - **IP Address**: Device IP (e.g., `192.168.0.201`)
   - **Port**: Device port (default: `4370`)
   - **Password**: Device password (default: `0`)
   - **Model**: Device model (e.g., `K40`)

## Using the Application

### System Tray Menu
Right-click the PrimeSync icon in the system tray to access:

- **Devices Status**: Check if all devices are online
- **Sync Data**: Pull attendance data from devices
- **Post Cloud**: Send data to cloud API
- **Pull Machine**: Download data from devices
- **Dashboard**: Open the main interface
- **Settings**: Quick access to configuration
- **Exit**: Close the application

### Dashboard Interface

#### Dashboard Tab
- **Status Overview**: Shows device status and sync information
- **Device List**: Displays all configured devices with their status
- **Action Buttons**: Quick access to common operations
- **Refresh**: Update the display with latest information

#### Settings Tab
- **API Configuration**: Cloud service settings
- **Time Settings**: Default processing times
- **Test Connection**: Verify API connectivity
- **Save/Reset**: Manage configuration

#### Credits Tab
- **Developer Information**: Contact details and links
- **Version Information**: Application version and build details

### Common Operations

#### Checking Device Status
1. Right-click system tray icon
2. Select "Devices Status"
3. Wait for notification with results

#### Syncing Data
1. **Pull from Devices**: 
   - Select "Pull Machine" from tray menu
   - This downloads attendance records from all devices
2. **Push to Cloud**:
   - Select "Post Cloud" from tray menu
   - This sends data to your configured API

#### Managing Users
1. Open Dashboard
2. Go to Dashboard tab
3. Use "Sync Users to Devices" to upload new users to devices

## Configuration

### API Settings
- **Cloud API URL**: Must be a valid HTTPS URL
- **Authentication**: Username/password are encrypted locally
- **Institute ID**: Used for multi-tenant setups

### Device Settings
- **IP Address**: Must be accessible from the application
- **Port**: Default ZKTeco port is 4370
- **Password**: Device admin password (usually "0")

### Time Settings
- **In Time Process**: Default check-in time for attendance processing
- **Out Time Process**: Default check-out time for attendance processing

### Advanced Settings
- **Auto-start**: Application starts with Windows/macOS
- **Notifications**: System notifications for events
- **Logging**: Detailed logs stored in `logs/` directory

## Troubleshooting

### Common Issues

#### Application Won't Start
**Symptoms**: Application fails to launch or crashes immediately

**Solutions**:
1. Check Python version (requires 3.9 or 3.10)
2. Verify all dependencies are installed
3. Check log files in `logs/primesync.log`
4. Run from command line for detailed error messages

#### Device Connection Issues
**Symptoms**: Devices show as "Offline" or connection errors

**Solutions**:
1. **Verify Network Connectivity**:
   ```bash
   ping 192.168.0.201
   telnet 192.168.0.201 4370
   ```
2. **Check Firewall Settings**: Ensure port 4370 is not blocked
3. **Verify Device Settings**: Confirm IP, port, and password
4. **Test with ZKAccess**: Use official software to verify device functionality

#### API Connection Problems
**Symptoms**: "Post Cloud" fails or connection errors

**Solutions**:
1. **Check API URL**: Verify the URL is correct and accessible
2. **Test Credentials**: Use "Test Connection" in settings
3. **Check Network**: Ensure internet connectivity
4. **Verify API Endpoints**: Confirm API is running and accessible

#### Notification Issues
**Symptoms**: No system notifications appear

**Solutions**:
1. **Windows**: Check notification settings in Windows Settings
2. **macOS**: 
   - Go to System Preferences > Notifications
   - Enable notifications for "PrimeSync"
3. **Check Logs**: Notifications are logged even if not displayed

#### Data Sync Problems
**Symptoms**: Data not syncing or incomplete syncs

**Solutions**:
1. **Check Device Status**: Ensure devices are online
2. **Verify API Settings**: Test connection in settings
3. **Check Logs**: Review detailed error messages
4. **Manual Sync**: Try individual operations (Pull then Post)

### Log Files
- **Main Log**: `logs/primesync.log`
- **Database**: `primesync.db` (SQLite database)
- **Temporary Files**: Check system temp directory

### Getting Help
1. **Check Logs**: Review log files for error details
2. **Test Components**: Use individual functions to isolate issues
3. **Contact Support**: Include log files when reporting issues

## Advanced Features

### Database Management
The application uses SQLite for local data storage:
- **Location**: `primesync.db` in application directory
- **Backup**: Regularly backup this file
- **Reset**: Delete the file to reset all data

### User Management
- **Local Users**: Stored in local database
- **Device Users**: Synced to/from devices
- **Cloud Users**: Managed through API

### Scheduling
- **Automatic Sync**: Configured through API settings
- **Manual Sync**: Available through tray menu
- **Status Checks**: Automatic device monitoring

### Security
- **Password Encryption**: API passwords are encrypted locally
- **Token Management**: Authentication tokens are secured
- **Local Storage**: All sensitive data stored locally

## Support

### Documentation
- **README**: Basic setup and usage
- **User Manual**: This document
- **Code Comments**: Inline documentation in source code

### Contact Information
- **Developer**: Riajul Kashem
- **GitHub**: [riajulkashem](https://github.com/riajulkashem)
- **LinkedIn**: [riajulkashem](https://linkedin.com/in/riajulkashem)

### Reporting Issues
When reporting issues, please include:
1. Operating system and version
2. Application version
3. Detailed error description
4. Relevant log files
5. Steps to reproduce the issue

### Version History
- **v1.0.0**: Initial release with core functionality
  - System tray application
  - Device management
  - Cloud synchronization
  - Dashboard interface

---

**Note**: This manual covers the current version of PrimeSync. For the latest information, check the project's GitHub repository. 