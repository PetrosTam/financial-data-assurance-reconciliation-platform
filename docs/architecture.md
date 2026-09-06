# System Architecture

## Overview

The current implementation of the **Financial Data Assurance & Reconciliation Platform (FDAR)** is a modular, workflow-driven FX market-data assurance system for ingestion, validation, normalization, persistence, monitoring, alerting, anomaly lifecycle management, and durable operational evidence.

The implemented runtime currently uses:

- n8n for workflow orchestration
- JavaScript for provider validation, normalization, and operational data-quality logic
- Alpha Vantage as the implemented FX market-data provider
- PostgreSQL 16 for operational persistence and audit evidence
- Docker Compose for the local runtime
- Gmail SMTP for the implemented critical-alert delivery channel

The broader platform is designed to evolve toward provider-neutral multi-source processing, temporally valid cross-source reconciliation, stronger observability, typed server-side product boundaries, and provider intelligence as those capabilities are implemented and verified.

The current implementation is **not yet a multi-provider reconciliation system**.

> **Scope boundary:** FDAR is not a trading bot. It does not execute or route trades, generate trading signals, manage positions, perform hedging, or calculate trading P&L. Market prices are treated as operational data to be validated, monitored, reconciled, and evidenced.

---

## Architectural Status Model

Architecture documentation follows the same evidence discipline as the repository.

- **TESTED** — behaviour or structure has been verified through inspected runtime, database, workflow, log, container, delivery, or deterministic test evidence.
- **IMPLEMENTED** — code, configuration, or schema exists but verification is incomplete.
- **PLANNED** — accepted future capability that is not currently implemented.
- **PROPOSED** — candidate design requiring further evidence or feasibility work.
- **OPTIONAL** — future or laboratory capability.
- **UNKNOWN** — available evidence is insufficient.

Architecture diagrams describe current behaviour unless explicitly labelled as planned.

---

## Current Runtime Boundary

The current runtime consists primarily of:

```text
Alpha Vantage
      |
      v
     n8n
      |
      +--> JavaScript validation / normalization / anomaly logic
      |
      +--> PostgreSQL 16
      |
      +--> Gmail SMTP
```

Current container identities are:

```text
fdar-postgres
fdar-n8n
```

Current PostgreSQL identity:

```text
Database: fdar
User:     fdar
```

Current persistent Docker volumes:

```text
fdar-postgres-data
fdar-n8n-data
```

Current lifecycle Webhook path:

```text
fdar-anomaly-lifecycle
```

Current lifecycle authentication header name:

```text
X-FDAR-Lifecycle-Token
```

The corresponding authentication value is secret and remains outside source control.

---

## Core Components

## 1. Workflow Orchestration

n8n currently coordinates:

- scheduled and manual market-data workflow execution
- Alpha Vantage REST integration
- sequential multi-instrument processing
- provider-response validation
- canonical quote normalization
- PostgreSQL persistence
- operational anomaly detection
- critical anomaly alert routing
- workflow execution lifecycle tracking
- centralized workflow failure handling
- authenticated anomaly lifecycle operations

Current version-controlled workflow exports are:

```text
workflows/fdar-fx-market-data-pipeline-alpha-vantage.json
workflows/fdar-workflow-error-handler.json
workflows/fdar-anomaly-lifecycle-manager.json
```

The workflow exports and inspected n8n runtime are authoritative for exact node wiring.

---

## 2. Market Data Integration

FX market data is currently retrieved from **Alpha Vantage** through its REST API.

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

The same provider adapter path is therefore reused across the three currently configured instruments.

Provider-specific responses are treated as **untrusted external input**.

The current implementation has only one market-data provider.

Therefore:

```text
single-provider ingestion ≠ cross-source reconciliation
```

Provider abstraction, a second independent source, and temporal reconciliation remain future capabilities.

---

## 3. Sequential Provider Request Flow

The current provider integration deliberately processes requests sequentially.

```text
Generate FX Pairs
      |
      v
Loop Over Items
Batch Size = 1
      |
      v
Fetch FX Quote
      |
      v
Wait 3 seconds
      |
      v
Next Pair
```

This pacing mechanism is specific to the current integration.

It must not be interpreted as a general retry, backoff, circuit-breaker, or resilience framework.

Those concerns require explicit implementation and verification before they can be claimed.

---

## 4. Validation and Normalization

JavaScript currently performs provider-response validation and normalization before persistence.

Current validation includes:

- provider error-payload detection
- expected response-shape validation
- required currency fields
- numeric bid validation
- numeric ask validation
- positive bid
- positive ask
- `ask >= bid`
- timestamp presence
- parseable timestamp semantics used by the current adapter

Invalid provider responses are rejected before normal quote persistence.

### Current Canonical Quote Shape

The current normalized quote includes fields such as:

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

Current canonical symbols include:

```text
EURUSD
GBPUSD
USDJPY
```

Derived values include:

```text
mid_price  = (bid + ask) / 2
spread     = ask - bid
spread_bps = (spread / mid_price) * 10000
```

The existence of a canonical output shape does **not** yet constitute a complete provider-abstraction layer.

---

## 5. PostgreSQL Persistence

PostgreSQL 16 is the current operational system of record.

It stores:

- normalized FX quotes
- raw provider payloads
- workflow execution lifecycle state
- detected anomalies
- alert-delivery state
- anomaly lifecycle state
- durable anomaly lifecycle transition evidence

The current operational tables are:

```text
fx_quotes
workflow_runs
anomalies
alerts
anomaly_lifecycle_events
```

### `fx_quotes`

Primary responsibility:

- normalized quote persistence
- provider/source provenance
- raw provider payload retention
- duplicate-safe logical quote storage

Current logical uniqueness:

```sql
UNIQUE (symbol, observed_at, source)
```

### `workflow_runs`

Primary responsibility:

- execution start state
- success/failure state
- execution identity
- processed-record count
- error evidence
- execution timestamps

### `anomalies`

Primary responsibility:

- persisted operational/data-quality findings
- severity
- metric and threshold evidence
- anomaly lifecycle state
- acknowledgement/resolution metadata

Current lifecycle states:

```text
open
acknowledged
resolved
```

### `alerts`

Primary responsibility:

- persisted alert-delivery state

Current delivery states:

```text
pending
sent
failed
```

### `anomaly_lifecycle_events`

Primary responsibility:

- durable evidence of successful lifecycle transitions
- previous and resulting state
- lifecycle action
- resolution context
- workflow/execution provenance
- transition timestamp

The table is linked to `anomalies(id)` with:

```text
ON DELETE RESTRICT
```

and the current transition model permits:

```text
open → acknowledged
acknowledged → resolved
```

---

## 6. Duplicate Safety and Idempotency

Quote persistence uses database-backed duplicate protection.

The current logical uniqueness model is:

```sql
UNIQUE (symbol, observed_at, source)
```

Conflict-safe persistence prevents a replay of the same logical quote from failing due solely to the existing record.

This provides idempotency for the current logical uniqueness definition.

It is not yet a complete multi-provider idempotency model.

---

## 7. Workflow Execution Lifecycle

The market-data workflow records execution state in `workflow_runs`.

### Start

```text
status = started
records_processed = 0
```

The execution record also preserves workflow identity, n8n execution identity, and start time.

### Success

Successful completion records:

```text
status = success
records_processed = <normalized output count>
finished_at = <completion timestamp>
```

`records_processed` currently represents normalized output count.

It must not automatically be interpreted as inserted-row count because duplicate conflict handling may prevent a new row from being inserted.

### Failure

The dedicated workflow:

```text
FDAR Workflow Error Handler
```

uses an n8n `Error Trigger` to update the corresponding workflow execution as failed.

```text
Workflow Failure
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

Failure evidence includes:

```text
status = failed
error_message = <captured failure>
finished_at = <failure timestamp>
```

---

## 8. Operational Anomaly Detection

The current operational anomaly types are:

```text
wide_spread
stale_quote
extreme_price_movement
```

Current thresholds are operational assumptions only.

They are not universal market truths.

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

The previous quote is retrieved using parameterized SQL.

### Current Safety Limitation

The previous-quote lookup is not yet explicitly source/provider-scoped.

This must be corrected before multi-provider operation.

Accidental cross-provider historical baselining must not be allowed.

---

## 9. Critical Alerting

Critical anomalies can enter the currently implemented email-alert path.

```text
Critical Anomaly
      |
      v
Create Alert
status = pending
      |
      v
Send Critical Alert Email
     / \
    /   \
success  failure
   |       |
   v       v
sent     failed
```

Successful delivery records:

```text
status = sent
sent_at = <delivery timestamp>
```

Failure records:

```text
status = failed
```

Current implemented delivery channel:

```text
Gmail SMTP
```

SMTP authentication is stored in n8n credentials.

Runtime sender and recipient values are supplied through environment configuration rather than hardcoded workflow values.

Other channels are not current runtime capabilities unless separately implemented and verified.

---

## 10. Anomaly Lifecycle Management

Anomaly lifecycle management is a **current tested capability**.

The workflow is:

```text
FDAR Anomaly Lifecycle Manager
```

Current supported transitions:

```text
open → acknowledged
acknowledged → resolved
```

The lifecycle path uses n8n Header Auth.

Current endpoint identity:

```text
fdar-anomaly-lifecycle
```

Current authentication header:

```text
X-FDAR-Lifecycle-Token
```

The authentication value is not stored in source control.

### Lifecycle Processing Flow

```text
Authenticated Lifecycle Request
            |
            v
          Webhook
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
     Success Response
```

Controlled error paths route through:

```text
Lifecycle Error
      |
      v
Build Webhook Error Response
      |
      v
Respond Lifecycle Error
```

### Lifecycle Request Model

The workflow accepts lifecycle command data containing:

```text
anomaly_id
action
resolution_reason
```

Request shape and lifecycle semantics are validated before successful mutation.

The current implementation enforces:

- supported action validation
- required resolution reason where applicable
- current anomaly existence
- legal state transitions
- optimistic-concurrency protection
- controlled HTTP error responses
- durable lifecycle audit evidence

Verified HTTP behaviour includes:

```text
403  authentication denial
400  invalid request/action or missing required resolution reason
404  anomaly not found
409  illegal lifecycle transition
200  successful acknowledge / resolve
```

### Atomic Transition and Audit

Successful lifecycle mutation and lifecycle audit insertion are coupled in one SQL statement.

This prevents a successful state transition from being recorded without its corresponding audit event.

The lifecycle event preserves:

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

A stale-write test also verified that a rejected mutation does not create a false lifecycle audit event.

---

## Current Market-Data Flow

The current market-data path can be represented conceptually as:

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
       /           |            \
      v            v             v
Persist Quote   Detect Ops    Check Price
PostgreSQL      Anomalies      Movement
                   \             /
                    \           /
                     v         v
                      Log Anomaly
                          |
                          v
                Is Critical Anomaly?
                          |
                       true
                          |
                          v
                    Create Alert
                          |
                          v
               Send Critical Email
                    /         \
               success       failure
                  |             |
                  v             v
           Mark Alert Sent  Mark Alert Failed
```

Run lifecycle persistence is maintained through the corresponding execution-tracking path.

The version-controlled workflow export and inspected n8n runtime remain authoritative for exact branching and node wiring.

---

## Current Lifecycle Flow

```text
Operator
   |
   v
Authenticated Lifecycle Webhook
   |
   v
Validate Request
   |
   v
Read Current Anomaly
   |
   v
Validate Transition
   |
   v
Atomic State Mutation
+ Lifecycle Audit Event
   |
   v
Controlled HTTP Response
```

The current lifecycle boundary is an operator/local control boundary.

It is not the final browser-facing product API architecture.

---

## Fresh Database Bootstrap

The PostgreSQL container mounts migrations under:

```text
/docker-entrypoint-initdb.d/
```

The current migration order is:

```text
001_schema.sql
      |
      v
002_alerting_anomaly_lifecycle.sql
      |
      v
003_anomaly_lifecycle_audit.sql
```

An isolated post-rebrand PostgreSQL 16 bootstrap test verified:

- clean empty-volume initialization
- database `fdar`
- user `fdar`
- ordered `001 → 002 → 003` execution
- expected operational tables
- expected lifecycle fields
- expected lifecycle constraints
- expected lifecycle indexes
- expected FDAR table ownership
- no relevant initialization `ERROR`, `FATAL`, or `PANIC`
- cleanup of the temporary test container and volume
- canonical `fdar-postgres` runtime remained healthy afterward

The clean-bootstrap path is therefore currently **TESTED**.

---

## Persistence Architecture

Current Docker persistence uses externally named volumes:

```text
fdar-postgres-data
fdar-n8n-data
```

The PostgreSQL volume protects operational database state across container recreation.

The n8n volume protects locally persisted n8n application state.

A volume declaration alone is not considered evidence of persistence.

Actual runtime mounts and restoration behaviour must be inspected.

---

## Security Boundaries

Current security principles include:

- provider API credentials remain outside Git
- SMTP credentials remain outside Git
- PostgreSQL passwords remain outside Git
- lifecycle authentication tokens remain outside Git
- `.env` files containing local values remain outside Git
- safe example configuration may be committed
- external provider responses are treated as untrusted input
- lifecycle requests are authenticated before mutation logic executes
- lifecycle mutations validate domain state
- privileged lifecycle actions generate durable audit evidence
- dynamic SQL uses parameterization where applicable
- raw request/execution data must be treated carefully because headers may contain secret material

The current lifecycle Header Auth boundary is suitable for the present local/operator workflow architecture.

It is **not** the intended final browser-facing privileged-action boundary.

---

## Planned Server-Side Product Boundary

The planned product architecture is:

```text
React / TypeScript Operator Console
               |
               v
        Platform API / BFF
               |
               +--> domain services
               |
               +--> operational / analytical data stores
               |
               +--> workflow / streaming adapters
               |
               +--> observability adapters
               |
               +--> authentication / authorization
               |
               +--> audit boundary
```

This architecture is **PLANNED**, not current runtime.

The browser must not receive unrestricted:

- database credentials
- provider credentials
- infrastructure credentials
- secret-management credentials
- backend service tokens

Privileged browser-facing writes should pass through a dedicated server-side authorization, validation, and audit boundary.

---

## Reliability Principles

Current implemented or verified principles include:

- validate external API responses before persistence
- reject structurally invalid market data
- preserve provider/source provenance
- preserve raw provider payloads for diagnostics
- prevent duplicate logical quote persistence
- process the current provider requests sequentially
- apply explicit current-provider pacing
- track workflow execution start, success, and failure
- persist captured workflow failure messages
- detect configured operational data-quality anomalies
- persist structured anomaly evidence
- persist alert-delivery state
- route critical anomalies through a verified email channel
- externalize runtime configuration
- keep credentials and secrets outside source control
- authenticate lifecycle operations
- enforce explicit lifecycle transitions
- use optimistic concurrency for lifecycle mutation safety
- couple successful lifecycle mutation with durable audit evidence
- persist n8n and PostgreSQL state through dedicated Docker volumes
- verify migrations against clean PostgreSQL state
- clean temporary verification artifacts after tests

---

## Current Architectural Limitations

The architecture intentionally retains several known limitations.

### Single Provider

Alpha Vantage is currently the only implemented market-data provider.

Provider abstraction and multi-source processing remain future work.

### No Temporal Cross-Source Reconciliation

No second source is currently integrated.

Therefore temporal matching, divergence evidence, provider-age comparison, match coverage, and unmatched-observation handling are not yet implemented.

### Source-Safe Previous-Quote Lookup

The current previous-quote lookup used by extreme movement detection is not yet explicitly provider/source-scoped.

This must be corrected before introducing another provider.

### Timestamp Provenance

Raw source timestamp text, timezone provenance, and timestamp precision are not yet represented as explicitly as required for robust multi-source processing.

### Provider Instrument Semantics

`provider_instrument_id` exists in the current schema but is not yet populated with verified provider-specific identifier semantics for the Alpha Vantage adapter.

### Configuration Provenance

Operational thresholds are currently hardcoded assumptions.

Versioned rule identity, severity-specific threshold provenance, and configuration provenance remain future work.

### Processing Counters

`records_processed` currently represents normalized output count.

The architecture does not yet expose separate counters such as:

```text
records_normalized
records_inserted
records_duplicate
records_rejected
```

### Final Product Security Boundary

Current lifecycle operations use n8n Header Auth.

A browser-facing product requires a dedicated authenticated and authorized Platform API/BFF boundary.

### Observability

Prometheus, Grafana, OpenTelemetry, and related observability infrastructure are not part of the current runtime.

### Runtime Reproducibility

The current n8n image configuration still requires hardening for reproducible version-pinned releases.

---

## Planned Architectural Evolution

The current dependency order is:

```text
Configuration-driven rules
+ reference data
        |
        v
Provider abstraction
        |
        v
Second independent source
        |
        v
Temporal cross-source reconciliation
        |
        v
Reproducible evaluation tooling
        |
        v
Observability
+ Platform API / BFF
        |
        v
Operator-facing product capabilities
+ provider intelligence
        |
        v
Extended streaming / analytics /
resilience / security / platform capabilities
where justified
```

### Configuration and Reference Data

Planned responsibilities include:

- configuration-driven instruments
- versioned operational thresholds
- severity-specific threshold provenance
- canonical/provider instrument mapping
- effective-dating semantics
- explicit provider-instrument identifiers
- source-safe historical lookup behaviour

### Provider Abstraction

Planned responsibilities include:

- provider-neutral contracts
- provider-specific adapters
- consistent validation boundaries
- explicit source provenance
- provider health evidence

### Second Source and Temporal Reconciliation

Planned responsibilities include:

- independent second-source ingestion
- timestamp normalization
- temporal matching
- causal matching rules where required
- tolerance policy
- unmatched observations
- provider age
- divergence evidence
- reconciliation coverage/confidence

Two-source ingestion must not be described as reconciliation until temporal comparison exists.

### Observability and Product Boundary

Planned responsibilities include:

- operational metrics
- service/workflow traces where useful
- dashboards
- Platform API / BFF
- typed contracts
- authenticated/authorized operator actions
- operator-facing web interface

### Extended Platform Capabilities

Components such as:

- Kafka
- Schema Registry
- Flink
- ClickHouse
- Redis
- analytical object storage
- Kubernetes
- GitOps
- stronger identity/authorization infrastructure
- advanced resilience testing

may be introduced only when a concrete engineering responsibility and measurable success criterion justify them.

Their presence in the architectural roadmap is **not an implementation claim**.

---

## Architectural Non-Goals

FDAR does not provide:

- trade execution
- order routing
- trading signals
- portfolio management
- position management
- hedging
- trading P&L calculation
- execution decisions

Market data is processed for assurance, quality control, operational evidence, reconciliation, observability, and provider intelligence.

---

## Architecture Verification Principle

An architecture capability is not considered implemented merely because it appears in a diagram or roadmap.

A current architectural claim must be supported by appropriate evidence such as:

- committed implementation
- inspected runtime behaviour
- database/schema inspection
- workflow execution evidence
- container/runtime inspection
- deterministic tests
- delivery evidence where applicable

Planned diagrams describe target boundaries only.

The repository README and current architecture documentation must remain consistent with the verified implementation state.