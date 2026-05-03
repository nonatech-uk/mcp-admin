"""Static-token CRUD routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin
from src.api.models import (
    StaticTokenCreate,
    StaticTokenOut,
    StaticTokenUpdate,
    StaticTokenWithCleartext,
)
from src.services.audit import write_audit
from src.services.crypto import hash_secret, preview
from src.services.gateway_reload import signal_reload
from src.services.secrets import new_bearer

router = APIRouter()


def _row_to_out(row) -> StaticTokenOut:
    return StaticTokenOut(
        id=row[0],
        name=row[1],
        token_preview=row[2],
        tools_glob=list(row[3] or []),
        ip_allowlist=[str(c) for c in (row[4] or [])],
        host_allowlist=list(row[5] or []),
        created_at=row[6],
        created_by=row[7],
        last_used_at=row[8],
        last_used_ip=str(row[9]) if row[9] else None,
        revoked_at=row[10],
    )


def _select(cur, where: str = "", *params) -> list:
    cur.execute(
        f"""
        SELECT id, name, token_preview, tools_glob, ip_allowlist, host_allowlist,
               created_at, created_by, last_used_at, last_used_ip, revoked_at
          FROM static_tokens
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
    out = _row_to_out(row)
    return out.model_dump(mode="json")


# -- Read --


@router.get("/tokens", response_model=list[StaticTokenOut])
def list_tokens(
    include_revoked: bool = False,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    rows = _select(cur, "" if include_revoked else "WHERE revoked_at IS NULL")
    return [_row_to_out(r) for r in rows]


# -- Create --


@router.post("/tokens", response_model=StaticTokenWithCleartext, status_code=201)
async def create_token(
    body: StaticTokenCreate,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cleartext = new_bearer()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO static_tokens
              (name, token_hash, token_preview, tools_glob, ip_allowlist, host_allowlist, created_by)
            VALUES (%s, %s, %s, %s, %s::inet[], %s, %s)
            RETURNING id, name, token_preview, tools_glob, ip_allowlist, host_allowlist,
                      created_at, created_by, last_used_at, last_used_ip, revoked_at
            """,
            (
                body.name,
                hash_secret(cleartext),
                preview(cleartext),
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
            target_type="static_token",
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
    return StaticTokenWithCleartext(**out.model_dump(), token=cleartext)


# -- Update --


@router.patch("/tokens/{id_}", response_model=StaticTokenOut)
async def update_token(
    id_: UUID,
    body: StaticTokenUpdate,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Token not found")
    if before_row[10] is not None:
        raise HTTPException(409, "Token is revoked")

    sets: list[str] = []
    params: list = []
    if body.tools_glob is not None:
        sets.append("tools_glob = %s")
        params.append(body.tools_glob)
    if body.ip_allowlist is not None:
        sets.append("ip_allowlist = %s::inet[]")
        params.append(body.ip_allowlist)
    if body.host_allowlist is not None:
        sets.append("host_allowlist = %s")
        params.append(body.host_allowlist)
    if not sets:
        return _row_to_out(before_row)
    params.append(str(id_))

    try:
        cur.execute(
            f"UPDATE static_tokens SET {', '.join(sets)} WHERE id = %s",
            params,
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="update",
            target_type="static_token",
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


# -- Revoke --


@router.delete("/tokens/{id_}", response_model=StaticTokenOut)
async def revoke_token(
    id_: UUID,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Token not found")
    if before_row[10] is not None:
        raise HTTPException(409, "Already revoked")

    try:
        cur.execute(
            "UPDATE static_tokens SET revoked_at = now() WHERE id = %s",
            (str(id_),),
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="revoke",
            target_type="static_token",
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


# -- Rotate --


@router.post("/tokens/{id_}/rotate", response_model=StaticTokenWithCleartext)
async def rotate_token(
    id_: UUID,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Token not found")
    if before_row[10] is not None:
        raise HTTPException(409, "Token is revoked — create a new one instead")

    cleartext = new_bearer()
    try:
        cur.execute(
            "UPDATE static_tokens SET token_hash = %s, token_preview = %s WHERE id = %s",
            (hash_secret(cleartext), preview(cleartext), str(id_)),
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="rotate",
            target_type="static_token",
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
    out = _row_to_out(after_row)
    return StaticTokenWithCleartext(**out.model_dump(), token=cleartext)
