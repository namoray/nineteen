-- migrate:up
CREATE TABLE IF NOT EXISTS participants (
    participant_id TEXT PRIMARY KEY,
    miner_hotkey TEXT NOT NULL,
    task TEXT NOT NULL,
    validator_hotkey TEXT NOT NULL,
    capacity FLOAT NOT NULL,
    capacity_to_score FLOAT NOT NULL,
    consumed_capacity FLOAT NOT NULL,
    delay_between_synthetic_requests FLOAT NOT NULL,
    synthetic_requests_still_to_make FLOAT NOT NULL,
    total_requests_made INTEGER NOT NULL DEFAULT 0,
    requests_429 INTEGER NOT NULL DEFAULT 0,
    requests_500 INTEGER NOT NULL DEFAULT 0,
    raw_capacity FLOAT NOT NULL,
    period_score FLOAT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE TABLE IF NOT EXISTS participants_history (
    id SERIAL PRIMARY KEY,
    participant_id TEXT NOT NULL,
    miner_hotkey TEXT NOT NULL,
    task TEXT NOT NULL,
    validator_hotkey TEXT NOT NULL,
    capacity FLOAT NOT NULL,
    capacity_to_score FLOAT NOT NULL,
    consumed_capacity FLOAT NOT NULL,
    delay_between_synthetic_requests FLOAT NOT NULL,
    synthetic_requests_still_to_make FLOAT NOT NULL,
    total_requests_made INTEGER NOT NULL DEFAULT 0,
    requests_429 INTEGER NOT NULL DEFAULT 0,
    requests_500 INTEGER NOT NULL DEFAULT 0,
    raw_capacity FLOAT NOT NULL,
    period_score FLOAT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    expired_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
);

-- migrate:down

DROP TABLE IF EXISTS participants;
DROP TABLE IF EXISTS participants_history;