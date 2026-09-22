# System Architecture

## Overview

The **Financial Data Assurance & Reconciliation Platform (FDAR)** is an evidence-driven platform for financial market-data validation, normalization, persistence, monitoring, temporal reconciliation, operational evidence, and provider intelligence.

FX is the initial bounded domain.

The repository currently contains two deliberately separated architectural paths:

1. an **operational FX market-data assurance runtime** based on n8n, JavaScript, Alpha Vantage REST, PostgreSQL 16, Docker Compose, and Gmail SMTP;
2. a bounded **MSc historical-data research path** using TrueFX, Dukascopy/JForex, Java, and Python for source auditing, acquisition, compatibility analysis, and later controlled empirical evaluation.

The operational path is currently single-provider.

The research path contains two candidate historical sources, but this does **not** mean the operational platform is already a multi-provider reconciliation system.

> **Scope boundary:** FDAR is not a trading bot. It does not execute or route trades, generate trading signals, manage positions, perform hedging, calculate trading P&L, or make buy/sell decisions. Market prices are treated as operational and research data.

---

## Architectural Status Model

Architecture documentation follows the same evidence discipline as the repository.

- **TESTED** — behaviour or structure has been verified through inspected runtime, database, execution, log, artifact, container, delivery, or deterministic test evidence.
- **IMPLEMENTED** — code, configuration, or schema exists but verification is incomplete.
- **IN PROGRESS** — partially implemented or actively being completed.
- **PLANNED** — accepted future capability that is not currently implemented.
- **PROPOSED** — candidate design requiring further evidence or feasibility work.
- **OPTIONAL** — future or laboratory capability.
- **PENDING** — a decision depends on incomplete evidence.
- **UNKNOWN** — available evidence is insufficient.

A diagram or document does not by itself upgrade implementation status.

---

# 1. Architectural Boundaries

The repository currently has three distinct boundaries:

```text
Operational Runtime
        |
        +--> Alpha Vantage / n8n / PostgreSQL / Gmail SMTP
        |
        +--> operational anomaly and lifecycle management

Historical Research Acquisition
        |
        +--> TrueFX local historical files
        |
        +--> Dukascopy / JForex historical acquisition

Research Analysis
        |
        +--> Python structural audit
        |
        +--> cross-source compatibility analysis
        |
        +--> future canonical research pipeline
        |
        +--> future reconciliation / monitoring / fault injection
```

These boundaries intentionally prevent research acquisition experiments from being confused with production provider integration.

---

# 2. Current Operational Runtime Boundary

The current verified operational runtime is:

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

Current Docker identities:

```text
Compose project: financial-data-assurance-reconciliation-platform

PostgreSQL container:
fdar-postgres

n8n container:
fdar-n8n
```

Current PostgreSQL identity:

```text
Database: fdar
User: fdar
```

Current persistent Docker volumes:

```text
fdar-postgres-data
fdar-n8n-data
```

Current lifecycle webhook path:

```text
fdar-anomaly-lifecycle
```

Current lifecycle authentication header:

```text
X-FDAR-Lifecycle-Token
```

The authentication value remains secret and outside source control.

---

# 3. Operational Workflow Orchestration

n8n currently coordinates:

- scheduled and manual market-data workflow execution;
- Alpha Vantage REST integration;
- sequential multi-instrument processing;
- provider-response validation;
- canonical quote normalization;
- PostgreSQL persistence;
- operational anomaly detection;
- critical anomaly alert routing;
- workflow execution lifecycle tracking;
- centralized workflow failure handling;
- authenticated anomaly lifecycle operations.

Current version-controlled workflow exports:

```text
workflows/fdar-fx-market-data-pipeline-alpha-vantage.json
workflows/fdar-workflow-error-handler.json
workflows/fdar-anomaly-lifecycle-manager.json
```

The workflow exports and inspected n8n runtime remain authoritative for exact node wiring.

---

# 4. Operational Market-Data Integration

The currently integrated operational FX provider is:

```text
Alpha Vantage
```

using:

```text
CURRENCY_EXCHANGE_RATE
```

The operational workflow currently processes:

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

The same provider-specific integration path is reused across the three configured instruments.

Provider responses are treated as untrusted external input.

The operational implementation still has one provider only.

Therefore:

```text
historical two-source research
        ≠
operational second-provider integration
        ≠
temporal reconciliation
```

---

# 5. Sequential Operational Provider Flow

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

This pacing mechanism is specific to the current Alpha Vantage integration.

It is not a general:

- retry framework;
- exponential backoff implementation;
- circuit breaker;
- bulkhead;
- provider-health framework.

Those require explicit implementation and verification.

---

# 6. Operational Validation and Normalization

JavaScript currently performs provider-response validation and normalization before persistence.

Current validation includes:

- provider error-payload detection;
- expected response-shape validation;
- required currency fields;
- numeric bid validation;
- numeric ask validation;
- positive bid;
- positive ask;
- `ask >= bid`;
- timestamp presence;
- timestamp parseability under the current adapter semantics.

Invalid responses are rejected before normal quote persistence.

## Current Canonical Operational Quote Shape

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
raw_payload
```

Current canonical symbols:

```text
EURUSD
GBPUSD
USDJPY
```

Derived values:

```text
mid_price  = (bid + ask) / 2
spread     = ask - bid
spread_bps = (spread / mid_price) * 10000
```

The existence of a canonical output shape does not yet constitute a complete provider-abstraction layer.

---

# 7. PostgreSQL Operational Persistence

PostgreSQL 16 is the current operational system of record.

Current operational tables:

```text
fx_quotes
workflow_runs
anomalies
alerts
anomaly_lifecycle_events
```

## `fx_quotes`

Responsibilities:

- normalized quote persistence;
- provider/source provenance;
- raw provider payload retention;
- duplicate-safe logical quote storage.

Current logical uniqueness:

```sql
UNIQUE (symbol, observed_at, source)
```

## `workflow_runs`

Responsibilities:

- execution start state;
- success/failure state;
- execution identity;
- processed-record count;
- error evidence;
- execution timestamps.

## `anomalies`

Responsibilities:

- persisted data-quality findings;
- severity;
- metric and threshold evidence;
- anomaly lifecycle state;
- acknowledgement/resolution metadata.

Current lifecycle states:

```text
open
acknowledged
resolved
```

## `alerts`

Current delivery states:

```text
pending
sent
failed
```

## `anomaly_lifecycle_events`

Responsibilities:

- durable transition evidence;
- previous and resulting state;
- lifecycle action;
- resolution context;
- workflow/execution provenance;
- transition timestamp.

The table references `anomalies(id)` using:

```text
ON DELETE RESTRICT
```

Current legal transitions:

```text
open → acknowledged
acknowledged → resolved
```

---

# 8. Duplicate Safety and Idempotency

Operational quote persistence uses database-backed duplicate protection.

```sql
UNIQUE (symbol, observed_at, source)
```

Conflict-safe persistence prevents replay of the same logical quote from failing solely because the record already exists.

This provides idempotency under the current uniqueness definition.

It is not yet a complete multi-provider replay or identity model.

---

# 9. Operational Execution Lifecycle

The market-data workflow records execution state in `workflow_runs`.

## Start

```text
status = started
records_processed = 0
```

## Success

```text
status = success
records_processed = <normalized output count>
finished_at = <completion timestamp>
```

`records_processed` currently represents normalized output count.

It must not automatically be interpreted as inserted-row count because duplicate conflict handling may prevent a new insert.

## Failure

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

Persisted failure evidence includes:

```text
status = failed
error_message = <captured failure>
finished_at = <failure timestamp>
```

---

# 10. Operational Anomaly Detection

Current anomaly types:

```text
wide_spread
stale_quote
extreme_price_movement
```

The current thresholds are operational assumptions only.

They are not universal market rules and are not the frozen MSc statistical-monitoring policy.

## Wide Spread

```text
spread_bps = (spread / mid_price) * 10000
```

Current thresholds:

```text
Warning:  > 2 bps
Critical: > 5 bps
```

## Stale Quote

Current thresholds:

```text
Warning:  > 600 seconds
Critical: > 1800 seconds
```

Freshness remains a deterministic operational policy.

## Extreme Price Movement

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

## Source-Safety Limitation

The current previous-quote lookup is not yet explicitly source/provider-scoped.

This must be corrected before operational multi-provider processing.

Accidental cross-provider historical baselining must not occur.

---

# 11. Critical Alerting

Current critical-alert flow:

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
success failure
   |       |
   v       v
 sent    failed
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

Current implemented notification channel:

```text
Gmail SMTP
```

Other channels remain future adapters unless separately implemented and verified.

---

# 12. Anomaly Lifecycle Management

Anomaly lifecycle management is a current **TESTED** capability.

Current workflow:

```text
FDAR Anomaly Lifecycle Manager
```

Current supported transitions:

```text
open → acknowledged
acknowledged → resolved
```

Current processing flow:

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

Controlled failures route through:

```text
Lifecycle Error
      |
      v
Build Webhook Error Response
      |
      v
Respond Lifecycle Error
```

Current verified HTTP behavior:

```text
403  authentication denial
400  invalid request/action or missing resolution reason
404  anomaly not found
409  illegal or stale lifecycle transition
200  successful acknowledge / resolve
```

Successful lifecycle mutation and audit insertion occur atomically.

---

# 13. Operational Market-Data Flow

Conceptual flow:

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
Persist Quote   Detect Ops   Check Price
PostgreSQL      Anomalies     Movement
        \          |            /
         \         v           /
          ------ Log Anomaly ---
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
            /           \
       success         failure
          |               |
          v               v
 Mark Alert Sent   Mark Alert Failed
```

The inspected n8n runtime and committed workflow export remain authoritative for exact branching.

---

# 14. Fresh Database Bootstrap

PostgreSQL mounts migrations under:

```text
/docker-entrypoint-initdb.d/
```

Current migration chain:

```text
001_schema.sql
      |
      v
002_alerting_anomaly_lifecycle.sql
      |
      v
003_anomaly_lifecycle_audit.sql
```

An isolated PostgreSQL 16 bootstrap verification confirmed:

- clean empty-volume initialization;
- database `fdar`;
- user `fdar`;
- ordered `001 → 002 → 003` execution;
- expected operational tables;
- expected lifecycle fields;
- expected lifecycle constraints;
- expected lifecycle indexes;
- expected FDAR table ownership;
- no relevant initialization `ERROR`, `FATAL`, or `PANIC`;
- cleanup of temporary test resources.

The clean-bootstrap path is currently **TESTED**.

---

# 15. Runtime Persistence Architecture

Current Docker persistence uses:

```text
fdar-postgres-data
fdar-n8n-data
```

The PostgreSQL volume protects database state across container recreation.

The n8n volume protects locally persisted n8n application state.

A volume declaration alone is not considered sufficient evidence of persistence.

Actual runtime mounts and restoration behavior must be inspected.

---

# 16. MSc Historical-Research Architecture

The MSc research path is deliberately independent from the operational Alpha Vantage workflow.

Current conceptual architecture:

```text
TrueFX Historical Files
        |
        v
TrueFX Structural Audit
        |
        |
        +-------------------------+
                                  |
                                  v
                         Compatibility Analysis
                                  ^
                                  |
        +-------------------------+
        |
        v
Dukascopy DEMO / Historical Data
        |
        v
JForex SDK
        |
        v
Main.java
        |
        v
HistoricalTickProbe.java
        |
        v
ticks.csv + metadata.json
(local research storage)
```

The historical datasets and generated evidence artifacts remain outside Git.

The repository contains code and documentation only.

---

# 17. TrueFX Research Boundary

Current utility:

```text
research/truefx/audit_truefx.py
```

Responsibilities:

- deterministic CSV parsing;
- timestamp validation;
- price validation;
- positive-price checks;
- bid/ask relationship checks;
- ordering checks;
- duplicate inspection;
- repeated-timestamp reporting;
- instrument validation;
- target-period row counts.

The audited TrueFX data remains local.

TrueFX historical observations are reference observations.

They are not universal FX ground truth.

---

# 18. Dukascopy/JForex Acquisition Boundary

Current module:

```text
acquisition/jforex-historical-probe/
```

Primary classes:

```text
Main.java
HistoricalTickProbe.java
```

Current Maven artifact:

```text
com.petros.thesis:jforex-historical-probe:1.0.0
```

Current JForex dependency:

```text
com.dukascopy.dds2:DDS2-jClient-JForex:3.6.51
```

Java source target:

```text
release 8
```

The acquisition process runs independently from n8n and Docker Compose.

---

# 19. JForex Acquisition Contract

The current acquisition policy permits exactly one canonical UTC hour per run:

```text
HH:00:00.000Z
through
HH:59:59.999Z
inclusive
```

Policy identifier:

```text
canonical_utc_hour
```

The one-hour boundary is a fail-closed engineering response to observed instability in larger historical requests.

A successful load must not be assumed merely because a provider callback reports completion.

Local artifact validation remains part of the acquisition contract.

---

# 20. JForex Main Process

`Main.java` is responsible for:

- CLI parsing;
- required-parameter validation;
- instrument parsing;
- UTC timestamp validation;
- millisecond-alignment validation;
- canonical-hour enforcement;
- credential loading from environment variables;
- unique run-directory allocation;
- Dukascopy connection;
- subscription confirmation;
- bounded strategy execution;
- historical-probe orchestration;
- CSV artifact promotion;
- SHA-256 calculation;
- metadata generation;
- bounded disconnect handling;
- process exit status.

Credentials are read only from:

```text
DUKASCOPY_DEMO_USERNAME
DUKASCOPY_DEMO_PASSWORD
```

They are never hard-coded.

---

# 21. HistoricalTickProbe Boundary

`HistoricalTickProbe.java` is responsible for the historical tick stream itself.

It uses:

```text
IHistory.readTicks
```

and writes only historical callback observations.

Live `onTick()` data is intentionally excluded.

Current structural validation includes:

- expected instrument;
- timestamp inside requested inclusive interval;
- finite bid;
- finite ask;
- positive bid;
- positive ask;
- `ask >= bid`;
- finite volumes;
- non-negative volumes;
- non-decreasing timestamps.

Equal timestamps may be preserved.

No acquisition-layer deduplication is invented.

---

# 22. Historical Artifact Commit Protocol

Historical output is first written as:

```text
ticks.csv.part
```

Successful completion requires:

```text
no local failure
loadingFinished observed
allDataLoaded = true
rows > 0
valid first/last timestamps
writer closed
temporary artifact exists
final artifact does not already exist
```

The final artifact is promoted to:

```text
ticks.csv
```

Atomic move is preferred when supported.

Fallback promotion retains no-overwrite behavior.

Research evidence is never silently replaced.

---

# 23. JForex Metadata and Provenance

Current metadata schema:

```text
schema_version = 2
```

Representative fields:

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

The metadata does not make unknown market-data semantics known.

For example, historical files do not establish original network-arrival latency unless the source explicitly provides it.

---

# 24. Canonical JForex Regression Oracle

Current canonical regression window:

```text
Instrument:     EUR/USD
From:           2026-01-27T12:00:00.000Z
To:             2026-01-27T12:59:59.999Z
Rows:           7630
First epoch_ms: 1769515200187
Last epoch_ms:  1769518799335
SHA-256:        259666ce9f4eee67afa5b8ce905eee6775478cff73c08a52f99f2fc3050f2f1e
```

The current hardened acquisition path reproduced:

```text
schema_version   = 2
window_policy    = canonical_utc_hour
all_data_loaded  = true
rows             = 7630
first_epoch_ms   = 1769515200187
last_epoch_ms    = 1769518799335
hash_matches     = true
part_exists      = false
```

This regression oracle demonstrates stable serialization for this known-good window.

It does not imply that other market hours must contain the same number of ticks.

---

# 25. Cross-Source Compatibility Analysis

Current utility:

```text
research/compatibility/compare_truefx_dukascopy.py
```

Responsibilities include bounded analysis of:

- temporal overlap;
- active minutes;
- causal reusable matching;
- timestamp separation;
- peer-evidence coverage.

Current one-hour pilot evidence showed incomplete ≤1-second causal peer coverage.

Therefore the protocol review trigger is active.

No final matching tolerance has yet been frozen.

---

# 26. Five-Day Compatibility Pilot

Primary instrument:

```text
EUR/USD
```

Frozen UTC calendar dates:

```text
2026-01-26
2026-01-27
2026-01-28
2026-01-29
2026-01-30
```

Candidate sources:

```text
TrueFX
Dukascopy / JForex
```

The pilot must evaluate:

- actual schema compatibility;
- timestamp semantics;
- observed overlap;
- temporal matching feasibility;
- coverage;
- unmatched behavior;
- candidate tolerances;
- data-use suitability.

Current status:

```text
TrueFX audit                     TESTED
JForex acquisition tooling       TESTED for canonical valid path
One-hour compatibility sample    TESTED
Five-day Dukascopy acquisition   IN PROGRESS
Five-day compatibility analysis  IN PROGRESS
Final source pair                PENDING
```

TrueFX and Dukascopy remain candidates until this work is complete.

---

# 27. Research Temporal-Reconciliation Boundary

The future thesis reconciliation policy must explicitly define:

- causal versus symmetric matching;
- matching direction;
- maximum tolerance;
- tie handling;
- one-to-one versus reusable evidence;
- unmatched behavior;
- maximum provider age;
- coverage;
- evidence availability;
- confidence semantics.

For operational causal claims:

```text
Source A observation at t
may use only eligible Source B evidence
available at or before t
```

No future look-ahead is permitted.

Historical file availability must not be confused with original real-time availability.

---

# 28. Research Ground Truth Boundary

Cross-source disagreement is not ground truth.

Known fault labels must come from:

```text
controlled deterministic fault injection
```

Primary fault families:

```text
F1 — price corruption
F2 — spread corruption
F3 — temporal fault
```

Non-injected history is treated as reference observations.

Provider agreement does not prove correctness.

Provider disagreement does not prove a fault.

---

# 29. Research Monitoring Architecture

The future research experiment uses four systems:

```text
                Single Source   Cross Source

Fixed           System A        System C
Adaptive        System B        System D
```

The fixed policy is calibrated chronologically and then frozen.

The adaptive policy uses past-only rolling statistics.

No random row-level split is used.

The evaluation sequence is:

```text
Compatibility Pilot
        |
        v
Development / Calibration
        |
        v
Protocol Freeze
        |
        v
Held-Out Reference Data
        |
        v
Controlled Fault Injection
        |
        v
Systems A-D
        |
        v
Evaluation
```

This research path is not yet complete.

---

# 30. Security Boundaries

Current security rules include:

- Alpha Vantage credentials remain outside Git;
- SMTP credentials remain outside Git;
- PostgreSQL passwords remain outside Git;
- lifecycle authentication tokens remain outside Git;
- Dukascopy DEMO credentials remain outside Git;
- `.env` files containing real values remain ignored;
- `.env.example` files contain placeholders only;
- external provider responses are treated as untrusted input;
- lifecycle requests are authenticated before mutation;
- lifecycle mutations validate legal state;
- privileged lifecycle operations generate durable audit evidence;
- dynamic SQL uses parameterization where applicable;
- raw request headers are treated as potentially secret-bearing;
- generated market-data artifacts remain outside Git;
- raw provider datasets remain outside Git unless redistribution rights permit publication.

## JForex-Specific Security Boundary

JForex DEBUG logs may expose:

- authentication/session identifiers;
- login identifiers;
- provider/API hosts;
- network information;
- public IP information;
- protocol material.

Therefore:

```text
logs/
*.log
```

remain local and ignored.

Raw DEBUG logs must not be committed or published.

Other ignored acquisition/runtime artifacts include:

```text
target/
out/
*.part
*.bi5
```

---

# 31. Repository Boundary

Version-controlled source includes:

```text
acquisition/
docs/
research/
sql/
workflows/
docker-compose.yml
README.md
safe configuration templates
```

Local/generated data does not belong in Git:

```text
.env
logs
target
generated acquisition CSVs
generated metadata
.part files
.bi5 provider data
raw licensed datasets
JForex cache
```

---

# 32. Planned Server-Side Product Boundary

The future product architecture is:

```text
React / TypeScript Operator Console
               |
               v
        Platform API / BFF
               |
               +--> domain services
               |
               +--> operational / analytical stores
               |
               +--> workflow / streaming adapters
               |
               +--> observability adapters
               |
               +--> authentication / authorization
               |
               +--> audit boundary
```

This architecture remains **PLANNED**.

The browser must not receive unrestricted:

- database credentials;
- provider credentials;
- infrastructure credentials;
- secret-management credentials;
- privileged backend tokens.

Privileged browser-facing writes require server-side authentication, authorization, validation, and audit.

---

# 33. Current Architectural Limitations

## Operational Single Provider

Alpha Vantage remains the only operational provider.

The JForex acquisition probe is research tooling, not operational integration.

## No Operational Temporal Reconciliation

Cross-source research compatibility analysis exists, but production temporal reconciliation does not.

## Source-Safe Previous Quote

The current operational previous-quote lookup is not explicitly provider/source-scoped.

This must be corrected before operational second-provider ingestion.

## Timestamp Provenance

The operational Alpha Vantage path does not yet preserve all raw timestamp, timezone, and precision semantics required by the target canonical model.

## Provider Instrument Semantics

`provider_instrument_id` is not yet populated with verified Alpha Vantage-specific identifier semantics.

## Configuration Provenance

Operational thresholds are still hardcoded assumptions.

Versioned rule/config provenance remains future work.

## Processing Counters

`records_processed` represents normalized output count.

The architecture does not yet expose separate:

```text
records_normalized
records_inserted
records_duplicate
records_rejected
```

## Product Security Boundary

Current lifecycle operations use n8n Header Auth.

A browser-facing product requires a dedicated API/BFF authorization boundary.

## Observability

Prometheus, Grafana, OpenTelemetry, Jaeger, Loki, and related infrastructure are not part of the current runtime.

## Historical Source Pair

TrueFX and Dukascopy have not yet passed the complete five-day source-selection pilot.

Final pair acceptance therefore remains pending.

---

# 34. Planned Architectural Evolution

The project maintains two dependency tracks.

## MSc Research Track

```text
Five-day source compatibility pilot
        |
        v
Canonical research representation
        |
        v
Fixed robust baseline
        |
        v
Past-only adaptive policy
        |
        v
Frozen temporal reconciliation
        |
        v
Controlled fault injection
        |
        v
2 x 2 held-out evaluation
        |
        v
Analysis / reproducibility
```

## Broader Engineering Track

```text
Configuration-driven rules
+ reference data
        |
        v
Operational provider abstraction
        |
        v
Second operational source
        |
        v
Temporal cross-source reconciliation
        |
        v
Observability
+ Platform API / BFF
        |
        v
Operator product
+ provider intelligence
        |
        v
Extended streaming / analytics /
resilience / security / platform capabilities
```

The engineering roadmap must not alter or invalidate the frozen research protocol.

---

# 35. Configuration and Reference Data — Next Engineering Dependency

Planned responsibilities include:

- configuration-driven instruments;
- versioned operational thresholds;
- severity-specific threshold provenance;
- canonical/provider instrument mappings;
- effective dating;
- explicit provider identifiers;
- explicit timestamp/provenance policy;
- source-safe historical lookup behavior.

---

# 36. Provider Abstraction

Future responsibilities include:

- provider-neutral contracts;
- provider-specific adapters;
- consistent validation boundaries;
- explicit source provenance;
- source-safe previous-observation semantics;
- provider metadata and health evidence.

The existing Alpha Vantage normalizer is not yet a complete provider-abstraction layer.

---

# 37. Second Operational Source and Reconciliation

A future operational second provider must be integrated through the provider abstraction.

It must not be implemented as duplicated workflow logic.

Operational reconciliation will require:

- timestamp normalization;
- temporal matching;
- causal matching rules where applicable;
- tolerance policy;
- tie policy;
- unmatched observations;
- provider age;
- divergence evidence;
- reconciliation coverage;
- confidence semantics.

Two-source ingestion alone must not be described as reconciliation.

---

# 38. Extended Platform Capabilities

Components such as:

- Kafka;
- Schema Registry;
- Kafka Connect;
- Debezium;
- Flink;
- ClickHouse;
- Redis;
- MongoDB;
- MinIO;
- Parquet;
- Iceberg;
- Spark;
- Trino;
- dbt;
- Temporal;
- Airflow;
- Kubernetes;
- Helm;
- GitOps;
- Vault;
- OIDC;
- OpenFGA;
- advanced load/chaos/recovery tooling;

may be introduced only when a distinct responsibility and measurable success criterion justify them.

Their presence in the architectural roadmap is not an implementation claim.

---

# 39. Architectural Non-Goals

FDAR does not provide:

- trade execution;
- order routing;
- trading signals;
- portfolio management;
- position management;
- hedging;
- trading P&L calculation;
- execution decisions.

Market data is processed for:

- assurance;
- quality control;
- operational evidence;
- temporal reconciliation;
- observability;
- research;
- provider intelligence.

---

# 40. Architecture Verification Principle

A capability is not considered implemented merely because it appears in:

- a diagram;
- a roadmap;
- a README;
- this architecture document;
- a proposal;
- a screenshot.

Current architectural claims must be supported by appropriate evidence such as:

- committed implementation;
- inspected runtime behavior;
- database/schema inspection;
- workflow execution evidence;
- artifact inspection;
- container/runtime inspection;
- deterministic tests;
- delivery evidence where applicable.

The evidence hierarchy for implementation status is:

```text
runtime / inspected tests
        >
committed HEAD / tag
        >
checkpoint
        >
architecture / README / guide
        >
research or product plans
```

The formal MSc proposal remains authoritative for the research questions, hypotheses, empirical protocol, and thesis-critical scope.

---

# 41. Current Architecture Status

```text
Operational Alpha Vantage ingestion           TESTED
Operational PostgreSQL persistence            TESTED
Operational anomaly detection                 TESTED
Critical Gmail alerting                       TESTED
Anomaly lifecycle manager                     TESTED
Lifecycle audit trail                         TESTED
Fresh PostgreSQL bootstrap                     TESTED
n8n persistence                               TESTED

TrueFX structural audit                       TESTED
JForex canonical-hour acquisition             TESTED
HistoricalTickProbe canonical valid path      TESTED
JForex deterministic artifact regression      TESTED
One-hour source compatibility analysis        TESTED — PILOT EVIDENCE

Five-day Dukascopy acquisition                IN PROGRESS
Five-day compatibility analysis               IN PROGRESS
Final historical source pair                  PENDING

Operational provider abstraction              PLANNED
Operational second source                     PLANNED
Operational temporal reconciliation           PLANNED
Platform API / BFF                            PLANNED
React operator console                        PLANNED
Provider intelligence                         PLANNED
```

---

## Current Architectural Next Steps

### Active MSc Research Work

```text
Complete the frozen five-day EUR/USD
TrueFX / Dukascopy compatibility pilot.
```

### Next Broader Engineering Dependency

```text
Configuration-driven rules
+ reference data
```

The two tracks remain deliberately separated.

The MSc compatibility pilot must be completed without allowing broader platform work to alter or invalidate the research protocol.