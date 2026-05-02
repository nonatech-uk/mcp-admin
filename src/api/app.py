"""mcp-admin API — FastAPI application."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import psycopg2
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from config.settings import settings
from src.api.auth_oidc import router as auth_router
from src.api.deps import close_pool, init_pool
from src.api.routers import access_log, audit, gateway_proxy, oauth_policies, tokens, unlock_profiles

STATIC_DIR = Path(_project_root) / "static"

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="mcp-admin",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for local dev (Vite proxy uses /api anyway, but harmless in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server-side session for OIDC. https_only=True relies on Traefik for TLS.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=True,
    max_age=8 * 60 * 60,  # 8h
)

# Auth + read-only routers
app.include_router(auth_router)
app.include_router(tokens.router, prefix="/api/v1", tags=["tokens"])
app.include_router(oauth_policies.router, prefix="/api/v1", tags=["oauth_policies"])
app.include_router(unlock_profiles.router, prefix="/api/v1", tags=["unlock_profiles"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
app.include_router(gateway_proxy.router, prefix="/api/v1", tags=["gateway"])
app.include_router(access_log.router, prefix="/api/v1", tags=["access_log"])


@app.exception_handler(psycopg2.IntegrityError)
async def _pg_integrity_handler(request: Request, exc: psycopg2.IntegrityError):
    """Translate Postgres constraint violations into clean 409s.

    Most often this fires on a duplicate active-name (e.g. trying to create a
    second active static_token with the same name as an existing un-revoked
    one). Without this handler, FastAPI surfaces the raw stack as 500.
    """
    msg = str(exc).strip().split("\n")[0]
    return JSONResponse({"detail": f"Integrity constraint: {msg}"}, status_code=409)


@app.get("/health")
def health():
    return {"status": "ok"}


if STATIC_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="static-assets",
    )

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Server-side auth gate: anyone hitting the SPA without a session
        # is bounced to KC before any HTML/JS loads — avoids the brief flash
        # of the app shell pre-redirect.
        if not request.session.get("user"):
            return RedirectResponse(
                f"/auth/login?next={request.url.path}", status_code=302,
            )
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
