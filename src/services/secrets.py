"""Secret generation for new bearer tokens / unlock-profile keys."""

from __future__ import annotations

import secrets


def new_bearer() -> str:
    """64 hex chars (32 random bytes)."""
    return secrets.token_hex(32)


def new_unlock_key() -> str:
    """32 hex chars (16 random bytes) — shorter, paste-friendlier than bearers."""
    return secrets.token_hex(16)
