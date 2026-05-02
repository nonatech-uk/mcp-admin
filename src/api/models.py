"""Pydantic response models. Read-only in Phase 1; CRUD models added in Phase 2."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


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


class UnlockProfileOut(BaseModel):
    id: UUID
    name: str
    key_preview: str
    tools_glob: list[str]
    created_at: datetime
    created_by: str
    revoked_at: datetime | None


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
