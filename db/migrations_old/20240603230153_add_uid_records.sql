-- migrate:up

CREATE TABLE IF NOT EXISTS uid_records (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    axon_uid INT NOT NULL,
    miner_hotkey TEXT NOT NULL,
    validator_hotkey TEXT NOT NULL,
    task TEXT NOT NULL,
    declared_volume FLOAT NOT NULL,
    consumed_volume FLOAT DEFAULT 0,
    total_requests_made INT DEFAULT 0,
    requests_429 INT DEFAULT 0,
    requests_500 INT DEFAULT 0,
    period_score FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- migrate:down

DROP TABLE IF EXISTS uid_records;