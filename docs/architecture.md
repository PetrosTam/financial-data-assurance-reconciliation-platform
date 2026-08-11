# System Architecture

## Overview

FX Operations Automation & Monitoring is designed as a modular workflow-driven system for ingesting, validating, processing, storing, and monitoring foreign exchange market data.

## Core Components

### Workflow Orchestration
n8n coordinates scheduled data ingestion, API integrations, validation steps, persistence, monitoring, and alerting.

### Market Data Integration
FX market data is retrieved from external services through REST APIs.

### Processing Layer
JavaScript and Python are used for data transformation, validation, analytical processing, and anomaly detection.

### Data Persistence
PostgreSQL stores normalized FX market data, workflow execution information, detected anomalies, and generated alerts.

### Monitoring and Reliability
Workflow executions are monitored for failures, invalid data, stale market information, duplicate records, and abnormal market conditions.

### AI Integration
LLM-based components can generate structured operational summaries for incidents detected by deterministic monitoring rules.

## Data Flow

1. Trigger workflow execution
2. Retrieve FX market data through a REST API
3. Validate the API response
4. Normalize structured market data
5. Persist data to PostgreSQL
6. Perform operational and analytical checks
7. Detect and record anomalies
8. Generate alerts when required
9. Record workflow execution status
10. Generate an AI-assisted incident summary when applicable

## Reliability Principles

- Validate external API responses before processing
- Prevent duplicate market-data records
- Detect stale or incomplete data
- Log workflow executions and failures
- Use retries and dedicated error-handling workflows
- Keep credentials and secrets outside source control