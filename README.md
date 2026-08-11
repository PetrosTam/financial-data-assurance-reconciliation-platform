# FX Operations Automation & Monitoring

An FX operations automation and monitoring system for ingesting, validating, normalizing, and storing foreign exchange market data.

## Overview

The system integrates external FX market data through REST APIs and processes it through automated n8n workflows.

Incoming market data is validated and normalized into a provider-independent internal format before being persisted to PostgreSQL.

The project is being developed with a focus on data quality, reliability, workflow monitoring, automated operational controls, and system observability.

## Current Architecture

    Manual Trigger
          |
          v
    Alpha Vantage REST API
          |
          v
    JavaScript Validation & Normalization
          |
          v
    PostgreSQL

The current ingestion workflow retrieves EUR/USD market data from Alpha Vantage, validates the API response, transforms provider-specific fields into the internal FX data model, calculates derived pricing metrics, and persists the normalized quote to PostgreSQL.

## Implemented Features

- EUR/USD market data ingestion through the Alpha Vantage REST API
- Secure API authentication using n8n credentials
- JavaScript-based validation of incoming FX quotes
- Provider-independent data normalization
- Validation of currency codes, bid prices, ask prices, and timestamps
- Detection of invalid bid/ask relationships
- Mid-price calculation
- Spread calculation
- UTC timestamp normalization
- PostgreSQL persistence
- Raw API payload retention for traceability and debugging
- Database-level duplicate quote protection
- Containerized local environment using Docker Compose

## Tech Stack

- n8n
- JavaScript
- REST APIs
- PostgreSQL
- Docker
- Git

## Data Model

The PostgreSQL schema currently contains four core tables:

- `fx_quotes` - normalized FX market data and original provider payloads
- `workflow_runs` - workflow execution and processing information
- `anomalies` - detected operational or market-data anomalies
- `alerts` - operational alerts generated from detected issues

The `fx_quotes` table stores normalized fields including:

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

## Workflow

The current FX quote ingestion workflow consists of four stages:

1. **Manual Trigger**  
   Starts the workflow during development and testing.

2. **Fetch EURUSD Quote**  
   Retrieves the latest EUR/USD exchange-rate data from the Alpha Vantage REST API.

3. **Validate & Normalize Quote**  
   Validates the API response using JavaScript, verifies required market-data fields, calculates the mid price and spread, and converts the provider-specific response into the internal FX data model.

4. **Persist Quote to PostgreSQL**  
   Stores the validated and normalized quote in the `fx_quotes` table.

## Security

API keys, database passwords, and other sensitive credentials are not stored in source control.

- API authentication is managed through n8n credentials
- Local environment variables are stored in `.env`
- `.env` is excluded from Git
- `.env.example` contains only configuration placeholders
- Credentials are not included in exported workflow files

## Project Structure

    .
    ├── docs/
    │   └── architecture.md
    ├── sql/
    │   └── 001_schema.sql
    ├── workflows/
    │   └── fx-quote-ingestion-alpha-vantage.json
    ├── .env.example
    ├── .gitignore
    ├── docker-compose.yml
    └── README.md

## Development Roadmap

- Scheduled FX market data ingestion
- Multi-instrument FX ingestion
- Idempotent ingestion and duplicate handling
- Operational data-quality checks
- Market-data anomaly detection
- Workflow execution monitoring
- Workflow failure logging
- Retry and error-handling workflows
- Automated operational alerts
- Python-based analytical processing
- Workflow health monitoring
- AI/LLM-generated incident summaries