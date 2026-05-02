#!/bin/bash
# Wrapper that runs the one-shot seed script with all the live podman-secret
# values injected as env vars. Run from the NAS host (needs podman socket).
#
# Idempotent — safe to re-run.
set -euo pipefail

show() { podman secret inspect --showsecret "$1" --format '{{.SecretData}}'; }

podman run --rm \
  --network podman-frontend \
  --env-file /zfs/Apps/AppData/mcp-admin/.env \
  -e DB_PASSWORD="$(show mcp_admin_postgres_pw)" \
  -e SESSION_SECRET="$(show mcp_admin_session_secret)" \
  -e TOKEN_PEPPER="$(show mcp_admin_token_pepper)" \
  -e MCP_BEARER_TOKEN_VALUE="$(show mcp_bearer_token)" \
  -e MCP_TOKEN_ALBURY_PARISH_VALUE="$(show mcp_token_albury_parish)" \
  -e MCP_TOKEN_ALBURY_APP_VALUE="$(show mcp_token_albury_app)" \
  -e MCP_GATEWAY_KEY_VALUE="$(show mcp_gateway_key)" \
  -v /zfs/Apps/AppData/mcp-gateway/tokens.yaml:/tmp/tokens.yaml:ro \
  -e MCP_GATEWAY_TOKENS_YAML=/tmp/tokens.yaml \
  localhost/mcp-admin:latest \
  python -m src.services.seed
