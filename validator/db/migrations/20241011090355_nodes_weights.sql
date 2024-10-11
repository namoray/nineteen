-- migrate:up

CREATE TABLE IF NOT EXISTS nodes_weights (
    version_key INTEGER PRIMARY KEY,
    netuid INTEGER NOT NULL,
    validator_hotkey TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
    node_hotkey TEXT NOT NULL,
    node_weight FLOAT
);

-- migrate:down
DROP TABLE IF EXISTS nodes_weights;