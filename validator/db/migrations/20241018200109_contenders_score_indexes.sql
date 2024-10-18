-- migrate:up
CREATE INDEX idx_contenders_period_score ON contenders (PERIOD_SCORE);
CREATE INDEX idx_contenders_total_requests_made ON contenders (TOTAL_REQUESTS_MADE);

-- migrate:down
DROP INDEX idx_contenders_period_score;
DROP INDEX idx_contenders_total_requests_made;