"""Unlock-profile CRUD routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from mees_shared.db import get_conn

from src.api.auth_oidc import CurrentUser, require_admin
from src.api.models import (
    UnlockProfileCreate,
    UnlockProfileOut,
    UnlockProfileUpdate,
    UnlockProfileWithCleartext,
)
from src.services.audit import write_audit
from src.services.crypto import hash_secret, preview
from src.services.gateway_reload import signal_reload
from src.services.secrets import new_unlock_key

router = APIRouter()


def _row_to_out(row) -> UnlockProfileOut:
    return UnlockProfileOut(
        id=row[0],
        name=row[1],
        key_preview=row[2],
        tools_glob=list(row[3] or []),
        host_allowlist=list(row[4] or []),
        created_at=row[5],
        created_by=row[6],
        revoked_at=row[7],
    )


def _select(cur, where: str = "", *params) -> list:
    cur.execute(
        f"""
        SELECT id, name, key_preview, tools_glob, host_allowlist,
               created_at, created_by, revoked_at
          FROM unlock_profiles
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


@router.get("/unlock_profiles", response_model=list[UnlockProfileOut])
def list_unlock_profiles(
    include_revoked: bool = False,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    rows = _select(cur, "" if include_revoked else "WHERE revoked_at IS NULL")
    return [_row_to_out(r) for r in rows]


@router.post("/unlock_profiles", response_model=UnlockProfileWithCleartext, status_code=201)
async def create_unlock_profile(
    body: UnlockProfileCreate,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cleartext = new_unlock_key()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO unlock_profiles (name, key_hash, key_preview, tools_glob, host_allowlist, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, key_preview, tools_glob, host_allowlist,
                      created_at, created_by, revoked_at
            """,
            (
                body.name,
                hash_secret(cleartext),
                preview(cleartext),
                body.tools_glob,
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
            target_type="unlock_profile",
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
    return UnlockProfileWithCleartext(**out.model_dump(), key=cleartext)


@router.patch("/unlock_profiles/{id_}", response_model=UnlockProfileOut)
async def update_unlock_profile(
    id_: UUID,
    body: UnlockProfileUpdate,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Profile not found")
    if before_row[7] is not None:
        raise HTTPException(409, "Profile is revoked")

    if body.tools_glob is None and body.name is None and body.host_allowlist is None:
        return _row_to_out(before_row)

    if body.name is not None and before_row[1] == "default" and body.name != "default":
        raise HTTPException(409, "Cannot rename the 'default' profile (legacy callers depend on it).")

    sets: list[str] = []
    params: list = []
    if body.name is not None:
        sets.append("name = %s")
        params.append(body.name)
    if body.tools_glob is not None:
        sets.append("tools_glob = %s")
        params.append(body.tools_glob)
    if body.host_allowlist is not None:
        sets.append("host_allowlist = %s")
        params.append(body.host_allowlist)
    params.append(str(id_))

    try:
        cur.execute(
            f"UPDATE unlock_profiles SET {', '.join(sets)} WHERE id = %s",
            params,
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="update",
            target_type="unlock_profile",
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


@router.delete("/unlock_profiles/{id_}", response_model=UnlockProfileOut)
async def revoke_unlock_profile(
    id_: UUID,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Profile not found")
    if before_row[7] is not None:
        raise HTTPException(409, "Already revoked")
    if before_row[1] == "default":
        # Only block if doing so would leave the gateway with no unlock mechanism.
        cur.execute(
            "SELECT count(*) FROM unlock_profiles WHERE revoked_at IS NULL AND id <> %s",
            (str(id_),),
        )
        remaining = cur.fetchone()[0]
        if remaining == 0:
            raise HTTPException(
                409,
                "Cannot revoke 'default' — no other unlock profile exists; the gateway "
                "would have no unlock mechanism. Create at least one other profile first.",
            )

    try:
        cur.execute(
            "UPDATE unlock_profiles SET revoked_at = now() WHERE id = %s",
            (str(id_),),
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="revoke",
            target_type="unlock_profile",
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


@router.post("/unlock_profiles/{id_}/rotate", response_model=UnlockProfileWithCleartext)
async def rotate_unlock_profile(
    id_: UUID,
    user: CurrentUser = Depends(require_admin),
    conn=Depends(get_conn),
):
    cur = conn.cursor()
    before_row = _get_by_id(cur, id_)
    if not before_row:
        raise HTTPException(404, "Profile not found")
    if before_row[7] is not None:
        raise HTTPException(409, "Profile is revoked — create a new one instead")

    cleartext = new_unlock_key()
    try:
        cur.execute(
            "UPDATE unlock_profiles SET key_hash = %s, key_preview = %s WHERE id = %s",
            (hash_secret(cleartext), preview(cleartext), str(id_)),
        )
        after_row = _get_by_id(cur, id_)
        write_audit(
            conn,
            actor_email=user.email or user.username,
            action="rotate",
            target_type="unlock_profile",
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
    return UnlockProfileWithCleartext(**out.model_dump(), key=cleartext)
