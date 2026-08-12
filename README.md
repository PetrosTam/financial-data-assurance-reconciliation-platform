# FX Operations Automation & Monitoring

An automated FX operations, data-quality, and workflow-monitoring system built with n8n, JavaScript, REST APIs, PostgreSQL, and Docker.

## Overview

This project implements an automated multi-instrument FX data pipeline designed around operational reliability, data quality, monitoring, and fault handling.

The system retrieves foreign-exchange market data from an external REST API, validates and normalizes provider-specific responses, stores structured quotes in PostgreSQL, performs automated operational anomaly checks, and tracks the complete lifecycle of each workflow execution.

The current pipeline processes multiple FX instruments:

- EUR/USD
- GBP/USD
- USD/JPY

The project is designed around several operational principles:

- Reduce manual processing through automation
- Validate incoming structured data before persistence
- Normalize provider-specific responses into a common internal model
- Monitor workflow execution health
- Detect operational and market-data anomalies
- Persist diagnostic information for investigation
- Handle production failures centrally
- Respect third-party API rate limits
- Keep sensitive credentials outside source control

---

## Current Architecture

### Multi-Instrument FX Operations Pipeline

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
                         Wait 3 sec
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
        Persist Quote   Detect Operational     Check Previous
        to PostgreSQL      Anomalies          Price Movement
              |              |                      |
              v              └──────────┬───────────┘
       Mark Run Success                 |
                                        v
                                   Log Anomaly
                                        |
                                        v
                                   PostgreSQL
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

The pipeline currently retrieves and processes:

```text
EUR/USD
GBP/USD
USD/JPY
```

FX pairs are generated dynamically by the `Generate FX Pairs` node rather than being hardcoded inside the HTTP request.

Each generated item contains:

```text
from_currency
to_currency
```

The same HTTP integration therefore works for multiple FX instruments.

### Sequential API Processing

The system processes external API requests sequentially using:

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

and the `Wait` node introduces a three-second delay between requests.

This prevents the workflow from sending all instrument requests simultaneously and provides explicit rate-limit control for the external API integration.

### Scheduled Automation

The production workflow is configured to execute automatically every four hours.

With three FX instruments, each scheduled run performs three external market-data requests.

Manual execution remains available for development and controlled testing.

---

## External API Integration

Market data is retrieved from the Alpha Vantage FX API using the:

```text
CURRENCY_EXCHANGE_RATE
```

function.

The HTTP request uses dynamic parameters:

```text
from_currency = {{ $json.from_currency }}
to_currency   = {{ $json.to_currency }}
```

This allows the same integration node to process any supported FX pair generated upstream.

API authentication is stored using n8n credentials and is not embedded directly in the workflow.

---

## FX Data Validation and Normalization

Provider-specific API responses are transformed into a common internal FX representation using JavaScript.

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

For example:

```text
EUR + USD → EURUSD
GBP + USD → GBPUSD
USD + JPY → USDJPY
```

### Validation Controls

The normalization layer validates:

- Expected API response structure
- Required currency codes
- Numeric bid values
- Numeric ask values
- Positive market prices
- Bid/ask consistency
- Market observation timestamp
- Provider error responses

Invalid provider responses are rejected before reaching PostgreSQL.

### Derived Metrics

The workflow calculates:

```text
mid_price = (bid + ask) / 2
```

and:

```text
spread = ask - bid
```

Timestamps are normalized to UTC before persistence.

---

## PostgreSQL Persistence

Validated quotes are stored in:

```text
fx_quotes
```

The table stores:

- Symbol
- Provider instrument identifier
- Bid
- Ask
- Mid price
- Spread
- Source
- Observation timestamp
- Receipt timestamp
- Raw provider payload

### Duplicate Protection

Database-level uniqueness constraints protect the system against duplicate market-data records.

The persistence node also uses conflict handling so duplicate quotes can be safely skipped rather than causing the workflow to fail.

This makes quote persistence idempotent.

---

## Workflow Execution Monitoring

Every workflow run is tracked in:

```text
workflow_runs
```

### Run Start

At the beginning of each execution, `Log Run Started` stores:

- Workflow name
- n8n execution ID
- Status
- Records processed
- Start timestamp

The initial state is:

```text
status = started
records_processed = 0
```

### Successful Execution

At the end of a successful run, `Mark Run Success` updates the corresponding execution using the n8n execution ID.

The final state becomes:

```text
status = success
records_processed = <number of normalized FX quotes>
finished_at = <completion timestamp>
```

For the current three-instrument pipeline:

```text
records_processed = 3
```

The processed-record count is calculated dynamically from the number of normalized quote items rather than being hardcoded.

`Mark Run Success` executes once per workflow execution, even when multiple FX records are processed.

---

## Production Failure Handling

A dedicated workflow named:

```text
FX Workflow Error Handler
```

handles production failures.

Architecture:

```text
Error Trigger
      ↓
Mark Run Failed
```

When the main production workflow fails, the error workflow receives information about the failed execution.

It correlates the failure with the original `workflow_runs` row using the execution ID and updates:

```text
status = failed
error_message = <actual failure message>
finished_at = <failure completion timestamp>
```

This provides centralized production error handling without duplicating failure logic across individual nodes.

Controlled production failures were used during development to verify the complete failure path.

---

## Operational Anomaly Detection

Validated quotes are evaluated by monitoring branches independently of quote persistence.

This means an unusual but structurally valid market-data record can still be stored while simultaneously being flagged for investigation.

Current anomaly types:

```text
wide_spread
stale_quote
extreme_price_movement
```

Detected anomalies are persisted in:

```text
anomalies
```

---

## Wide Spread Detection

The system calculates the spread in basis points:

```text
spread_bps = (spread / mid_price) * 10000
```

Current initial thresholds:

```text
Warning:  2 bps
Critical: 5 bps
```

When the configured threshold is exceeded, the workflow creates:

```text
anomaly_type = wide_spread
```

Diagnostic information includes:

- Bid
- Ask
- Mid price
- Absolute spread
- Spread in basis points
- Source
- Observation timestamp

---

## Stale Quote Detection

The system compares the quote observation timestamp with the current workflow time.

Current initial thresholds:

```text
Warning:  600 seconds
Critical: 1800 seconds
```

Quotes older than the configured threshold generate:

```text
anomaly_type = stale_quote
```

The anomaly stores the calculated quote age and original observation timestamp.

---

## Extreme Price Movement Detection

The pipeline compares each current quote with the most recent earlier quote for the same FX symbol stored in PostgreSQL.

The previous quote is retrieved using a parameterized SQL query.

Price movement is calculated as:

```text
movement_bps =
    abs(
        (current_mid_price - previous_mid_price)
        / previous_mid_price
    ) * 10000
```

Current initial thresholds:

```text
Warning:  20 bps
Critical: 50 bps
```

When the threshold is exceeded:

```text
anomaly_type = extreme_price_movement
```

The diagnostic payload includes:

- Previous mid price
- Current mid price
- Movement in basis points
- Previous observation timestamp
- Current observation timestamp

Controlled tests were used to verify that extreme movements are correctly detected and persisted without modifying production market-data records.

---

## Anomaly Persistence

All anomaly types use a common persistence structure:

```text
symbol
anomaly_type
severity
metric_value
threshold_value
details
detected_at
resolved_at
```

The `details` field uses PostgreSQL `JSONB` to retain additional diagnostic context.

Current severity levels are:

```text
info
warning
critical
```

If no anomaly is detected, the anomaly branch emits no record and normal quote processing continues unaffected.

---

## Data Model

The PostgreSQL schema currently contains four core operational tables.

### `fx_quotes`

Stores normalized market data and raw provider responses.

### `workflow_runs`

Stores workflow execution lifecycle information.

### `anomalies`

Stores detected data-quality and operational anomalies.

### `alerts`

Reserved for operational notifications generated from detected anomalies and workflow conditions.

---

## Reliability Controls

The project currently implements multiple reliability controls across the data lifecycle:

- Scheduled automation
- Sequential API request processing
- Explicit API request throttling
- Provider-response validation
- Structured data normalization
- Bid/ask integrity checks
- Positive-price validation
- UTC timestamp normalization
- Database uniqueness constraints
- Duplicate-safe persistence
- Raw provider payload retention
- Workflow execution IDs
- Execution lifecycle tracking
- Dynamic processed-record counting
- Success-state persistence
- Failure-state persistence
- Centralized error handling
- Error-message capture
- Wide-spread monitoring
- Stale-data monitoring
- Previous-quote comparison
- Extreme price-movement detection
- Anomaly severity classification
- Structured anomaly persistence
- Independent monitoring branches

---

## Security

Sensitive information is kept outside source control.

### API Credentials

External API authentication is managed through n8n credentials.

API keys are not embedded directly in exported workflow logic.

### PostgreSQL Credentials

Database credentials are managed through n8n credentials.

### Environment Variables

Local configuration is stored in:

```text
.env
```

The file is excluded from Git.

A safe configuration template is provided through:

```text
.env.example
```

### SQL Safety

Dynamic PostgreSQL price comparisons use query parameters rather than directly interpolating runtime values into SQL statements.

### Repository Safety

Exported workflow files are reviewed for secrets before being committed to Git.

---

## Tech Stack

- n8n
- JavaScript
- REST APIs
- PostgreSQL
- Docker
- Git

---

## Project Structure

```text
.
├── docs/
│   └── architecture.md
├── sql/
│   └── 001_schema.sql
├── workflows/
│   ├── multi-instrument-fx-operations-pipeline-alpha-vantage.json
│   └── fx-workflow-error-handler.json
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Current Pipeline Capabilities

The current system can:

1. Automatically start FX ingestion workflows
2. Generate multiple FX instrument requests dynamically
3. Process external API requests sequentially
4. Throttle third-party API traffic
5. Retrieve multiple FX instruments through one reusable REST integration
6. Validate external structured data
7. Normalize provider-specific responses
8. Calculate FX pricing metrics
9. Persist normalized market data
10. Protect against duplicate records
11. Track workflow execution lifecycles
12. Count processed records dynamically
13. Detect successful and failed workflow runs
14. Capture production failure messages
15. Detect wide spreads
16. Detect stale quotes
17. Compare current and historical FX prices
18. Detect extreme market-data movements
19. Classify anomalies by severity
20. Persist structured anomaly information

---

## Development Roadmap

Planned extensions include:

- Additional FX instruments
- Configurable instrument lists
- Instrument-specific anomaly thresholds
- Configurable anomaly rules
- Multi-source market-data integration
- Cross-provider quote comparison
- Automated anomaly alerts
- Anomaly resolution lifecycle
- Workflow health metrics
- Retry strategies for recoverable API failures
- Application-level API rate-limit handling
- Python-based analytical processing
- Statistical anomaly detection
- Monitoring and operational dashboard
- Data visualization
- AI/LLM-generated operational incident summaries
