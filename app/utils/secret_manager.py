import os
import base64
import logging

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_FERNET = True
except Exception:
    Fernet = None
    InvalidToken = Exception
    _HAS_FERNET = False

_logger = logging.getLogger(__name__)


def _get_key_from_env():
    # Prefer BOT_SECRETS_KEY, fall back to SECRETS_KEY
    key = os.getenv('BOT_SECRETS_KEY') or os.getenv('SECRETS_KEY')
    return key


def get_fernet():
    """Return a Fernet instance if a valid key is provided, else None.

    The key must be a URL-safe base64-encoded 32-byte value (the output of
    Fernet.generate_key()). If no key is provided, this module becomes a noop
    (encrypt/decrypt will return plaintext) to avoid breaking development flows.
    """
    if not _HAS_FERNET:
        _logger.warning("cryptography.fernet not installed; secrets will not be encrypted")
        return None

    key = _get_key_from_env()
    if not key:
        _logger.warning("No BOT_SECRETS_KEY provided; secrets will not be encrypted")
        return None

    try:
        # Ensure key is bytes
        if isinstance(key, str):
            key_bytes = key.encode()
        else:
            key_bytes = key

        # Validate by creating a Fernet instance
        return Fernet(key_bytes)
    except Exception as e:
        _logger.error(f"Invalid BOT_SECRETS_KEY provided: {e}")
        return None


def encrypt_secret(plaintext: str) -> str:
    """Encrypt plaintext using the configured Fernet key.

    If no key is configured, returns the plaintext unchanged.
    """
    if plaintext is None:
        return None

    f = get_fernet()
    if not f:
        return plaintext

    token = f.encrypt(plaintext.encode())
    return token.decode()


def decrypt_secret(token: str) -> str:
    """Decrypt token using the configured Fernet key.

    If no key is configured, returns the token unchanged.
    If decryption fails, returns the original token and logs a warning.
    """
    if token is None:
        return None

    f = get_fernet()
    if not f:
        return token

    try:
        plain = f.decrypt(token.encode())
        return plain.decode()
    except InvalidToken:
        _logger.warning("Failed to decrypt secret; returning raw token")
        return token
    except Exception as e:
        _logger.error(f"Error decrypting secret: {e}")
        return token
