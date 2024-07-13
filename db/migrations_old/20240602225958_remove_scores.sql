-- migrate:up
DROP TABLE scores;
-- migrate:down

CREATE TABLE scores
(
    id INTEGER PRIMARY KEY,
    axon_uid INT NOT NULL,
    hotkey TEXT NOT NULL,
    response_time FLOAT,
    score FLOAT,
    synapse TEXT,
    valid_response BOOLEAN,
    quickest_response BOOLEAN,
    checked_with_server BOOLEAN,
    timestamp TIMESTAMP
);


