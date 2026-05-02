"""OIDC authentication against Keycloak (realm 'mees').

Server-side authorization-code flow with PKCE. The authenticated identity is
stashed in a signed cookie session (Starlette SessionMiddleware) and authorised
by realm-role membership. This is the household's first OIDC-secured app —
the pattern landed here is intended to be extracted into mees-shared-py once
proven.
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from config.settings import settings

log = logging.getLogger(__name__)


@dataclass
class CurrentUser:
    sub: str
    email: str
    username: str
    roles: list[str]


_oauth = OAuth()
_oauth.register(
    name="keycloak",
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    server_metadata_url=f"{settings.oidc_issuer}/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile email"},
)


def _decode_jwt_payload(jwt_str: str) -> dict:
    """Decode a JWT's payload without signature verification.

    Used only on tokens we *just* received over an authenticated TLS channel
    from Keycloak via the OIDC code-exchange — the signature was checked by
    authlib during the exchange. We just need the payload to read claims.
    """
    try:
        _, payload_b64, _ = jwt_str.split(".")
        # JWT base64url, no padding
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        log.exception("Failed to decode JWT payload")
        return {}


def _extract_user(token: dict) -> CurrentUser:
    """Build a CurrentUser from the OIDC token bundle.

    Sub / email / username come from userinfo (cleanest source). Roles come
    from the access_token because Keycloak doesn't put `realm_access.roles`
    in userinfo or the id_token by default.
    """
    userinfo = token.get("userinfo") or {}
    access_claims = _decode_jwt_payload(token.get("access_token", "")) if token.get("access_token") else {}

    realm_access = access_claims.get("realm_access") or {}
    roles = list(realm_access.get("roles") or [])

    return CurrentUser(
        sub=userinfo.get("sub") or access_claims.get("sub", ""),
        email=(userinfo.get("email") or access_claims.get("email") or "").lower(),
        username=userinfo.get("preferred_username") or access_claims.get("preferred_username", ""),
        roles=roles,
    )


def require_admin(request: Request) -> CurrentUser:
    """FastAPI dependency: 401 if no session, 403 if missing the required role."""
    user_data = request.session.get("user")
    if not user_data:
        raise HTTPException(401, "Not authenticated")
    user = CurrentUser(**user_data)
    if settings.oidc_required_role not in user.roles:
        raise HTTPException(
            403,
            f"User {user.email or user.username!r} lacks required role "
            f"{settings.oidc_required_role!r}",
        )
    return user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request, next: str = "/"):
    """Kick off the OIDC code flow."""
    request.session["next"] = next
    return await _oauth.keycloak.authorize_redirect(request, settings.oidc_redirect_uri)


@router.get("/callback")
async def callback(request: Request):
    """Exchange the auth code for tokens, validate, store user in session."""
    try:
        token = await _oauth.keycloak.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(401, f"OAuth error: {e}")
    user = _extract_user(token)
    if settings.oidc_required_role not in user.roles:
        log.warning(
            "OAuth callback denied — user %r (sub=%s) lacks role %r; roles=%s",
            user.email or user.username, user.sub, settings.oidc_required_role, user.roles,
        )
        raise HTTPException(
            403,
            f"User {user.email or user.username!r} lacks required role "
            f"{settings.oidc_required_role!r}",
        )
    request.session["user"] = {
        "sub": user.sub,
        "email": user.email,
        "username": user.username,
        "roles": user.roles,
    }
    next_url = request.session.pop("next", "/")
    return RedirectResponse(next_url)


@router.get("/logout")
async def logout(request: Request):
    """Clear session + redirect to KC end-session for full logout."""
    request.session.clear()
    end_session = (
        f"{settings.oidc_issuer}/protocol/openid-connect/logout"
        f"?post_logout_redirect_uri=https://mcp-admin.mees.st/"
        f"&client_id={settings.oidc_client_id}"
    )
    return RedirectResponse(end_session)


@router.get("/me")
async def me(user: CurrentUser = Depends(require_admin)):
    """Current user, for the UI to render the header."""
    return {"sub": user.sub, "email": user.email, "username": user.username, "roles": user.roles}
