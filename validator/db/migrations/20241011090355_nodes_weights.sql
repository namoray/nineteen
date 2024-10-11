-- migrate:up

CREATE TABLE IF NOT EXISTS nodes_weights (
    version_key INTEGER NOT NULL,
    netuid INTEGER NOT NULL,
    validator_hotkey TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
    node_hotkey TEXT NOT NULL,
    node_weight FLOAT,
    PRIMARY KEY (version_key, netuid, validator_hotkey, created_at, node_hotkey)
);

-- migrate:down
DROP TABLE IF EXISTS nodes_weights;