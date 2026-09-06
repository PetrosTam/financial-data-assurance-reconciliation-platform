# Financial Data Assurance & Reconciliation Platform

**Independent financial data assurance and reconciliation platform for reliable multi-source processing, temporal reconciliation, observability, operational evidence and provider intelligence.**

The current implementation is an **FX market-data assurance profile** built incrementally with evidence-driven engineering. The verified runtime uses **n8n, JavaScript, Alpha Vantage REST, PostgreSQL 16, Docker Compose, Git/GitHub, and Gmail SMTP**.

Today the platform provides single-provider FX ingestion, validation, normalization, persistence, workflow lifecycle tracking, operational anomaly detection, critical alerting, anomaly lifecycle management, and durable audit evidence. Multi-provider processing, temporal cross-source reconciliation, advanced observability, and provider intelligence are planned capabilities and are not current runtime claims.

> **Scope boundary:** this is not a trading bot. The platform does not execute or route trades, generate trading signals, manage positions, perform hedging, or calculate trading P&L. Market prices are treated as operational data to be validated, monitored, reconciled, and evidenced.

---

## Project Status

The repository uses explicit implementation states:

- **TESTED** — verified through inspected runtime, database, execution, log, container, delivery, or deterministic test evidence.
- **IMPLEMENTED** — code/config/schema exists, but verification is incomplete.
- **IN PROGRESS** — partially implemented.
- **PLANNED** — accepted target capability, not yet implemented.
- **PROPOSED** — candidate enhancement requiring design or feasibility confirmation.
- **OPTIONAL** — future or laboratory capability.
- **UNKNOWN** — evidence is insufficient.

### Current Verified State

| Capability | Status | Evidence / interpretation |
|---|---|---|
| Multi-instrument FX ingestion | **TESTED** | EUR/USD, GBP/USD, and USD/JPY normalized and persisted in verified runs |
| Workflow lifecycle and failure handling | **TESTED** | `started` / `success` / `failed` paths verified |
| Duplicate-safe quote persistence | **TESTED** | Database uniqueness plus conflict-safe persistence |
| Operational anomaly detection | **TESTED** | Wide-spread, stale-quote, and extreme-movement paths |
| Critical email alerting | **TESTED** | Persisted pending alert → Gmail SMTP → `sent` / `failed` |
| Alert delivery-state persistence | **TESTED** | `pending`, `sent`, `failed`; `sent_at` on success |
| Environment-based email routing | **TESTED** | Sender and recipient loaded from environment variables |
| n8n state persistence | **TESTED** | Persistent volume mount and state restoration verified |
| Anomaly lifecycle database schema | **TESTED** | `open` / `acknowledged` / `resolved`, lifecycle columns, constraints, and indexes verified |
| Lifecycle audit trail | **TESTED** | Atomic `anomaly_lifecycle_events` persistence with constrained transitions and workflow/execution provenance |
| Operator lifecycle manager | **TESTED** | Authenticated webhook validates requests, enforces legal transitions, blocks stale writes, and returns controlled HTTP responses |
| Fresh PostgreSQL bootstrap | **TESTED** | Isolated PostgreSQL 16 bootstrap verified ordered `001 → 002 → 003` execution and resulting schema |
| Configuration-driven rules and reference data | **PLANNED — NEXT** | Required before provider abstraction and multi-source processing |
| Provider abstraction | **PLANNED** | Canonical output exists, but only Alpha Vantage integration is implemented |
| Second independent source | **PLANNED** | Not yet integrated |
| Temporal cross-source reconciliation | **PLANNED** | Current single-provider ingestion must not be described as reconciliation |
| Prometheus / Grafana | **PLANNED** | Not integrated in the current runtime |
| Platform API / BFF | **PLANNED** | Target browser/server boundary |
| React / TypeScript operator console | **PLANNED** | No current browser product |
| Provider intelligence and scorecards | **PLANNED** | Depends on multi-provider evidence and temporal comparison |

> `records_processed=3` means **three normalized output records** for the current three-pair workflow. It does not guarantee three new database inserts when duplicate conflict handling is active.

---

## Current Runtime Identity

The current Docker Compose runtime uses:

```text
Compose project: financial-data-assurance-reconciliation-platform
PostgreSQL container: fdar-postgres
n8n container: fdar-n8n
PostgreSQL database: fdar
PostgreSQL role: fdar
PostgreSQL volume: fdar-postgres-data
n8n volume: fdar-n8n-data
```

The service-level PostgreSQL hostname used by n8n remains:

```text
postgres
```

because containers communicate through the Docker Compose service network rather than the host-facing container name.

---

## Core Engineering Principles

The platform prioritizes:

1. correctness before scale
2. evidence before status claims
3. deterministic validation at boundaries
4. provider-neutral internal contracts
5. explicit provenance
6. idempotent persistence
7. failure transparency
8. reproducible bootstrap and verification
9. least privilege and secret isolation
10. simple verified components before additional infrastructure

Technology is added only when it has a distinct responsibility, a simpler alternative has been considered, and success can be measured.

---

## Quick Start

### Prerequisites

- Git
- Docker Desktop with Docker Compose
- an Alpha Vantage API credential
- SMTP credentials if email alerting will be exercised

### 1. Clone the repository

```bash
git clone https://github.com/PetrosTam/financial-data-assurance-reconciliation-platform.git
cd financial-data-assurance-reconciliation-platform
```

### 2. Create local environment configuration

Create `.env` from `.env.example` and provide local values for the required environment variables.

Example shape:

```dotenv
POSTGRES_PASSWORD=<strong-local-password>
ALERT_EMAIL_FROM=<sender-address>
ALERT_EMAIL_TO=<recipient-address>
```

Do not commit `.env` or real credentials.

### 3. Create the persistent Docker volumes

The current Compose configuration uses explicit external volumes:

```bash
docker volume create fdar-postgres-data
docker volume create fdar-n8n-data
```

### 4. Validate the resolved Compose configuration

```bash
docker compose config --no-interpolate
```

### 5. Start the platform

```bash
docker compose up -d
```

### 6. Inspect runtime state

```bash
docker ps --filter "name=fdar"
docker inspect fdar-postgres --format '{{.State.Health.Status}}'
```

Expected PostgreSQL health state:

```text
healthy
```

### 7. Inspect the database

```bash
docker exec fdar-postgres psql -U fdar -d fdar -c "\dt"
```

The current schema should contain:

```text
alerts
anomalies
anomaly_lifecycle_events
fx_quotes
workflow_runs
```

### 8. Open n8n

```text
http://localhost:5678
```

Configure the required n8n credentials locally. Secret values must remain outside Git.

---

## n8n Credentials

The current workflows depend on local n8n credentials with these logical names:

```text
Alpha Vantage API
FDAR PostgreSQL
FDAR Gmail SMTP
FDAR Lifecycle Webhook Header Auth
```

### PostgreSQL Credential

Expected connection shape:

```text
Host: postgres
Database: fdar
User: fdar
Password: <local POSTGRES_PASSWORD>
```

### Lifecycle Header Authentication

The lifecycle webhook uses a Header Auth credential with header name:

```text
X-FDAR-Lifecycle-Token
```

The token value is secret and must not be committed, logged intentionally, pasted into documentation, or exposed in screenshots.

---

## Current Workflows

The repository contains three n8n workflow exports:

```text
FDAR FX Market Data Pipeline - Alpha Vantage
FDAR Workflow Error Handler
FDAR Anomaly Lifecycle Manager
```

Current export files:

```text
workflows/fdar-fx-market-data-pipeline-alpha-vantage.json
workflows/fdar-workflow-error-handler.json
workflows/fdar-anomaly-lifecycle-manager.json
```

Workflow exports are configuration artifacts. Runtime execution evidence remains necessary before a capability is marked **TESTED**.

---

## Current Architecture

### Main Market-Data Flow

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

### Anomaly Lifecycle Flow

```text
Authenticated Webhook
        |
        v
Extract Webhook Request
        |
        v
Validate Lifecycle Request
        |
        v
Read Current Anomaly
        |
        v
Validate Legal Transition
        |
        v
Apply Lifecycle Transition
        |
        v
Verify Transition Applied
        |
        v
Respond to Webhook
```

Node failures are routed through:

```text
Build Webhook Error Response
        |
        v
Respond Lifecycle Error
```

---

## Multi-Instrument FX Ingestion

The current market-data workflow processes:

```text
EUR/USD
GBP/USD
USD/JPY
```

Pairs are generated dynamically using:

```text
from_currency
to_currency
```

The same provider integration is reused for all three instruments.

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

This is a current-provider pacing mechanism. It is not a general retry, backoff, rate-limit, or resilience framework.

### Schedule

The committed market-data workflow is scheduled every four hours at minute 5.

Manual execution is also available for controlled verification.

---

## Current Provider Integration

The implemented provider is **Alpha Vantage** using:

```text
CURRENCY_EXCHANGE_RATE
```

Dynamic request parameters are derived from the current pair:

```text
from_currency = {{ $json.from_currency }}
to_currency   = {{ $json.to_currency }}
```

API authentication is stored in an n8n credential rather than embedded in workflow logic.

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
- timestamp parseability under the current adapter semantics

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
mid_price  = (bid + ask) / 2
spread     = ask - bid
spread_bps = (spread / mid_price) * 10000
```

### Current Canonical-Model Gaps

The current normalizer provides a common output shape, but this is not yet a complete provider-abstraction layer.

Known gaps include:

- `provider_instrument_id` is not yet populated with verified provider-specific identifier semantics
- raw provider timestamp text is not yet retained separately as `source_timestamp_raw`
- timezone and timestamp-precision provenance are not yet fully explicit
- arrival-time semantics must not be fabricated when unavailable
- configuration/version provenance is not yet attached to every derived monitoring decision

These items must be hardened before multi-provider processing.

---

## PostgreSQL Data Model

The current database contains five operational tables.

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

Stores operational/data-quality findings and lifecycle state.

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

### `anomaly_lifecycle_events`

Stores durable evidence for successful lifecycle transitions.

Representative fields:

```text
anomaly_id
action
from_status
to_status
resolution_reason
workflow_name
execution_id
created_at
```

The table constrains the supported transition model and uses a foreign key to `anomalies(id)` with `ON DELETE RESTRICT`.

---

## Duplicate Safety and Idempotency

Quote persistence uses database-backed duplicate protection.

Current uniqueness:

```sql
UNIQUE (symbol, observed_at, source)
```

The persistence path uses conflict handling so replaying the same logical quote does not fail because of a duplicate insert.

This provides idempotency for the current logical uniqueness definition.

It does **not** yet solve every future multi-provider identity or replay problem; those semantics must be defined explicitly as the platform expands.

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

For the current three-pair workflow, a verified successful run produced:

```text
records_processed = 3
```

### Failure Handling

The dedicated workflow:

```text
FDAR Workflow Error Handler
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

Controlled failures were used to verify the failure path.

---

## Operational Anomaly Detection

Current anomaly types are:

```text
wide_spread
stale_quote
extreme_price_movement
```

The current thresholds are **operational assumptions only**. They are not universal market rules.

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

Freshness is currently treated as a deterministic operational policy.

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

### Multi-Provider Safety Requirement

The current previous-quote lookup is not yet explicitly provider/source-safe.

Before introducing a second live provider, previous-quote semantics must become source/provider-scoped or be replaced by explicitly defined temporal cross-source comparison logic.

Accidental cross-provider baselining must not be allowed.

---

## Anomaly Persistence

Current severity values are:

```text
info
warning
critical
```

Type-specific evidence is stored in PostgreSQL `JSONB` through the `details` field.

If no anomaly is detected, the monitoring branch emits no anomaly row and normal quote processing continues.

### Threshold-Provenance Debt

The current `threshold_value` field stores the base operational threshold, while critical severity may be determined by a second hardcoded boundary.

Configuration-driven rules should preserve:

- rule identifier
- rule version
- severity-specific threshold
- effective configuration version
- configuration provenance
- evaluation timestamp

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

### Delivery States

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

The Gmail SMTP path has been verified using:

- deterministic test input
- configured n8n SMTP credential
- environment-based sender/recipient
- successful SMTP acceptance
- real inbox delivery
- persisted success state
- persisted failure path
- cleanup of temporary test artifacts

Email/Gmail SMTP is the only currently implemented alert channel.

Other notification or incident-management channels remain future adapters.

---

## Email Configuration

SMTP authentication remains in the n8n credential:

```text
FDAR Gmail SMTP
```

The workflow reads:

```text
$env.ALERT_EMAIL_FROM
$env.ALERT_EMAIL_TO
```

Real local values belong in `.env`, which must remain excluded from Git.

A safe committed template may contain placeholders only.

---

## Anomaly Lifecycle Management

Migration:

```text
sql/002_alerting_anomaly_lifecycle.sql
```

provides:

```text
status
acknowledged_at
resolved_at
resolution_reason
```

Current states:

```text
open
acknowledged
resolved
```

Audit migration:

```text
sql/003_anomaly_lifecycle_audit.sql
```

creates:

```text
anomaly_lifecycle_events
```

with constrained `acknowledge` / `resolve` actions, legal `from_status → to_status` combinations, workflow/execution provenance, and an `ON DELETE RESTRICT` relationship to the parent anomaly.

### FDAR Anomaly Lifecycle Manager

The operator lifecycle workflow is **TESTED**.

Current command shape:

```json
{
  "anomaly_id": 123,
  "action": "acknowledge"
}
```

Resolution requires a reason:

```json
{
  "anomaly_id": 123,
  "action": "resolve",
  "resolution_reason": "Verified and closed by operator"
}
```

Supported transitions:

```text
open → acknowledged
acknowledged → resolved
```

The workflow uses the previously read state as an optimistic-concurrency precondition on the update, preventing a stale request from silently overwriting a newer state.

Successful state mutation and audit insertion occur atomically so a successful lifecycle update and its corresponding audit event remain coupled.

### Lifecycle Endpoint

Current webhook path:

```text
fdar-anomaly-lifecycle
```

Header authentication:

```text
X-FDAR-Lifecycle-Token: <secret-token>
```

In n8n test mode, the endpoint is available only while **Listen for test event** is active:

```text
http://localhost:5678/webhook-test/fdar-anomaly-lifecycle
```

When the workflow is active for production execution, n8n uses the production webhook route:

```text
http://localhost:5678/webhook/fdar-anomaly-lifecycle
```

### Verified HTTP Contract

```text
403  authentication denial
400  invalid action or missing required resolution reason
404  anomaly not found
409  illegal lifecycle transition
200  successful acknowledge or resolve
```

Future lifecycle states require an explicit schema/API/workflow change and must not be introduced implicitly.

---

## Fresh PostgreSQL Bootstrap

A fresh PostgreSQL data directory applies the migration chain in order:

```text
001_schema.sql
      ↓
002_alerting_anomaly_lifecycle.sql
      ↓
003_anomaly_lifecycle_audit.sql
```

Docker Compose mounts the three SQL files under:

```text
/docker-entrypoint-initdb.d/
```

An isolated PostgreSQL 16 bootstrap verification confirmed:

- ordered `001 → 002 → 003` execution
- all five core tables exist
- table ownership is `fdar`
- `status` defaults to `open`
- `anomalies_status_check` allows `open`, `acknowledged`, `resolved`
- lifecycle columns exist
- lifecycle-event primary key exists
- transition checks exist
- `ON DELETE RESTRICT` foreign key exists
- anomaly lifecycle indexes exist
- initialization completed without relevant `ERROR`, `FATAL`, or `PANIC`
- temporary verification resources were removed afterward

Do not destroy the persistent runtime volume merely to re-test bootstrap behavior. Use isolated temporary resources for destructive bootstrap verification.

---

## n8n Persistence

n8n state is persisted at:

```text
/home/node/.n8n
```

through the external volume:

```text
fdar-n8n-data
```

Persistence verification includes both the declared Compose configuration and the actual container mount.

A volume declaration alone is not sufficient evidence; the running service must mount it at the expected application path.

---

## Security and Repository Hygiene

Current engineering rules:

- provider API keys stay outside Git
- SMTP passwords stay outside Git
- database passwords stay outside Git
- lifecycle authentication tokens stay outside Git
- `.env` and local secret-bearing environment files remain ignored
- n8n credentials hold provider, SMTP, PostgreSQL, and lifecycle authentication secrets
- privileged lifecycle requests are authenticated before mutation logic executes
- dynamic SQL uses parameterization where applicable
- workflow exports are inspected for secret leakage
- committed exports must not contain real personal email addresses
- committed exports must not contain API keys, passwords, tokens, authorization headers, `client_secret`, or pinned secret-bearing test data
- raw provider data must be handled according to its applicable data-use terms
- runtime volumes, backups, local logs, and secret files must not be committed

Raw webhook execution data can contain request headers. Execution retention and access must therefore be treated as part of the security boundary.

---

## Current Tech Stack

### Implemented

| Domain | Technology | Responsibility | Status |
|---|---|---|---|
| Workflow orchestration | n8n | ingestion, validation orchestration, monitoring, alerting, lifecycle workflows | **TESTED** |
| Workflow logic | JavaScript | validation, normalization, rule evaluation, request shaping | **TESTED** |
| Market-data provider | Alpha Vantage REST | current FX quote source | **TESTED** |
| Operational database | PostgreSQL 16 | quotes, runs, anomalies, alerts, lifecycle audit | **TESTED** |
| Local runtime | Docker Compose | reproducible local service orchestration | **TESTED** |
| Source control | Git / GitHub | versioned code/configuration and reviewable change history | **CURRENT** |
| Notification channel | Gmail SMTP | current critical-alert delivery | **TESTED** |

### Planned Technology Landscape

Future technology adoption is responsibility-driven rather than checklist-driven.

| Domain | Candidate technologies | Purpose | Status |
|---|---|---|---|
| Service/backend layer | Python, Go, Java, TypeScript | provider adapters, APIs, evaluation services, platform services | **PLANNED / PROPOSED** |
| APIs/contracts | REST, WebSocket, SSE, gRPC, OpenAPI, Protobuf, AsyncAPI, Pact | typed integration boundaries and contract testing | **PLANNED** |
| Streaming | Kafka, Schema Registry, Kafka Connect, Debezium, Flink | durable event backbone and event-time processing when justified | **PLANNED** |
| Data stores | PostgreSQL, ClickHouse, Redis, MongoDB | operational, analytical, cache/state, and document responsibilities | **PLANNED / PROPOSED** |
| Analytical storage | MinIO, Parquet, Iceberg, Spark, Trino, dbt | replay, historical analysis, quality analytics, reproducibility | **PLANNED** |
| Observability | OpenTelemetry, Prometheus, Grafana, Alertmanager, Loki, Jaeger, Sentry, Pyroscope | metrics, logs, traces, errors, profiling | **PLANNED** |
| Frontend | React, TypeScript, Redux Toolkit, TanStack, Vite, Storybook | operator and provider-intelligence console | **PLANNED** |
| Platform delivery | Terraform, Kubernetes, Helm, Argo CD, KEDA | infrastructure, deployment, scaling, and GitOps | **PLANNED** |
| Security | OIDC/OAuth2, RBAC, OpenFGA, Vault, mTLS, OPA | authentication, authorization, secret management, policy | **PLANNED** |
| Verification | Testcontainers, Playwright, k6, Toxiproxy, Chaos Mesh, API fuzz/property testing, mutation testing | integration, E2E, performance, failure, and recovery testing | **PLANNED** |
| Reproducibility | manifests, hashes, Git SHA, dataset/version tracking, MLflow where justified | repeatable evaluation and evidence traceability | **PLANNED** |

Presence in this table is not an implementation claim.

---

## Planned Platform Boundary

The future browser boundary is intentionally server-side:

```text
React / TypeScript Console
          |
          v
Platform API / BFF
          |
          +--> domain services
          +--> PostgreSQL / analytical stores
          +--> workflow / streaming / observability adapters
          +--> authentication / authorization
          +--> audit boundary
```

The browser must never receive unrestricted:

- database credentials
- provider secrets
- streaming-platform credentials
- infrastructure credentials
- Vault credentials
- privileged backend tokens

Privileged writes require authentication, authorization, validation, and audit evidence.

---

## Provider Intelligence Direction

Provider intelligence is a planned product capability that becomes meaningful only after independent provider evidence exists.

Planned capabilities include:

- provider health and availability metrics
- data-quality scorecards
- temporal coverage metrics
- divergence and unmatched-event metrics
- latency/age evidence where semantics are actually available
- provider certification checks
- provider migration assurance
- configuration replay/change assurance
- lineage and blast-radius evidence

Provider disagreement is evidence to investigate; it is not automatically proof that either provider is wrong.

---

## Project Structure

```text
.
├── docs/
│   └── architecture.md
├── sql/
│   ├── 001_schema.sql
│   ├── 002_alerting_anomaly_lifecycle.sql
│   └── 003_anomaly_lifecycle_audit.sql
├── workflows/
│   ├── fdar-anomaly-lifecycle-manager.json
│   ├── fdar-fx-market-data-pipeline-alpha-vantage.json
│   └── fdar-workflow-error-handler.json
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

New modules should be introduced only when their responsibility is concrete and the dependency order justifies them.

---

## Testing and Verification Evidence

Current verified evidence includes:

- three-pair FX ingestion
- normalized output generation
- PostgreSQL quote persistence
- duplicate-safe reprocessing
- `started` / `success` workflow lifecycle
- controlled production failure handling
- provider-response validation
- wide-spread detection
- stale-quote detection
- extreme price-movement detection
- critical anomaly routing
- persisted pending alert
- successful Gmail SMTP delivery
- persisted alert success state
- alert failure state
- environment-based alert routing
- n8n persistent-volume restoration
- lifecycle schema verification
- lifecycle authentication denial
- invalid lifecycle request handling
- missing-anomaly handling
- illegal-transition handling
- successful lifecycle transitions
- persisted acknowledgement and resolution metadata
- optimistic-concurrency stale-write rejection
- atomic lifecycle audit persistence
- isolated fresh PostgreSQL bootstrap
- migration-order verification
- runtime container/database identity verification
- workflow export JSON validation
- secret-pattern inspection
- temporary verification-resource cleanup

A capability remains below **TESTED** until the relevant result has been inspected.

---

## Known Technical Debt

### 1. Source-Safe Previous Quote

The current extreme-movement previous-quote lookup is not yet provider/source-scoped.

This must be resolved before second-provider operation.

### 2. Timestamp / Timezone / Precision Provenance

The current adapter does not yet preserve full raw timestamp, timezone, and precision semantics as explicit provenance.

### 3. Provider Instrument Semantics

`provider_instrument_id` exists but is not yet populated with verified provider-specific identifier semantics.

### 4. Threshold / Configuration Provenance

Operational thresholds are currently hardcoded. Future rules must be versioned and preserve the exact effective configuration used for each decision.

### 5. Normalized vs Inserted Counts

`records_processed` currently represents normalized output count.

Future observability should separate metrics such as:

```text
records_normalized
records_inserted
records_duplicate
records_rejected
```

### 6. Lifecycle Security Boundary

Header Auth is acceptable for the current local/operator workflow boundary, but browser-facing privileged actions should move behind a dedicated API/BFF with explicit authorization and audit controls.

### 7. n8n Runtime Configuration Warnings

The current n8n image reports configuration deprecation/task-runner warnings. Current JavaScript workflows remain operational, but production hardening should remove deprecated configuration and define runner behavior explicitly before relying on it at larger scale.

---

## Engineering Independence

The platform is provider-neutral and institution-independent.

Technology or architecture choices should be justified by:

- a concrete problem
- a clear responsibility
- the simplest viable alternative
- measurable success criteria
- a verification plan
- dependency order
- actual implementation evidence

No technology enters the core solely because it is popular, appears in an employer stack, or looks useful on a technology list.

---

## Development Roadmap

The current engineering sequence is:

```text
Configuration-driven rules + reference data
      ↓
Provider abstraction
      ↓
Second independent source
      ↓
Temporal cross-source reconciliation
      ↓
Replay / deterministic evaluation / fault-injection tooling
      ↓
Observability + Platform API/BFF + operator console
      ↓
Provider intelligence
      ↓
Extended streaming, analytics, resilience, security, and platform capabilities
```

### 1. Configuration-Driven Rules and Reference Data — NEXT

Planned scope:

- externalized instrument configuration
- versioned operational thresholds
- severity-specific threshold provenance
- explicit rule identifiers and versions
- canonical instrument reference data
- provider-specific instrument mappings
- effective-dated mappings
- explicit timestamp/provenance policy

### 2. Provider Abstraction

Planned scope:

- provider-neutral ingestion contract
- source-specific adapters
- provider-specific validation boundaries
- source-safe historical lookup semantics
- provider metadata and health evidence

### 3. Second Independent Source

A second provider/source must be integrated through the provider boundary rather than duplicated workflow logic.

### 4. Temporal Cross-Source Reconciliation

Reconciliation must explicitly define:

- matching direction
- time tolerance
- tie handling
- event reuse policy
- unmatched behavior
- provider age
- coverage metrics
- confidence/evidence semantics

Two-source ingestion alone is not reconciliation.

### 5. Replay and Deterministic Evaluation

Planned capabilities:

- deterministic replay
- controlled fault injection
- versioned datasets/configuration
- repeatable quality checks
- comparison of monitoring policies
- reproducible evidence manifests

### 6. Observability and Product Boundary

Planned capabilities:

- metrics and dashboards
- distributed tracing where justified
- structured operational logs
- Platform API/BFF
- typed contracts
- React/TypeScript console
- role-controlled operator actions

### 7. Provider Intelligence

Planned capabilities:

- provider scorecards
- SLA/availability evidence
- temporal coverage metrics
- certification and migration assurance
- configuration replay/change assurance
- lineage and blast-radius evidence

### 8. Extended Platform

Only after simpler verified baselines justify the added complexity:

- Kafka / Schema Registry / Kafka Connect
- Flink
- ClickHouse
- Redis / MongoDB where justified
- MinIO / Parquet / Iceberg
- Spark / Trino / dbt
- Temporal / Airflow
- high-performance replay components where measured need exists
- Kubernetes / Helm / GitOps
- Vault / OIDC / fine-grained authorization
- autoscaling and progressive delivery
- load, failure, chaos, recovery, and DR exercises
- advanced observability and profiling
- developer-platform and governance capabilities
- governed advisory automation where justified

---

## Definition of Done

A milestone is complete only when:

1. implementation exists
2. key success and failure paths are tested
3. relevant runtime, database, log, metric, trace, container, or browser evidence is inspected
4. destructive or temporary test artifacts are cleaned
5. `git diff`, `git status`, and secret checks are inspected
6. committed `HEAD` equals the tested state
7. push is confirmed when the milestone is intended to be shared
8. current repository documentation agrees with the committed behavior

If these conditions are not satisfied, the capability remains at a lower status.

---

## Current Next Step

> **Implement configuration-driven rules and reference data.**

The next engineering block should externalize operational thresholds, preserve rule/severity/configuration provenance, define canonical and provider-specific instrument mappings, and establish explicit temporal/reference semantics before provider abstraction and second-source integration.
