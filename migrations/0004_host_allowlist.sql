-- Per-host access control for host-aware MCP tools (mcp-host-tools, mcp-loki).
--
-- Adds host_allowlist text[] to all three policy tables. Empty array = deny;
-- '*' (literal magic value) = allow any host; otherwise the array is the
-- exact set of permitted hostnames (case-sensitive).
--
-- Backfill: every currently-active row gets ['*'] so existing behaviour is
-- preserved. New rows default to '{}' (deny) — operators must populate the
-- field at creation time.
--
-- Run as the table owner (mcp_admin). Single transaction so live rows never
-- spend a moment with '{}' (which would deny under the new gateway).

BEGIN;

ALTER TABLE static_tokens   ADD COLUMN host_allowlist text[] NOT NULL DEFAULT '{}'::text[];
ALTER TABLE oauth_policies  ADD COLUMN host_allowlist text[] NOT NULL DEFAULT '{}'::text[];
ALTER TABLE unlock_profiles ADD COLUMN host_allowlist text[] NOT NULL DEFAULT '{}'::text[];

UPDATE static_tokens   SET host_allowlist = ARRAY['*'] WHERE revoked_at IS NULL;
UPDATE oauth_policies  SET host_allowlist = ARRAY['*'] WHERE revoked_at IS NULL;
UPDATE unlock_profiles SET host_allowlist = ARRAY['*'] WHERE revoked_at IS NULL;

COMMIT;
