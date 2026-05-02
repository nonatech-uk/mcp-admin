"""Access-log read endpoints. Paginated + filterable."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin

router = APIRouter()


class AccessEntryOut(BaseModel):
    id: int
    ts: datetime
    event: str
    actor_kind: str | None
    actor_name: str | None
    client_ip: str | None
    tool_name: str | None
    profile: str | None
    detail: Any | None


def _row_to_out(row) -> AccessEntryOut:
    return AccessEntryOut(
        id=row[0],
        ts=row[1],
        event=row[2],
        actor_kind=row[3],
        actor_name=row[4],
        client_ip=str(row[5]) if row[5] else None,
        tool_name=row[6],
        profile=row[7],
        detail=row[8],
    )


@router.get("/access_log", response_model=list[AccessEntryOut])
def list_access_log(
    limit: int = Query(200, ge=1, le=2000),
    event: str | None = None,
    actor_name: str | None = None,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    """Paginated access log. Newest first. Optional event / actor filters."""
    where: list[str] = []
    params: list = []
    if event:
        where.append("event = %s")
        params.append(event)
    if actor_name:
        where.append("actor_name = %s")
        params.append(actor_name)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, ts, event, actor_kind, actor_name, client_ip,
               tool_name, profile, detail
          FROM gateway_access_log
          {where_sql}
         ORDER BY ts DESC
         LIMIT %s
        """,
        [*params, limit],
    )
    return [_row_to_out(r) for r in cur.fetchall()]
