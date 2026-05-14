# AI Memory OS — Cryptographic Utilities
import base64
import hashlib
from cryptography.fernet import Fernet
from backend.services.config import settings

def _get_fernet() -> Fernet:
    """Derive a 32-byte Fernet-compatible key securely from the configured jwt_secret."""
    key_hash = hashlib.sha256(settings.jwt_secret.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)

def encrypt_key(plain_text: str) -> str:
    """Encrypt plain text API key into an AES-encrypted cipher string."""
    if not plain_text:
        return ""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()

def decrypt_key(cipher_text: str) -> str:
    """Decrypt AES-encrypted cipher string back into plain text."""
    if not cipher_text:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(cipher_text.encode()).decode()
    except Exception:
        # Graceful fallback: return as-is if string was stored unencrypted
        return cipher_text
