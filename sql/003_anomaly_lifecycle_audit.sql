CREATE TABLE IF NOT EXISTS anomaly_lifecycle_events (
    id                  BIGSERIAL PRIMARY KEY,
    anomaly_id          BIGINT NOT NULL
                        REFERENCES anomalies(id) ON DELETE RESTRICT,
    action              TEXT NOT NULL
                        CHECK (action IN ('acknowledge', 'resolve')),
    from_status         TEXT NOT NULL
                        CHECK (from_status IN ('open', 'acknowledged', 'resolved')),
    to_status           TEXT NOT NULL
                        CHECK (to_status IN ('open', 'acknowledged', 'resolved')),
    resolution_reason   TEXT,
    workflow_name       TEXT NOT NULL,
    execution_id        TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT anomaly_lifecycle_events_transition_check
    CHECK (
        (
            action = 'acknowledge'
            AND from_status = 'open'
            AND to_status = 'acknowledged'
        )
        OR
        (
            action = 'resolve'
            AND from_status = 'acknowledged'
            AND to_status = 'resolved'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_anomaly_lifecycle_events_anomaly_created_at
    ON anomaly_lifecycle_events (anomaly_id, created_at DESC);
