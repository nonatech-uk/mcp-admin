"""Read-only audit-log feed."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin
from src.api.models import AuditEntryOut

router = APIRouter()


def _row_to_out(row) -> AuditEntryOut:
    return AuditEntryOut(
        id=row[0],
        actor_email=row[1],
        action=row[2],
        target_type=row[3],
        target_id=row[4],
        target_name=row[5],
        before=row[6],
        after=row[7],
        ts=row[8],
    )


@router.get("/audit", response_model=list[AuditEntryOut])
def list_audit(
    limit: int = 100,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    limit = max(1, min(limit, 500))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, actor_email, action, target_type, target_id, target_name,
               before, after, ts
          FROM audit_log
         ORDER BY ts DESC
         LIMIT %s
        """,
        (limit,),
    )
    return [_row_to_out(r) for r in cur.fetchall()]
