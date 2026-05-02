"""Audit-log helper. Every mutation in the admin API ends here."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID


def _json_default(o: Any):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, UUID):
        return str(o)
    raise TypeError(f"unserialisable {type(o).__name__}")


def write_audit(
    conn,
    *,
    actor_email: str,
    action: str,
    target_type: str,
    target_id: UUID,
    target_name: str,
    before: dict | None,
    after: dict | None,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audit_log
          (actor_email, action, target_type, target_id, target_name, before, after)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
        """,
        (
            actor_email,
            action,
            target_type,
            str(target_id),
            target_name,
            json.dumps(before, default=_json_default) if before is not None else None,
            json.dumps(after, default=_json_default) if after is not None else None,
        ),
    )
