-- migrate:up
CREATE TABLE nodes_history (
    id SERIAL PRIMARY KEY,
    hotkey TEXT NOT NULL,
    coldkey TEXT NOT NULL,
    node_id INTEGER NOT NULL,
    incentive FLOAT NOT NULL,
    netuid INTEGER NOT NULL,
    stake FLOAT NOT NULL,
    trust FLOAT NOT NULL,
    vtrust FLOAT NOT NULL,
    ip TEXT NOT NULL,
    ip_type INTEGER NOT NULL,
    port INTEGER NOT NULL,
    protocol INTEGER NOT NULL DEFAULT 4,
    network TEXT NOT NULL,
    our_validator BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    expired_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- migrate:down
DROP TABLE IF EXISTS node_history;