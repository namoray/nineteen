-- migrate:up

CREATE TABLE IF NOT EXISTS capacities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    miner_hotkey TEXT NOT NULL,
    validator_hotkey TEXT NOT NULL,
    task TEXT NOT NULL,
    volume INTEGER NOT NULL,
    raw_capacity INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- migrate:down

DROP TABLE IF EXISTS capacities;