# JForex Historical Tick Probe

Read-only Dukascopy/JForex historical tick acquisition utility for the MSc EUR/USD source-compatibility pilot.

The utility acquires historical market-data evidence only. It does **not** submit orders, generate trading signals, manage positions, perform hedging, or implement any trading logic.

## Acquisition contract

Each acquisition run must cover exactly one canonical UTC hour:

```text
HH:00:00.000Z through HH:59:59.999Z inclusive
```

The current research instrument is:

```text
EUR/USD
```

CSV fields are:

```text
event_time_utc
epoch_ms
bid
ask
bid_volume
ask_volume
```

The one-hour restriction is deliberate. Larger historical requests previously exhibited unstable JForex/provider retrieval behaviour, so the acquisition boundary fails closed rather than treating a potentially partial multi-hour result as valid research evidence.

## Canonical regression window

The current known-good regression oracle is:

```text
Instrument: EUR/USD
From:       2026-01-27T12:00:00.000Z
To:         2026-01-27T12:59:59.999Z
Rows:       7630
First:      1769515200187
Last:       1769518799335
SHA-256:    259666ce9f4eee67afa5b8ce905eee6775478cff73c08a52f99f2fc3050f2f1e
```

This oracle is a regression reference for the acquisition implementation. It is not a claim that every requested hour must contain the same number of observations.

## Output layout

Each successful acquisition is stored as a self-contained evidence bundle. The hierarchy separates provider, instrument, requested market-data window, and acquisition execution time:

```text
out/
  runs/
    dukascopy/
      eurusd/
        2026-01-27/
          1200-1300utc/
            2026-09-21T224508.314Z/
              ticks.csv
              metadata.json
```

The requested market-data time and acquisition execution time are separate concepts.

`metadata.json` records acquisition provenance including:

- schema version;
- unique run ID;
- provider and acquisition route;
- Dukascopy SDK version;
- instrument;
- canonical window policy;
- exact requested UTC boundaries;
- probe timeout;
- `all_data_loaded`;
- row count;
- first and last provider event timestamps;
- output file name;
- CSV SHA-256;
- acquisition start/completion timestamps;
- Java and operating-system information.

Generated acquisition artifacts remain local and must not be committed to Git.

If two runs begin within the same millisecond, the later run receives a deterministic collision suffix such as `-02`. Existing evidence is never silently overwritten.

During acquisition, `ticks.csv.part` is used as a temporary artifact. It is promoted to `ticks.csv` only after the historical load completes successfully and local validation succeeds.

## Prerequisites

1. Dukascopy JForex DEMO account.
2. Java/JDK.
3. Apache Maven.
4. Internet access to the Dukascopy DEMO service and public Maven repository.

## Credentials

Credentials must never be hard-coded, committed to Git, written to acquisition metadata, or intentionally published in logs/screenshots.

The application reads only:

```text
DUKASCOPY_DEMO_USERNAME
DUKASCOPY_DEMO_PASSWORD
```

For an interactive PowerShell session:

```powershell
$env:DUKASCOPY_DEMO_USERNAME = Read-Host "Dukascopy DEMO login"

$SecurePassword = Read-Host "Dukascopy DEMO password" -AsSecureString

$env:DUKASCOPY_DEMO_PASSWORD = (
    New-Object System.Net.NetworkCredential("", $SecurePassword)
).Password
```

JForex DEBUG logging may contain authentication/session identifiers, provider endpoints, network information, and other sensitive runtime material. Raw DEBUG logs must not be committed or published.

## Build

```powershell
mvn compile
```

A successful build should end with:

```text
BUILD SUCCESS
```

Known effective-model warnings from Dukascopy/transitive Maven dependencies may appear during dependency collection. They are upstream warnings and are not by themselves evidence of a build failure.

## Run

Required acquisition parameters are passed through Maven properties.

Example:

```powershell
mvn exec:exec `
  '-Dprobe.instrument=EUR/USD' `
  '-Dprobe.from=2026-01-27T12:00:00.000Z' `
  '-Dprobe.to=2026-01-27T12:59:59.999Z'
```

To store raw research data outside the repository:

```powershell
mvn exec:exec `
  '-Dprobe.instrument=EUR/USD' `
  '-Dprobe.from=2026-01-27T12:00:00.000Z' `
  '-Dprobe.to=2026-01-27T12:59:59.999Z' `
  '-Dprobe.output.root=C:\path\to\local-research-data'
```

The probe timeout can also be overridden when required:

```powershell
'-Dprobe.timeout.ms=120000'
```

A plain:

```powershell
mvn exec:exec
```

is intentionally invalid because the required instrument and time-window properties use sentinel defaults. This prevents an accidental acquisition from silently running against an unintended interval.

## Successful-run criteria

A successful acquisition must:

- satisfy the canonical UTC-hour policy;
- connect and confirm instrument subscription;
- complete the historical load with `allDataLoaded=true`;
- contain at least one historical tick;
- preserve provider bid/ask and bid/ask volumes;
- preserve provider millisecond event time;
- contain only timestamps inside the requested inclusive interval;
- maintain non-decreasing historical event timestamps;
- serialize UTC event times deterministically;
- produce one unique run directory;
- promote `ticks.csv.part` to `ticks.csv` only after successful validation;
- produce `metadata.json`;
- record the final CSV SHA-256;
- leave no `ticks.csv.part` after successful promotion;
- return control to the shell without manual termination.

For the canonical regression window, the strongest regression check is equality of:

```text
rows
first_epoch_ms
last_epoch_ms
output_sha256
```

against the known-good oracle above.

## Disconnect behaviour

The Dukascopy disconnect callback may not always be observed before the bounded disconnect timeout.

When acquisition, validation, artifact promotion, and metadata generation have already succeeded, this condition is reported as an advisory warning rather than rewriting the completed acquisition as failed.

Repeated disconnect anomalies or evidence of incomplete acquisition must be investigated separately.

## Repository hygiene

Do not commit:

- real `.env` files;
- passwords or demo credentials;
- JForex runtime logs;
- authentication/session material;
- Maven build output;
- `.part` files;
- Dukascopy `.bi5` raw/cache data;
- generated `ticks.csv`;
- generated acquisition metadata containing local runtime paths;
- licensed/raw research datasets.

Safe source code, configuration templates, documentation, and research utilities belong in Git. Raw market data remains outside the repository unless redistribution rights explicitly allow otherwise.