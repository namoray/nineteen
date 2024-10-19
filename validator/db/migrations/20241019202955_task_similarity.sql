-- migrate:up

CREATE TABLE IF NOT EXISTS task_similarity (
    id SERIAL PRIMARY KEY,
    left_task TEXT NOT NULL,
    right_task TEXT NOT NULL,
    similarity FLOAT NOT NULL DEFAULT 0,
    UNIQUE (left_task, right_task)
);

-- migrate:down
DROP TABLE IF EXISTS task_similarity;
