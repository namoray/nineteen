-- migrate:up
CREATE TABLE axon_info_history (
    hotkey TEXT PRIMARY KEY,
    coldkey TEXT NOT NULL,
    version TEXT NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    ip_type TEXT NOT NULL,
    axon_uid INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    expired_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- migrate:down
DROP TABLE IF EXISTS axon_info_history;
