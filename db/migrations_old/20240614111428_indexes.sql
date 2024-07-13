
-- migrate:up

CREATE UNIQUE INDEX idx_api_keys_key_unique ON api_keys(key);

CREATE INDEX idx_logs_key ON logs(key);
CREATE INDEX idx_logs_endpoint ON logs(endpoint);
CREATE INDEX idx_logs_created_at ON logs(created_at);

CREATE INDEX idx_reward_data_task ON reward_data(task);
CREATE INDEX idx_reward_data_axon_uid ON reward_data(axon_uid);
CREATE INDEX idx_reward_data_quality_score ON reward_data(quality_score);
CREATE INDEX idx_reward_data_validator_hotkey ON reward_data(validator_hotkey);
CREATE INDEX idx_reward_data_miner_hotkey ON reward_data(miner_hotkey);
CREATE INDEX idx_reward_data_created_at ON reward_data(created_at);

CREATE INDEX idx_tasks_task_name ON tasks(task_name);
CREATE INDEX idx_tasks_miner_hotkey ON tasks(miner_hotkey);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);

CREATE INDEX idx_uid_records_task ON uid_records(task);
CREATE INDEX idx_uid_records_axon_uid ON uid_records(axon_uid);
CREATE INDEX idx_uid_records_validator_hotkey ON uid_records(validator_hotkey);
CREATE INDEX idx_uid_records_miner_hotkey ON uid_records(miner_hotkey);
CREATE INDEX idx_uid_records_created_at ON uid_records(created_at);

CREATE INDEX idx_miner_task_config_task_name ON miner_task_config(task_name);
CREATE INDEX idx_miner_task_config_miner_hotkey ON miner_task_config(miner_hotkey);
CREATE INDEX idx_miner_task_config_concurrency_group_id ON miner_task_config(concurrency_group_id);

-- migrate:down

DROP INDEX IF EXISTS idx_api_keys_key_unique;

DROP INDEX IF EXISTS idx_logs_key;
DROP INDEX IF EXISTS idx_logs_endpoint;
DROP INDEX IF EXISTS idx_logs_created_at;

DROP INDEX IF EXISTS idx_reward_data_task;
DROP INDEX IF EXISTS idx_reward_data_axon_uid;
DROP INDEX IF EXISTS idx_reward_data_quality_score;
DROP INDEX IF EXISTS idx_reward_data_validator_hotkey;
DROP INDEX IF EXISTS idx_reward_data_miner_hotkey;
DROP INDEX IF EXISTS idx_reward_data_created_at;

DROP INDEX IF EXISTS idx_tasks_task_name;
DROP INDEX IF EXISTS idx_tasks_miner_hotkey;
DROP INDEX IF EXISTS idx_tasks_created_at;

DROP INDEX IF EXISTS idx_uid_records_task;
DROP INDEX IF EXISTS idx_uid_records_axon_uid;
DROP INDEX IF EXISTS idx_uid_records_validator_hotkey;
DROP INDEX IF EXISTS idx_uid_records_miner_hotkey;
DROP INDEX IF EXISTS idx_uid_records_created_at;

DROP INDEX IF EXISTS idx_miner_task_config_task_name;
DROP INDEX IF EXISTS idx_miner_task_config_miner_hotkey;
DROP INDEX IF EXISTS idx_miner_task_config_concurrency_group_id;
