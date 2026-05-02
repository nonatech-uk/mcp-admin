"""One-shot seed: copy live tokens.yaml + podman secrets into PG.

Idempotent: run as many times as you like, only inserts rows whose `name`
isn't already present. Designed to be invoked once during Phase 1 deploy so
the read-only UI has something to show — Phase 2 makes the gateway authoritative.

Usage (from the host):

  scripts/seed.sh

…which wraps `podman run` with the relevant podman secrets injected as env
vars matching each policy's `token_env` field, plus `MCP_GATEWAY_KEY_VALUE`
for the global unlock key, plus `MCP_GATEWAY_TOKENS_YAML` pointing at a
read-only mount of the live YAML.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import psycopg2
import yaml

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config.settings import settings
from src.services.crypto import hash_secret, preview

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seed")

ACTOR = "seed-script"


def _seed_static(conn, name: str, token_env: str, tools: list[str], ips: list[str]) -> None:
    cleartext = os.environ.get(f"{token_env}_VALUE", "")
    if not cleartext:
        log.warning("Skipping static %r — env %s_VALUE not set", name, token_env)
        return
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM static_tokens WHERE name = %s", (name,))
    if cur.fetchone():
        log.info("Static token %r already exists, skipping", name)
        return
    cur.execute(
        """
        INSERT INTO static_tokens
          (name, token_hash, token_preview, tools_glob, ip_allowlist, created_by)
        VALUES (%s, %s, %s, %s, %s::inet[], %s)
        """,
        (name, hash_secret(cleartext), preview(cleartext), tools, ips, ACTOR),
    )
    log.info("Seeded static_token %r (%d tools, %d IPs)", name, len(tools), len(ips))


def _seed_oauth(conn, name: str, subs: list[str], emails: list[str], usernames: list[str], tools: list[str], ips: list[str]) -> None:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM oauth_policies WHERE name = %s", (name,))
    if cur.fetchone():
        log.info("OAuth policy %r already exists, skipping", name)
        return
    cur.execute(
        """
        INSERT INTO oauth_policies
          (name, oauth_sub, oauth_email, oauth_username, tools_glob, ip_allowlist, created_by)
        VALUES (%s, %s, %s, %s, %s, %s::inet[], %s)
        """,
        (name, subs, emails, usernames, tools, ips, ACTOR),
    )
    log.info("Seeded oauth_policy %r", name)


def _seed_default_unlock(conn) -> None:
    key = os.environ.get("MCP_GATEWAY_KEY_VALUE", "")
    if not key:
        log.warning("Skipping default unlock_profile — MCP_GATEWAY_KEY_VALUE not set")
        return
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM unlock_profiles WHERE name = 'default'")
    if cur.fetchone():
        log.info("Unlock profile 'default' already exists, skipping")
        return
    cur.execute(
        """
        INSERT INTO unlock_profiles (name, key_hash, key_preview, tools_glob, created_by)
        VALUES ('default', %s, %s, %s, %s)
        """,
        (hash_secret(key), preview(key), ["*"], ACTOR),
    )
    log.info("Seeded default unlock_profile (tools=['*'])")


def main() -> None:
    yaml_path = os.environ.get("MCP_GATEWAY_TOKENS_YAML", settings.seed_tokens_yaml)
    log.info("Reading %s", yaml_path)
    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}
    entries = data.get("tokens") or []

    conn = psycopg2.connect(settings.dsn)
    conn.autocommit = False
    try:
        for entry in entries:
            name = entry.get("name") or "unnamed"
            tools = list(entry.get("tools") or [])
            ips = list(entry.get("ip_allowlist") or [])
            token_env = entry.get("token_env")
            if token_env:
                _seed_static(conn, name, token_env, tools, ips)
                continue
            subs = entry.get("oauth_sub") or []
            emails = entry.get("oauth_email") or []
            usernames = entry.get("oauth_username") or []
            if not isinstance(subs, list):
                subs = [subs]
            if not isinstance(emails, list):
                emails = [emails]
            if not isinstance(usernames, list):
                usernames = [usernames]
            if subs or emails or usernames:
                _seed_oauth(conn, name, subs, emails, usernames, tools, ips)
                continue
            log.warning("Entry %r has neither token_env nor oauth_* matchers — skipping", name)

        _seed_default_unlock(conn)
        conn.commit()
        log.info("Seed complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
