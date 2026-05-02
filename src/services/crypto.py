"""Hash + verify bearer tokens / unlock keys with argon2 + a server-side pepper.

Pepper is sourced from settings.token_pepper (podman secret). The pepper is
prepended to the cleartext before hashing; PG compromise alone doesn't yield
usable bearers without it.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from config.settings import settings

_hasher = PasswordHasher()


def hash_secret(cleartext: str) -> str:
    return _hasher.hash(settings.token_pepper + cleartext)


def verify_secret(cleartext: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, settings.token_pepper + cleartext)
    except VerifyMismatchError:
        return False


def preview(cleartext: str, n: int = 8) -> str:
    return cleartext[:n]
