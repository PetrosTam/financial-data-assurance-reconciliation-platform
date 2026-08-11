# FX Operations Automation & Monitoring

An FX operations automation and monitoring system for ingesting, validating, normalizing, and storing foreign exchange market data.

## Overview

The system integrates external FX market data through REST APIs and processes it through automated n8n workflows.

Incoming market data is validated and normalized into a provider-independent internal format before being persisted to PostgreSQL.

The project is being developed with a focus on data quality, reliability, workflow monitoring, automated operational controls, and system observability.

## Current Architecture

    Manual Trigger ────────┐
                           |
    Schedule Trigger ──────┤
                           v
                 Alpha Vantage REST API
                           |
                           v
             JavaScript Validation & Normalization
                           |
                           v
                     PostgreSQL

The ingestion workflow retrieves EUR/USD market data from Alpha Vantage, validates the API response, transforms provider-specific fields into the internal FX data model, calculates derived pricing metrics, and persists normalized quotes to PostgreSQL.

The workflow can be executed manually for development and testing or automatically through an hourly schedule.

## Implemented Features

- EUR/USD market data ingestion through the Alpha Vantage REST API
- Hourly scheduled FX quote ingestion using n8n
- Manual workflow execution for development and testing
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
- Idempotent quote persistence using conflict handling
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

The ingestion workflow also uses conflict handling so repeated quotes can be safely ignored without causing the workflow to fail.

## Workflow

The current FX quote ingestion workflow consists of five stages:

1. **Manual Trigger**  
   Starts the workflow manually during development and testing.

2. **Schedule Trigger**  
   Automatically starts the ingestion workflow once per hour.

3. **Fetch EURUSD Quote**  
   Retrieves the latest EUR/USD exchange-rate data from the Alpha Vantage REST API.

4. **Validate & Normalize Quote**  
   Validates the API response using JavaScript, verifies required market-data fields, calculates the mid price and spread, and converts the provider-specific response into the internal FX data model.

5. **Persist Quote to PostgreSQL**  
   Stores the validated and normalized quote in the `fx_quotes` table while safely skipping duplicate records that conflict with the database uniqueness constraint.

## Reliability and Data Quality

The current workflow includes several controls designed to improve ingestion reliability:

- Required API response validation
- Currency-code validation
- Numeric bid and ask validation
- Positive-price validation
- Detection of ask prices below bid prices
- Timestamp validation and UTC normalization
- Database-level uniqueness constraints
- Duplicate-safe PostgreSQL inserts
- Raw provider response retention for troubleshooting

## Security

API keys, database passwords, and other sensitive credentials are not stored in source control.

- API authentication is managed through n8n credentials
- Database authentication is managed through n8n credentials
- Local environment variables are stored in `.env`
- `.env` is excluded from Git
- `.env.example` contains only configuration placeholders
- Credentials are not included directly in exported workflow files

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

- Multi-instrument FX ingestion
- Operational data-quality checks
- Market-data anomaly detection
- Workflow execution monitoring
- Workflow failure logging
- Retry and error-handling workflows
- Automated operational alerts
- Python-based analytical processing
- Workflow health monitoring
- AI/LLM-generated incident summaries