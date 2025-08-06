import base64
import logging
import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecurityManager:
    """
    Handles encryption and decryption of sensitive data.
    Uses Fernet symmetric encryption with a securely derived key.
    """

    def __init__(self):
        """Initialize the security manager with a derived encryption key."""
        self.logger = logging.getLogger(__name__)
        self.key = self._derive_key()
        self.cipher = Fernet(self.key)
        self.logger.info("SecurityManager initialized")

    def _derive_key(self) -> bytes:
        """
        Derive a consistent encryption key based on machine-specific information.
        Uses a secure salt stored in a protected location.
        Returns:
            bytes: A derived encryption key.
        """
        try:
            # Get the application data directory for storing the salt
            config_dir = self._get_config_directory()
            salt_file = config_dir / ".salt"

            # Generate or load salt
            if salt_file.exists():
                with open(salt_file, "rb") as f:
                    salt = f.read()
            else:
                # Generate a new secure salt
                salt = secrets.token_bytes(16)
                config_dir.mkdir(parents=True, exist_ok=True)
                with open(salt_file, "wb") as f:
                    f.write(salt)
                # Set restrictive permissions on salt file
                salt_file.chmod(0o600)

            # Use environment variable for master key if available, otherwise prompt
            master_key = os.environ.get("PRIMESYNC_MASTER_KEY")
            if not master_key:
                # Fallback to a more secure default that's not hardcoded
                master_key = self._get_fallback_master_key()

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
            self.logger.debug("Encryption key derived successfully")
            return key
        except Exception as e:
            self.logger.error(f"Failed to derive encryption key: {e}")
            # Fall back to a generated key if derivation fails
            return Fernet.generate_key()

    def _get_config_directory(self) -> Path:
        """Get the configuration directory for storing security files."""
        if os.name == "nt":  # Windows
            config_dir = Path(os.getenv("APPDATA", "")) / "PrimeSync" / "config"
        else:  # Unix-like systems
            config_dir = Path.home() / ".config" / "primesync"
        return config_dir

    def _get_fallback_master_key(self) -> str:
        """
        Generate a fallback master key based on machine-specific information.
        This is less secure than a user-provided key but better than hardcoded.
        """
        # Use machine-specific information to create a unique key
        machine_id = self._get_machine_id()
        # Combine with a fixed component to ensure consistency
        fallback_key = f"PrimeSync_{machine_id}_v1"
        self.logger.warning(
            "Using fallback master key - consider setting PRIMESYNC_MASTER_KEY environment variable"
        )
        return fallback_key

    def _get_machine_id(self) -> str:
        """Get a unique machine identifier."""
        try:
            if os.name == "nt":  # Windows
                import subprocess

                result = subprocess.run(
                    ["wmic", "csproduct", "get", "uuid"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    return lines[1].strip()
            else:  # Unix-like systems
                if os.path.exists("/etc/machine-id"):
                    with open("/etc/machine-id", "r") as f:
                        return f.read().strip()
                elif os.path.exists("/var/lib/dbus/machine-id"):
                    with open("/var/lib/dbus/machine-id", "r") as f:
                        return f.read().strip()
        except Exception:
            pass

        # Fallback to hostname
        return (
            os.uname().nodename
            if hasattr(os, "uname")
            else os.environ.get("COMPUTERNAME", "unknown")
        )

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string using Fernet symmetric encryption.
        Args:
            data: The plaintext string to encrypt.
        Returns:
            str: The encrypted data as a base64 string.
        """
        if not data:
            return ""

        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")

    def decrypt(self, data: str) -> str:
        """
        Decrypt a string that was encrypted with Fernet.
        Args:
            data: The encrypted string (base64 encoded).
        Returns:
            str: The decrypted plaintext string.
        """
        if not data:
            return ""

        try:
            # Decode from base64 first
            encrypted_bytes = base64.urlsafe_b64decode(data.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except InvalidToken:
            self.logger.error("Decryption failed: Invalid token")
            raise ValueError("Invalid encrypted data")
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")

    def save_token_to_settings(self, token: str, settings_repo) -> None:
        """
        Save the authentication token to the settings database.
        Args:
            token: The authentication token to save.
            settings_repo: The settings repository instance.
        """
        try:
            encrypted_token = self.encrypt(token)
            settings = settings_repo.get_settings()
            if settings:
                settings.auth_token = encrypted_token
                settings.save()
                self.logger.debug("Authentication token saved to database")
            else:
                self.logger.warning("No settings found to save token")
        except Exception as e:
            self.logger.error(f"Failed to save token: {e}")
            raise ValueError("Failed to save authentication token")
