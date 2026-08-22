# System Architecture

## Overview

FX Operations Automation & Monitoring is a modular workflow-driven system for ingesting, validating, normalizing, storing, monitoring, and alerting on foreign-exchange market data.

The current implementation focuses on operational reliability, deterministic data-quality controls, anomaly detection, workflow lifecycle monitoring, and verified critical email alerting.

The system is not a trading bot. FX prices are treated as operational data for ingestion, validation, monitoring, investigation, and future research.

## Core Components

### Workflow Orchestration

n8n coordinates:

- scheduled and manual workflow execution
- REST API integration
- sequential multi-instrument processing
- validation and normalization
- PostgreSQL persistence
- operational anomaly detection
- critical anomaly alert routing
- centralized workflow failure handling

### Market Data Integration

FX market data is currently retrieved from Alpha Vantage through a REST API.

The current production workflow processes:

- EUR/USD
- GBP/USD
- USD/JPY

Provider-specific responses are treated as untrusted input and are validated before persistence.

### Processing Layer

JavaScript is currently used for:

- provider-response validation
- quote normalization
- derived market-data calculations
- operational anomaly detection
- anomaly classification

Python is planned for the future research and analytical layer but is not part of the current implemented runtime.

### Data Persistence

PostgreSQL stores:

- normalized FX quotes
- raw provider payloads
- workflow execution lifecycle data
- detected anomalies
- generated alerts

The current operational tables are:

- `fx_quotes`
- `workflow_runs`
- `anomalies`
- `alerts`

### Monitoring and Reliability

The current implementation monitors:

- workflow execution status
- malformed or invalid provider responses
- duplicate market-data records
- stale quotes
- abnormal spreads
- abnormal price movements
- critical anomaly alert delivery state

A separate error-handling workflow records production workflow failures.

### Alerting

Critical anomalies can enter the alerting path:

```text
Critical Anomaly
      ↓
Create Alert
status = pending
      ↓
Send Critical Alert Email
   ├─ success → status = sent + sent_at
   └─ failure → status = failed
```

Email sender and recipient configuration are supplied through environment variables rather than hardcoded workflow values.

SMTP authentication remains stored in n8n credentials.

### Anomaly Lifecycle Schema

The `anomalies` table includes lifecycle-ready fields:

- `status`
- `acknowledged_at`
- `resolved_at`
- `resolution_reason`

Allowed lifecycle states are:

```text
open
acknowledged
resolved
```

The database schema is implemented.

The operator-facing workflow that will manage transitions between these states is not yet implemented.

## Current Data Flow

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

## Production Failure Flow

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

## Reliability Principles

Current implemented principles include:

- validate external API responses before processing
- reject structurally invalid market data
- prevent duplicate market-data persistence
- process provider requests sequentially
- apply explicit request throttling
- preserve raw provider payloads for diagnostics
- track workflow execution start, success, and failure
- capture production failure messages
- detect stale and abnormal market conditions
- persist structured anomaly records
- route critical anomalies to verified email alerts
- externalize runtime email configuration
- keep credentials and secrets outside source control
- persist n8n state using a Docker named volume

## Planned Extensions

The following are planned but are not part of the current implemented runtime:

- anomaly lifecycle manager for `open → acknowledged → resolved`
- config-driven instruments and anomaly rules
- provider abstraction
- second FX data source
- cross-source reconciliation
- Python research and analytical processing
- fixed and adaptive statistical anomaly detection
- controlled fault injection and 2×2 evaluation
- retry/backoff and resilience controls
- Prometheus and Grafana observability
- operator-facing API and dashboard
- distributed streaming and storage components where justified
- AI/LLM-assisted incident explanation after deterministic monitoring matures
