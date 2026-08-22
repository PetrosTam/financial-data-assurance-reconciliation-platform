# FX Operations Automation & Monitoring

A reliability-focused FX market-data operations platform built with n8n, JavaScript, REST APIs, PostgreSQL, Docker Compose, and Git.

The broader project scope treats FX prices as operational and research data for ingestion, validation, persistence, monitoring, anomaly detection, alerting, reconciliation, replay, analytics, incidents, and experiments.

It is **not a trading bot**.

---

## Overview

The current implementation provides a multi-instrument FX ingestion and monitoring pipeline that:

- retrieves FX market data from Alpha Vantage through a REST API
- processes EUR/USD, GBP/USD, and USD/JPY sequentially
- validates and normalizes provider-specific responses
- persists normalized quotes and raw provider payloads in PostgreSQL
- tracks workflow execution lifecycle
- detects operational anomalies
- compares current and previous prices
- persists structured anomaly records
- routes critical anomalies to email alerts
- records alert delivery success or failure
- keeps runtime email routing configuration outside source control
- includes a verified anomaly lifecycle-ready database schema
- automatically applies the base schema and lifecycle migration when initializing a fresh PostgreSQL data volume

The current system is designed around evidence-driven engineering principles: deterministic validation, idempotency, explicit failure handling, observable workflow state, small changes, controlled testing, secure configuration, and reproducible checkpoints.

---

## Current Architecture

### Main FX Operations Pipeline

```text
Manual Trigger ──────────────┐
                             │
Schedule Trigger ────────────┤
                             v
                      Log Run Started
                             |
                             v
                     Generate FX Pairs
                             |
                             v
                     Loop Over Items
                     Batch Size = 1
                             |
                         loop output
                             |
                             v
                       Fetch FX Quote
                             |
                             v
                          Wait
                             |
                             └──────────────→ Loop Over Items

                     done output
                             |
                             v
                  Validate & Normalize Quote
                             |
              ┌──────────────┼──────────────────────┐
              |              |                      |
              v              v                      v
        Persist Quote   Detect Operational      Check Price
        to PostgreSQL      Anomalies             Movement
              |              |                      |
              v              └──────────┬───────────┘
       Mark Run Success                 |
                                        v
                                   Log Anomaly
                                        |
                                        v
                              Is Critical Anomaly?
                                  true |
                                       v
                                  Create Alert
                                       |
                                       v
                          Send Critical Alert Email
                              /                  \
                        success                  error
                           |                       |
                           v                       v
                    Mark Alert Sent        Mark Alert Failed
```

### Production Failure Handling

```text
Production Workflow Failure
            |
            v
       Error Trigger
            |
            v
      Mark Run Failed
            |
            v
       PostgreSQL
```

---

## Implemented Features

### Multi-Instrument FX Ingestion

The current workflow processes:

```text
EUR/USD
GBP/USD
USD/JPY
```

Pairs are generated dynamically by the `Generate FX Pairs` node.

Each generated item contains:

```text
from_currency
to_currency
```

The same REST integration therefore processes multiple FX instruments without duplicating the HTTP integration node.

### Sequential API Processing

External provider requests are processed sequentially:

```text
Generate FX Pairs
      ↓
Loop Over Items
      ↓
Fetch FX Quote
      ↓
Wait
      ↓
Loop Over Items
```

`Loop Over Items` uses:

```text
Batch Size = 1
```

and the workflow introduces a three-second wait between provider requests.

This provides explicit request pacing for the current provider integration.

### Scheduled Automation

The workflow supports:

- manual execution for development and controlled testing
- scheduled execution for automated ingestion

The current production schedule runs every four hours.

---

## External API Integration

Market data is currently retrieved from the Alpha Vantage FX API using:

```text
CURRENCY_EXCHANGE_RATE
```

Dynamic request parameters are used:

```text
from_currency = {{ $json.from_currency }}
to_currency   = {{ $json.to_currency }}
```

API authentication is stored using n8n credentials and is not embedded directly in exported workflow logic.

Provider responses are treated as untrusted input.

---

## FX Data Validation and Normalization

Provider-specific responses are transformed into a common internal representation using JavaScript.

Each normalized quote contains:

```text
symbol
provider_instrument_id
bid
ask
mid_price
spread
source
observed_at
raw_payload
```

Examples:

```text
EUR + USD → EURUSD
GBP + USD → GBPUSD
USD + JPY → USDJPY
```

### Validation Controls

The current validation layer checks:

- expected provider response structure
- required source/target currency fields
- numeric bid values
- numeric ask values
- positive bid and ask values
- `ask >= bid`
- presence and validity of the market timestamp
- provider error responses

Invalid provider responses are rejected before persistence.

### Derived Metrics

```text
mid_price = (bid + ask) / 2
spread    = ask - bid
```

Operational spread monitoring also uses:

```text
spread_bps = (spread / mid_price) * 10000
```

Timestamps are normalized before persistence.

---

## PostgreSQL Persistence

Validated quotes are stored in:

```text
fx_quotes
```

The table stores:

- symbol
- provider instrument identifier
- bid
- ask
- mid price
- spread
- source
- observation timestamp
- receipt timestamp
- raw provider payload

### Duplicate Protection

Database-level uniqueness constraints protect against duplicate market-data records.

The persistence path uses conflict handling so duplicate quotes can be skipped safely instead of failing the entire workflow.

This makes quote persistence idempotent for the current uniqueness model.

---

## Workflow Execution Monitoring

Each workflow run is tracked in:

```text
workflow_runs
```

### Run Start

`Log Run Started` records:

- workflow name
- n8n execution ID
- status
- records processed
- start timestamp

Initial state:

```text
status = started
records_processed = 0
```

### Successful Execution

`Mark Run Success` updates the matching execution row using the n8n execution ID.

Final success state:

```text
status = success
records_processed = <number of normalized FX quotes>
finished_at = <completion timestamp>
```

For the current three-instrument pipeline:

```text
records_processed = 3
```

The processed-record count is calculated dynamically.

---

## Production Failure Handling

A dedicated workflow named:

```text
FX Workflow Error Handler
```

handles production workflow failures.

Architecture:

```text
Error Trigger
      ↓
Mark Run Failed
```

The failure workflow correlates the failed execution with the corresponding `workflow_runs` row using the execution ID and updates:

```text
status = failed
error_message = <actual failure message>
finished_at = <failure completion timestamp>
```

Controlled failures were used during development to verify the failure path.

---

## Operational Anomaly Detection

Validated quotes are evaluated by monitoring branches independently of quote persistence.

This allows structurally valid but operationally unusual market-data records to remain available for analysis while also being flagged for investigation.

Current anomaly types:

```text
wide_spread
stale_quote
extreme_price_movement
```

Detected anomalies are stored in:

```text
anomalies
```

---

## Wide Spread Detection

The system calculates:

```text
spread_bps = (spread / mid_price) * 10000
```

Current operational assumptions:

```text
Warning:  > 2 bps
Critical: > 5 bps
```

These are project-level operational thresholds, not universal FX market rules.

When exceeded, the workflow creates:

```text
anomaly_type = wide_spread
```

Diagnostic context includes:

- bid
- ask
- mid price
- absolute spread
- spread in basis points
- source
- observation timestamp

---

## Stale Quote Detection

The workflow compares the quote observation timestamp with the current workflow time.

Current operational assumptions:

```text
Warning:  > 600 seconds
Critical: > 1800 seconds
```

When exceeded:

```text
anomaly_type = stale_quote
```

The anomaly retains quote-age and timestamp context.

Freshness is treated as a deterministic operational control.

---

## Extreme Price Movement Detection

The workflow compares each current quote with the latest earlier quote for the same FX symbol stored in PostgreSQL.

The previous quote is retrieved using a parameterized SQL query.

Current movement calculation:

```text
movement_bps =
    abs(
        (current_mid_price - previous_mid_price)
        / previous_mid_price
    ) * 10000
```

Current operational assumptions:

```text
Warning:  > 20 bps
Critical: > 50 bps
```

When exceeded:

```text
anomaly_type = extreme_price_movement
```

Diagnostic context includes:

- previous mid price
- current mid price
- movement in basis points
- previous observation timestamp
- current observation timestamp

Controlled tests were used to verify this anomaly path without altering production market-data records.

---

## Anomaly Persistence

Anomalies use a common persistence structure including:

```text
symbol
anomaly_type
severity
metric_value
threshold_value
details
detected_at
resolved_at
status
acknowledged_at
resolution_reason
```

`details` uses PostgreSQL `JSONB` for diagnostic context.

Current severity values are:

```text
info
warning
critical
```

If no anomaly is detected, the anomaly branch emits no anomaly record and normal quote processing continues.

---

## Critical Anomaly Email Alerting

Critical anomalies enter a dedicated alerting path:

```text
Log Anomaly
      ↓
Is Critical Anomaly?
      ↓ true
Create Alert
status = pending
      ↓
Send Critical Alert Email
   ├─ success → Mark Alert Sent
   └─ error   → Mark Alert Failed
```

### Alert Persistence

Generated notifications are stored in:

```text
alerts
```

The current alert delivery lifecycle supports:

```text
pending
sent
failed
```

On successful delivery:

```text
status = sent
sent_at = <delivery timestamp>
```

On delivery failure:

```text
status = failed
```

The alert record retains its relationship to the originating anomaly where applicable.

### Verified Delivery

The email path has been verified with:

- deterministic test input
- the configured SMTP credential
- environment-based sender and recipient configuration
- successful SMTP acceptance
- real Gmail mailbox delivery
- cleanup of temporary test artifacts

---

## Email Configuration and Secret Handling

SMTP authentication remains stored in the n8n credential:

```text
FX Ops Gmail SMTP
```

Email sender and recipient addresses are not hardcoded in the exported production workflow.

The workflow uses:

```text
$env.ALERT_EMAIL_FROM
$env.ALERT_EMAIL_TO
```

Real local values are stored in:

```text
.env
```

The file is excluded from Git.

A safe template is committed as:

```text
.env.example
```

Example:

```text
ALERT_EMAIL_FROM=alerts@example.com
ALERT_EMAIL_TO=operator@example.com
```

Docker Compose passes the configured values into the n8n container.

---

## Anomaly Lifecycle Schema

The repository contains:

```text
sql/002_alerting_anomaly_lifecycle.sql
```

The migration adds lifecycle support to `anomalies` through:

```text
status
acknowledged_at
resolution_reason
```

The base schema already contains:

```text
resolved_at
```

Allowed lifecycle states are:

```text
open
acknowledged
resolved
```

The migration also defines:

```text
idx_anomalies_status_detected_at
```

for status/time-oriented lifecycle queries.

### Current Status

The lifecycle database schema is **implemented and verified**.

The operator-facing workflow that will manage transitions such as:

```text
open → acknowledged → resolved
```

is **not yet implemented**.

The next planned workflow is:

```text
FX Anomaly Lifecycle Manager
```

### Fresh Database Initialization

A fresh PostgreSQL data volume automatically executes the repository initialization scripts in order:

```text
001_schema.sql
      ↓
002_alerting_anomaly_lifecycle.sql
```

Docker Compose mounts both scripts into:

```text
/docker-entrypoint-initdb.d/
```

Fresh-database initialization was verified in an isolated temporary PostgreSQL 16 container.

The verification confirmed:

- `001_schema.sql` executed
- `002_alerting_anomaly_lifecycle.sql` executed
- lifecycle columns were created
- `status` defaults to `open`
- `anomalies_status_check` exists
- allowed states are `open`, `acknowledged`, and `resolved`
- `idx_anomalies_status_detected_at` exists
- no initialization `ERROR` or `FATAL` condition was observed

The temporary test container was removed after verification and the normal project PostgreSQL service remained healthy.

---

## Data Model

The PostgreSQL database currently contains four core operational tables.

### `fx_quotes`

Stores normalized FX market data and raw provider responses.

### `workflow_runs`

Stores workflow execution lifecycle information.

### `anomalies`

Stores detected operational/data-quality anomalies and lifecycle-related fields.

### `alerts`

Stores operational alert records and email-delivery state.

---

## Reliability Controls

The current implementation includes:

- scheduled automation
- manual controlled execution
- sequential API request processing
- explicit provider request pacing
- provider-response validation
- structured quote normalization
- positive-price validation
- bid/ask consistency checks
- timestamp validation
- database uniqueness constraints
- duplicate-safe persistence
- raw provider payload retention
- workflow execution IDs
- execution lifecycle tracking
- dynamic processed-record counting
- success-state persistence
- failure-state persistence
- centralized error handling
- error-message capture
- wide-spread monitoring
- stale-data monitoring
- previous-quote comparison
- extreme price-movement detection
- anomaly severity classification
- structured anomaly persistence
- critical anomaly routing
- persisted alert state
- verified email delivery
- alert success/failure state handling
- environment-based alert routing configuration
- ordered fresh-database schema initialization
- persistent n8n state through a Docker named volume

---

## Docker Persistence

n8n application state is persisted through:

```yaml
volumes:
  - n8n_data:/home/node/.n8n
```

The named volume preserves n8n application state across container recreation.

Persistence was explicitly regression-tested during development by verifying:

- the resolved Docker Compose mount
- the actual container mount at `/home/node/.n8n`
- successful export of both persisted workflows
- restoration of the existing n8n account and workflow state after container recreation

---

## Security

Sensitive runtime values are kept outside source control.

### API Credentials

External API authentication is managed through n8n credentials.

### PostgreSQL Credentials

Database credentials are managed through local environment configuration and n8n credentials where required by workflow nodes.

### SMTP Credentials

SMTP authentication is stored in n8n credentials.

### Environment Variables

Local configuration is stored in:

```text
.env
```

`.env` is excluded by `.gitignore`.

Only safe placeholders are committed in `.env.example`.

### SQL Safety

Dynamic PostgreSQL queries that depend on runtime values use parameterized SQL where applicable.

### Repository Safety

Before checkpointing, tracked source and workflow exports are reviewed for:

- hardcoded personal email addresses
- API keys
- passwords
- bearer tokens
- authorization headers
- client secrets
- pinned n8n test data

Project checkpoints are created from committed `HEAD` using `git archive`, not by manually zipping the working directory.

---

## Current Tech Stack

The implemented runtime currently uses:

- n8n
- JavaScript
- REST APIs
- PostgreSQL
- Docker Compose
- Git

---

## Planned Research and Platform Components

The broader MSc thesis/platform roadmap includes additional technologies only when they have a concrete responsibility, simpler-alternative review, success criteria, and verification plan.

Planned components include:

- Python
- provider abstraction
- second-source reconciliation
- Prometheus
- Grafana
- Go
- Kafka
- Flink
- ClickHouse
- MinIO / Parquet
- Spark
- Trino
- Redis where justified
- MongoDB quarantine where justified
- C++ replay/resilience components
- REST / gRPC / GraphQL operator APIs with distinct responsibilities
- React + TypeScript operator console
- Kubernetes / GitOps / Argo CD when operational scale justifies them

These are **not claimed as implemented** unless supported by repository and runtime evidence.

---

## Project Structure

```text
.
├── docs/
│   └── architecture.md
├── sql/
│   ├── 001_schema.sql
│   └── 002_alerting_anomaly_lifecycle.sql
├── workflows/
│   ├── fx-workflow-error-handler.json
│   └── multi-instrument-fx-operations-pipeline-alpha-vantage.json
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Current Pipeline Capabilities

The current implementation can:

1. Start FX ingestion manually or on schedule
2. Generate multiple FX instrument requests dynamically
3. Process provider requests sequentially
4. Apply explicit request pacing
5. Reuse one REST integration across multiple FX pairs
6. Validate provider responses before persistence
7. Normalize provider-specific market data
8. Calculate mid price and spread
9. Persist normalized FX quotes
10. Preserve raw provider payloads
11. Prevent duplicate quote persistence
12. Track workflow execution lifecycle
13. Count processed records dynamically
14. Mark successful workflow runs
15. Capture production failures through a dedicated error workflow
16. Persist workflow failure messages
17. Detect wide spreads
18. Detect stale quotes
19. Compare current and previous FX prices
20. Detect extreme price movements
21. Classify anomalies by severity
22. Persist structured anomaly records
23. Route critical anomalies into the alerting path
24. Create pending alert records
25. Deliver critical alerts through Gmail SMTP
26. Mark successful alerts as `sent`
27. Persist `sent_at`
28. Mark failed alert deliveries as `failed`
29. Load alert sender/recipient configuration from environment variables
30. Keep real alert addresses outside committed workflow exports
31. Support anomaly lifecycle fields at the database-schema level
32. Apply the lifecycle migration automatically during fresh PostgreSQL initialization
33. Persist n8n application state through a named Docker volume

---

## Testing and Verification

Verified development/testing evidence includes:

- multi-pair ingestion
- three normalized/persisted FX records for a successful current run
- workflow execution start/success lifecycle
- controlled production failure handling
- provider/malformed response handling during development
- operational anomaly paths
- rate-limit-aware sequential request processing
- duplicate-safe persistence
- extreme price-movement detection
- critical anomaly routing
- pending alert creation
- real Gmail delivery
- successful alert state transition to `sent`
- `sent_at` persistence
- failed alert state path
- test-data cleanup
- externalized email routing configuration
- removal of hardcoded personal email addresses from the production workflow export
- empty n8n `pinData` in the committed workflow export
- Docker/n8n persistent-volume recovery and verification
- anomaly lifecycle schema verification in PostgreSQL
- isolated fresh-database execution of `001_schema.sql` followed by `002_alerting_anomaly_lifecycle.sql`
- fresh-database verification of lifecycle columns, constraint, and index
- cleanup of the temporary PostgreSQL test container after verification

A capability is treated as tested only after its result has been inspected.

---

## MSc Thesis Direction

The platform is also being evolved into an MSc thesis artifact focused on operational FX market-data quality.

The proposed research direction is:

**Evaluating Adaptive Anomaly Detection and Cross-Source Reconciliation for Operational FX Market Data Quality**

The research core is planned around two questions:

- whether temporally aligned cross-source evidence improves classification of injected source-specific data-quality faults compared with single-source monitoring
- how adaptive statistical anomaly detection compares with an equivalent fixed statistical baseline under changing normal FX conditions and controlled price/spread faults

The research layer is planned to remain independently executable from the current n8n operational runtime.

Ground truth will come from controlled fault injection rather than provider disagreement.

Research data must remain zero-cost. Candidate historical sources must pass a compatibility and data-use pilot before adoption.

---

## Development Roadmap

### Near-Term

- implement `FX Anomaly Lifecycle Manager`
- validate lifecycle API requests
- enforce valid lifecycle transitions
- add operator-facing acknowledge/resolve actions
- make instruments and operational rules configuration-driven
- improve lifecycle auditability

### Provider and Reconciliation Layer

- introduce provider abstraction
- integrate a second compatible source
- implement temporal alignment
- implement actual cross-source reconciliation
- add provider-health evidence

### Research Layer

- perform a zero-cost dataset compatibility pilot
- add Python research modules
- implement a fixed robust statistical baseline
- implement a rolling median/MAD adaptive detector
- implement deterministic controlled fault injection
- use chronological calibration → freeze → held-out evaluation
- compare single-source vs cross-source monitoring
- compare fixed vs adaptive statistical monitoring

### Reliability and Observability

- add Prometheus metrics
- add Grafana dashboards
- introduce deterministic automated tests and CI
- add retry/backoff for recoverable failures
- implement completeness/gap detection
- add replay and DLQ/circuit-breaker patterns where justified

### Extended Platform

Additional technologies such as Go, Kafka, Flink, ClickHouse, MinIO, Spark, Trino, Redis, MongoDB, C++, Kubernetes, GitOps, and an operator-facing React application will be introduced only when each has a concrete engineering or research responsibility.

AI/LLM components remain optional future work for incident explanation and operational assistance. They will not determine whether market data is valid.
