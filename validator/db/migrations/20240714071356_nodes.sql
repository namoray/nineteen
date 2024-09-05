-- migrate:up
CREATE TABLE nodes (
    hotkey TEXT NOT NULL,
    coldkey TEXT NOT NULL,
    node_id INTEGER NOT NULL,
    incentive FLOAT NOT NULL,
    netuid INTEGER NOT NULL,
    stake FLOAT NOT NULL,
    trust FLOAT NOT NULL,
    vtrust FLOAT NOT NULL,
    last_updated FLOAT,
    ip TEXT NOT NULL,
    ip_type INTEGER NOT NULL,
    port INTEGER NOT NULL,
    protocol INTEGER NOT NULL DEFAULT 4,
    network TEXT NOT NULL,
    symmetric_key TEXT,
    symmetric_key_uuid TEXT,
    our_validator BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
    PRIMARY KEY (hotkey, netuid)
);

-- migrate:down
DROP TABLE IF EXISTS nodes;