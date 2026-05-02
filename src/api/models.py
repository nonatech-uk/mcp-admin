"""Pydantic models for the admin API.

Read-side outputs hide the hashed credential entirely; only `*_preview` is
shown. Cleartext bearers / unlock keys appear *exactly once* in the response
to a create/rotate call (the `*WithCleartext` models) and are never
retrievable again.
"""

from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _validate_cidrs(v: list[str]) -> list[str]:
    for s in v:
        try:
            ipaddress.ip_network(s, strict=False)
        except ValueError as e:
            raise ValueError(f"{s!r} is not a valid CIDR: {e}")
    return v


def _validate_globs(v: list[str]) -> list[str]:
    if not v:
        raise ValueError("tools_glob must contain at least one pattern")
    for p in v:
        if not p or any(c.isspace() for c in p):
            raise ValueError(f"tool pattern {p!r} must be non-empty and contain no whitespace")
    return v


def _validate_name(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("name must not be empty")
    if any(c.isspace() for c in v):
        raise ValueError("name must contain no whitespace")
    return v


# ---------------------------------------------------------------------------
# Static tokens
# ---------------------------------------------------------------------------


class StaticTokenOut(BaseModel):
    id: UUID
    name: str
    token_preview: str
    tools_glob: list[str]
    ip_allowlist: list[str]
    created_at: datetime
    created_by: str
    last_used_at: datetime | None
    last_used_ip: str | None
    revoked_at: datetime | None


class StaticTokenWithCleartext(StaticTokenOut):
    token: str = Field(..., description="Cleartext bearer — shown exactly once.")


class StaticTokenCreate(BaseModel):
    name: str
    tools_glob: list[str]
    ip_allowlist: list[str] = Field(default_factory=list)

    _name = field_validator("name")(_validate_name)
    _globs = field_validator("tools_glob")(_validate_globs)
    _ips = field_validator("ip_allowlist")(_validate_cidrs)


class StaticTokenUpdate(BaseModel):
    tools_glob: list[str] | None = None
    ip_allowlist: list[str] | None = None

    @field_validator("tools_glob")
    @classmethod
    def _v_globs(cls, v: list[str] | None) -> list[str] | None:
        return v if v is None else _validate_globs(v)

    @field_validator("ip_allowlist")
    @classmethod
    def _v_ips(cls, v: list[str] | None) -> list[str] | None:
        return v if v is None else _validate_cidrs(v)


# ---------------------------------------------------------------------------
# OAuth policies
# ---------------------------------------------------------------------------


class OAuthPolicyOut(BaseModel):
    id: UUID
    name: str
    oauth_sub: list[str]
    oauth_email: list[str]
    oauth_username: list[str]
    tools_glob: list[str]
    ip_allowlist: list[str]
    created_at: datetime
    created_by: str
    revoked_at: datetime | None


class OAuthPolicyCreate(BaseModel):
    name: str
    oauth_sub: list[str] = Field(default_factory=list)
    oauth_email: list[str] = Field(default_factory=list)
    oauth_username: list[str] = Field(default_factory=list)
    tools_glob: list[str]
    ip_allowlist: list[str] = Field(default_factory=list)

    _name = field_validator("name")(_validate_name)
    _globs = field_validator("tools_glob")(_validate_globs)
    _ips = field_validator("ip_allowlist")(_validate_cidrs)

    @field_validator("oauth_sub", "oauth_email", "oauth_username")
    @classmethod
    def _at_least_one_matcher(cls, v, info):
        # Per-field check; final cross-field check happens in the model_validator below.
        return v

    def model_post_init(self, _ctx) -> None:
        if not (self.oauth_sub or self.oauth_email or self.oauth_username):
            raise ValueError("policy must declare at least one of oauth_sub / oauth_email / oauth_username")


class OAuthPolicyUpdate(BaseModel):
    oauth_sub: list[str] | None = None
    oauth_email: list[str] | None = None
    oauth_username: list[str] | None = None
    tools_glob: list[str] | None = None
    ip_allowlist: list[str] | None = None

    @field_validator("tools_glob")
    @classmethod
    def _v_globs(cls, v: list[str] | None) -> list[str] | None:
        return v if v is None else _validate_globs(v)

    @field_validator("ip_allowlist")
    @classmethod
    def _v_ips(cls, v: list[str] | None) -> list[str] | None:
        return v if v is None else _validate_cidrs(v)


# ---------------------------------------------------------------------------
# Unlock profiles
# ---------------------------------------------------------------------------


class UnlockProfileOut(BaseModel):
    id: UUID
    name: str
    key_preview: str
    tools_glob: list[str]
    created_at: datetime
    created_by: str
    revoked_at: datetime | None


class UnlockProfileWithCleartext(UnlockProfileOut):
    key: str = Field(..., description="Cleartext key — shown exactly once.")


class UnlockProfileCreate(BaseModel):
    name: str
    tools_glob: list[str]

    _name = field_validator("name")(_validate_name)
    _globs = field_validator("tools_glob")(_validate_globs)


class UnlockProfileUpdate(BaseModel):
    name: str | None = None
    tools_glob: list[str] | None = None

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str | None) -> str | None:
        return v if v is None else _validate_name(v)

    @field_validator("tools_glob")
    @classmethod
    def _v_globs(cls, v: list[str] | None) -> list[str] | None:
        return v if v is None else _validate_globs(v)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


class AuditEntryOut(BaseModel):
    id: int
    actor_email: str
    action: str
    target_type: str
    target_id: UUID
    target_name: str
    before: Any | None
    after: Any | None
    ts: datetime


# ---------------------------------------------------------------------------
# Mutation responses
# ---------------------------------------------------------------------------


class MutationResult(BaseModel):
    """Mirror what the gateway saw after the mutation. Includes a warning
    field if the gateway-reload signal failed."""

    ok: bool = True
    reload_warning: str | None = None
