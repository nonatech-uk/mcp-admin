"""POSTs to the gateway's /admin/reload endpoint after every mutation.

The gateway re-reads its policies from the same Postgres db. If the call
fails (network blip, gateway down), the mutation is *not* rolled back —
the audit log already records what happened — but the API response carries
a `reload_warning` field and the admin UI shows a non-blocking banner.
"""

from __future__ import annotations

import logging

import httpx

from config.settings import settings

log = logging.getLogger(__name__)


async def signal_reload() -> str | None:
    """POST to gateway /admin/reload. Returns None on success, a human-readable
    warning string on failure."""
    if not settings.gateway_reload_url or not settings.gateway_reload_token:
        return None  # not configured — silent no-op (e.g. local dev)
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.post(
                settings.gateway_reload_url,
                headers={"Authorization": f"Bearer {settings.gateway_reload_token}"},
            )
            if r.status_code != 200:
                log.warning("Gateway reload returned %d: %s", r.status_code, r.text[:200])
                return f"gateway reload returned HTTP {r.status_code}"
    except Exception as e:
        log.warning("Gateway reload failed: %s", e)
        return f"gateway reload error: {e}"
    return None
