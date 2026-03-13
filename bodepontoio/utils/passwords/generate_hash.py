import hashlib
import hmac
import os
from typing import Tuple


def _pbkdf2_generate(
    password: str, iterations: int = 200_000, salt_bytes: int = 16, dklen: int = 32
) -> Tuple[bytes, bytes]:
    salt = os.urandom(salt_bytes)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=dklen)
    return salt, dk


def hash_password_pbkdf2(password: str, iterations: int = 200_000) -> str:
    """
    Retorna string formatada: pbkdf2$<iterations>$<salt_hex>$<hash_hex>
    """
    if not isinstance(password, str):
        raise TypeError("password deve ser uma string")
    salt, dk = _pbkdf2_generate(password, iterations=iterations)
    return f"pbkdf2${iterations}${salt.hex()}${dk.hex()}"


def verify_password_pbkdf2(stored: str, password: str) -> bool:
    """
    Verifica string formatada criada por hash_password_pbkdf2.
    Usa comparação time-constant (hmac.compare_digest).
    """
    try:
        parts = stored.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError, IndexError):
        return False
