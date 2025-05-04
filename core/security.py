import base64
import logging
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecurityManager:
    """
    Handles encryption and decryption of sensitive data.
    Uses Fernet symmetric encryption with a derived key.
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
        Returns:
            bytes: A derived encryption key.
        """
        try:
            # Create a salt based on machine info
            # This ensures the key is consistent across app restarts
            # but unique to this machine
            hostname = os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'unknown')
            salt = hostname.encode()[:16].ljust(16, b'x')
            
            # Use a fixed password as base - this is not for high security
            # but just to make stored passwords not plaintext
            password = b"PrimeSyncDefaultKey"
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.logger.debug("Encryption key derived successfully")
            return key
        except Exception as e:
            self.logger.error(f"Failed to derive encryption key: {e}")
            # Fall back to a default key if derivation fails
            return Fernet.generate_key()

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
            return encrypted.decode()
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            # Return a special marker if encryption fails
            return f"ENCRYPTION_FAILED"

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
            
        # Handle the error marker
        if data == "ENCRYPTION_FAILED":
            self.logger.warning("Attempted to decrypt data that failed encryption")
            return ""
            
        try:
            decrypted = self.cipher.decrypt(data.encode())
            return decrypted.decode()
        except InvalidToken:
            self.logger.error("Decryption failed: Invalid token")
            return ""
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            return ""

    def save_token_to_settings(self, token: str, settings_repo) -> None:
        """
        Save the authentication token to the settings database.
        
        Args:
            token: The authentication token to store
            settings_repo: Repository for settings
        """
        if not token:
            return
            
        try:
            settings = settings_repo.get_settings()
            if settings:
                encrypted_token = self.encrypt(token)
                settings_repo.model.update(auth_token=encrypted_token).where(
                    settings_repo.model.id == settings.id
                ).execute()
                self.logger.debug("Authentication token saved to database")
        except Exception as e:
            self.logger.error(f"Failed to save authentication token: {e}")

    def get_token_from_settings(self, settings_repo) -> str:
        """
        Get the authentication token from settings database.
        
        Args:
            settings_repo: Repository for settings
            
        Returns:
            str: The decrypted authentication token or empty string if not found
        """
        try:
            settings = settings_repo.get_settings()
            if settings and settings.auth_token:
                return self.decrypt(settings.auth_token)
            return ""
        except Exception as e:
            self.logger.error(f"Failed to get authentication token: {e}")
            return ""