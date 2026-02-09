"""
Encryption utilities for sensitive data (Plaid access tokens, etc.)
Uses AES-256-GCM for authenticated encryption with per-value random salt
"""

import os
import base64
import logging
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Encryption key from environment variable
# In production, use Azure Key Vault instead
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Version prefix for encrypted data format
# v1: nonce (12 bytes) + ciphertext
# v2: salt (16 bytes) + nonce (12 bytes) + ciphertext (with per-value random salt)
ENCRYPTION_VERSION = "v2"


class EncryptionError(Exception):
    """Custom exception for encryption errors"""
    pass


class EncryptionService:
    """
    Handles encryption and decryption of sensitive data using AES-256-GCM.

    Security features:
    - Per-value random salt for key derivation (prevents rainbow table attacks)
    - Random nonce for each encryption (prevents IV reuse)
    - Authenticated encryption (detects tampering)
    - PBKDF2 with 100k iterations for key stretching
    """

    def __init__(self):
        self._base_key = None
        self._initialized = False

    def _initialize(self):
        """Initialize the encryption service with the base key"""
        if self._initialized:
            return

        if not ENCRYPTION_KEY:
            logger.error("ENCRYPTION_KEY not set - this is required for production")
            raise EncryptionError(
                "ENCRYPTION_KEY environment variable is not set. "
                "Encryption is required for storing sensitive data like Plaid access tokens."
            )

        self._base_key = ENCRYPTION_KEY.encode()
        self._initialized = True
        logger.info("Encryption service initialized successfully")

    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derive a 256-bit encryption key from the base key and salt.

        Args:
            salt: Random 16-byte salt unique to each encrypted value

        Returns:
            32-byte derived key for AES-256
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(self._base_key)

    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt a string using AES-256-GCM with per-value random salt.

        Format: enc:v2:<base64(salt + nonce + ciphertext)>

        Args:
            plaintext: The string to encrypt

        Returns:
            Encrypted string with version prefix, or None if input is empty
        """
        self._initialize()

        if not plaintext:
            return plaintext

        try:
            # Generate random 16-byte salt for this specific value
            salt = os.urandom(16)

            # Derive key from base key + random salt
            derived_key = self._derive_key(salt)
            aesgcm = AESGCM(derived_key)

            # Generate a random 12-byte nonce (recommended for GCM)
            nonce = os.urandom(12)

            # Encrypt the data
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

            # Combine salt + nonce + ciphertext and base64 encode
            # Format: salt (16 bytes) + nonce (12 bytes) + ciphertext (variable)
            encrypted_data = base64.b64encode(salt + nonce + ciphertext).decode('utf-8')

            # Prefix with version identifier
            return f"enc:{ENCRYPTION_VERSION}:{encrypted_data}"

        except Exception as e:
            logger.exception("Encryption failed")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")

    def decrypt(self, encrypted_text: str) -> Optional[str]:
        """
        Decrypt a string encrypted with AES-256-GCM.

        Supports both v1 (legacy fixed salt) and v2 (per-value salt) formats.

        Args:
            encrypted_text: Encrypted string with 'enc:' prefix

        Returns:
            Decrypted plaintext string
        """
        self._initialize()

        if not encrypted_text:
            return encrypted_text

        # Check if the value is encrypted (has 'enc:' prefix)
        if not encrypted_text.startswith("enc:"):
            logger.warning(
                "SECURITY WARNING: Unencrypted sensitive data found in database. "
                "This data should be re-encrypted."
            )
            return encrypted_text

        try:
            # Parse the encrypted text format
            parts = encrypted_text.split(":", 2)

            if len(parts) == 2:
                # Legacy v1 format: enc:<base64_data>
                return self._decrypt_v1(parts[1])
            elif len(parts) == 3 and parts[1] == "v2":
                # New v2 format: enc:v2:<base64_data>
                return self._decrypt_v2(parts[2])
            else:
                # Unknown format, try v1
                return self._decrypt_v1(parts[1] if len(parts) > 1 else "")

        except Exception as e:
            logger.exception("Decryption failed")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")

    def _decrypt_v1(self, encrypted_data: str) -> str:
        """
        Decrypt legacy v1 format (fixed salt).

        This maintains backwards compatibility with existing encrypted data.
        """
        # For v1, use a fixed salt (legacy behavior)
        legacy_salt = os.getenv("ENCRYPTION_SALT", "FamilyWealthManagement2024").encode()

        # Decode from base64
        data = base64.b64decode(encrypted_data)

        # Extract nonce (first 12 bytes) and ciphertext
        nonce = data[:12]
        ciphertext = data[12:]

        # Derive key using legacy fixed salt
        derived_key = self._derive_key(legacy_salt)
        aesgcm = AESGCM(derived_key)

        # Decrypt
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')

    def _decrypt_v2(self, encrypted_data: str) -> str:
        """
        Decrypt v2 format (per-value random salt).
        """
        # Decode from base64
        data = base64.b64decode(encrypted_data)

        # Extract salt (first 16 bytes), nonce (next 12 bytes), and ciphertext
        salt = data[:16]
        nonce = data[16:28]
        ciphertext = data[28:]

        # Derive key using the stored salt
        derived_key = self._derive_key(salt)
        aesgcm = AESGCM(derived_key)

        # Decrypt
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted (has 'enc:' prefix)"""
        return value is not None and value.startswith("enc:")

    def needs_reencryption(self, value: str) -> bool:
        """Check if a value uses legacy encryption and should be re-encrypted"""
        if not value or not value.startswith("enc:"):
            return True  # Unencrypted data needs encryption
        return not value.startswith(f"enc:{ENCRYPTION_VERSION}:")


# Lazy-loaded encryption service instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """Get or create the encryption service (lazy initialization)"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions
def encrypt_sensitive_data(plaintext: str) -> Optional[str]:
    """Encrypt sensitive data"""
    return get_encryption_service().encrypt(plaintext)


def decrypt_sensitive_data(encrypted_text: str) -> Optional[str]:
    """Decrypt sensitive data"""
    return get_encryption_service().decrypt(encrypted_text)
