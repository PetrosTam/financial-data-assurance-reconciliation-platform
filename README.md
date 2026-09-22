# Financial Data Assurance & Reconciliation Platform

**Independent financial-data assurance and reconciliation platform for reliable multi-source processing, temporal reconciliation, observability, operational evidence, and provider intelligence.**

The current operational implementation is an **FX market-data assurance profile** built incrementally with evidence-driven engineering. The verified operational runtime uses **n8n, JavaScript, Alpha Vantage REST, PostgreSQL 16, Docker Compose, Git/GitHub, and Gmail SMTP**.

The repository additionally contains bounded **MSc research tooling in Java/JForex and Python** for historical-source acquisition, structural auditing, and source-compatibility evaluation. This research tooling is deliberately separated from the current Alpha Vantage operational provider path.

Today the operational platform provides single-provider FX ingestion, validation, normalization, persistence, workflow lifecycle tracking, operational anomaly detection, critical alerting, anomaly lifecycle management, and durable audit evidence.

The research path currently provides deterministic TrueFX auditing, bounded Dukascopy/JForex historical acquisition, and initial cross-source compatibility analysis for the MSc source-selection pilot.

Operational multi-provider processing, production temporal cross-source reconciliation, advanced observability, and provider intelligence remain future capabilities.

> **Scope boundary:** this is not a trading bot. The platform does not execute or route trades, generate trading signals, manage positions, perform hedging, or calculate trading P&L. Market prices are treated as operational and research data to be validated, monitored, reconciled, and evidenced.

---

## Project Status

The repository uses explicit implementation states:

- **TESTED** — verified through inspected runtime, database, execution, log, container, delivery, deterministic test, or artifact evidence.
- **IMPLEMENTED** — code/config/schema exists, but verification is incomplete.
- **IN PROGRESS** — partially implemented or actively being completed.
- **PLANNED** — accepted target capability, not yet implemented.
- **PROPOSED** — candidate enhancement requiring design or feasibility confirmation.
- **OPTIONAL** — future or laboratory capability.
- **PENDING** — a decision depends on evidence that is not yet complete.
- **UNKNOWN** — evidence is insufficient.

A capability is not promoted to **TESTED** merely because code, documentation, screenshots, or plans exist.

---

## Current Verified State

| Capability | Status | Evidence / interpretation |
|---|---|---|
| Multi-instrument operational FX ingestion | **TESTED** | EUR/USD, GBP/USD, and USD/JPY normalized and persisted in verified Alpha Vantage runs |
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
| TrueFX structural audit tooling | **TESTED** | January 2026 EUR/USD source file audited for parsing, price validity, ordering, duplicates, timestamp behavior, and frozen pilot-week counts |
| Dukascopy JForex historical acquisition probe | **TESTED — RESEARCH TOOLING** | Canonical one-hour EUR/USD acquisition reproduced with deterministic row count, boundaries, metadata schema v2, SHA-256, and no residual `.part` artifact |
| One-hour TrueFX/Dukascopy compatibility analysis | **TESTED — PILOT EVIDENCE** | Bounded EUR/USD sample evaluated for temporal overlap and causal matching coverage |
| Five-day EUR/USD source compatibility pilot | **IN PROGRESS** | Frozen UTC dates 2026-01-26 through 2026-01-30; full Dukascopy acquisition and compatibility evaluation are not complete |
| Final historical source-pair selection | **PENDING** | TrueFX and Dukascopy remain candidates until the five-day pilot and data-use suitability review are complete |
| Configuration-driven rules and reference data | **PLANNED — NEXT ENGINEERING DEPENDENCY** | Required before operational provider abstraction and multi-provider processing |
| Operational provider abstraction | **PLANNED** | Canonical output exists, but only Alpha Vantage is integrated into the operational provider path |
| Second independent operational source | **PLANNED** | Dukascopy currently exists as bounded MSc historical-acquisition tooling, not as an integrated operational provider |
| Operational temporal cross-source reconciliation | **PLANNED** | Research compatibility analysis is not equivalent to production reconciliation |
| Prometheus / Grafana | **PLANNED** | Not integrated in the current runtime |
| Platform API / BFF | **PLANNED** | Target browser/server boundary |
| React / TypeScript operator console | **PLANNED** | No current browser product |
| Provider intelligence and scorecards | **PLANNED** | Depends on independent multi-provider evidence and temporal reconciliation |

> `records_processed=3` means **three normalized output records** for the current three-pair operational workflow. It does not guarantee three new database inserts when duplicate conflict handling is active.

---

## Operational Runtime Identity

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

The JForex historical-acquisition utility is a separate local research process and is not part of this Docker Compose runtime.

---

## MSc Research Authority

Formal thesis title:

> **Engineering and Empirical Evaluation of a Financial Market Data Assurance and Reconciliation Platform: An FX Case Study**

### RQ1 — Cross-Source Evidence

To what extent does temporally valid cross-source evidence improve the classification of controlled source-specific FX data-quality faults in a multi-source FX market-data platform compared with an otherwise equivalent single-source design?

### RQ2 — Adaptive Monitoring

Under changing reference FX conditions, how does a past-only adaptive robust monitoring policy compare with an equivalent fixed robust policy in false-alert behaviour while preserving detection effectiveness for controlled price and spread faults?

### Core Research Rules

- Ground truth comes from **controlled fault injection**.
- Provider disagreement is **contextual evidence**, never ground truth.
- Non-injected historical observations are reference observations, not universal proof of correctness.
- No random row-level split is used.
- Development/calibration occurs chronologically.
- Detector, reconciliation, and fault-injection policies are frozen before held-out evaluation.
- Operational causal claims must not use future observations.
- Reconciliation must explicitly define tolerance, causality, ties, reuse, unmatched observations, provider age, coverage, and confidence.
- Unknown timestamp, arrival-time, sequence, or latency semantics remain unknown rather than being fabricated.
- Raw licensed historical data remains local unless redistribution rights explicitly permit publication.

The research-critical path remains deliberately smaller than the broader engineering/product roadmap.

---

## Core Engineering Principles

The platform prioritizes:

1. correctness before scale;
2. evidence before status claims;
3. deterministic validation at boundaries;
4. provider-neutral internal contracts;
5. explicit provenance;
6. idempotent persistence;
7. failure transparency;
8. reproducible bootstrap and verification;
9. least privilege and secret isolation;
10. simple verified components before additional infrastructure.

Technology is added only when it has a distinct responsibility, a simpler alternative has been considered, success can be measured, and verification is possible.

---

## Quick Start — Operational Platform

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

The current operational workflows depend on local n8n credentials with these logical names:

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

## Current Operational Workflows

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

## Current Operational Architecture

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

## Multi-Instrument Operational FX Ingestion

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

The same Alpha Vantage provider integration is reused for all three instruments.

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

## Current Operational Provider Integration

The implemented operational provider is **Alpha Vantage** using:

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

Dukascopy/JForex is currently used only in the bounded historical MSc acquisition path described below. It must not be described as a second operational provider until it is integrated through the future provider abstraction and temporal reconciliation path.

---

## Validation and Normalization

Provider-specific operational responses are validated before persistence.

### Current Operational Validation Controls

The current Alpha Vantage normalization path checks:

- provider error payloads;
- expected provider response shape;
- required currency fields;
- numeric bid;
- numeric ask;
- positive bid;
- positive ask;
- `ask >= bid`;
- presence of timestamp data;
- timestamp parseability under the current adapter semantics.

Invalid responses are rejected before quote persistence.

### Current Canonical Quote Shape

The normalized operational output includes fields such as:

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

The current operational normalizer provides a common output shape, but this is not yet a complete provider-abstraction layer.

Known gaps include:

- `provider_instrument_id` is not yet populated with verified provider-specific identifier semantics;
- raw provider timestamp text is not yet retained separately as `source_timestamp_raw`;
- timezone and timestamp-precision provenance are not yet fully explicit;
- arrival-time semantics must not be fabricated when unavailable;
- configuration/version provenance is not yet attached to every derived monitoring decision.

These items must be hardened before operational multi-provider processing.

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

It does **not** yet solve every future multi-provider identity or replay problem. Those semantics must be defined explicitly as the platform expands.

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

The current thresholds are **operational assumptions only**. They are not universal market rules and are not the frozen thesis monitoring policies.

### Wide Spread

```text
spread_bps = (spread / mid_price) * 10000
```

Current operational thresholds:

```text
Warning:  > 2 bps
Critical: > 5 bps
```

### Stale Quote

Current operational thresholds:

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

Current operational thresholds:

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

- rule identifier;
- rule version;
- severity-specific threshold;
- effective configuration version;
- configuration provenance;
- evaluation timestamp.

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

- deterministic test input;
- configured n8n SMTP credential;
- environment-based sender/recipient;
- successful SMTP acceptance;
- real inbox delivery;
- persisted success state;
- persisted failure path;
- cleanup of temporary test artifacts.

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

- ordered `001 → 002 → 003` execution;
- all five core tables exist;
- table ownership is `fdar`;
- `status` defaults to `open`;
- `anomalies_status_check` allows `open`, `acknowledged`, `resolved`;
- lifecycle columns exist;
- lifecycle-event primary key exists;
- transition checks exist;
- `ON DELETE RESTRICT` foreign key exists;
- anomaly lifecycle indexes exist;
- initialization completed without relevant `ERROR`, `FATAL`, or `PANIC`;
- temporary verification resources were removed afterward.

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

A volume declaration alone is not sufficient evidence. The running service must mount it at the expected application path.

---

# MSc Research Acquisition and Compatibility Tooling

The repository contains a bounded research path for evaluating candidate historical FX sources independently from the current Alpha Vantage operational workflow.

This tooling supports the MSc source-compatibility pilot and does not by itself constitute operational provider abstraction or production reconciliation.

---

## TrueFX Structural Audit Utility

Location:

```text
research/truefx/audit_truefx.py
```

The utility performs deterministic structural inspection of the local TrueFX EUR/USD source data, including:

- row parsing;
- timestamp parsing;
- price parsing;
- positive-price validation;
- bid/ask relationship checks;
- chronological ordering;
- exact-duplicate detection;
- repeated-timestamp reporting;
- millisecond-position coverage;
- instrument validation;
- frozen target-period counts.

### Current Tested TrueFX Evidence

Audited source:

```text
EURUSD-2026-01.csv
```

Observed audit results:

```text
total rows                 = 755175
malformed rows             = 0
timestamp parse failures   = 0
price parse failures       = 0
non-positive prices        = 0
column4 < column3          = 0
out-of-order rows          = 0
exact duplicates           = 0
repeated timestamps        = 0
target-week rows           = 230148
```

All 1000 millisecond positions were observed within the source file.

Frozen pilot-day counts:

```text
2026-01-26 = 43267
2026-01-27 = 44046
2026-01-28 = 45279
2026-01-29 = 45399
2026-01-30 = 52157
```

The final TrueFX observation on 2026-01-30 is:

```text
2026-01-30 21:59:56.406 UTC
```

No TrueFX rows were observed during UTC hours 22 or 23 on that date.

The frozen calendar day is not shortened because of this. Absence of observations is preserved as observed source behaviour.

Raw TrueFX data remains outside Git.

---

## Dukascopy JForex Historical Tick Probe

Location:

```text
acquisition/jforex-historical-probe/
```

The probe is a read-only historical market-data acquisition utility using the Dukascopy JForex SDK.

It does not submit orders or implement trading logic.

### Toolchain

Current Maven artifact:

```text
com.petros.thesis:jforex-historical-probe:1.0.0
```

Main JForex dependency:

```text
com.dukascopy.dds2:DDS2-jClient-JForex:3.6.51
```

Java source target:

```text
release 8
```

Runtime testing has been performed with a newer Java runtime while preserving Java-8 source compatibility.

Known Maven effective-model warnings from Dukascopy/transitive dependencies may appear during dependency collection. These warnings have not prevented successful compilation or acquisition in the currently inspected evidence.

### Credentials

Credentials are read exclusively from:

```text
DUKASCOPY_DEMO_USERNAME
DUKASCOPY_DEMO_PASSWORD
```

Credentials must never be hard-coded.

The committed template contains placeholders only:

```dotenv
DUKASCOPY_DEMO_USERNAME=YOUR_DEMO_USERNAME
DUKASCOPY_DEMO_PASSWORD=YOUR_DEMO_PASSWORD
```

### Canonical Acquisition Policy

Each acquisition run must cover exactly one canonical UTC hour:

```text
HH:00:00.000Z through HH:59:59.999Z inclusive
```

Current policy identifier:

```text
canonical_utc_hour
```

The one-hour restriction is deliberate.

Earlier larger historical requests exhibited unstable JForex/provider retrieval behaviour, including provider/network failures and situations in which a load could report completion while the returned evidence was not suitable for trusted multi-hour research acquisition.

The acquisition path therefore fails closed rather than treating a potentially partial larger request as valid evidence.

### Historical Probe Validation

The historical probe validates:

- expected instrument;
- event timestamp inside the requested inclusive interval;
- finite bid and ask;
- positive bid and ask;
- `ask >= bid`;
- finite volumes;
- non-negative volumes;
- non-decreasing historical timestamps.

Equal provider timestamps may be preserved.

Live `onTick()` data is deliberately excluded from the historical CSV.

Unexpected historical bar callbacks are treated as acquisition-contract violations.

### Temporary Artifact Policy

Historical CSV output is first written as:

```text
ticks.csv.part
```

The temporary artifact is promoted to:

```text
ticks.csv
```

only after the probe reports successful historical loading and local validation succeeds.

Existing final research evidence is never silently overwritten.

Atomic filesystem promotion is preferred when supported.

### Canonical Regression Oracle

Current known-good regression window:

```text
Instrument:     EUR/USD
From:           2026-01-27T12:00:00.000Z
To:             2026-01-27T12:59:59.999Z
Rows:           7630
First epoch_ms: 1769515200187
Last epoch_ms:  1769518799335
SHA-256:        259666ce9f4eee67afa5b8ce905eee6775478cff73c08a52f99f2fc3050f2f1e
```

The acquisition has been reproduced with the same:

```text
row count
first timestamp
last timestamp
SHA-256
```

The hardened historical probe also reproduced this oracle without serialization drift.

### Metadata Schema

Current metadata schema:

```text
schema_version = 2
```

Relevant metadata fields include:

```text
schema_version
run_id
provider
acquisition_route
endpoint
dukascopy_sdk_version
instrument
window_policy
requested_from_utc
requested_to_utc
requested_duration_ms
probe_timeout_ms
all_data_loaded
rows
first_epoch_ms
last_epoch_ms
run_directory
output_csv
output_sha256
started_at_utc
completed_at_utc
java_version
os_name
```

The canonical regression artifact verified:

```text
schema_version   = 2
window_policy    = canonical_utc_hour
instrument       = EUR/USD
all_data_loaded  = true
rows             = 7630
first_epoch_ms   = 1769515200187
last_epoch_ms    = 1769518799335
hash_matches     = true
part_exists      = false
```

### Disconnect Advisory

The Dukascopy disconnect callback may not always be observed before the bounded disconnect timeout.

When acquisition, validation, artifact promotion, and metadata generation have already succeeded, this condition is reported as an advisory warning rather than rewriting completed evidence as failed.

Repeated disconnect anomalies or evidence of incomplete acquisition must be investigated separately.

---

## JForex Build and Run

Working directory:

```text
acquisition/jforex-historical-probe
```

### Build

```powershell
mvn compile
```

Expected successful completion:

```text
BUILD SUCCESS
```

### Credential Presence Check

Do not print credential values.

```powershell
[bool]$env:DUKASCOPY_DEMO_USERNAME
[bool]$env:DUKASCOPY_DEMO_PASSWORD
```

Expected when configured:

```text
True
True
```

### Run a Canonical Hour

Example:

```powershell
mvn exec:exec `
  '-Dprobe.instrument=EUR/USD' `
  '-Dprobe.from=2026-01-27T12:00:00.000Z' `
  '-Dprobe.to=2026-01-27T12:59:59.999Z' `
  '-Dprobe.output.root=C:\path\to\local-research-data'
```

A plain:

```powershell
mvn exec:exec
```

is intentionally invalid because required run properties use sentinel defaults.

This prevents an accidental acquisition against an unintended interval.

---

## Cross-Source Compatibility Utility

Location:

```text
research/compatibility/compare_truefx_dukascopy.py
```

The utility accepts explicit CLI paths rather than relying on required hard-coded local data locations.

Current inputs include:

```text
--truefx
--dukascopy
--output-root
```

The utility evaluates temporal compatibility between candidate historical sources.

Provider disagreement is contextual evidence only and is never treated as ground truth.

### Current One-Hour Compatibility Evidence

A bounded EUR/USD comparison for 2026-01-26 12:00–13:00 UTC observed:

```text
TrueFX rows    = 1721
Dukascopy rows = 3002
```

Both sources contained observations in:

```text
60 / 60 requested minutes
```

Observed causal reusable coverage:

```text
TrueFX -> Dukascopy

1 second = 63.858%
2 seconds = 78.501%
5 seconds = 93.260%
```

```text
Dukascopy -> TrueFX

1 second = 55.829%
2 seconds = 74.950%
5 seconds = 92.605%
```

The pilot protocol review trigger is therefore active because causal peer coverage is below 90% at tolerances of one second or less.

This does **not** freeze five seconds as the final reconciliation tolerance.

The full five-day compatibility evidence must be completed before the final temporal policy is frozen.

---

## Five-Day EUR/USD Compatibility Pilot

The primary compatibility pilot uses the following frozen UTC calendar dates:

```text
2026-01-26
2026-01-27
2026-01-28
2026-01-29
2026-01-30
```

Candidate historical sources:

```text
TrueFX
Dukascopy / JForex
```

Primary instrument:

```text
EUR/USD
```

The pilot evaluates:

- source schema;
- timestamp semantics;
- observed overlap;
- temporal matching feasibility;
- matching coverage;
- unmatched observations;
- candidate tolerance behavior;
- data-use suitability.

TrueFX and Dukascopy remain **candidate sources** until this pilot is complete.

The pilot is not the final thesis evaluation and does not establish provider correctness.

---

## Research Temporal-Reconciliation Rules

The final research reconciliation policy must explicitly define:

- matching direction;
- causal versus symmetric matching;
- maximum matching tolerance;
- tie handling;
- one-to-one versus reusable evidence;
- unmatched-observation behavior;
- maximum provider age;
- coverage;
- evidence availability;
- confidence semantics.

For operational causal claims, a Source A observation at time `t` may use only eligible Source B evidence available at or before `t`.

Historical files must not be treated as if original network-arrival timing were known when that timing is unavailable.

Two-source ingestion alone is not reconciliation.

---

## Research Ground Truth and Controlled Fault Injection

Provider disagreement is not fault ground truth.

Known labels come from deterministic validation or controlled source-specific fault injection.

Primary thesis fault families include:

```text
F1 — price corruption
F2 — spread corruption
F3 — temporal fault
```

Supporting engineering/auxiliary fault families may include structural, missing, sequence, clock, freeze/gap, throttling, schema, and dependency-failure scenarios where relevant.

Fault injection must preserve provenance including:

- fault family;
- source;
- magnitude;
- duration;
- seed;
- expected label;
- dataset version;
- code/configuration version.

---

## Research Evaluation Discipline

The main experiment follows a 2 × 2 structure:

| | Single Source | Cross Source |
|---|---|---|
| Fixed | System A | System C |
| Adaptive | System B | System D |

### Fixed Policy

The fixed robust baseline is calibrated only on chronological calibration data and then frozen before held-out evaluation.

### Adaptive Policy

The adaptive policy uses past-only rolling robust statistics, primarily median/MAD, with frozen:

- rolling-window length;
- warm-up behavior;
- minimum history;
- missing-data handling;
- contamination policy;
- numerical safeguard.

No future look-ahead is permitted.

### Evaluation Order

```text
compatibility pilot
    ↓
development / calibration
    ↓
development fault injection and parameter selection
    ↓
protocol / configuration freeze
    ↓
held-out reference period
    ↓
frozen final fault injection
    ↓
Systems A-D evaluation
    ↓
final analysis
```

Random row-level splitting is not used.

Negative or mixed results remain valid research outcomes.

---

## Research Metrics

Primary and supporting metrics include:

### Classification

- Macro-F1;
- per-class precision;
- per-class recall;
- per-class F1;
- confusion matrix;
- false-positive rate on non-injected reference observations.

### Episode-Level Evaluation

- fault-episode detection rate;
- missed-episode rate;
- time to first detection;
- detection delay.

### Reconciliation

- match coverage;
- unmatched rate;
- timestamp-separation distribution;
- evidence availability;
- abstention where relevant.

### Diagnostics

- errors by fault family;
- errors by magnitude;
- errors by source;
- selected market-context diagnostics.

### Uncertainty

Where practical, uncertainty is evaluated using trading days, chronological blocks, or fault episodes rather than treating every tick as statistically independent.

---

## Security and Repository Hygiene

Current engineering rules include:

- provider API keys stay outside Git;
- SMTP passwords stay outside Git;
- database passwords stay outside Git;
- lifecycle authentication tokens stay outside Git;
- Dukascopy DEMO credentials stay outside Git;
- `.env` and local secret-bearing environment files remain ignored;
- `.env.example` files contain placeholders only;
- n8n credentials hold provider, SMTP, PostgreSQL, and lifecycle authentication secrets;
- privileged lifecycle requests are authenticated before mutation logic executes;
- dynamic SQL uses parameterization where applicable;
- workflow exports are inspected for secret leakage;
- committed exports must not contain real personal email addresses;
- committed exports must not contain API keys, passwords, tokens, authorization headers, `client_secret`, or pinned secret-bearing test data;
- JForex runtime logs remain local;
- JForex DEBUG output must not be published when it contains authentication/session identifiers, provider endpoints, login identifiers, public IP/network information, or protocol material;
- Maven `target/` output remains ignored;
- acquisition `.part` files remain ignored;
- Dukascopy `.bi5` raw/cache artifacts remain ignored;
- generated historical CSV acquisition artifacts remain outside Git;
- generated runtime metadata containing local paths remains outside Git;
- raw market-data files remain outside Git unless redistribution rights explicitly allow publication;
- runtime volumes, backups, local logs, and secret files must not be committed.

Raw webhook execution data can contain request headers. Execution retention and access must therefore be treated as part of the security boundary.

---

## Current Tech Stack

### Implemented / Tested Operational Stack

| Domain | Technology | Responsibility | Status |
|---|---|---|---|
| Workflow orchestration | n8n | ingestion, validation orchestration, monitoring, alerting, lifecycle workflows | **TESTED** |
| Workflow logic | JavaScript | validation, normalization, rule evaluation, request shaping | **TESTED** |
| Operational market-data provider | Alpha Vantage REST | current operational FX quote source | **TESTED** |
| Operational database | PostgreSQL 16 | quotes, runs, anomalies, alerts, lifecycle audit | **TESTED** |
| Local runtime | Docker Compose | reproducible local service orchestration | **TESTED** |
| Source control | Git / GitHub | versioned code/configuration and reviewable change history | **CURRENT** |
| Notification channel | Gmail SMTP | current critical-alert delivery | **TESTED** |

### MSc Research Tooling

| Domain | Technology | Responsibility | Status |
|---|---|---|---|
| Historical FX acquisition | Java + Dukascopy JForex SDK | bounded read-only historical EUR/USD acquisition | **TESTED — RESEARCH TOOLING** |
| Structural source auditing | Python | deterministic TrueFX structural inspection | **TESTED** |
| Cross-source compatibility analysis | Python | bounded temporal-overlap and matching-feasibility analysis | **TESTED FOR CURRENT PILOT SAMPLE** |
| Five-day compatibility pilot | TrueFX + Dukascopy candidates | determine source-pair suitability for the thesis | **IN PROGRESS** |

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

- database credentials;
- provider secrets;
- streaming-platform credentials;
- infrastructure credentials;
- Vault credentials;
- privileged backend tokens.

Privileged writes require authentication, authorization, validation, and audit evidence.

---

## Provider Intelligence Direction

Provider intelligence is a planned product capability that becomes meaningful only after independent multi-provider evidence exists.

Planned capabilities include:

- provider health and availability metrics;
- data-quality scorecards;
- temporal coverage metrics;
- divergence and unmatched-event metrics;
- latency/age evidence where semantics are actually available;
- provider certification checks;
- provider migration assurance;
- configuration replay/change assurance;
- lineage and blast-radius evidence.

Provider disagreement is evidence to investigate. It is not automatically proof that either provider is wrong.

---

## Project Structure

```text
.
├── acquisition/
│   └── jforex-historical-probe/
│       ├── src/
│       │   └── main/
│       │       └── java/
│       │           └── com/
│       │               └── petros/
│       │                   └── thesis/
│       │                       └── jforex/
│       │                           ├── HistoricalTickProbe.java
│       │                           └── Main.java
│       ├── .env.example
│       ├── .gitignore
│       ├── pom.xml
│       └── README.md
├── docs/
│   └── architecture.md
├── research/
│   ├── compatibility/
│   │   └── compare_truefx_dukascopy.py
│   └── truefx/
│       └── audit_truefx.py
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

Generated acquisition output, logs, build directories, provider cache files, credentials, and raw research data are deliberately excluded from this source tree.

New modules should be introduced only when their responsibility is concrete and the dependency order justifies them.

---

## Testing and Verification Evidence

### Operational Platform

Current verified operational evidence includes:

- three-pair FX ingestion;
- normalized output generation;
- PostgreSQL quote persistence;
- duplicate-safe reprocessing;
- `started` / `success` workflow lifecycle;
- controlled production failure handling;
- provider-response validation;
- wide-spread detection;
- stale-quote detection;
- extreme price-movement detection;
- critical anomaly routing;
- persisted pending alert;
- successful Gmail SMTP delivery;
- persisted alert success state;
- alert failure state;
- environment-based alert routing;
- n8n persistent-volume restoration;
- lifecycle schema verification;
- lifecycle authentication denial;
- invalid lifecycle request handling;
- missing-anomaly handling;
- illegal-transition handling;
- successful lifecycle transitions;
- persisted acknowledgement and resolution metadata;
- optimistic-concurrency stale-write rejection;
- atomic lifecycle audit persistence;
- isolated fresh PostgreSQL bootstrap;
- migration-order verification;
- runtime container/database identity verification;
- workflow export JSON validation;
- secret-pattern inspection;
- temporary verification-resource cleanup.

### Research / Acquisition Tooling

Current inspected evidence includes:

- TrueFX January 2026 structural audit;
- frozen TrueFX five-day EUR/USD pilot counts;
- JForex Maven compilation;
- required-parameter fail-closed behavior;
- missing-credential fail-closed behavior;
- canonical one-hour window validation;
- rejection of non-canonical multi-hour requests;
- Dukascopy connection and EUR/USD subscription confirmation;
- successful canonical Jan-27 EUR/USD historical acquisition;
- repeated canonical acquisition with identical row count and timestamp boundaries;
- byte-identical canonical CSV SHA-256 regression;
- metadata schema-v2 verification;
- `window_policy=canonical_utc_hour` verification;
- output-hash verification;
- successful `.part` promotion;
- absence of `.part` after successful completion;
- bounded one-hour TrueFX/Dukascopy compatibility analysis.

The following are **not yet complete**:

```text
five-day Dukascopy acquisition
full five-day TrueFX/Dukascopy compatibility evaluation
final reconciliation tolerance
final source-pair selection
held-out thesis experiment
```

A capability remains below **TESTED** until the relevant result has been inspected.

---

## Known Technical Debt

### 1. Source-Safe Previous Quote

The current operational extreme-movement previous-quote lookup is not yet provider/source-scoped.

This must be resolved before second-provider operation.

### 2. Timestamp / Timezone / Precision Provenance

The current Alpha Vantage operational adapter does not yet preserve full raw timestamp, timezone, and precision semantics as explicit provenance.

The research canonical pipeline must preserve these semantics explicitly where the source supports them.

### 3. Provider Instrument Semantics

`provider_instrument_id` exists but is not yet populated with verified provider-specific identifier semantics in the operational pipeline.

### 4. Threshold / Configuration Provenance

Operational thresholds are currently hardcoded.

Future rules must be versioned and preserve the exact effective configuration used for each decision.

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

The current n8n image reports configuration deprecation/task-runner warnings.

Current JavaScript workflows remain operational, but production hardening should remove deprecated configuration and define runner behavior explicitly before relying on it at larger scale.

### 8. JForex Provider/Network Variability

Historical JForex acquisition has exhibited intermittent provider/network failures during development.

The current one-hour acquisition boundary reduces exposure and fails closed, but it does not imply that the provider or network is failure-free.

Repeated failures must be investigated using bounded, sanitized evidence.

### 9. Research Source Pair

TrueFX and Dukascopy remain candidate historical sources.

The final pair must not be frozen until the full five-day compatibility pilot and data-use suitability review are complete.

---

## Engineering Independence

The platform is provider-neutral and institution-independent.

Technology or architecture choices should be justified by:

- a concrete problem;
- a clear responsibility;
- the simplest viable alternative;
- measurable success criteria;
- a verification plan;
- dependency order;
- actual implementation evidence.

No technology enters the core solely because it is popular, appears in an employer stack, or looks useful on a technology list.

Public provider, industry, or repository material may inform implementation patterns or bounded experiments, but it does not establish runtime state, research truth, or proprietary architecture.

---

# Development Roadmap

The project deliberately separates:

1. the bounded MSc research track; and
2. the broader long-term engineering/product track.

The two tracks share components where useful, but broader engineering work must not silently alter, delay, or invalidate the frozen thesis protocol.

---

## MSc Research Track

Current sequence:

```text
Five-day source compatibility pilot
      ↓
Canonical research representation + provenance
      ↓
Fixed robust monitoring baseline
      ↓
Past-only adaptive monitoring policy
      ↓
Frozen temporal reconciliation policy
      ↓
Controlled fault injection
      ↓
2 × 2 held-out evaluation
      ↓
Analysis and reproducibility artifacts
```

### R1. Dataset Compatibility Pilot — ACTIVE

Current task:

```text
Complete the frozen five-day EUR/USD TrueFX/Dukascopy compatibility pilot.
```

Required evidence includes:

- schema compatibility;
- timestamp semantics;
- overlap;
- temporal matching feasibility;
- coverage;
- unmatched observations;
- candidate tolerance behavior;
- data-use suitability.

### R2. Canonical Research Pipeline

Planned scope:

- provider/source adapters;
- deterministic validation;
- timestamp normalization;
- canonical representation;
- explicit provenance;
- reproducible hashes/versions;
- deterministic tests.

### R3. Fixed Robust Baseline

Planned scope:

- chronological calibration;
- robust location and scale;
- equivalent fixed alert budget;
- freeze before held-out evaluation.

### R4. Past-Only Adaptive Policy

Planned scope:

- rolling median/MAD;
- past-only windows;
- frozen warm-up policy;
- minimum-history policy;
- missing-data policy;
- contamination policy;
- numerical safeguards.

### R5. Temporal Reconciliation

Planned scope:

- causal and symmetric analysis;
- tolerance;
- ties;
- reuse;
- unmatched behavior;
- provider age;
- coverage;
- confidence/evidence semantics.

### R6. Controlled Fault Injection

Planned scope:

- F1 price corruption;
- F2 spread corruption;
- F3 temporal faults;
- frozen magnitudes;
- frozen durations;
- deterministic seeds;
- source/config/dataset provenance.

### R7. Held-Out 2 × 2 Evaluation

```text
System A = Fixed + Single Source
System B = Adaptive + Single Source
System C = Fixed + Cross Source
System D = Adaptive + Cross Source
```

All systems must be evaluated on equivalent chronological held-out scenarios under the frozen protocol.

### R8. Analysis and Reproducibility

Planned outputs:

- Macro-F1;
- per-class metrics;
- false-positive rate;
- detection delay;
- reconciliation coverage;
- unmatched rate;
- uncertainty;
- sensitivity;
- failure cases;
- code/data/config/seed/Git provenance;
- negative or mixed result reporting.

---

## Broader Engineering Track

The current broader engineering sequence is:

```text
Configuration-driven rules + reference data
      ↓
Operational provider abstraction
      ↓
Second independent operational source
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

### 1. Configuration-Driven Rules and Reference Data — NEXT ENGINEERING DEPENDENCY

Planned scope:

- externalized instrument configuration;
- versioned operational thresholds;
- severity-specific threshold provenance;
- explicit rule identifiers and versions;
- canonical instrument reference data;
- provider-specific instrument mappings;
- effective-dated mappings;
- explicit timestamp/provenance policy.

### 2. Operational Provider Abstraction

Planned scope:

- provider-neutral ingestion contract;
- source-specific adapters;
- provider-specific validation boundaries;
- source-safe historical lookup semantics;
- provider metadata and health evidence.

### 3. Second Independent Operational Source

A second operational provider must be integrated through the provider boundary rather than duplicated workflow logic.

The current Dukascopy historical research probe does not satisfy this milestone by itself.

### 4. Temporal Cross-Source Reconciliation

Operational reconciliation must explicitly define:

- matching direction;
- time tolerance;
- tie handling;
- event reuse policy;
- unmatched behavior;
- provider age;
- coverage metrics;
- confidence/evidence semantics.

Two-source ingestion alone is not reconciliation.

### 5. Replay and Deterministic Evaluation

Planned capabilities:

- deterministic replay;
- controlled fault injection;
- versioned datasets/configuration;
- repeatable quality checks;
- comparison of monitoring policies;
- reproducible evidence manifests.

### 6. Observability and Product Boundary

Planned capabilities:

- metrics and dashboards;
- distributed tracing where justified;
- structured operational logs;
- Platform API/BFF;
- typed contracts;
- React/TypeScript console;
- role-controlled operator actions.

### 7. Provider Intelligence

Planned capabilities:

- provider scorecards;
- SLA/availability evidence;
- temporal coverage metrics;
- certification and migration assurance;
- configuration replay/change assurance;
- lineage and blast-radius evidence.

### 8. Extended Platform

Only after simpler verified baselines justify the added complexity:

- Kafka / Schema Registry / Kafka Connect;
- Flink;
- ClickHouse;
- Redis / MongoDB where justified;
- MinIO / Parquet / Iceberg;
- Spark / Trino / dbt;
- Temporal / Airflow;
- high-performance replay components where measured need exists;
- Kubernetes / Helm / GitOps;
- Vault / OIDC / fine-grained authorization;
- autoscaling and progressive delivery;
- load, failure, chaos, recovery, and DR exercises;
- advanced observability and profiling;
- developer-platform and governance capabilities;
- governed advisory automation where justified.

---

## Definition of Done

A milestone is complete only when:

1. implementation exists;
2. key success and failure paths are tested;
3. relevant runtime, database, log, metric, trace, container, artifact, or browser evidence is inspected;
4. destructive or temporary test artifacts are cleaned;
5. `git diff`, `git status`, and secret checks are inspected;
6. committed `HEAD` equals the tested state;
7. push is confirmed when the milestone is intended to be shared;
8. current repository documentation agrees with the committed behavior.

If these conditions are not satisfied, the capability remains at a lower status.

---

## Current Next Steps

The repository currently has two deliberately separated execution tracks.

### MSc Research Track — ACTIVE

> **Complete the frozen five-day EUR/USD TrueFX/Dukascopy compatibility pilot.**

Frozen UTC calendar dates:

```text
2026-01-26
2026-01-27
2026-01-28
2026-01-29
2026-01-30
```

Remaining work includes:

- complete bounded canonical-hour Dukascopy acquisition for the required pilot windows;
- preserve immutable acquisition provenance;
- evaluate full-period overlap;
- evaluate temporal matching feasibility;
- inspect coverage and unmatched behavior;
- review candidate matching tolerances;
- confirm data-use suitability;
- decide whether TrueFX + Dukascopy are acceptable as the final thesis source pair.

The final source pair and reconciliation tolerance must not be frozen before this evidence is complete.

### Broader Engineering Track — NEXT DEPENDENCY

> **Implement configuration-driven rules and reference data.**

This engineering block will:

- externalize operational thresholds;
- preserve rule/severity/configuration provenance;
- define canonical instrument semantics;
- define provider-specific instrument mappings;
- establish explicit timestamp/reference semantics;
- prepare the operational platform for provider abstraction and second-source integration.

Broader engineering work must not alter, delay, or invalidate the MSc research protocol.

---

## Current Research Status Summary

```text
TrueFX structural audit                     TESTED
TrueFX frozen pilot-week counts             TESTED
JForex Maven compilation                    TESTED
Canonical-hour Main.java validation         TESTED
Non-canonical multi-hour rejection          TESTED
Credential fail-closed behavior             TESTED
Jan-27 12:00 JForex acquisition             TESTED
Jan-27 acquisition repeatability            TESTED
HistoricalTickProbe canonical valid path    TESTED
Metadata schema-v2 verification             TESTED
Artifact SHA-256 verification               TESTED
No residual .part after success             TESTED
One-hour cross-source compatibility         TESTED — PILOT EVIDENCE
Five-day Dukascopy acquisition              IN PROGRESS
Five-day compatibility evaluation           IN PROGRESS
Final source-pair acceptance                PENDING
Final temporal reconciliation policy        PENDING
Fixed/adaptive research experiment          PLANNED
Held-out Systems A-D evaluation             PLANNED
```

---

## Final Scope Reminder

This repository contains:

```text
operational FX data assurance
+
bounded MSc market-data research tooling
+
a broader staged engineering/product roadmap
```

It does not contain or target:

```text
trade execution
order routing
trading signals
positions
hedging
P&L logic
buy/sell decision making
```

The project exists to engineer, evaluate, and evidence the reliability, validity, provenance, temporal consistency, and operational manageability of financial market-data flows.