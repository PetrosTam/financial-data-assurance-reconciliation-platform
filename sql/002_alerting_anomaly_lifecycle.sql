ALTER TABLE anomalies
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open',
    ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolution_reason TEXT;

ALTER TABLE anomalies
    DROP CONSTRAINT IF EXISTS anomalies_status_check;

ALTER TABLE anomalies
    ADD CONSTRAINT anomalies_status_check
    CHECK (status IN ('open', 'acknowledged', 'resolved'));

CREATE INDEX IF NOT EXISTS idx_anomalies_status_detected_at
    ON anomalies (status, detected_at DESC);
