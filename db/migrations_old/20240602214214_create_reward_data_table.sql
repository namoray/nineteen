-- migrate:up

CREATE TABLE IF NOT EXISTS reward_data (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    task TEXT NOT NULL,
    axon_uid INTEGER NOT NULL,
    quality_score FLOAT NOT NULL,
    validator_hotkey TEXT NOT NULL,
    miner_hotkey TEXT NOT NULL,
    synthetic_query BOOLEAN NOT NULL,
    speed_scoring_factor FLOAT,
    response_time FLOAT,
    volume FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- migrate:down

DROP TABLE IF EXISTS reward_data;
