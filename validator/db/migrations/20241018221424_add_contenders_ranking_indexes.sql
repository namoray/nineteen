-- migrate:up
CREATE INDEX idx_contenders_synthetic ON contenders (TOTAL_REQUESTS_MADE);

CREATE INDEX idx_contenders_organic ON contenders (
    PERIOD_SCORE,
    TOTAL_REQUESTS_MADE,
    REQUESTS_429,
    REQUESTS_500
);

-- migrate:down
DROP INDEX IF EXISTS idx_contenders_synthetic;
DROP INDEX IF EXISTS idx_contenders_organic;
