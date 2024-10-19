-- migrate:up
CREATE INDEX IF NOT EXISTS idx_contenders_weights_stats_node_hotkey
ON contenders_weights_stats (node_hotkey);

-- migrate:down
DROP INDEX IF EXISTS idx_contenders_weights_stats_node_hotkey;