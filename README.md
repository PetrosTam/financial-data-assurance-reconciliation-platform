# FX Operations Automation & Monitoring

A reliability-focused **FX market-data quality, monitoring, alerting, reconciliation, observability, and research platform** built incrementally with evidence-driven engineering.

The current verified runtime is based on **n8n, JavaScript, Alpha Vantage REST, PostgreSQL 16, Docker Compose, Git/GitHub, and Gmail SMTP**.

The broader project evolves this operational foundation toward a provider-neutral market-data assurance platform and an MSc thesis artifact.

> **This is not a trading bot.**  
> The project does not execute trades, generate trading signals, manage positions, perform hedging, or calculate trading P&L. FX prices are treated as operational and research data.

---

## Project Status

The repository distinguishes implementation status explicitly:

- **TESTED** — verified through inspected runtime, database, execution, log, container, delivery, or deterministic test evidence.
- **IMPLEMENTED** — code/config/schema exists, but verification is incomplete.
- **IN PROGRESS** — partially implemented.
- **PLANNED** — accepted target capability, not yet implemented.
- **PROPOSED** — candidate enhancement requiring design or feasibility confirmation.
- **OPTIONAL** — future/laboratory capability.
- **UNKNOWN** — evidence is insufficient.

### Verified End-of-Part-02 State

| Capability | Status | Evidence / interpretation |
|---|---|---|
| Multi-instrument FX ingestion | **TESTED** | EUR/USD, GBP/USD, USD/JPY normalized and persisted in a verified run |
| Workflow lifecycle and failure handling | **TESTED** | `started` / `success` / `failed` paths verified |
| Duplicate-safe quote persistence | **TESTED** | Database uniqueness + conflict-safe persistence |
| Operational anomaly detection | **TESTED** | Wide spread, stale quote, and extreme movement paths |
| Critical email alerting | **TESTED** | Persisted pending alert → Gmail SMTP → `sent` / `failed` |
| Alert delivery state persistence | **TESTED** | `pending`, `sent`, `failed`; `sent_at` on success |
| Environment-based email routing | **TESTED** | Sender/recipient loaded from environment variables |
| n8n state persistence | **TESTED** | Named-volume mount and restoration verified |
| Anomaly lifecycle database schema | **TESTED** | `open` / `acknowledged` / `resolved`, constraint and index verified |
| Fresh PostgreSQL bootstrap | **TESTED** | `001_schema.sql` then `002_alerting_anomaly_lifecycle.sql` verified |
| Operator lifecycle manager | **PLANNED** | Transition workflow/API not yet implemented |
| Provider abstraction | **PLANNED** | Canonical output exists, but only Alpha Vantage integration is implemented |
| Second source | **PLANNED** | Not yet integrated |
| Temporal cross-source reconciliation | **PLANNED** | Do not call current ingestion “reconciliation” |
| Python research layer | **PLANNED** | Defined by the MSc proposal, not current runtime |
| Prometheus / Grafana | **PLANNED** | Not integrated in current runtime |
| Platform API / BFF | **PLANNED** | Target browser/server boundary |
| React/TypeScript operator console | **PLANNED** | No current operator web product |
| Expanded platform stack | **PLANNED / PROPOSED / OPTIONAL** | Target architecture only; no implementation claim |

> `records_processed=3` in the verified three-pair run means **three normalized output records**, not necessarily three newly inserted rows when duplicate conflict handling is active.

---

## Current System Purpose

The current system provides a small but verified operational foundation for:

- FX market-data ingestion
- provider-response validation
- provider-specific normalization into a common internal shape
- PostgreSQL persistence
- duplicate protection
- execution lifecycle tracking
- controlled failure handling
- operational anomaly detection
- persisted anomaly evidence
- critical alert generation
- real email delivery
- delivery-state persistence
- lifecycle-ready anomaly schema
- reproducible local database bootstrap
- secure configuration and checkpoint discipline

The project prioritizes:

1. correctness
2. explicit evidence
3. reproducibility
4. failure transparency
5. idempotency
6. provenance
7. simple verified components before additional complexity

---

## Current Architecture

### Main Operational Flow

```text
Manual Trigger / Schedule Trigger
              |
              v
       Log Run Started
              |
              v
      Generate FX Pairs
              |
              v
     Sequential Pair Loop
              |
              v
        Fetch FX Quote
              |
              v
             Wait
              |
              v
   Validate & Normalize Quote
        /          |           \
       v           v            v
 Persist Quote  Detect Ops   Check Price
 PostgreSQL     Anomalies     Movement
       \           |            /
        \          v           /
         ------ Log Anomaly ----
                  |
                  v
        Is Critical Anomaly?
                  |
               true
                  v
            Create Alert
          status = pending
                  |
                  v
     Send Critical Alert Email
          /               \
     success               error
        |                    |
        v                    v
 Mark Alert Sent      Mark Alert Failed
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
       workflow_runs
```

The workflow export and runtime remain the authoritative source for exact node wiring.

---

## Multi-Instrument FX Ingestion

The current workflow processes:

```text
EUR/USD
GBP/USD
USD/JPY
```

Pairs are generated dynamically by the `Generate FX Pairs` node using:

```text
from_currency
to_currency
```

The same provider integration is therefore reused for all three pairs.

### Sequential Provider Requests

The current integration uses explicit pacing:

```text
Generate FX Pairs
      ↓
Loop Over Items
      ↓
Fetch FX Quote
      ↓
Wait 3 seconds
      ↓
Next item
```

`Loop Over Items` uses:

```text
Batch Size = 1
```

This is a deliberate current-provider pacing mechanism, not a general retry/resilience framework.

### Schedule

The committed production workflow is scheduled every four hours at minute 5.

Manual execution is also available for controlled development and verification.

---

## Current Provider Integration

The implemented provider is **Alpha Vantage** using:

```text
CURRENCY_EXCHANGE_RATE
```

with dynamic request parameters:

```text
from_currency = {{ $json.from_currency }}
to_currency   = {{ $json.to_currency }}
```

API authentication is stored in n8n credentials rather than embedded in workflow logic.

External provider responses are treated as **untrusted input**.

---

## Validation and Normalization

Provider-specific responses are validated before persistence.

### Current Validation Controls

The current normalization path checks:

- provider error payloads
- expected provider response shape
- required currency fields
- numeric bid
- numeric ask
- positive bid
- positive ask
- `ask >= bid`
- presence of timestamp data
- parseable timestamp semantics used by the current adapter

Invalid responses are rejected before quote persistence.

### Current Canonical Quote Shape

The normalized output includes fields such as:

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

Canonical symbols currently include:

```text
EURUSD
GBPUSD
USDJPY
```

### Derived Values

```text
mid_price = (bid + ask) / 2
spread    = ask - bid
spread_bps = (spread / mid_price) * 10000
```

### Important Current Limitation

The current Alpha Vantage normalizer produces a canonical output shape, but that does **not** yet equal a full provider-abstraction layer.

Known gaps include:

- `provider_instrument_id` is currently `NULL` because no provider identifier semantics have yet been implemented for the current adapter.
- raw provider timestamp text is not yet retained separately as `source_timestamp_raw`.
- timezone and timestamp-precision provenance are not yet fully explicit.
- historical/live arrival-time semantics must not be fabricated when unavailable.

These are planned hardening items before multi-provider research and reconciliation.

---

## PostgreSQL Data Model

The current database contains four core operational tables.

### `fx_quotes`

Stores normalized quotes and raw provider payloads.

Representative fields:

```text
symbol
provider_instrument_id
bid
ask
mid_price
spread
source
observed_at
received_at
raw_payload
```

Current logical uniqueness:

```sql
UNIQUE (symbol, observed_at, source)
```

### `workflow_runs`

Stores workflow execution state.

Representative fields:

```text
workflow_name
execution_id
status
records_processed
error_message
started_at
finished_at
```

### `anomalies`

Stores operational/data-quality findings and lifecycle fields.

Representative fields:

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

### `alerts`

Stores alert-delivery state.

Representative fields:

```text
anomaly_id
channel
status
message
sent_at
created_at
```

---

## Duplicate Safety and Idempotency

Quote persistence uses database-backed duplicate protection.

The current uniqueness model is:

```sql
UNIQUE (symbol, observed_at, source)
```

The persistence path uses conflict handling so replaying the same logical quote does not cause an insertion failure.

This provides idempotency for the current logical uniqueness definition.

---

## Workflow Execution Lifecycle

### Run Start

`Log Run Started` writes:

```text
status = started
records_processed = 0
```

along with workflow identity, n8n execution ID, and start timestamp.

### Successful Completion

`Mark Run Success` updates the corresponding row by execution ID.

Successful state:

```text
status = success
records_processed = <normalized output count>
finished_at = <completion timestamp>
```

For the verified three-pair run:

```text
records_processed = 3
```

### Failure Handling

A dedicated workflow:

```text
FX Workflow Error Handler
```

uses:

```text
Error Trigger
      ↓
Mark Run Failed
```

and updates:

```text
status = failed
error_message = <actual failure message>
finished_at = <failure timestamp>
```

Controlled failures were used to verify this path.

---

## Operational Anomaly Detection

Current anomaly types are:

```text
wide_spread
stale_quote
extreme_price_movement
```

The current thresholds are **operational assumptions only**. They are not universal market rules and are not the thesis-calibrated statistical baselines.

### Wide Spread

```text
spread_bps = (spread / mid_price) * 10000
```

Current thresholds:

```text
Warning:  > 2 bps
Critical: > 5 bps
```

### Stale Quote

Current thresholds:

```text
Warning:  > 600 seconds
Critical: > 1800 seconds
```

Freshness is treated as a deterministic operational policy.

### Extreme Price Movement

Current calculation:

```text
movement_bps =
    abs(
        (current_mid_price - previous_mid_price)
        / previous_mid_price
    ) * 10000
```

Current thresholds:

```text
Warning:  > 20 bps
Critical: > 50 bps
```

The previous quote is retrieved with parameterized SQL.

### Critical Multi-Provider Safety Gap

The current previous-quote lookup is based on symbol/time semantics and is not yet explicitly provider/source-safe.

Before introducing a second live provider, the lookup must be made source/provider-scoped or moved into explicitly defined cross-source reconciliation logic.

Accidental cross-provider baselining must not be allowed.

---

## Anomaly Persistence

Detected findings use a common structure.

Current severity values:

```text
info
warning
critical
```

`details` is stored in PostgreSQL `JSONB` for type-specific evidence.

If no anomaly is detected, the monitoring branch emits no anomaly record and normal quote processing continues.

### Current Threshold-Provenance Debt

The current `threshold_value` field stores the base operational detection threshold, while critical severity may be determined by a second hardcoded boundary.

Future configuration-driven rules should preserve:

- severity-specific threshold
- rule identifier
- configuration version
- effective configuration provenance

---

## Critical Alerting

Critical anomalies enter the verified email-alert path:

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

### Current Delivery States

```text
pending
sent
failed
```

On success:

```text
status = sent
sent_at = <delivery timestamp>
```

On failure:

```text
status = failed
```

### Verified Delivery Evidence

The current Gmail SMTP path has been verified using:

- deterministic test input
- configured n8n SMTP credential
- environment-based sender/recipient
- successful SMTP acceptance
- real Gmail inbox delivery
- persisted success state
- persisted failure path
- cleanup of temporary test artifacts

Email/Gmail SMTP is the only currently implemented alert channel.

Slack, Teams, Jira, ServiceNow, and PagerDuty remain future adapters.

---

## Email Configuration and Secret Handling

SMTP authentication remains in the n8n credential:

```text
FX Ops Gmail SMTP
```

The workflow reads:

```text
$env.ALERT_EMAIL_FROM
$env.ALERT_EMAIL_TO
```

Real local values are stored in:

```text
.env
```

and are excluded from Git.

A safe template is committed as:

```text
.env.example
```

Example:

```text
ALERT_EMAIL_FROM=alerts@example.com
ALERT_EMAIL_TO=operator@example.com
```

No real personal alert address should be committed in workflow exports.

---

## Anomaly Lifecycle Schema

Migration:

```text
sql/002_alerting_anomaly_lifecycle.sql
```

adds:

```text
status
acknowledged_at
resolution_reason
```

The base schema already contains:

```text
resolved_at
```

Current allowed states:

```text
open
acknowledged
resolved
```

The migration also creates:

```text
idx_anomalies_status_detected_at
```

### Current Lifecycle Status

The lifecycle schema is **TESTED**.

The operator transition manager is **not implemented**.

The exact next feature is:

```text
FX Anomaly Lifecycle Manager
```

It must implement:

- anomaly/action validation
- legal transition checks
- `open → acknowledged → resolved`
- timestamp updates
- resolution reason
- deterministic success tests
- invalid-transition tests
- missing-ID / malformed-input tests
- database inspection
- auditability
- cleanup
- Git diff/status/secret verification before completion

Future case-management states such as `investigating`, `mitigated`, or `reopened` require a separate migration/API/UI change and are not current Part-02 states.

---

## Fresh PostgreSQL Bootstrap

A fresh PostgreSQL volume automatically applies:

```text
001_schema.sql
      ↓
002_alerting_anomaly_lifecycle.sql
```

Docker Compose mounts both under:

```text
/docker-entrypoint-initdb.d/
```

An isolated PostgreSQL 16 bootstrap test verified:

- `001_schema.sql` executed
- `002_alerting_anomaly_lifecycle.sql` executed
- lifecycle columns exist
- `status` defaults to `open`
- `anomalies_status_check` exists
- allowed states are correct
- `idx_anomalies_status_detected_at` exists
- initialization completed without relevant `ERROR` / `FATAL`
- the temporary test container was removed afterward

---

## n8n Persistence

n8n state is persisted through:

```yaml
volumes:
  - n8n_data:/home/node/.n8n
```

Persistence verification included:

- resolved Docker Compose inspection
- actual container mount inspection
- workflow export checks
- container recreation
- successful restoration of the existing n8n account/workflow state

A named volume declaration alone is not considered sufficient evidence; the service mount must be verified.

---

## Security and Repository Hygiene

Current engineering rules include:

- API keys stay outside Git
- SMTP passwords stay outside Git
- database secrets stay outside Git
- `.env` and `.env.*` remain ignored except safe `.env.example`
- n8n credentials hold provider/SMTP authentication
- dynamic SQL uses parameterization where applicable
- workflow exports are inspected for:
  - personal emails
  - API keys
  - passwords
  - bearer/auth tokens
  - authorization headers
  - `client_secret`
  - pinned test data
- raw licensed research data must remain local unless redistribution rights explicitly allow otherwise
- public checkpoints exclude:
  - `.env`
  - `.git`
  - runtime volumes
  - backups
  - logs
  - licensed raw datasets
  - secrets

Project checkpoints are created from committed state using `git archive`, not by manually zipping a working directory.

---

## Current Tech Stack

### Implemented / Current

- n8n
- JavaScript
- Alpha Vantage REST API
- PostgreSQL 16
- Docker Compose
- Git / GitHub
- Gmail SMTP

### Planned / Proposed / Optional Target Landscape

The broader platform may introduce components only when each has a distinct responsibility, a simpler alternative has been considered, and success criteria can be verified.

| Domain | Target technologies / tools | Current status |
|---|---|---|
| Orchestration | n8n, Temporal.io, Apache Airflow | n8n current; others planned |
| Languages | Python, Go, Java, JavaScript, TypeScript, C++, optional Kotlin/Swift | JS current; others planned/optional |
| APIs/contracts | REST, WebSocket, SSE, gRPC, GraphQL, OpenAPI, Protobuf, AsyncAPI, Pact | outbound REST current; owned contracts planned |
| Streaming | Kafka, Schema Registry, Kafka Connect, Debezium, Flink, Strimzi, Flink Operator, MirrorMaker 2 | planned |
| Data stores | PostgreSQL, ClickHouse, Redis, MongoDB | PostgreSQL current; others planned |
| Lakehouse/analytics | MinIO, Parquet, Iceberg, Spark, Trino, dbt, OpenMetadata | planned |
| Observability | OpenTelemetry, Jaeger, Prometheus, Grafana, Alertmanager, Loki, Sentry, Pyroscope | planned |
| Security | OIDC/OAuth2/JWT, RBAC, OpenFGA, Vault, mTLS, OPA/Gatekeeper | planned |
| Frontend | React, TypeScript, Redux Toolkit, TanStack, Vite, Storybook | planned |
| Delivery/platform | Terraform, Kubernetes, Helm, GitOps/Argo CD, Argo Rollouts, KEDA | planned |
| Testing/resilience | Testcontainers, Pact, Playwright, k6, Toxiproxy, Chaos Mesh, Hypothesis, Schemathesis, mutation testing, OWASP ZAP | planned |
| Research reproducibility | MLflow, manifests/hashes/Git SHA, dataset/version tracking | planned |
| Optional AIOps | governed LLM/RAG assistant and optional inference lab | optional / final maturity |

Presence in this table is **not an implementation claim**.

---

## Planned Platform Boundary

The target browser boundary is:

```text
React / TypeScript Console
          |
          v
Platform API / BFF
          |
          +--> domain services
          +--> PostgreSQL / analytical stores via server-side clients
          +--> Kafka / Flink / n8n / Kubernetes / Argo / Prometheus adapters
          +--> authorization and audit boundary
```

The browser must never receive:

- database credentials
- provider secrets
- Kafka credentials
- Kubernetes credentials
- Vault credentials
- unrestricted infrastructure tokens

The product boundary is server-side and typed. Internally, each subsystem should use the appropriate protocol, SDK, driver, or API rather than forcing REST everywhere.

---

## Project Structure

Current Part-02 repository structure:

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

Future modules will be introduced incrementally rather than pre-created without need.

---

## Testing and Verification Evidence

Verified evidence includes:

- three-pair ingestion
- three normalized outputs in a verified current run
- PostgreSQL persistence inspection
- duplicate-safe reprocessing
- `started` / `success` execution lifecycle
- controlled production failure
- original failed run updated by error workflow
- provider/malformed response validation
- wide-spread detection
- stale-quote detection
- extreme price-movement detection
- critical anomaly routing
- persisted pending alert
- successful Gmail SMTP acceptance
- real Gmail inbox delivery
- `sent` + `sent_at`
- alert failure path
- environment-based email routing
- no hardcoded personal email in committed workflow export
- empty n8n `pinData` in committed workflow export
- n8n persistent-volume restoration
- anomaly lifecycle columns/constraint/index
- isolated fresh PostgreSQL bootstrap
- ordered `001 → 002` migration execution
- temporary test cleanup
- checkpoint hygiene inspection

A capability is **TESTED only after its result is inspected**.

---

## Known Technical Debt

The current Part-02 implementation intentionally retains several known gaps that must be resolved before later milestones.

### Source-Safe Previous Quote

The current extreme-movement previous-quote query is not yet provider/source-scoped.

**Required before second-provider operation.**

### Timestamp / Timezone / Precision Provenance

The current adapter does not yet preserve the full raw timestamp and explicit timezone/precision semantics required by the planned canonical research representation.

### Provider Instrument Semantics

`provider_instrument_id` exists in the schema but is not yet populated with verified Alpha Vantage-specific identifier semantics.

### Threshold / Configuration Provenance

Current thresholds are hardcoded operational assumptions. Future rules must be versioned and retain severity-specific threshold/config provenance.

### Normalized vs Inserted Counts

`records_processed` currently represents normalized output count.

Future observability may separate:

```text
records_normalized
records_inserted
records_duplicate
records_rejected
```

### Lifecycle Transition Manager

The database schema is ready, but transition legality is not yet enforced by an operator workflow/API.

---

## MSc Thesis Direction

The platform is being evolved into an MSc thesis artifact titled:

**Evaluating Adaptive Anomaly Detection and Cross-Source Reconciliation for Operational FX Market Data Quality**

The research layer remains separate from current runtime claims.

### Research Question 1

> **Does temporally aligned cross-source evidence improve the classification of injected source-specific data-quality faults in FX market data compared with single-source monitoring?**

### Research Question 2

> **How does adaptive statistical anomaly detection compare with an equivalent fixed statistical baseline under changing reference FX market conditions and controlled price/spread faults?**

### Core Research Boundaries

- Cross-source disagreement is **contextual evidence, not ground truth**.
- Ground truth comes from **controlled fault injection**.
- Non-injected historical observations are **reference observations**, not assumed universally fault-free.
- Structural validity remains deterministic.
- Freshness/staleness remains an operational policy.
- The fixed-versus-adaptive statistical comparison focuses primarily on:
  - spread
  - price movement
- The primary adaptive approach is a past-only rolling median/MAD detector.
- The fixed baseline uses equivalent robust statistics calibrated chronologically and frozen before evaluation.
- Random row-level train/test splitting is not used for the main time-series experiment.
- Calibration → protocol/config freeze → chronological held-out evaluation.
- Reconciliation must explicitly define:
  - causal vs symmetric matching
  - maximum tolerance
  - tie handling
  - one-to-one vs reusable matching
  - unmatched behaviour
  - provider age
  - match coverage/confidence
- Operational claims must not use future look-ahead.
- Historical files must not be assigned fabricated live arrival-time semantics.

### 2×2 Experimental Design

| | Single-source | Cross-source |
|---|---|---|
| Fixed | System A | System C |
| Adaptive | System B | System D |

### Research Data

The thesis has a zero-cost research-data requirement.

**TrueFX and Dukascopy remain candidate sources only.**

The final pair will be accepted only after a five-day EUR/USD compatibility pilot verifies:

- source schema
- timestamp semantics
- UTC normalization feasibility
- bid/ask validity
- duplicate behaviour
- overlapping market coverage
- temporal matching feasibility
- natural midpoint divergence
- natural spread divergence
- data-use suitability

A negative pilot result is valid and may lead to selection of another research-suitable zero-cost pair.

---

## Engineering and Research Independence

The platform is provider-neutral and institution-independent.

Technology selection is based on:

- concrete responsibility
- simpler alternative
- measurable success criterion
- verification plan
- dependency order
- actual evidence

Public industry documentation may inform general engineering patterns, but it is not a design authority and does not prove any proprietary architecture.

---

## Development Roadmap

The current engineering order remains:

```text
Lifecycle Manager
      ↓
Configuration-driven rules + reference data
      ↓
Provider abstraction
      ↓
Second source
      ↓
Temporal reconciliation
      ↓
Research core
      ↓
Observability / BFF / productisation
      ↓
Extended streaming, analytics, resilience, security and platform labs
```

### 1. Lifecycle Manager

Exact next implementation block:

- operator action input
- anomaly/action validation
- legal transition enforcement
- `open → acknowledged → resolved`
- timestamp/resolution handling
- deterministic success/failure tests
- database inspection
- auditability
- cleanup
- Git verification

### 2. Configuration and Reference Data

- configuration-driven instruments
- versioned operational thresholds
- severity-specific threshold provenance
- effective-dated canonical/provider mappings
- explicit provider instrument semantics

### 3. Provider Abstraction

- provider-neutral contracts
- source-specific adapters
- source-safe quote history semantics
- provider health

### 4. Second Source and Temporal Reconciliation

- second compatible provider/source
- temporal alignment
- causal matching policy
- divergence evidence
- coverage / unmatched metrics

Do not describe two-source ingestion as reconciliation until temporal comparison exists.

### 5. Research Core

- dataset compatibility pilot
- Python adapters
- canonical research representation
- fixed robust baseline
- rolling median/MAD adaptive detector
- deterministic fault injection
- 2×2 experiment
- leakage-safe chronological evaluation
- statistical analysis and sensitivity reporting

### 6. Observability and Product Boundary

- Prometheus / Grafana
- OpenTelemetry path
- Platform API / BFF
- React/TypeScript console
- typed APIs/contracts
- role-controlled operator actions

### 7. Extended Platform

Only after simpler verified baselines justify them:

- Kafka / Schema Registry / Kafka Connect
- Flink
- ClickHouse
- MinIO / Parquet / Iceberg
- Spark / Trino / dbt
- Redis / MongoDB where justified
- Temporal / Airflow
- C++ replay
- Kubernetes / Helm / Argo CD
- Vault / OIDC / fine-grained authorization
- progressive delivery / autoscaling
- load / chaos / recovery labs
- advanced observability
- developer portal / governance
- experiment registry / dataset versioning
- optional advisory AIOps

---

## Definition of Done

A milestone is complete only when:

1. implementation exists
2. key success and failure paths are tested
3. relevant runtime/database/log/metric/trace/container/browser evidence is inspected
4. temporary test artifacts are cleaned
5. `git diff` / `git status` and secret checks are inspected
6. committed `HEAD` equals the tested state
7. push is confirmed
8. documentation/checkpoint agrees with that exact state

If those conditions are not satisfied, the capability remains at a lower status.

---

## Checkpoint and Source-of-Truth Discipline

For implementation status, stronger evidence wins:

```text
Runtime / inspected execution evidence
        >
Committed repository HEAD / verified checkpoint
        >
Current technical guide
        >
MSc proposal for research goals and planned architecture
        >
older documents/history
```

The MSc proposal does **not** upgrade runtime status.

The Part-02 checkpoint is historical committed evidence and should not be rewritten merely because later documentation or research framing changes.

Current repository HEAD/push state beyond the verified checkpoint must be re-checked when development resumes.

---

## Current Next Step

> **Implement the FX Anomaly Lifecycle Manager.**

Success requires legal transition enforcement, deterministic success/failure coverage, inspected PostgreSQL evidence, cleanup, Git verification, and documentation synchronized to the tested committed state.
