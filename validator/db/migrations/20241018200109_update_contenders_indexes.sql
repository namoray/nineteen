-- migrate:up

-- Create new indexes to optimize the selection queries

-- Index to optimize organic queries in get_contenders_for_task
-- Helps filter by task and join on node_hotkey efficiently
CREATE INDEX idx_contenders_task_node_hotkey ON contenders (task, node_hotkey);

-- Index to optimize synthetic queries in get_contenders_for_task
-- Helps filter by task and order by total_requests_made efficiently
CREATE INDEX idx_contenders_task_total_requests_made ON contenders (task, total_requests_made);

-- Index to optimize access to historical period scores in contenders_history
-- Helps filter by task, node_hotkey, and quickly access recent scores via created_at
CREATE INDEX idx_contenders_history_task_hotkey_created_at ON contenders_history (task, node_hotkey, created_at DESC);

-- migrate:down

-- Drop the new indexes
DROP INDEX IF EXISTS idx_contenders_task_node_hotkey;
DROP INDEX IF EXISTS idx_contenders_task_total_requests_made;
DROP INDEX IF EXISTS idx_contenders_history_task_hotkey_created_at;
