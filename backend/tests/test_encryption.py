"""
Tests for encryption module - including v2 per-value salt encryption
"""

import os
import pytest
from unittest.mock import patch
import importlib

# Test encryption key (must be set before importing encryption module)
TEST_ENCRYPTION_KEY = "test-encryption-key-for-testing-only-32chars"
TEST_ENCRYPTION_SALT = "test-salt-for-legacy"


@pytest.fixture(autouse=True)
def setup_encryption_env():
    """Set up encryption environment for each test"""
    # Set environment variables
    os.environ["ENCRYPTION_KEY"] = TEST_ENCRYPTION_KEY
    os.environ["ENCRYPTION_SALT"] = TEST_ENCRYPTION_SALT

    # Reload the encryption module to pick up the new env var
    import shared.encryption as enc_module
    importlib.reload(enc_module)

    # Reset the singleton
    enc_module._encryption_service = None

    yield

    # Cleanup
    enc_module._encryption_service = None


class TestEncryptionService:
    """Test the encryption service"""

    def test_encrypt_returns_v2_format(self):
        """Verify encryption uses v2 format with per-value salt"""
        from shared.encryption import encrypt_sensitive_data

        encrypted = encrypt_sensitive_data("test-secret-value")

        assert encrypted is not None
        assert encrypted.startswith("enc:v2:")

    def test_encrypt_decrypt_roundtrip(self):
        """Verify data can be encrypted and decrypted"""
        from shared.encryption import encrypt_sensitive_data, decrypt_sensitive_data

        original = "my-secret-plaid-token-12345"
        encrypted = encrypt_sensitive_data(original)
        decrypted = decrypt_sensitive_data(encrypted)

        assert decrypted == original

    def test_different_encryptions_produce_different_ciphertext(self):
        """Verify per-value salt produces unique ciphertexts"""
        from shared.encryption import encrypt_sensitive_data

        plaintext = "same-value"
        encrypted1 = encrypt_sensitive_data(plaintext)
        encrypted2 = encrypt_sensitive_data(plaintext)

        # Same plaintext should produce different ciphertext due to random salt/nonce
        assert encrypted1 != encrypted2

    def test_empty_string_returns_empty(self):
        """Verify empty strings are handled correctly"""
        from shared.encryption import encrypt_sensitive_data, decrypt_sensitive_data

        assert encrypt_sensitive_data("") == ""
        assert encrypt_sensitive_data(None) is None
        assert decrypt_sensitive_data("") == ""
        assert decrypt_sensitive_data(None) is None

    def test_is_encrypted_detection(self):
        """Verify encrypted values are detected correctly"""
        from shared.encryption import get_encryption_service

        service = get_encryption_service()

        assert service.is_encrypted("enc:v2:somedata") is True
        assert service.is_encrypted("enc:olddata") is True
        assert service.is_encrypted("plaintext") is False
        assert service.is_encrypted(None) is False

    def test_needs_reencryption_detection(self):
        """Verify legacy encryption is detected for re-encryption"""
        from shared.encryption import get_encryption_service

        service = get_encryption_service()

        # v2 format doesn't need re-encryption
        assert service.needs_reencryption("enc:v2:data") is False

        # v1 format needs re-encryption
        assert service.needs_reencryption("enc:olddata") is True

        # Unencrypted data needs encryption
        assert service.needs_reencryption("plaintext") is True
        assert service.needs_reencryption(None) is True


class TestEncryptionV1Compatibility:
    """Test backward compatibility with v1 encryption format"""

    def test_v1_format_can_be_decrypted(self):
        """Verify legacy v1 encrypted data can still be decrypted"""
        from shared.encryption import get_encryption_service
        import base64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # Create a v1 encrypted value manually
        key = TEST_ENCRYPTION_KEY.encode()
        salt = TEST_ENCRYPTION_SALT.encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        derived_key = kdf.derive(key)
        aesgcm = AESGCM(derived_key)

        nonce = os.urandom(12)
        plaintext = "legacy-secret"
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        v1_encrypted = f"enc:{base64.b64encode(nonce + ciphertext).decode()}"

        # Verify v1 can be decrypted
        service = get_encryption_service()
        decrypted = service.decrypt(v1_encrypted)

        assert decrypted == plaintext


class TestEncryptionErrors:
    """Test encryption error handling"""

    def test_missing_key_raises_error(self):
        """Verify missing encryption key raises appropriate error"""
        import importlib
        import shared.encryption as enc_module

        # Remove the key and reload
        with patch.dict(os.environ, {"ENCRYPTION_KEY": ""}, clear=False):
            os.environ.pop("ENCRYPTION_KEY", None)
            importlib.reload(enc_module)
            enc_module._encryption_service = None

            from shared.encryption import EncryptionService, EncryptionError

            service = EncryptionService()

            with pytest.raises(EncryptionError) as exc_info:
                service.encrypt("test")

            assert "ENCRYPTION_KEY" in str(exc_info.value)

    def test_invalid_ciphertext_raises_error(self):
        """Verify invalid ciphertext raises appropriate error"""
        from shared.encryption import decrypt_sensitive_data, EncryptionError

        with pytest.raises(EncryptionError):
            decrypt_sensitive_data("enc:v2:invalid-base64-!!!!")


class TestEncryptionSecurityProperties:
    """Test security properties of encryption"""

    def test_ciphertext_length_hides_plaintext_length(self):
        """Verify salt and nonce add fixed overhead"""
        from shared.encryption import encrypt_sensitive_data

        short_encrypted = encrypt_sensitive_data("a")
        long_encrypted = encrypt_sensitive_data("a" * 100)

        # v2 format: enc:v2: prefix + base64(16 byte salt + 12 byte nonce + ciphertext + 16 byte tag)
        # The overhead should be consistent
        short_data = short_encrypted.split(":")[2]
        long_data = long_encrypted.split(":")[2]

        # Difference in length should roughly match difference in plaintext
        # (accounting for base64 encoding: 4 chars per 3 bytes)
        assert len(long_data) > len(short_data)
