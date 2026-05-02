-- mcp-admin schema: source of truth for MCP gateway authorization.
--
-- Three entity types (static_tokens, oauth_policies, unlock_profiles), one
-- audit_log. Token / unlock-profile values are stored as argon2 hashes; the
-- cleartext is shown to the operator exactly once at creation and never
-- retrievable again. Gateway compares incoming bearers against these hashes.

CREATE TABLE IF NOT EXISTS static_tokens (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,
    token_hash      text NOT NULL,
    token_preview   text NOT NULL,           -- first 8 chars, for UI display
    tools_glob      text[] NOT NULL,
    ip_allowlist    inet[] NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      text NOT NULL,
    last_used_at    timestamptz,
    last_used_ip    inet,
    revoked_at      timestamptz
);

CREATE TABLE IF NOT EXISTS oauth_policies (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,
    oauth_sub       text[] NOT NULL DEFAULT '{}',
    oauth_email     text[] NOT NULL DEFAULT '{}',
    oauth_username  text[] NOT NULL DEFAULT '{}',
    tools_glob      text[] NOT NULL,
    ip_allowlist    inet[] NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      text NOT NULL,
    revoked_at      timestamptz
);

CREATE TABLE IF NOT EXISTS unlock_profiles (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL UNIQUE,    -- 'default', 'readonly', 'albury-only'
    key_hash        text NOT NULL,
    key_preview     text NOT NULL,
    tools_glob      text[] NOT NULL,         -- ['*'] for full
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      text NOT NULL,
    revoked_at      timestamptz
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              bigserial PRIMARY KEY,
    actor_email     text NOT NULL,
    action          text NOT NULL,           -- 'create' | 'update' | 'revoke' | 'rotate'
    target_type     text NOT NULL,           -- 'static_token' | 'oauth_policy' | 'unlock_profile'
    target_id       uuid NOT NULL,
    target_name     text NOT NULL,
    before          jsonb,
    after           jsonb,
    ts              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_log_ts_idx ON audit_log (ts DESC);
CREATE INDEX IF NOT EXISTS audit_log_target_idx ON audit_log (target_type, target_id);

-- Read-only role for the gateway (Phase 2 — gateway will use this DSN).
CREATE ROLE mcp_admin_ro NOLOGIN;
GRANT CONNECT ON DATABASE mcp_admin TO mcp_admin_ro;
GRANT USAGE ON SCHEMA public TO mcp_admin_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_admin_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_admin_ro;
