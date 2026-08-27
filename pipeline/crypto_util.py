"""AES-GCM + PBKDF2 encryption for sensitive sections, matching the browser-side
decrypt in docs/app.js exactly (same KDF algorithm, hash, iteration count, and
field names) so a value encrypted here decrypts there with no extra glue.

Wire format for one encrypted value (JSON-serializable dict):
    {
        "encrypted": true,
        "ciphertext": "<base64>",   # AES-GCM output (includes the auth tag)
        "iv": "<base64>",           # 12 random bytes
        "salt": "<base64>",         # 16 random bytes, PBKDF2 salt
    }

KDF: PBKDF2-HMAC-SHA256, 100_000 iterations, 32-byte (256-bit) key.
Cipher: AES-256-GCM, 12-byte IV, no additional authenticated data.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 100_000
KEY_LEN_BYTES = 32
IV_LEN_BYTES = 12
SALT_LEN_BYTES = 16


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN_BYTES,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_value(value: Any, passphrase: str) -> dict:
    """Encrypt any JSON-serializable value. Returns the wire-format dict above."""
    plaintext = json.dumps(value, ensure_ascii=False).encode("utf-8")
    salt = os.urandom(SALT_LEN_BYTES)
    iv = os.urandom(IV_LEN_BYTES)
    key = _derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(iv, plaintext, None)
    return {
        "encrypted": True,
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "salt": base64.b64encode(salt).decode("ascii"),
    }


def decrypt_value(payload: dict, passphrase: str) -> Any:
    """Round-trip check helper (the browser does the real decryption at read time)."""
    salt = base64.b64decode(payload["salt"])
    iv = base64.b64decode(payload["iv"])
    ciphertext = base64.b64decode(payload["ciphertext"])
    key = _derive_key(passphrase, salt)
    plaintext = AESGCM(key).decrypt(iv, ciphertext, None)
    return json.loads(plaintext.decode("utf-8"))
