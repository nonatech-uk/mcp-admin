from pathlib import Path

from mees_shared.settings import BaseAppSettings


class Settings(BaseAppSettings):
    db_name: str = "mcp_admin"
    db_user: str = "mcp_admin"
    db_sslmode: str = "prefer"
    api_port: int = 8804
    db_pool_max: int = 5

    cors_origins: list[str] = [
        "https://mcp-admin.mees.st",
        "http://localhost:5173",
    ]

    # OIDC client (Keycloak realm 'mees')
    oidc_issuer: str = "https://kc.mees.st/realms/mees"
    oidc_client_id: str = "mcp-admin"
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "https://mcp-admin.mees.st/auth/callback"
    oidc_required_role: str = "mcp-admin"

    # Cookie session signing key
    session_secret: str = ""

    # Pepper applied when hashing tokens / unlock keys (argon2)
    token_pepper: str = ""

    # Path to the live tokens.yaml — used by the seed script only.
    seed_tokens_yaml: str = "/zfs/Apps/AppData/mcp-gateway/tokens.yaml"

    # Gateway reload signaling. URL is the gateway's /admin/reload endpoint
    # reachable on the podman-frontend network; the bearer is shared with the
    # gateway (podman secret mcp_reload_token).
    gateway_reload_url: str = "http://mcp-gateway:8080/admin/reload"
    gateway_reload_token: str = ""

    model_config = {
        "env_file": str(Path(__file__).resolve().parent / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
