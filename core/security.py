# core/security.py
import base64
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config import Singleton


class SecurityManager(Singleton):
    """
    Singleton class for managing encryption and decryption of sensitive data.
    Uses Fernet symmetric encryption with a key derived from a fixed password.
    """

    def __init__(self):
        """Initialize the security manager with a generated encryption key."""
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.logger = logging.getLogger(__name__)
        self.key: bytes = self._generate_key()
        self.cipher: Fernet = Fernet(self.key)
        self.logger.info("SecurityManager initialized")

    def _generate_key(self) -> bytes:
        """
        Generate a Fernet key using PBKDF2HMAC from a fixed password and salt.
        Returns:
            bytes: Base64-encoded encryption key.
        """
        password = b"primesync_app_secret"
        salt = b"fixed_salt"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.logger.debug("Encryption key generated")
        return key

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string using Fernet encryption.
        Args:
            data: The plaintext string to encrypt.
        Returns:
            str: The encrypted string (base64 encoded).
        Raises:
            Exception: If encryption fails.
        """
        try:
            encrypted = self.cipher.encrypt(data.encode())
            self.logger.debug("Data encrypted successfully")
            return encrypted.decode()
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a Fernet-encrypted string.
        Args:
            encrypted_data: The encrypted string (base64 encoded).
        Returns:
            str: The decrypted plaintext string.
        Raises:
            Exception: If decryption fails.
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            self.logger.debug("Data decrypted successfully")
            return decrypted.decode()
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            raise
