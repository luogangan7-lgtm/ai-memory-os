"""API Key encryption/decryption using AES-256-GCM."""
import os, base64, logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MASTER_KEY = os.environ.get("MEMORY_OS_MASTER_KEY", "")
_key_bytes = base64.b64decode(_MASTER_KEY) if _MASTER_KEY else None

if _key_bytes is None:
    logging.getLogger("crypto").warning(
        "MEMORY_OS_MASTER_KEY is not set — provider API keys will be stored in PLAINTEXT. "
        "Set MEMORY_OS_MASTER_KEY to a base64-encoded 32-byte value to enable AES-256-GCM at rest."
    )

def encrypt(plaintext: str) -> str:
    """Encrypt API key, returns base64(nonce + ciphertext)."""
    if not plaintext or not _key_bytes:
        return plaintext
    aesgcm = AESGCM(_key_bytes)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt(encoded: str) -> str:
    """Decrypt API key."""
    if not encoded or not _key_bytes:
        return encoded
    try:
        data = base64.b64decode(encoded)
        nonce, ct = data[:12], data[12:]
        aesgcm = AESGCM(_key_bytes)
        return aesgcm.decrypt(nonce, ct, None).decode()
    except Exception:
        return encoded  # Return as-is if decryption fails (backward compat)

# Aliases for backward compatibility
encrypt_key = encrypt
decrypt_key = decrypt
