CREATE TABLE IF NOT EXISTS fx_quotes (
    id                      BIGSERIAL PRIMARY KEY,
    symbol                  TEXT NOT NULL,
    provider_instrument_id  TEXT,
    bid                     NUMERIC(18,8),
    ask                     NUMERIC(18,8),
    mid_price               NUMERIC(18,8),
    spread                  NUMERIC(18,8),
    source                  TEXT NOT NULL,
    observed_at             TIMESTAMPTZ NOT NULL,
    received_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload             JSONB,
    UNIQUE (symbol, observed_at, source)
);

CREATE INDEX IF NOT EXISTS idx_fx_quotes_symbol_observed_at
    ON fx_quotes (symbol, observed_at DESC);


CREATE TABLE IF NOT EXISTS workflow_runs (
    id                  BIGSERIAL PRIMARY KEY,
    workflow_name       TEXT NOT NULL,
    execution_id        TEXT,
    status              TEXT NOT NULL
                        CHECK (status IN ('started', 'success', 'warning', 'failed')),
    records_processed   INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ
);


CREATE TABLE IF NOT EXISTS anomalies (
    id                  BIGSERIAL PRIMARY KEY,
    symbol              TEXT NOT NULL,
    anomaly_type        TEXT NOT NULL,
    severity            TEXT NOT NULL
                        CHECK (severity IN ('info', 'warning', 'critical')),
    metric_value        NUMERIC(20,8),
    threshold_value     NUMERIC(20,8),
    details             JSONB,
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_anomalies_symbol_detected_at
    ON anomalies (symbol, detected_at DESC);


CREATE TABLE IF NOT EXISTS alerts (
    id              BIGSERIAL PRIMARY KEY,
    anomaly_id      BIGINT REFERENCES anomalies(id) ON DELETE SET NULL,
    channel         TEXT NOT NULL,
    status          TEXT NOT NULL
                    CHECK (status IN ('pending', 'sent', 'failed')),
    message         TEXT,
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);