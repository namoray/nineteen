-- migrate:up
CREATE TABLE axon_info_history (
    id SERIAL PRIMARY KEY,
    hotkey TEXT NOT NULL,
    coldkey TEXT NOT NULL,
    axon_version INTEGER NOT NULL,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    ip_type INTEGER NOT NULL,
    axon_uid INTEGER NOT NULL,
    incentive FLOAT,
    netuid INTEGER NOT NULL,
    network TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE,
    expired_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- migrate:down
DROP TABLE IF EXISTS axon_info_history;