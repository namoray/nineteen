-- migrate:up
CREATE TABLE IF NOT EXISTS miner_concurrency_group (
    concurrency_group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    concurrent_tasks_limit INTEGER NOT NULL,
    name TEXT
);

CREATE TABLE IF NOT EXISTS miner_task_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT NOT NULL,
    miner_hotkey TEXT NOT NULL,
    volume FLOAT NOT NULL,
    concurrency_group_id INTEGER,
    FOREIGN KEY (concurrency_group_id) REFERENCES miner_concurrency_group(concurrency_group_id) ON DELETE CASCADE
);

-- migrate:down
DROP TABLE IF EXISTS miner_task_config;

DROP TABLE IF EXISTS miner_concurrency_group;