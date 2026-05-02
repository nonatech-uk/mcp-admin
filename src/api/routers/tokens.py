"""Read-only static-token listing. Phase 2 will add create/revoke/rotate."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin
from src.api.models import StaticTokenOut

router = APIRouter()


def _row_to_out(row) -> StaticTokenOut:
    return StaticTokenOut(
        id=row[0],
        name=row[1],
        token_preview=row[2],
        tools_glob=list(row[3] or []),
        ip_allowlist=[str(c) for c in (row[4] or [])],
        created_at=row[5],
        created_by=row[6],
        last_used_at=row[7],
        last_used_ip=str(row[8]) if row[8] else None,
        revoked_at=row[9],
    )


@router.get("/tokens", response_model=list[StaticTokenOut])
def list_tokens(
    include_revoked: bool = False,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    where = "" if include_revoked else "WHERE revoked_at IS NULL"
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, name, token_preview, tools_glob, ip_allowlist,
               created_at, created_by, last_used_at, last_used_ip, revoked_at
          FROM static_tokens
          {where}
         ORDER BY created_at DESC
        """,
    )
    return [_row_to_out(r) for r in cur.fetchall()]
