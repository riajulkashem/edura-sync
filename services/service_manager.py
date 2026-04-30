# services/service_manager.py
"""
Windows Service Management for EduraSync.
Handles installation, removal, and status checking of the Windows service.
"""

import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import Tuple

# Windows-only imports
try:
    import ctypes
    from ctypes import wintypes
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False


logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages EduraSync Windows Service."""
    
    SERVICE_NAME = "EduraSyncService"
    DISPLAY_NAME = "EduraSync Attendance Service"
    DESCRIPTION = "Synchronizes attendance data from ZKTeco devices to the cloud."
    
    def __init__(self):
        self.is_windows = sys.platform.startswith('win')
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def is_admin() -> bool:
        """Check if the current process has administrator privileges."""
        if not WINDOWS_AVAILABLE:
            return False
        
        try:
            return bool(ctypes.windll.shell.IsUserAnAdmin())
        except Exception as e:
            logger.error(f"Failed to check admin status: {e}")
            return False
    
    @staticmethod
    def request_admin_elevation(script_path: str, args: list) -> Tuple[bool, str]:
        """
        Request admin elevation to run a script with elevated privileges.
        Shows Windows UAC prompt.
        
        Args:
            script_path: Path to install_service.py
            args: Arguments to pass (e.g., ['install'])
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not WINDOWS_AVAILABLE:
            return False, "Windows platform required"
        
        try:
            # Request UAC elevation via ShellExecuteW.
            # Avoids manual ctypes structure construction errors and works from GUI context.
            python_exe = sys.executable or "python.exe"
            params = f'"{script_path}" {" ".join(args)}'
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", python_exe, params, None, 1
            )
            # Per WinAPI docs, return value > 32 indicates success.
            if result > 32:
                return True, "Elevation requested. Please allow UAC and refresh service status."
            return False, "Failed to request admin elevation (UAC canceled or unavailable)"
        
        except Exception as e:
            logger.error(f"Error requesting admin elevation: {e}")
            return False, f"Error: {str(e)}"
    
    def _get_service_script_path(self) -> str:
        """
        Get the path to install_service.py.
        Handles both development and bundled (PyInstaller) environments.
        
        Returns:
            Absolute path to install_service.py
        """
        # Try relative path first (development)
        script_path = os.path.join(
            os.path.dirname(__file__),
            "..", "scripts", "install_service.py"
        )
        script_path = os.path.abspath(script_path)
        
        if os.path.exists(script_path):
            return script_path
        
        # If running from PyInstaller bundle, try _MEIPASS
        if hasattr(sys, "_MEIPASS"):
            bundle_script = os.path.join(sys._MEIPASS, "scripts", "install_service.py")
            if os.path.exists(bundle_script):
                return bundle_script
        
        # Fallback: still return the original path (may fail gracefully)
        return script_path
    
    def install_service(self) -> Tuple[bool, str]:
        """
        Install the EduraSync Windows Service.
        Requires administrator privileges.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_windows:
            return False, "Service installation only available on Windows"
        
        script_path = self._get_service_script_path()
        
        if not os.path.exists(script_path):
            return False, f"Service script not found: {script_path}"
        
        # Check if running as admin
        if not self.is_admin():
            # Request elevation with UAC
            return self.request_admin_elevation(script_path, ["install"])
        
        # Already admin, proceed with installation
        try:
            # Run install_service.py install
            result = subprocess.run(
                [sys.executable, script_path, "install"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Start the service
                subprocess.run(
                    [sys.executable, script_path, "start"],
                    capture_output=True,
                    timeout=30
                )
                return True, "Service installed and started successfully"
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return False, f"Installation failed: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return False, "Service installation timed out"
        except Exception as e:
            logger.error(f"Error installing service: {e}")
            return False, f"Error: {str(e)}"
    
    def uninstall_service(self) -> Tuple[bool, str]:
        """
        Uninstall the EduraSync Windows Service.
        Requires administrator privileges.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_windows:
            return False, "Service uninstallation only available on Windows"
        
        script_path = self._get_service_script_path()
        
        if not os.path.exists(script_path):
            return False, f"Service script not found: {script_path}"
        
        # Check if running as admin
        if not self.is_admin():
            # Request elevation with UAC
            return self.request_admin_elevation(script_path, ["stop", "remove"])
        
        # Already admin, proceed with removal
        try:
            # Stop the service
            subprocess.run(
                [sys.executable, script_path, "stop"],
                capture_output=True,
                timeout=30
            )
            
            # Remove the service
            result = subprocess.run(
                [sys.executable, script_path, "remove"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return True, "Service uninstalled successfully"
            else:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return False, f"Uninstallation failed: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return False, "Service uninstallation timed out"
        except Exception as e:
            logger.error(f"Error uninstalling service: {e}")
            return False, f"Error: {str(e)}"
    
    def is_service_installed(self) -> bool:
        """
        Check if the EduraSync service is currently installed.
        
        Returns:
            True if service exists, False otherwise
        """
        if not self.is_windows:
            return False
        
        try:
            result = subprocess.run(
                ["sc", "query", self.SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking service status: {e}")
            return False
    
    def get_service_status(self) -> str:
        """
        Get the current status of the EduraSync service.
        
        Returns:
            Service status string (e.g., "running", "stopped", "not_installed")
        """
        if not self.is_windows:
            return "not_applicable"
        
        if not self.is_service_installed():
            return "not_installed"
        
        try:
            result = subprocess.run(
                ["sc", "query", self.SERVICE_NAME],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "RUNNING" in result.stdout:
                return "running"
            elif "STOPPED" in result.stdout:
                return "stopped"
            else:
                return "unknown"
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return "unknown"
