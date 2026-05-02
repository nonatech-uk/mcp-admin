-- Per-request access log written by mcp-gateway. Captures auth events,
-- unlock events, and tool-call allow/deny so the admin UI can show who
-- did what from where.
--
-- Run as the table owner (mcp_admin).

CREATE TABLE IF NOT EXISTS gateway_access_log (
    id          bigserial PRIMARY KEY,
    ts          timestamptz NOT NULL DEFAULT now(),
    event       text NOT NULL,
        -- 'auth_success' | 'auth_fail_token' | 'auth_fail_ip'
        -- | 'unlock_success' | 'unlock_fail'
        -- | 'tool_allow' | 'tool_deny'
    actor_kind  text,                     -- 'static_bearer' | 'oauth'
    actor_name  text,                     -- policy name, null on rejection
    client_ip   inet,
    tool_name   text,
    profile     text,
    detail      jsonb
);

CREATE INDEX IF NOT EXISTS gateway_access_log_ts_idx ON gateway_access_log (ts DESC);
CREATE INDEX IF NOT EXISTS gateway_access_log_actor_idx ON gateway_access_log (actor_name, ts DESC);
CREATE INDEX IF NOT EXISTS gateway_access_log_event_idx ON gateway_access_log (event, ts DESC);

-- Grant the gateway (which connects as mcp_admin) implicitly via ownership.
-- The mcp_admin_ro read-only role gets INSERT here too so the gateway can
-- write under that lower-privilege identity if we ever switch to it.
GRANT INSERT ON gateway_access_log TO mcp_admin_ro;
GRANT USAGE ON SEQUENCE gateway_access_log_id_seq TO mcp_admin_ro;
