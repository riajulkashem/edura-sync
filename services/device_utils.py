# services/device_utils.py
"""
Utility functions for device operations and common patterns.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from zk import ZK

from core.exceptions import ConnectionError
from interfaces.database.models import Device


class DeviceConnectionManager:
    """
    Manager for device connections with common patterns.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        
    def create_connection(self, device: Device) -> Optional[ZK]:
        """
        Create a connection to a ZKTeco device with enhanced retry logic and exponential backoff.
        
        Args:
            device: Device model containing connection details.
            
        Returns:
            Optional[ZK]: Connected ZK instance or None if connection fails.
            
        Raises:
            ConnectionError: If connection fails after all retries.
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Calculate exponential backoff delay
                current_delay = self.retry_delay * (2 ** attempt)
                
                self.logger.debug(
                    f"Connection attempt {attempt + 1}/{self.max_retries} for {device.ip_address}:{device.port}"
                )
                
                # Use default password if empty. Some firmwares prefer int for numeric passwords.
                password_str = device.password if device.password else "0"
                try:
                    password = int(password_str) if password_str.isdigit() else password_str
                except Exception:
                    password = password_str
                
                zk = ZK(
                    device.ip_address,
                    port=device.port,
                    password=password,
                    timeout=10,  # Increased timeout for better reliability
                )
                
                conn = zk.connect()
                if conn:
                    self.logger.info(
                        f"Successfully connected to device {device.ip_address}:{device.port} on attempt {attempt + 1}"
                    )
                    return zk
                else:
                    raise ConnectionError(
                        f"Failed to establish connection to device {device.ip_address}"
                    )
            
            except Exception as e:
                # Store exception for error message
                last_exception = e
                self.logger.warning(
                    f"Connection attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                
                # Wait before retry (except on last attempt)
                if attempt < self.max_retries - 1:
                    self.logger.debug(f"Waiting {current_delay:.1f}s before retry...")
                    time.sleep(current_delay)
        
        # All attempts failed
        error_msg = f"Failed to connect to device {device.ip_address} after {self.max_retries} attempts"
        if last_exception:
            error_msg += f": {str(last_exception)}"
            
        self.logger.error(error_msg)
        raise ConnectionError(error_msg)

    def safe_disconnect(self, zk: ZK, device_ip: str) -> None:
        """
        Safely disconnect from device with error handling.
        
        Args:
            zk: ZK instance to disconnect
            device_ip: Device IP address for logging
        """
        if zk:
            zk.disconnect()
            self.logger.debug(f"Disconnected from device {device_ip}")

    def update_device_status(self, device: Device, status: str, error_message: str = None) -> None:
        """
        Update device status in database.
        
        Args:
            device: Device to update
            status: New status
            error_message: Optional error message
        """
        device.status = status
        if error_message:
            device.last_error = error_message
        elif status == "Online":
            # Clear error message when device comes online
            device.last_error = None
        device.updated_at = datetime.now()
        device.save()


class BatchProcessor:
    """
    Utility for processing data in batches.
    """
    
    @staticmethod
    def process_in_batches(data: List[Any], batch_size: int, process_func: callable) -> int:
        """
        Process data in batches.
        
        Args:
            data: List of data to process
            batch_size: Size of each batch
            process_func: Function to process each batch
            
        Returns:
            int: Total number of items processed
        """
        if not data:
            return 0
            
        processed_count = 0
        
        # Process data in batches
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            processed_count += process_func(batch)
            
        return processed_count


def extract_device_data(zk: ZK, device: Device, days_limit: int = None) -> Dict[str, Any]:
    """
    Extract data from device.
    
    Args:
        zk: Connected ZK instance
        device: Device model
        days_limit: Optional limit to only pull records from last N days
        
    Returns:
        Dictionary containing users and attendance records
    """
    # Get users
    users = zk.get_users()
    if users is None:
        users = []

    # Get attendance records
    attendance_records = zk.get_attendance()
    if attendance_records is None:
        attendance_records = []
    
    # Filter by days if limit provided
    if days_limit and attendance_records:
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days_limit)
        attendance_records = [
            r for r in attendance_records 
            if getattr(r, 'timestamp', datetime.min) > cutoff
        ]

    return {
        "users": users,
        "attendance": attendance_records,
        "device": device
    }