"""OAuth-policy CRUD routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin
from src.api.models import OAuthPolicyCreate, OAuthPolicyOut, OAuthPolicyUpdate
from src.services.audit import write_audit
from src.services.gateway_reload import signal_reload

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
        host_allowlist=list(row[7] or []),
        created_at=row[8],
        created_by=row[9],
        revoked_at=row[10],
    )


def _select(cur, where: str = "", *params) -> list:
    cur.execute(
        f"""
        SELECT id, name, oauth_sub, oauth_email, oauth_username, tools_glob,
               ip_allowlist, host_allowlist, created_at, created_by, revoked_at
          FROM oauth_policies
          {where}
         ORDER BY created_at DESC
        """,
        params,
    )
    return cur.fetchall()


def _get_by_id(cur, id_: UUID):
    rows = _select(cur, "WHERE id = %s", str(id_))
    return rows[0] if rows else None


def _to_audit(row) -> dict:
    return _row_to_out(row).model_dump(mode="json")


@router.get("/oauth_policies", response_model=list[OAuthPolicyOut])
def list_oauth_policies(
    include_revoked: bool = False,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    rows = _select(cur, "" if include_revoked else "WHERE revoked_at IS NULL")
    return [_row_to_out(r) for r in rows]


@router.post("/oauth_policies", response_model=OAuthPolicyOut, status_code=201)
async def create_oauth_policy(
    body: OAuthPolicyCreate,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO oauth_policies
              (name, oauth_sub, oauth_email, oauth_username, tools_glob, ip_allowlist, host_allowlist, created_by)
            VALUES (%s, %s, %s, %s, %s, %s::inet[], %s, %s)
            RETURNING id, name, oauth_sub, oauth_email, oauth_username, tools_glob,
                      ip_allowlist, host_allowlist, created_at, created_by, revoked_at
            """,
            (
                body.name,
                body.oauth_sub,
                body.oauth_email,
                body.oauth_username,
                body.tools_glob,
                body.ip_allowlist,
                body.host_allowlist,
                user.email or user.username,
            ),
        )
        row = cur.fetchone()
        out = _row_to_out(row)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="create",
            target_type="oauth_policy",
            target_id=out.id,
            target_name=out.name,
            before=None,
            after=_to_audit(row),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    await signal_reload()
    return out


@router.patch("/oauth_policies/{id_}", response_model=OAuthPolicyOut)
async def update_oauth_policy(
    id_: UUID,
    body: OAuthPolicyUpdate,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Policy not found")
    if before_row[10] is not None:
        raise HTTPException(409, "Policy is revoked")

    sets: list[str] = []
    params: list = []
    for col, val in [
        ("oauth_sub", body.oauth_sub),
        ("oauth_email", body.oauth_email),
        ("oauth_username", body.oauth_username),
        ("tools_glob", body.tools_glob),
        ("host_allowlist", body.host_allowlist),
    ]:
        if val is not None:
            sets.append(f"{col} = %s")
            params.append(val)
    if body.ip_allowlist is not None:
        sets.append("ip_allowlist = %s::inet[]")
        params.append(body.ip_allowlist)
    if not sets:
        return _row_to_out(before_row)
    params.append(str(id_))

    try:
        cur.execute(
            f"UPDATE oauth_policies SET {', '.join(sets)} WHERE id = %s",
            params,
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="update",
            target_type="oauth_policy",
            target_id=id_,
            target_name=after_row[1],
            before=_to_audit(before_row),
            after=_to_audit(after_row),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    await signal_reload()
    return _row_to_out(after_row)


@router.delete("/oauth_policies/{id_}", response_model=OAuthPolicyOut)
async def revoke_oauth_policy(
    id_: UUID,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Policy not found")
    if before_row[10] is not None:
        raise HTTPException(409, "Already revoked")

    try:
        cur.execute(
            "UPDATE oauth_policies SET revoked_at = now() WHERE id = %s",
            (str(id_),),
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="revoke",
            target_type="oauth_policy",
            target_id=id_,
            target_name=after_row[1],
            before=_to_audit(before_row),
            after=_to_audit(after_row),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    await signal_reload()
    return _row_to_out(after_row)
