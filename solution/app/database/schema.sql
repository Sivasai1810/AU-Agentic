-- schema.sql: the one table that tracks every lead (one row per lead per campaign).
-- state flow:  ready -> dialing -> active -> ready (retry/callback)
--                                         -> completed | exhausted
--              ready -> dnd_blocked (same phone said "do not call")
-- A row is saved as 'dialing' BEFORE we call the provider, so a crash never loses a call.
CREATE TABLE IF NOT EXISTS leads (
    campaign_id      TEXT,
    lead_id          TEXT,
    phone            TEXT,
    tenant_id        TEXT,
    state            TEXT    DEFAULT 'ready',
    attempts         INTEGER DEFAULT 0,      -- calls the provider accepted
    attempt_no       INTEGER DEFAULT 0,      -- the attempt currently being dialled
    kind             TEXT    DEFAULT 'fresh',-- fresh | retry | callback (decides priority)
    next_time        TEXT,                   -- earliest time we may call this lead
    request_id       TEXT    DEFAULT '',     -- idempotency key sent to the provider
    checked_at       REAL    DEFAULT 0,      -- last real time we looked at this call
    last_status      TEXT    DEFAULT '',
    last_disposition TEXT    DEFAULT '',
    PRIMARY KEY (campaign_id, lead_id)
);
