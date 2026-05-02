"""Read-only proxies into the gateway's /admin/* endpoints.

The gateway's tool list and reload status need surfacing in the admin UI;
this router handles the cross-service HTTP call (Bearer + httpx) so the
frontend just hits /api/v1/gateway/*.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException

from config.settings import settings
from src.api.auth_oidc import CurrentUser, require_admin

log = logging.getLogger(__name__)
router = APIRouter()


def _gateway_base() -> str:
    # /admin/reload URL → strip the /reload suffix to get the base.
    url = settings.gateway_reload_url
    if url.endswith("/reload"):
        return url[: -len("/reload")]
    return url.rstrip("/")


@router.get("/gateway/tools")
async def gateway_tools(user: CurrentUser = Depends(require_admin)):
    """Live tool inventory from mcp-gateway. Useful when authoring tools_glob
    patterns to know what tools actually exist."""
    if not settings.gateway_reload_token:
        raise HTTPException(503, "Gateway reload token not configured")
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(
                f"{_gateway_base()}/tools",
                headers={"Authorization": f"Bearer {settings.gateway_reload_token}"},
            )
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        log.warning("Gateway /admin/tools failed: %s", e)
        raise HTTPException(502, f"Gateway unreachable: {e}")
