# FX Operations Automation & Monitoring

An FX operations automation and monitoring system for ingesting, validating, normalizing, storing, and monitoring foreign exchange market data and operational workflows.

## Overview

The system integrates external FX market data through REST APIs and processes it through automated n8n workflows.

Incoming market data is validated and normalized into a provider-independent internal format before being persisted to PostgreSQL.

The platform also monitors workflow executions, records successful and failed runs, performs automated operational data-quality checks, detects abnormal market-data conditions, and stores structured anomaly records for investigation.

The project is being developed with a focus on data quality, reliability, workflow observability, automated operational controls, fault handling, and system monitoring.

## Current Architecture

### FX Quote Ingestion and Monitoring Workflow

    Manual Trigger ─────────┐
                            │
    Schedule Trigger ───────┤
                            v
                     Log Run Started
                            |
                            v
                  Alpha Vantage REST API
                            |
                            v
              JavaScript Validation & Normalization
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

### Failure Handling Workflow

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

The ingestion workflow retrieves EUR/USD market data from Alpha Vantage, validates the provider response, transforms provider-specific fields into an internal FX data model, calculates derived pricing metrics, and persists normalized quotes to PostgreSQL.

Each workflow execution is registered in the `workflow_runs` table when it begins.

Successful executions update the corresponding run with completion status, processed-record count, and completion timestamp.

Production failures are routed to a dedicated error-handling workflow that records the failure status, error message, and completion timestamp against the original execution.

Validated quotes are also evaluated by independent operational monitoring branches. These checks can identify wide spreads, stale market data, and extreme price movements without interrupting normal quote persistence.

## Implemented Features

### FX Market Data Ingestion

- EUR/USD market data ingestion through the Alpha Vantage REST API
- Hourly scheduled FX quote ingestion using n8n
- Manual workflow execution for development and testing
- Secure API authentication using n8n credentials
- Provider-independent FX data normalization
- PostgreSQL persistence
- Raw provider payload retention for traceability and debugging

### Data Validation

- Provider-response validation
- Currency-code validation
- Bid and ask numeric validation
- Positive-price validation
- Detection of invalid bid/ask relationships
- Timestamp validation
- UTC timestamp normalization
- Mid-price calculation
- Spread calculation

### Reliability and Idempotency

- Database-level duplicate quote protection
- Idempotent quote persistence using conflict handling
- Duplicate-safe PostgreSQL inserts
- Containerized local environment using Docker Compose
- Explicit n8n timezone configuration using `Asia/Nicosia`

### Workflow Execution Monitoring

- Workflow execution start logging
- n8n execution ID tracking
- Workflow name tracking
- Execution status tracking
- Processed-record counts
- Automatic execution start timestamps
- Automatic completion timestamps
- Successful execution tracking
- Persistent execution history in PostgreSQL

### Failure Handling

- Dedicated n8n error-handling workflow
- Centralized production failure handling
- Automatic failed-run detection
- Failed execution ID correlation
- Error-message persistence
- Failed-run completion timestamps
- Separation of success and failure handling logic
- Controlled production failure testing

### Operational Anomaly Detection

- Independent anomaly-detection branch
- Wide-spread detection
- Stale-quote detection
- Previous-quote price comparison
- Extreme price-movement detection
- Warning and critical severity classification
- Structured anomaly metadata
- PostgreSQL anomaly persistence
- Raw metric and threshold persistence
- Previous/current quote context for price-movement anomalies
- Controlled anomaly testing without modifying production market data
- Anomaly detection that does not interrupt normal quote persistence

## Tech Stack

- n8n
- JavaScript
- REST APIs
- PostgreSQL
- Docker
- Git

## Data Model

The PostgreSQL schema contains four core tables:

- `fx_quotes` - normalized FX market data and original provider payloads
- `workflow_runs` - workflow execution and processing information
- `anomalies` - detected operational and market-data anomalies
- `alerts` - operational alerts generated from detected issues

### `fx_quotes`

The `fx_quotes` table stores:

- Symbol
- Provider instrument identifier
- Bid price
- Ask price
- Mid price
- Spread
- Data source
- Market observation timestamp
- Data receipt timestamp
- Raw provider payload

Duplicate quotes are protected by a database-level unique constraint based on symbol, observation timestamp, and source.

The ingestion workflow also uses conflict handling so repeated quotes can be safely ignored without causing the workflow to fail.

### `workflow_runs`

The `workflow_runs` table stores:

- Workflow name
- n8n execution ID
- Execution status
- Number of records processed
- Error message
- Execution start timestamp
- Execution completion timestamp

A workflow run is initially recorded with:

    status = started

Successful runs are updated to:

    status = success

Failed production runs are updated through the dedicated error workflow to:

    status = failed

The n8n execution ID is used to correlate the start, success, and failure stages of the same workflow execution.

### `anomalies`

The `anomalies` table stores:

- FX symbol
- Anomaly type
- Severity
- Observed metric value
- Configured threshold value
- Structured anomaly details
- Detection timestamp
- Resolution timestamp

Current anomaly types include:

    wide_spread
    stale_quote
    extreme_price_movement

The `details` JSONB field stores additional diagnostic context such as bid/ask prices, calculated spread, quote age, previous and current mid prices, price movement, data source, and observation timestamps.

## Main Workflow

The current FX quote ingestion workflow combines ingestion, execution monitoring, and operational data-quality controls.

### 1. Manual Trigger

Starts the workflow manually during development and testing.

### 2. Schedule Trigger

Automatically starts the production ingestion workflow once per hour.

### 3. Log Run Started

Creates a record in `workflow_runs` containing the workflow name, n8n execution ID, initial `started` status, and execution start timestamp.

### 4. Fetch EURUSD Quote

Retrieves the latest EUR/USD exchange-rate data from the Alpha Vantage REST API.

### 5. Validate & Normalize Quote

Uses JavaScript to:

- Validate the provider response
- Verify required currency fields
- Validate bid and ask prices
- Detect invalid quote relationships
- Normalize the provider response into the internal FX data model
- Calculate mid price
- Calculate spread
- Normalize timestamps to UTC

After validation, the workflow separates into independent persistence and monitoring branches.

### 6. Persist Quote to PostgreSQL

Stores the validated and normalized quote in `fx_quotes`.

Duplicate quotes are safely skipped when they conflict with the database uniqueness constraint.

### 7. Mark Run Success

Updates the corresponding `workflow_runs` record using the n8n execution ID.

The completed execution is marked with:

- `status = success`
- Number of records processed
- Completion timestamp

## Operational Anomaly Detection

Operational checks run independently from the main persistence branch so that an unusual but structurally valid quote can still be stored while being flagged for investigation.

### Wide Spread Detection

The system converts the absolute spread into basis points using:

    spread_bps = (spread / mid_price) * 10000

Current initial thresholds:

    Warning threshold: 2 bps
    Critical threshold: 5 bps

When the configured threshold is exceeded, a `wide_spread` anomaly is created.

### Stale Quote Detection

The system compares the market observation timestamp with the current execution time.

Current initial thresholds:

    Warning threshold: 600 seconds
    Critical threshold: 1800 seconds

Quotes exceeding the configured age threshold generate a `stale_quote` anomaly.

### Extreme Price Movement Detection

The system queries PostgreSQL for the most recent earlier quote for the same symbol and compares its mid price with the current quote.

The movement is calculated in basis points:

    movement_bps =
        abs((current_mid_price - previous_mid_price) / previous_mid_price)
        * 10000

Current initial thresholds:

    Warning threshold: 20 bps
    Critical threshold: 50 bps

A movement above the configured threshold generates an:

    extreme_price_movement

anomaly.

The anomaly record includes:

- Previous mid price
- Current mid price
- Movement in basis points
- Previous observation timestamp
- Current observation timestamp

Parameterized PostgreSQL queries are used when retrieving the previous quote.

### Anomaly Persistence

Detected anomalies are normalized into a common structure before being inserted into PostgreSQL:

    symbol
    anomaly_type
    severity
    metric_value
    threshold_value
    details

This allows different operational checks to use the same persistence model.

If no anomaly is detected, the monitoring branch produces no anomaly record and the normal ingestion path continues unaffected.

## Error Handling Workflow

A separate workflow named:

    FX Workflow Error Handler

handles production failures.

Its architecture is:

    Error Trigger
         |
         v
    Mark Run Failed

When the main production workflow fails, n8n passes information about the failed execution to the error handler.

The error handler correlates the failure with the original `workflow_runs` record using the failed execution ID and updates:

- `status = failed`
- Error message
- Completion timestamp

This allows successful and failed workflow executions to be monitored through the same PostgreSQL execution history.

## Reliability and Observability

The system currently implements controls across the complete ingestion lifecycle:

- Input validation before persistence
- Provider-response validation
- Quote integrity checks
- Database uniqueness constraints
- Duplicate-safe persistence
- Raw payload retention
- Workflow execution IDs
- Execution start logging
- Success-state persistence
- Failure-state persistence
- Error-message capture
- Execution timestamps
- Dedicated production error handling
- Wide-spread monitoring
- Stale-data monitoring
- Historical quote comparison
- Extreme price-movement detection
- Severity classification
- Structured anomaly persistence
- Independent monitoring branches

These controls allow both technical failures and market-data quality issues to be traced across the workflow and database layers.

## Security

API keys, database passwords, and other sensitive credentials are not stored in source control.

- API authentication is managed through n8n credentials
- Database authentication is managed through n8n credentials
- Local environment variables are stored in `.env`
- `.env` is excluded from Git
- `.env.example` contains only configuration placeholders
- Credentials are not stored directly in exported workflow files
- API credentials are restricted to the required external API domain where applicable
- Dynamic PostgreSQL comparisons use query parameters instead of directly interpolating values into SQL

## Project Structure

    .
    ├── docs/
    │   └── architecture.md
    ├── sql/
    │   └── 001_schema.sql
    ├── workflows/
    │   ├── fx-quote-ingestion-alpha-vantage.json
    │   └── fx-workflow-error-handler.json
    ├── .env.example
    ├── .gitignore
    ├── docker-compose.yml
    └── README.md

## Development Roadmap

- Multi-instrument FX ingestion
- Configurable anomaly thresholds
- Instrument-specific anomaly thresholds
- Automated operational alerts
- Anomaly resolution lifecycle
- Workflow health monitoring
- Retry strategies for recoverable failures
- Python-based analytical processing
- Statistical anomaly detection
- Multi-source market-data integration
- AI/LLM-generated incident summaries
- Monitoring and operational dashboard