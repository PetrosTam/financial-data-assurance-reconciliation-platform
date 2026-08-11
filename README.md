# FX Operations Automation & Monitoring

An FX operations automation and monitoring system for ingesting, validating, normalizing, storing, and monitoring foreign exchange market data workflows.

## Overview

The system integrates external FX market data through REST APIs and processes it through automated n8n workflows.

Incoming market data is validated and normalized into a provider-independent internal format before being persisted to PostgreSQL.

The platform also tracks workflow executions, records successful and failed runs, captures operational errors, and maintains execution metadata for monitoring and troubleshooting.

The project is being developed with a focus on data quality, reliability, workflow observability, automated operational controls, and fault handling.

## Current Architecture

### FX Quote Ingestion Workflow

    Manual Trigger ────────┐
                           │
    Schedule Trigger ──────┤
                           v
                    Log Run Started
                           |
                           v
                 Alpha Vantage REST API
                           |
                           v
             JavaScript Validation & Normalization
                           |
                           v
                     PostgreSQL
                           |
                           v
                    Mark Run Success

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

The ingestion workflow retrieves EUR/USD market data from Alpha Vantage, validates the API response, transforms provider-specific fields into the internal FX data model, calculates derived pricing metrics, and persists normalized quotes to PostgreSQL.

Each workflow execution is registered in the `workflow_runs` table when it begins.

Successful executions update the corresponding run with completion status, processed-record count, and completion timestamp.

Production failures are routed to a dedicated error-handling workflow that records the failure status, error message, and completion timestamp against the original execution.

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
- `anomalies` - detected operational or market-data anomalies
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

## Main Workflow

The current FX quote ingestion workflow consists of seven stages.

### 1. Manual Trigger

Starts the workflow manually during development and testing.

### 2. Schedule Trigger

Automatically starts the production ingestion workflow once per hour.

### 3. Log Run Started

Creates a new record in `workflow_runs` containing the workflow name, n8n execution ID, initial `started` status, and execution start timestamp.

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

### 6. Persist Quote to PostgreSQL

Stores the validated and normalized quote in `fx_quotes`.

Duplicate quotes are safely skipped when they conflict with the database uniqueness constraint.

### 7. Mark Run Success

Updates the corresponding `workflow_runs` record using the n8n execution ID.

The completed execution is marked with:

- `status = success`
- Number of records processed
- Completion timestamp

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

The system currently implements multiple controls across the ingestion lifecycle:

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

These controls allow failures and data-quality issues to be traced across both the workflow layer and the database layer.

## Security

API keys, database passwords, and other sensitive credentials are not stored in source control.

- API authentication is managed through n8n credentials
- Database authentication is managed through n8n credentials
- Local environment variables are stored in `.env`
- `.env` is excluded from Git
- `.env.example` contains only configuration placeholders
- Credentials are not stored directly in exported workflow files
- API credentials are restricted to the required external API domain where applicable

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
- Operational data-quality checks
- Market-data anomaly detection
- Automated anomaly persistence
- Workflow health monitoring
- Retry strategies for recoverable failures
- Automated operational alerts
- Python-based analytical processing
- Statistical anomaly detection
- AI/LLM-generated incident summaries
- Monitoring and operational dashboard