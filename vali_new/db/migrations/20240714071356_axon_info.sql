-- migrate:up
CREATE TABLE axon_info (
    hotkey TEXT PRIMARY KEY,
    coldkey TEXT NOT NULL,
    version TEXT NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    ip_type TEXT NOT NULL,
    axon_uid INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- migrate:down
DROP TABLE IF EXISTS axon_info;
