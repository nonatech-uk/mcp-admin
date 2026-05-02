"""Read-only unlock-profile listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin
from src.api.models import UnlockProfileOut

router = APIRouter()


def _row_to_out(row) -> UnlockProfileOut:
    return UnlockProfileOut(
        id=row[0],
        name=row[1],
        key_preview=row[2],
        tools_glob=list(row[3] or []),
        created_at=row[4],
        created_by=row[5],
        revoked_at=row[6],
    )


@router.get("/unlock_profiles", response_model=list[UnlockProfileOut])
def list_unlock_profiles(
    include_revoked: bool = False,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    where = "" if include_revoked else "WHERE revoked_at IS NULL"
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, name, key_preview, tools_glob,
               created_at, created_by, revoked_at
          FROM unlock_profiles
          {where}
         ORDER BY created_at DESC
        """,
    )
    return [_row_to_out(r) for r in cur.fetchall()]
