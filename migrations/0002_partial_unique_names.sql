-- Allow re-use of names from revoked rows. Partial unique index on
-- name WHERE revoked_at IS NULL lets multiple revoked entries share a
-- name while still preventing two *active* entries with the same name.
--
-- Run as the table owner (mcp_admin).

ALTER TABLE static_tokens DROP CONSTRAINT IF EXISTS static_tokens_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS static_tokens_active_name_idx
    ON static_tokens (name) WHERE revoked_at IS NULL;

ALTER TABLE oauth_policies DROP CONSTRAINT IF EXISTS oauth_policies_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS oauth_policies_active_name_idx
    ON oauth_policies (name) WHERE revoked_at IS NULL;

ALTER TABLE unlock_profiles DROP CONSTRAINT IF EXISTS unlock_profiles_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS unlock_profiles_active_name_idx
    ON unlock_profiles (name) WHERE revoked_at IS NULL;
