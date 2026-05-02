"""Read-only OAuth-policy listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin
from src.api.models import OAuthPolicyOut

router = APIRouter()


def _row_to_out(row) -> OAuthPolicyOut:
    return OAuthPolicyOut(
        id=row[0],
        name=row[1],
        oauth_sub=list(row[2] or []),
        oauth_email=list(row[3] or []),
        oauth_username=list(row[4] or []),
        tools_glob=list(row[5] or []),
        ip_allowlist=[str(c) for c in (row[6] or [])],
        created_at=row[7],
        created_by=row[8],
        revoked_at=row[9],
    )


@router.get("/oauth_policies", response_model=list[OAuthPolicyOut])
def list_oauth_policies(
    include_revoked: bool = False,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    where = "" if include_revoked else "WHERE revoked_at IS NULL"
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, name, oauth_sub, oauth_email, oauth_username, tools_glob,
               ip_allowlist, created_at, created_by, revoked_at
          FROM oauth_policies
          {where}
         ORDER BY created_at DESC
        """,
    )
    return [_row_to_out(r) for r in cur.fetchall()]
