import argparse
import csv
import hashlib
import math
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from pathlib import Path
from statistics import median

EXPECTED_INSTRUMENT = "EUR/USD"
EXPECTED_COLUMN_COUNT = 4

TARGET_DATES = (
    "20260126",
    "20260127",
    "20260128",
    "20260129",
    "20260130",
)

TIMESTAMP_FORMAT = "%Y%m%d %H:%M:%S.%f"
TIMESTAMP_PATTERN = re.compile(
    r"^\d{8} \d{2}:\d{2}:\d{2}\.\d{3}$"
)

ONE_MILLISECOND = timedelta(milliseconds=1)


@dataclass
class AuditState:
    total_rows: int = 0

    wrong_column_count_rows: int = 0
    timestamp_parse_failures: int = 0
    price_parse_failures: int = 0

    unexpected_instrument_rows: int = 0
    non_finite_price_rows: int = 0
    non_positive_price_rows: int = 0
    reversed_price_rows: int = 0

    out_of_order_rows: int = 0
    exact_duplicate_rows: int = 0
    repeated_timestamp_rows: int = 0

    instrument_counts: Counter[str] = field(
        default_factory=Counter
    )
    date_counts: Counter[str] = field(
        default_factory=Counter
    )
    millisecond_positions: set[int] = field(
        default_factory=set
    )

    first_ts_by_date: dict[str, datetime] = field(
        default_factory=dict
    )
    last_ts_by_date: dict[str, datetime] = field(
        default_factory=dict
    )

    target_timestamps_by_date: defaultdict[
        str,
        list[datetime],
    ] = field(
        default_factory=lambda: defaultdict(list)
    )
    target_hour_counts: Counter[
        tuple[str, int]
    ] = field(
        default_factory=Counter
    )

    seen_rows: set[tuple[str, ...]] = field(
        default_factory=set
    )
    seen_timestamps: set[datetime] = field(
        default_factory=set
    )

    previous_timestamp: datetime | None = None

    @property
    def malformed_rows(self) -> int:
        return (
            self.wrong_column_count_rows
            + self.timestamp_parse_failures
            + self.price_parse_failures
        )

    @property
    def target_week_total_rows(self) -> int:
        return sum(
            self.date_counts[date]
            for date in TARGET_DATES
        )


def parse_args(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the structural/data-integrity audit for the "
            "TrueFX EUR/USD historical CSV used by the MSc pilot."
        )
    )

    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the TrueFX historical CSV file to audit.",
    )

    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    """Return the file SHA-256 as uppercase hexadecimal."""
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for chunk in iter(
            lambda: source.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest().upper()


def parse_source_timestamp(
    raw_value: str,
) -> datetime:
    """
    Parse exactly YYYYMMDD HH:MM:SS.mmm.

    The archive value contains no explicit UTC offset. The audit therefore
    preserves it as a naive source timestamp instead of inventing timezone
    or original-arrival semantics.
    """
    if TIMESTAMP_PATTERN.fullmatch(raw_value) is None:
        raise ValueError(
            "timestamp must match "
            "YYYYMMDD HH:MM:SS.mmm exactly"
        )

    # TrueFX archive rows contain no explicit timezone offset. Keeping this
    # source timestamp naive is intentional so this structural audit does not
    # invent timezone semantics that are absent from the source evidence.
    parsed = datetime.strptime( # noqa: DTZ007
        raw_value,
        TIMESTAMP_FORMAT,
    )

    # The regex already requires exactly three fractional digits.
    # Keep millisecond alignment explicit so a future parser change
    # cannot silently weaken this acquisition invariant.
    if parsed.microsecond % 1000 != 0:
        raise ValueError(
            "timestamp is not millisecond aligned"
        )

    return parsed


def parse_price(
    raw_value: str,
) -> Decimal:
    """
    Parse a source price without binary floating-point conversion.

    Decimal preserves the provider text value for the structural
    positivity and ordering checks performed by this audit.
    """
    try:
        return Decimal(raw_value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(
            f"invalid decimal price: {raw_value!r}"
        ) from exc


def milliseconds_between(
    earlier: datetime,
    later: datetime,
) -> int:
    """Return an exact integer millisecond difference."""
    return (later - earlier) // ONE_MILLISECOND


def nearest_rank_percentile(
    values: Sequence[int],
    probability: float,
) -> int:
    """
    Return a deterministic nearest-rank empirical percentile.

    This definition is explicit so p95/p99 diagnostics remain
    reproducible across runs without relying on library defaults.
    """
    if not values:
        raise ValueError(
            "percentile requires at least one value"
        )

    if not 0.0 <= probability <= 1.0:
        raise ValueError(
            "probability must be between 0.0 and 1.0"
        )

    ordered = sorted(values)

    if probability == 0.0:
        return ordered[0]

    rank = math.ceil(
        probability * len(ordered)
    )

    return ordered[rank - 1]


def format_datetime(
    value: datetime | None,
) -> str:
    """Render source timestamps to millisecond precision."""
    if value is None:
        return "None"

    return value.strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )[:-3]


def update_timestamp_state(
    state: AuditState,
    timestamp: datetime,
) -> None:
    date_key = timestamp.strftime(
        "%Y%m%d"
    )

    state.date_counts[date_key] += 1

    state.millisecond_positions.add(
        timestamp.microsecond // 1000
    )

    first = state.first_ts_by_date.get(
        date_key
    )

    if first is None or timestamp < first:
        state.first_ts_by_date[date_key] = (
            timestamp
        )

    last = state.last_ts_by_date.get(
        date_key
    )

    if last is None or timestamp > last:
        state.last_ts_by_date[date_key] = (
            timestamp
        )

    if (
        state.previous_timestamp is not None
        and timestamp
        < state.previous_timestamp
    ):
        state.out_of_order_rows += 1

    state.previous_timestamp = timestamp

    if timestamp in state.seen_timestamps:
        state.repeated_timestamp_rows += 1
    else:
        state.seen_timestamps.add(
            timestamp
        )

    if date_key in TARGET_DATES:
        state.target_timestamps_by_date[
            date_key
        ].append(timestamp)

        state.target_hour_counts[
            (date_key, timestamp.hour)
        ] += 1


def audit_csv(
    path: Path,
) -> AuditState:
    state = AuditState()

    reader = None

    try:
        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as source:
            reader = csv.reader(source)

            for row in reader:
                state.total_rows += 1

                # Duplicate detection is independent of downstream parsing.
                # Even a structurally invalid duplicate row remains useful
                # audit evidence.
                row_tuple = tuple(row)

                if row_tuple in state.seen_rows:
                    state.exact_duplicate_rows += 1
                else:
                    state.seen_rows.add(
                        row_tuple
                    )

                if (
                    len(row)
                    != EXPECTED_COLUMN_COUNT
                ):
                    state.wrong_column_count_rows += 1
                    continue

                (
                    instrument,
                    timestamp_raw,
                    price_1_raw,
                    price_2_raw,
                ) = row

                state.instrument_counts[
                    instrument
                ] += 1

                if (
                    instrument
                    != EXPECTED_INSTRUMENT
                ):
                    state.unexpected_instrument_rows += 1

                try:
                    timestamp = (
                        parse_source_timestamp(
                            timestamp_raw
                        )
                    )
                except ValueError:
                    state.timestamp_parse_failures += 1
                    continue

                # Timestamp diagnostics are independent of price validity.
                # A row with an invalid price still contributes evidence
                # about source temporal behaviour.
                update_timestamp_state(
                    state,
                    timestamp,
                )

                try:
                    price_1 = parse_price(
                        price_1_raw
                    )

                    price_2 = parse_price(
                        price_2_raw
                    )

                except ValueError:
                    state.price_parse_failures += 1
                    continue

                if (
                    not price_1.is_finite()
                    or not price_2.is_finite()
                ):
                    state.non_finite_price_rows += 1
                    continue

                if (
                    price_1 <= 0
                    or price_2 <= 0
                ):
                    state.non_positive_price_rows += 1

                # Keep these columns semantically conservative here.
                #
                # The structural auditor verifies ordering without silently
                # promoting provider semantics that belong in explicit
                # source/provenance documentation.
                if price_2 < price_1:
                    state.reversed_price_rows += 1

    except csv.Error as exc:
        line_number = (
            reader.line_num
            if reader is not None
            else "unknown"
        )

        raise RuntimeError(
            "CSV parser failed near physical "
            f"line {line_number}: {exc}"
        ) from exc

    return state


def print_main_report(
    path: Path,
    source_sha256: str,
    state: AuditState,
) -> None:
    print()
    print(
        "=== TRUEFX JANUARY 2026 "
        "PILOT AUDIT ==="
    )
    print()

    print(
        f"File: {path}"
    )

    print(
        f"SHA-256: {source_sha256}"
    )

    print(
        f"Total rows: {state.total_rows}"
    )

    print()
    print(
        "--- Structure / parsing ---"
    )

    print(
        "Wrong-column-count rows: "
        f"{state.wrong_column_count_rows}"
    )

    print(
        "Timestamp parse failures: "
        f"{state.timestamp_parse_failures}"
    )

    print(
        "Price parse failures: "
        f"{state.price_parse_failures}"
    )

    print(
        "Malformed rows total: "
        f"{state.malformed_rows}"
    )

    print()
    print(
        "--- Instrument validity ---"
    )

    print(
        "Unexpected instrument rows: "
        f"{state.unexpected_instrument_rows}"
    )

    print()
    print(
        "--- Price validity ---"
    )

    print(
        "Non-finite price rows: "
        f"{state.non_finite_price_rows}"
    )

    print(
        "Non-positive price rows: "
        f"{state.non_positive_price_rows}"
    )

    print(
        "Rows where column4 < column3: "
        f"{state.reversed_price_rows}"
    )

    print()
    print(
        "--- Ordering / duplicates ---"
    )

    print(
        "Out-of-order rows: "
        f"{state.out_of_order_rows}"
    )

    print(
        "Exact duplicate rows: "
        f"{state.exact_duplicate_rows}"
    )

    print(
        "Repeated timestamp rows: "
        f"{state.repeated_timestamp_rows}"
    )

    print()
    print(
        "--- Timestamp precision ---"
    )

    print(
        "Distinct millisecond positions: "
        f"{len(state.millisecond_positions)} "
        "/ 1000"
    )

    print()
    print(
        "--- Instruments ---"
    )

    for instrument, count in sorted(
        state.instrument_counts.items()
    ):
        print(
            f"{instrument}: {count}"
        )


def print_target_week_report(
    state: AuditState,
) -> None:
    print()
    print(
        "=== TARGET WEEK ==="
    )
    print()

    print(
        "Target-week total rows: "
        f"{state.target_week_total_rows}"
    )

    print()

    for date_key in TARGET_DATES:
        print(
            f"{date_key} "
            f"rows={state.date_counts[date_key]} "
            "first="
            f"{format_datetime(
                state.first_ts_by_date.get(
                    date_key
                )
            )} "
            "last="
            f"{format_datetime(
                state.last_ts_by_date.get(
                    date_key
                )
            )}"
        )


def print_continuity_report(
    state: AuditState,
) -> None:
    print()
    print(
        "=== TARGET-WEEK CONTINUITY ==="
    )

    for date_key in TARGET_DATES:
        # File ordering is audited independently.
        #
        # Sorting here makes these diagnostics describe temporal coverage
        # rather than accidentally mixing row-order defects into gap sizes.
        timestamps = sorted(
            state.target_timestamps_by_date[
                date_key
            ]
        )

        gaps_ms = [
            milliseconds_between(
                previous,
                current,
            )
            for previous, current in pairwise(timestamps)
        ]

        print()
        print(
            date_key
        )

        print(
            f"rows={len(timestamps)}"
        )

        if not gaps_ms:
            print(
                "No inter-arrival gaps available."
            )
            continue

        max_gap_ms = max(
            gaps_ms
        )

        max_gap_index = gaps_ms.index(
            max_gap_ms
        )

        print(
            "median_gap_ms="
            f"{median(gaps_ms):.3f}"
        )

        print(
            "p95_gap_ms="
            f"{nearest_rank_percentile(
                gaps_ms,
                0.95,
            ):.3f}"
        )

        print(
            "p99_gap_ms="
            f"{nearest_rank_percentile(
                gaps_ms,
                0.99,
            ):.3f}"
        )

        print(
            "max_gap_ms="
            f"{max_gap_ms:.3f}"
        )

        print(
            "max_gap_start="
            f"{format_datetime(
                timestamps[
                    max_gap_index
                ]
            )}"
        )

        print(
            "max_gap_end="
            f"{format_datetime(
                timestamps[
                    max_gap_index + 1
                ]
            )}"
        )

        print(
            "gaps_gt_30s="
            f"{sum(
                gap > 30_000
                for gap in gaps_ms
            )}"
        )

        print(
            "gaps_gt_60s="
            f"{sum(
                gap > 60_000
                for gap in gaps_ms
            )}"
        )

        print(
            "gaps_gt_5m="
            f"{sum(
                gap > 300_000
                for gap in gaps_ms
            )}"
        )


def print_hourly_counts(
    state: AuditState,
) -> None:
    print()
    print(
        "=== TARGET-WEEK HOURLY COUNTS ==="
    )

    for date_key in TARGET_DATES:
        print()
        print(
            date_key
        )

        for hour in range(24):
            count = (
                state.target_hour_counts[
                    (date_key, hour)
                ]
            )

            print(
                f"{hour:02d}:00 "
                f"{count}"
            )


def print_all_dates(
    state: AuditState,
) -> None:
    print()
    print(
        "=== ALL DATES PRESENT ==="
    )

    for date_key in sorted(
        state.date_counts
    ):
        print(
            f"{date_key} "
            f"{state.date_counts[date_key]}"
        )


def print_audit_summary(
    state: AuditState,
) -> None:
    print()
    print(
        "=== AUDIT SUMMARY ==="
    )

    checks = (
        (
            "Non-empty source file",
            state.total_rows > 0,
        ),
        (
            "Target dates present",
            all(
                state.date_counts[date] > 0
                for date in TARGET_DATES
            ),
        ),
        (
            "Expected EUR/USD instrument only",
            (
                state.unexpected_instrument_rows == 0
                and set(
                    state.instrument_counts
                )
                == {EXPECTED_INSTRUMENT}
            ),
        ),
        (
            "All 1000 millisecond positions observed",
            (
                len(
                    state.millisecond_positions
                )
                == 1000
            ),
        ),
        (
            "No structural parsing failures",
            state.malformed_rows == 0,
        ),
        (
            "No non-finite prices",
            state.non_finite_price_rows == 0,
        ),
        (
            "No non-positive prices",
            state.non_positive_price_rows == 0,
        ),
        (
            "No reversed price ordering",
            state.reversed_price_rows == 0,
        ),
        (
            "Chronologically ordered",
            state.out_of_order_rows == 0,
        ),
        (
            "No exact duplicate rows",
            state.exact_duplicate_rows == 0,
        ),
        (
            "No repeated timestamps",
            state.repeated_timestamp_rows == 0,
        ),
    )

    for label, passed in checks:
        print(
            f"{label}: {passed}"
        )


def run(
    csv_path: Path,
) -> None:
    path = csv_path.expanduser()

    if not path.is_file():
        raise FileNotFoundError(
            f"TrueFX CSV not found: {path}"
        )

    # Hash on both sides of the audit.
    #
    # The reported digest must describe the same immutable source bytes
    # that were actually inspected. If the source changes while this
    # process is running, the run is invalid rather than silently mixing
    # two versions of research evidence.
    sha256_before = sha256_file(
        path
    )

    state = audit_csv(
        path
    )

    sha256_after = sha256_file(
        path
    )

    if sha256_before != sha256_after:
        raise RuntimeError(
            "TrueFX source file changed "
            "while the audit was running"
        )

    print_main_report(
        path,
        sha256_before,
        state,
    )

    print_target_week_report(
        state
    )

    print_continuity_report(
        state
    )

    print_hourly_counts(
        state
    )

    print_all_dates(
        state
    )

    print_audit_summary(
        state
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = parse_args(
        argv
    )

    run(
        args.csv_path
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )