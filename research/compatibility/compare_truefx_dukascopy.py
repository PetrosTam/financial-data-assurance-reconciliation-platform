#!/usr/bin/env python3
"""
One-hour TrueFX <-> Dukascopy temporal-compatibility comparator.

Purpose
-------
Implements the bounded EUR/USD source-compatibility pilot for:
    2026-01-26T12:00:00.000Z .. 2026-01-26T12:59:59.999Z

The program produces aggregate compatibility statistics only. It does not:
- assign data-quality fault labels;
- treat provider disagreement as ground truth;
- infer unavailable network-arrival or latency semantics;
- perform trading or order-related actions.

Matching modes
--------------
1. causal_reusable
   For each monitored event at t, choose the latest peer event satisfying
   peer_time <= t and age <= tolerance. Peer reuse is allowed.

2. causal_one_to_one
   Greedy chronological one-to-one matching. For each monitored event, choose
   the latest currently-unused causal peer within tolerance. Each peer may be
   used at most once.

3. symmetric_nearest
   OFFLINE DIAGNOSTIC ONLY. Choose the peer with the smallest absolute
   timestamp separation. Equal-distance ties choose the earlier peer
   timestamp; equal timestamps choose the lower source order.

Tolerance grid:
    10, 25, 50, 100, 250, 500, 1000, 2000, 5000 ms

Directions:
    TrueFX -> Dukascopy
    Dukascopy -> TrueFX

Outputs
-------
A unique completed run directory containing:
    match_coverage.csv
    summary.json

The run is written inside a ".part" directory and promoted only after all
output postconditions succeed. No row-level provider prices are written.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import platform
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from typing import TypeVar, overload

getcontext().prec = 28

SCHEMA_VERSION = 2
PROTOCOL_VERSION = "one_hour_compatibility_v2"
INSTRUMENT = "EUR/USD"

UTC = timezone.utc
UNIX_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=UTC)

PILOT_START_UTC = datetime(2026, 1, 26, 12, 0, 0, 0, tzinfo=UTC)
PILOT_END_UTC = datetime(2026, 1, 26, 12, 59, 59, 999000, tzinfo=UTC)

TOLERANCES_MS = (10, 25, 50, 100, 250, 500, 1000, 2000, 5000)

TRUEFX_TIMESTAMP_FORMAT = "%Y%m%d %H:%M:%S.%f"
TRUEFX_TIMESTAMP_PATTERN = re.compile(r"^\d{8} \d{2}:\d{2}:\d{2}\.\d{3}$")

DUKASCOPY_EVENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DUKASCOPY_EVENT_TIME_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
)

DUKASCOPY_HEADER = (
    "event_time_utc",
    "epoch_ms",
    "bid",
    "ask",
    "bid_volume",
    "ask_volume",
)

T = TypeVar("T")
NumericValue = int | Decimal


@dataclass(frozen=True)
class Quote:
    source_index: int
    epoch_ms: int
    bid: Decimal
    ask: Decimal

    @property
    def mid(self) -> Decimal:
        return (self.bid + self.ask) / Decimal(2)

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    @property
    def spread_bps(self) -> Decimal:
        # Input validation guarantees mid > 0.
        return (self.spread / self.mid) * Decimal(10000)


@dataclass(frozen=True)
class Match:
    monitored_index: int
    peer_index: int
    separation_ms: int
    tie: bool = False


@dataclass(frozen=True)
class RunDirectories:
    temporary: Path
    final: Path


def datetime_to_epoch_ms(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")

    delta = value.astimezone(UTC) - UNIX_EPOCH_UTC
    if delta.microseconds % 1000 != 0:
        raise ValueError("datetime must be millisecond aligned")

    return (
        delta.days * 86_400_000
        + delta.seconds * 1000
        + delta.microseconds // 1000
    )


PILOT_START_MS = datetime_to_epoch_ms(PILOT_START_UTC)
PILOT_END_MS = datetime_to_epoch_ms(PILOT_END_UTC)


def validate_protocol_constants() -> None:
    if PILOT_END_MS < PILOT_START_MS:
        raise RuntimeError("Pilot interval is reversed.")

    if PILOT_END_MS - PILOT_START_MS + 1 != 3_600_000:
        raise RuntimeError("Pilot interval must cover exactly one UTC hour.")

    if (
        PILOT_START_UTC.minute != 0
        or PILOT_START_UTC.second != 0
        or PILOT_START_UTC.microsecond != 0
    ):
        raise RuntimeError("Pilot start is not aligned to the UTC hour.")

    if not (
        PILOT_END_UTC.minute == 59
        and PILOT_END_UTC.second == 59
        and PILOT_END_UTC.microsecond == 999000
    ):
        raise RuntimeError("Pilot end is not the final millisecond of the hour.")

    if tuple(sorted(set(TOLERANCES_MS))) != TOLERANCES_MS:
        raise RuntimeError("Tolerance grid must be unique and increasing.")

    if not TOLERANCES_MS or TOLERANCES_MS[0] < 0:
        raise RuntimeError("Tolerance grid contains an invalid value.")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the fixed one-hour TrueFX and Dukascopy EUR/USD "
            "historical compatibility interval."
        )
    )
    parser.add_argument(
        "--truefx",
        type=Path,
        required=True,
        help="Path to the TrueFX monthly EUR/USD historical CSV.",
    )
    parser.add_argument(
        "--dukascopy",
        type=Path,
        required=True,
        help="Path to canonical Dukascopy JForex ticks.csv.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Local-only output root for aggregate compatibility results.",
    )
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def fmt_utc_ms(epoch_ms: int) -> str:
    value = UNIX_EPOCH_UTC + timedelta(milliseconds=epoch_ms)
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_truefx_timestamp(raw_value: str) -> int:
    if TRUEFX_TIMESTAMP_PATTERN.fullmatch(raw_value) is None:
        raise ValueError(
            "timestamp must match YYYYMMDD HH:MM:SS.mmm exactly"
        )

    parsed = datetime.strptime(
        raw_value,
        TRUEFX_TIMESTAMP_FORMAT,
    ).replace(tzinfo=UTC)

    # Protocol assumption: the offset-free TrueFX archive timestamp is treated
    # as UTC-equivalent for this pilot. The raw row itself contains no offset.
    return datetime_to_epoch_ms(parsed)


def parse_dukascopy_event_time(raw_value: str) -> int:
    if DUKASCOPY_EVENT_TIME_PATTERN.fullmatch(raw_value) is None:
        raise ValueError(
            "event_time_utc must match YYYY-MM-DDTHH:MM:SS.mmmZ exactly"
        )

    parsed = datetime.strptime(
        raw_value,
        DUKASCOPY_EVENT_TIME_FORMAT,
    ).replace(tzinfo=UTC)

    return datetime_to_epoch_ms(parsed)


def parse_finite_decimal(raw_value: str, context: str) -> Decimal:
    try:
        value = Decimal(raw_value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal {raw_value!r} at {context}") from exc

    if not value.is_finite():
        raise ValueError(f"Non-finite decimal {raw_value!r} at {context}")

    return value


def validate_price_pair(bid: Decimal, ask: Decimal, context: str) -> None:
    if bid <= 0 or ask <= 0:
        raise ValueError(
            f"Non-positive price at {context}: bid={bid}, ask={ask}"
        )
    if ask < bid:
        raise ValueError(f"ask < bid at {context}: bid={bid}, ask={ask}")


def validate_volume_pair(
    bid_volume: Decimal,
    ask_volume: Decimal,
    context: str,
) -> None:
    if bid_volume < 0 or ask_volume < 0:
        raise ValueError(
            f"Negative volume at {context}: "
            f"bid_volume={bid_volume}, ask_volume={ask_volume}"
        )


def ensure_nondecreasing(
    previous_epoch_ms: int | None,
    current_epoch_ms: int,
    context: str,
) -> None:
    if previous_epoch_ms is not None and current_epoch_ms < previous_epoch_ms:
        raise ValueError(
            f"Timestamp reversal at {context}: "
            f"{current_epoch_ms} < {previous_epoch_ms}"
        )


def numeric_sort_key(value: NumericValue) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(value)


@overload
def nearest_rank_percentile(
    values: Sequence[int],
    probability: float,
) -> int | None:
    ...


@overload
def nearest_rank_percentile(
    values: Sequence[Decimal],
    probability: float,
) -> Decimal | None:
    ...


def nearest_rank_percentile(
    values: Sequence[int] | Sequence[Decimal],
    probability: float,
) -> NumericValue | None:
    """Nearest-rank percentile: rank = ceil(p*n), using one-based ranks."""
    if not values:
        return None
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0.0 and 1.0")

    ordered = sorted(values, key=numeric_sort_key)
    if probability == 0.0:
        return ordered[0]

    rank = math.ceil(probability * len(ordered))
    return ordered[rank - 1]


def decimal_mean(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return sum(values, Decimal(0)) / Decimal(len(values))


def decimal_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None

    converted = float(value)
    if not math.isfinite(converted):
        raise OverflowError(f"Decimal cannot be represented as finite float: {value}")
    return converted


def stable_load(
    path: Path,
    loader: Callable[[Path], tuple[T, dict[str, object]]],
) -> tuple[T, dict[str, object]]:
    """Hash before and after parsing so metadata describes the bytes inspected."""
    sha_before = sha256_file(path)
    loaded, metadata = loader(path)
    sha_after = sha256_file(path)

    if sha_before != sha_after:
        raise RuntimeError(f"Input changed while being read: {path}")

    metadata = dict(metadata)
    metadata["sha256"] = sha_before
    return loaded, metadata


def load_truefx(path: Path) -> tuple[list[Quote], dict[str, object]]:
    """
    Expected TrueFX archive layout:
        instrument,timestamp,bid,ask

    The timestamp carries no explicit offset. The frozen pilot protocol treats
    it as UTC-equivalent and records that assumption in summary.json.
    """
    quotes: list[Quote] = []
    raw_rows = 0
    outside_window = 0
    previous_epoch_ms: int | None = None
    physical_line: int | str = "unknown"

    try:
        with path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.reader(source, strict=True)

            for row_number, row in enumerate(reader, start=1):
                physical_line = reader.line_num
                raw_rows += 1

                if len(row) != 4:
                    raise ValueError(
                        f"Unexpected TrueFX column count at row {row_number}: "
                        f"expected 4, got {len(row)}"
                    )

                instrument, timestamp_raw, bid_raw, ask_raw = row

                if instrument != INSTRUMENT:
                    raise ValueError(
                        f"Unexpected TrueFX instrument {instrument!r} "
                        f"at row {row_number}; expected {INSTRUMENT!r}"
                    )

                try:
                    epoch_ms = parse_truefx_timestamp(timestamp_raw)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid TrueFX timestamp {timestamp_raw!r} "
                        f"at row {row_number}"
                    ) from exc

                bid = parse_finite_decimal(
                    bid_raw,
                    f"TrueFX row {row_number} bid",
                )
                ask = parse_finite_decimal(
                    ask_raw,
                    f"TrueFX row {row_number} ask",
                )
                validate_price_pair(bid, ask, f"TrueFX row {row_number}")

                ensure_nondecreasing(
                    previous_epoch_ms,
                    epoch_ms,
                    f"TrueFX row {row_number}",
                )
                previous_epoch_ms = epoch_ms

                if PILOT_START_MS <= epoch_ms <= PILOT_END_MS:
                    quotes.append(
                        Quote(
                            source_index=row_number,
                            epoch_ms=epoch_ms,
                            bid=bid,
                            ask=ask,
                        )
                    )
                else:
                    outside_window += 1

    except csv.Error as exc:
        raise RuntimeError(
            "TrueFX CSV parser failed near physical line "
            f"{physical_line}: {exc}"
        ) from exc

    if not quotes:
        raise ValueError(
            "TrueFX input produced zero quotes in the pilot interval."
        )

    return quotes, {
        "file_name": path.name,
        "raw_rows": raw_rows,
        "rows_in_pilot_interval": len(quotes),
        "rows_outside_pilot_interval": outside_window,
        "first_event_utc": fmt_utc_ms(quotes[0].epoch_ms),
        "last_event_utc": fmt_utc_ms(quotes[-1].epoch_ms),
        "timestamp_interpretation": (
            "Offset-free TrueFX archive timestamps are treated as "
            "UTC-equivalent by the frozen pilot protocol. The raw row "
            "contains no explicit timezone offset."
        ),
    }


def load_dukascopy(path: Path) -> tuple[list[Quote], dict[str, object]]:
    """
    Expected canonical JForex probe CSV:
        event_time_utc,epoch_ms,bid,ask,bid_volume,ask_volume
    """
    quotes: list[Quote] = []
    raw_rows = 0
    previous_epoch_ms: int | None = None
    physical_line: int | str = "unknown"

    try:
        with path.open("r", encoding="utf-8", newline="") as source:
            reader = csv.reader(source, strict=True)

            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError("Dukascopy CSV is empty.") from exc

            if tuple(header) != DUKASCOPY_HEADER:
                raise ValueError(
                    f"Unexpected Dukascopy CSV header: {header!r}; "
                    f"expected {list(DUKASCOPY_HEADER)!r}"
                )

            for row_number, row in enumerate(reader, start=2):
                physical_line = reader.line_num
                raw_rows += 1

                if len(row) != len(DUKASCOPY_HEADER):
                    raise ValueError(
                        f"Unexpected Dukascopy column count at row {row_number}: "
                        f"expected {len(DUKASCOPY_HEADER)}, got {len(row)}"
                    )

                (
                    event_time_raw,
                    epoch_ms_raw,
                    bid_raw,
                    ask_raw,
                    bid_volume_raw,
                    ask_volume_raw,
                ) = row

                try:
                    epoch_ms = int(epoch_ms_raw)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid Dukascopy epoch_ms {epoch_ms_raw!r} "
                        f"at row {row_number}"
                    ) from exc

                try:
                    event_time_epoch_ms = parse_dukascopy_event_time(
                        event_time_raw
                    )
                except ValueError as exc:
                    raise ValueError(
                        "Invalid Dukascopy event_time_utc "
                        f"{event_time_raw!r} at row {row_number}"
                    ) from exc

                if event_time_epoch_ms != epoch_ms:
                    raise ValueError(
                        "Dukascopy event_time_utc / epoch_ms mismatch "
                        f"at row {row_number}: "
                        f"{event_time_epoch_ms} != {epoch_ms}"
                    )

                bid = parse_finite_decimal(
                    bid_raw,
                    f"Dukascopy row {row_number} bid",
                )
                ask = parse_finite_decimal(
                    ask_raw,
                    f"Dukascopy row {row_number} ask",
                )
                bid_volume = parse_finite_decimal(
                    bid_volume_raw,
                    f"Dukascopy row {row_number} bid_volume",
                )
                ask_volume = parse_finite_decimal(
                    ask_volume_raw,
                    f"Dukascopy row {row_number} ask_volume",
                )

                validate_price_pair(bid, ask, f"Dukascopy row {row_number}")
                validate_volume_pair(
                    bid_volume,
                    ask_volume,
                    f"Dukascopy row {row_number}",
                )
                ensure_nondecreasing(
                    previous_epoch_ms,
                    epoch_ms,
                    f"Dukascopy row {row_number}",
                )
                previous_epoch_ms = epoch_ms

                if not PILOT_START_MS <= epoch_ms <= PILOT_END_MS:
                    raise ValueError(
                        "Dukascopy canonical-hour artifact contains a row "
                        f"outside the pilot interval at row {row_number}: "
                        f"{epoch_ms}"
                    )

                quotes.append(
                    Quote(
                        source_index=row_number,
                        epoch_ms=epoch_ms,
                        bid=bid,
                        ask=ask,
                    )
                )

    except csv.Error as exc:
        raise RuntimeError(
            "Dukascopy CSV parser failed near physical line "
            f"{physical_line}: {exc}"
        ) from exc

    if not quotes:
        raise ValueError(
            "Dukascopy input produced zero quotes in the pilot interval."
        )

    return quotes, {
        "file_name": path.name,
        "raw_rows": raw_rows,
        "rows_in_pilot_interval": len(quotes),
        "rows_outside_pilot_interval": 0,
        "first_event_utc": fmt_utc_ms(quotes[0].epoch_ms),
        "last_event_utc": fmt_utc_ms(quotes[-1].epoch_ms),
        "timestamp_interpretation": (
            "epoch_ms is preserved from the JForex historical tick callback; "
            "event_time_utc is independently parsed and required to represent "
            "the same millisecond."
        ),
    }


def causal_reusable(
    monitored: Sequence[Quote],
    peers: Sequence[Quote],
    tolerance_ms: int,
) -> list[Match | None]:
    results: list[Match | None] = []
    peer_position = -1

    for monitored_index, monitored_quote in enumerate(monitored):
        while (
            peer_position + 1 < len(peers)
            and peers[peer_position + 1].epoch_ms <= monitored_quote.epoch_ms
        ):
            peer_position += 1

        if peer_position < 0:
            results.append(None)
            continue

        separation_ms = monitored_quote.epoch_ms - peers[peer_position].epoch_ms

        if separation_ms <= tolerance_ms:
            results.append(
                Match(
                    monitored_index=monitored_index,
                    peer_index=peer_position,
                    separation_ms=separation_ms,
                )
            )
        else:
            results.append(None)

    return results


def causal_one_to_one(
    monitored: Sequence[Quote],
    peers: Sequence[Quote],
    tolerance_ms: int,
) -> list[Match | None]:
    """
    Greedy latest-unused causal matching.

    Each newly available peer is pushed onto a stack. The latest unused
    eligible peer is consumed first. Older unused peers remain available until
    they become permanently older than the tolerance. Assignments therefore
    need not preserve peer-index order; that is an explicit property of this
    pilot diagnostic rather than an accidental implementation detail.
    """
    results: list[Match | None] = []
    available_peer_indices: list[int] = []
    peer_cursor = 0

    for monitored_index, monitored_quote in enumerate(monitored):
        while (
            peer_cursor < len(peers)
            and peers[peer_cursor].epoch_ms <= monitored_quote.epoch_ms
        ):
            available_peer_indices.append(peer_cursor)
            peer_cursor += 1

        if not available_peer_indices:
            results.append(None)
            continue

        latest_peer_index = available_peer_indices[-1]
        separation_ms = (
            monitored_quote.epoch_ms - peers[latest_peer_index].epoch_ms
        )

        if separation_ms > tolerance_ms:
            # If the latest available peer is stale, every earlier available
            # peer is at least as old and can never become eligible later.
            available_peer_indices.clear()
            results.append(None)
            continue

        available_peer_indices.pop()
        results.append(
            Match(
                monitored_index=monitored_index,
                peer_index=latest_peer_index,
                separation_ms=separation_ms,
            )
        )

    return results


def symmetric_nearest(
    monitored: Sequence[Quote],
    peers: Sequence[Quote],
    tolerance_ms: int,
) -> list[Match | None]:
    peer_times = [quote.epoch_ms for quote in peers]
    results: list[Match | None] = []

    for monitored_index, monitored_quote in enumerate(monitored):
        target_time = monitored_quote.epoch_ms
        left = bisect.bisect_left(peer_times, target_time)
        right = bisect.bisect_right(peer_times, target_time)

        # Exact-time peers are the nearest possible evidence. Lower source
        # order wins when multiple peer observations share the exact time.
        if left != right:
            chosen_peer_index = left
            separation_ms = 0
            tie = right - left > 1
        else:
            candidate_indices: list[int] = []

            if left > 0:
                previous_time = peer_times[left - 1]
                previous_first_index = bisect.bisect_left(
                    peer_times,
                    previous_time,
                    0,
                    left,
                )
                candidate_indices.append(previous_first_index)

            if left < len(peers):
                # bisect_left already points to the first observation at the
                # next timestamp, so lower source order is preserved.
                candidate_indices.append(left)

            if not candidate_indices:
                results.append(None)
                continue

            candidate_distances = [
                abs(peers[index].epoch_ms - target_time)
                for index in candidate_indices
            ]
            separation_ms = min(candidate_distances)
            tied_indices = [
                index
                for index, distance in zip(
                    candidate_indices,
                    candidate_distances,
                )
                if distance == separation_ms
            ]
            chosen_peer_index = min(
                tied_indices,
                key=lambda index: (
                    peers[index].epoch_ms,
                    peers[index].source_index,
                ),
            )
            tie = len(tied_indices) > 1

        if separation_ms <= tolerance_ms:
            results.append(
                Match(
                    monitored_index=monitored_index,
                    peer_index=chosen_peer_index,
                    separation_ms=separation_ms,
                    tie=tie,
                )
            )
        else:
            results.append(None)

    return results


def validate_matches(
    mode: str,
    tolerance_ms: int,
    monitored: Sequence[Quote],
    peers: Sequence[Quote],
    matches: Sequence[Match | None],
) -> None:
    if len(matches) != len(monitored):
        raise AssertionError(
            "Matcher result length does not equal monitored length."
        )

    used_peer_indices: set[int] = set()

    for expected_monitored_index, match in enumerate(matches):
        if match is None:
            continue

        if match.monitored_index != expected_monitored_index:
            raise AssertionError(
                "Matcher returned an inconsistent monitored index."
            )

        if not 0 <= match.peer_index < len(peers):
            raise AssertionError("Matcher returned an out-of-range peer index.")

        monitored_quote = monitored[match.monitored_index]
        peer_quote = peers[match.peer_index]

        if mode in ("causal_reusable", "causal_one_to_one"):
            if peer_quote.epoch_ms > monitored_quote.epoch_ms:
                raise AssertionError("Causal matcher used future peer evidence.")
            expected_separation = monitored_quote.epoch_ms - peer_quote.epoch_ms
        elif mode == "symmetric_nearest":
            expected_separation = abs(
                monitored_quote.epoch_ms - peer_quote.epoch_ms
            )
        else:
            raise AssertionError(f"Unknown matching mode: {mode}")

        if match.separation_ms != expected_separation:
            raise AssertionError("Matcher reported an incorrect separation.")

        if not 0 <= match.separation_ms <= tolerance_ms:
            raise AssertionError("Matcher returned a match outside tolerance.")

        if mode == "causal_one_to_one":
            if match.peer_index in used_peer_indices:
                raise AssertionError("One-to-one matcher reused a peer.")
            used_peer_indices.add(match.peer_index)


def consecutive_unmatched_runs(
    matches: Sequence[Match | None],
) -> list[int]:
    runs: list[int] = []
    current = 0

    for match in matches:
        if match is None:
            current += 1
        elif current:
            runs.append(current)
            current = 0

    if current:
        runs.append(current)

    return runs


def reuse_stats(
    matches: Sequence[Match | None],
) -> dict[str, object]:
    counts: dict[int, int] = {}

    for match in matches:
        if match is not None:
            counts[match.peer_index] = counts.get(match.peer_index, 0) + 1

    reuse_values = list(counts.values())

    if not reuse_values:
        return {
            "distinct_peers_used": 0,
            "peers_reused_more_than_once": 0,
            "reuse_p50": None,
            "reuse_p90": None,
            "reuse_p95": None,
            "reuse_p99": None,
            "reuse_max": None,
        }

    return {
        "distinct_peers_used": len(reuse_values),
        "peers_reused_more_than_once": sum(
            value > 1 for value in reuse_values
        ),
        "reuse_p50": nearest_rank_percentile(reuse_values, 0.50),
        "reuse_p90": nearest_rank_percentile(reuse_values, 0.90),
        "reuse_p95": nearest_rank_percentile(reuse_values, 0.95),
        "reuse_p99": nearest_rank_percentile(reuse_values, 0.99),
        "reuse_max": max(reuse_values),
    }


def price_diagnostics(
    monitored: Sequence[Quote],
    peers: Sequence[Quote],
    matches: Sequence[Match | None],
) -> dict[str, object]:
    signed_mid: list[Decimal] = []
    absolute_mid: list[Decimal] = []
    signed_spread: list[Decimal] = []
    absolute_spread: list[Decimal] = []

    for match in matches:
        if match is None:
            continue

        monitored_quote = monitored[match.monitored_index]
        peer_quote = peers[match.peer_index]

        reference_mid = (monitored_quote.mid + peer_quote.mid) / Decimal(2)
        mid_divergence = (
            (monitored_quote.mid - peer_quote.mid)
            / reference_mid
            * Decimal(10000)
        )
        spread_divergence = monitored_quote.spread_bps - peer_quote.spread_bps

        signed_mid.append(mid_divergence)
        absolute_mid.append(abs(mid_divergence))
        signed_spread.append(spread_divergence)
        absolute_spread.append(abs(spread_divergence))

    return {
        "mid_div_signed_mean_bps": decimal_to_float(decimal_mean(signed_mid)),
        "mid_div_abs_p50_bps": decimal_to_float(
            nearest_rank_percentile(absolute_mid, 0.50)
        ),
        "mid_div_abs_p95_bps": decimal_to_float(
            nearest_rank_percentile(absolute_mid, 0.95)
        ),
        "mid_div_abs_p99_bps": decimal_to_float(
            nearest_rank_percentile(absolute_mid, 0.99)
        ),
        "mid_div_abs_max_bps": decimal_to_float(
            max(absolute_mid) if absolute_mid else None
        ),
        "spread_div_signed_mean_bps": decimal_to_float(
            decimal_mean(signed_spread)
        ),
        "spread_div_abs_p50_bps": decimal_to_float(
            nearest_rank_percentile(absolute_spread, 0.50)
        ),
        "spread_div_abs_p95_bps": decimal_to_float(
            nearest_rank_percentile(absolute_spread, 0.95)
        ),
        "spread_div_abs_p99_bps": decimal_to_float(
            nearest_rank_percentile(absolute_spread, 0.99)
        ),
        "spread_div_abs_max_bps": decimal_to_float(
            max(absolute_spread) if absolute_spread else None
        ),
    }


def summarize_matches(
    direction: str,
    mode: str,
    tolerance_ms: int,
    monitored: Sequence[Quote],
    peers: Sequence[Quote],
    matches: Sequence[Match | None],
) -> dict[str, object]:
    matched = [match for match in matches if match is not None]
    separations = [match.separation_ms for match in matched]
    unmatched_runs = consecutive_unmatched_runs(matches)

    row: dict[str, object] = {
        "direction": direction,
        "mode": mode,
        "tolerance_ms": tolerance_ms,
        "eligible_monitored_events": len(monitored),
        "matched_events": len(matched),
        "unmatched_events": len(monitored) - len(matched),
        "coverage_pct": len(matched) / len(monitored) * 100.0,
        "separation_p50_ms": nearest_rank_percentile(separations, 0.50),
        "separation_p90_ms": nearest_rank_percentile(separations, 0.90),
        "separation_p95_ms": nearest_rank_percentile(separations, 0.95),
        "separation_p99_ms": nearest_rank_percentile(separations, 0.99),
        "separation_max_ms": max(separations) if separations else None,
        "unmatched_run_count": len(unmatched_runs),
        "unmatched_run_p50_events": nearest_rank_percentile(
            unmatched_runs,
            0.50,
        ),
        "unmatched_run_p95_events": nearest_rank_percentile(
            unmatched_runs,
            0.95,
        ),
        "unmatched_run_max_events": (
            max(unmatched_runs) if unmatched_runs else 0
        ),
        "tie_count": sum(match.tie for match in matched),
        "tie_rule": (
            "equal-distance -> earlier peer timestamp; "
            "equal timestamp -> lower source order"
            if mode == "symmetric_nearest"
            else "not_applicable"
        ),
    }

    # Actual reuse is measured for every mode. Symmetric-nearest can reuse
    # peers too; one-to-one naturally reports zero reuse.
    row.update(reuse_stats(matches))

    # Descriptive provider disagreement only; never fault ground truth.
    row.update(price_diagnostics(monitored, peers, matches))
    return row


def minute_availability(quotes: Sequence[Quote]) -> set[int]:
    return {quote.epoch_ms // 60_000 for quote in quotes}


def common_coverage_summary(
    truefx: Sequence[Quote],
    dukascopy: Sequence[Quote],
) -> dict[str, object]:
    requested_minutes = set(
        range(
            PILOT_START_MS // 60_000,
            PILOT_END_MS // 60_000 + 1,
        )
    )
    truefx_active = minute_availability(truefx) & requested_minutes
    dukascopy_active = minute_availability(dukascopy) & requested_minutes
    common_active = truefx_active & dukascopy_active

    return {
        "requested_interval_start_utc": fmt_utc_ms(PILOT_START_MS),
        "requested_interval_end_utc": fmt_utc_ms(PILOT_END_MS),
        "truefx_first_event_utc": fmt_utc_ms(truefx[0].epoch_ms),
        "truefx_last_event_utc": fmt_utc_ms(truefx[-1].epoch_ms),
        "dukascopy_first_event_utc": fmt_utc_ms(dukascopy[0].epoch_ms),
        "dukascopy_last_event_utc": fmt_utc_ms(dukascopy[-1].epoch_ms),
        "requested_minutes": len(requested_minutes),
        "truefx_active_minutes": len(truefx_active),
        "dukascopy_active_minutes": len(dukascopy_active),
        "common_active_minutes": len(common_active),
        "truefx_only_active_minutes": len(
            truefx_active - dukascopy_active
        ),
        "dukascopy_only_active_minutes": len(
            dukascopy_active - truefx_active
        ),
        "both_available_pct_of_requested_minutes": (
            len(common_active) / len(requested_minutes) * 100.0
        ),
    }


def create_run_directories(output_root: Path) -> RunDirectories:
    output_root = output_root.expanduser()
    now = datetime.now(UTC)
    stamp = (
        now.strftime("%Y-%m-%dT%H%M%S.")
        + f"{now.microsecond // 1000:03d}Z"
    )

    interval_end_exclusive = PILOT_END_UTC + timedelta(milliseconds=1)
    base = (
        output_root
        / "eurusd"
        / PILOT_START_UTC.strftime("%Y-%m-%d")
        / (
            PILOT_START_UTC.strftime("%H%M")
            + "-"
            + interval_end_exclusive.strftime("%H%M")
            + "utc"
        )
    )

    suffix = 1
    while True:
        run_name = stamp if suffix == 1 else f"{stamp}-{suffix:02d}"
        final = base / run_name
        temporary = base / f"{run_name}.part"

        if final.exists():
            suffix += 1
            continue

        try:
            temporary.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            suffix += 1
            continue

        return RunDirectories(temporary=temporary, final=final)


def write_coverage_csv(
    path: Path,
    rows: Sequence[dict[str, object]],
) -> None:
    if not rows:
        raise ValueError("No compatibility summary rows to write.")

    fieldnames = list(rows[0].keys())
    expected_keys = set(fieldnames)

    for row_number, row in enumerate(rows, start=1):
        if set(row) != expected_keys:
            raise ValueError(
                f"Inconsistent coverage row schema at row {row_number}."
            )

    with path.open("x", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=fieldnames,
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary_json(
    path: Path,
    summary: dict[str, object],
) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as target:
        json.dump(
            summary,
            target,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        target.write("\n")


def promote_run_directory(directories: RunDirectories) -> None:
    if directories.final.exists():
        raise FileExistsError(directories.final)

    required = (
        directories.temporary / "match_coverage.csv",
        directories.temporary / "summary.json",
    )
    for path in required:
        if not path.is_file():
            raise RuntimeError(
                f"Temporary compatibility run is missing: {path.name}"
            )

    # The run name is unique and the final destination is checked first.
    # On failure before promotion, the ".part" directory remains forensic
    # evidence of an incomplete run.
    directories.temporary.rename(directories.final)


def build_summary(
    *,
    truefx_metadata: dict[str, object],
    dukascopy_metadata: dict[str, object],
    truefx: Sequence[Quote],
    dukascopy: Sequence[Quote],
    coverage_sha256: str,
    coverage_rows: int,
    analysis_script_sha256: str,
) -> dict[str, object]:
    generated_at_utc = (
        datetime.now(UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "status": "completed",
        "purpose": "one-hour cross-source temporal compatibility pilot",
        "instrument": INSTRUMENT,
        "not_ground_truth": True,
        "provider_disagreement_is_context_only": True,
        "price_diagnostics_are_context_only": True,
        "symmetric_nearest_is_offline_diagnostic_only": True,
        "pilot_interval": {
            "start_utc": fmt_utc_ms(PILOT_START_MS),
            "end_utc": fmt_utc_ms(PILOT_END_MS),
            "inclusive_boundaries": True,
        },
        "tolerance_grid_ms": list(TOLERANCES_MS),
        "percentile_method": "nearest_rank: rank=ceil(p*n), one-based",
        "matching_modes": {
            "causal_reusable": {
                "definition": (
                    "latest peer_time <= monitored_time within tolerance; "
                    "peer reuse allowed"
                ),
                "future_lookahead": False,
                "peer_reuse": True,
                "equal_peer_timestamp_rule": (
                    "latest source order wins because the latest eligible "
                    "peer is selected"
                ),
            },
            "causal_one_to_one": {
                "definition": (
                    "greedy chronological latest-unused causal peer "
                    "within tolerance"
                ),
                "future_lookahead": False,
                "peer_reuse": False,
                "peer_index_order_preserved": False,
                "equal_peer_timestamp_rule": (
                    "latest available source order is consumed first"
                ),
            },
            "symmetric_nearest": {
                "definition": "nearest absolute-time peer within tolerance",
                "future_lookahead": True,
                "operational_claim_allowed": False,
                "peer_reuse": True,
                "tie_rule": (
                    "equal-distance -> earlier peer timestamp; "
                    "equal timestamp -> lower source order"
                ),
            },
        },
        "price_diagnostics": {
            "mid_divergence_bps": (
                "(monitored_mid - peer_mid) / "
                "mean(monitored_mid, peer_mid) * 10000"
            ),
            "spread_divergence_bps": (
                "monitored_spread_bps - peer_spread_bps"
            ),
            "interpretation": (
                "descriptive provider disagreement only; never fault ground truth"
            ),
        },
        "inputs": {
            "truefx": truefx_metadata,
            "dukascopy": dukascopy_metadata,
        },
        "common_coverage": common_coverage_summary(truefx, dukascopy),
        "aggregate_output": {
            "file_name": "match_coverage.csv",
            "rows": coverage_rows,
            "sha256": coverage_sha256,
        },
        "execution_provenance": {
            "analysis_script": Path(__file__).name,
            "analysis_script_sha256": analysis_script_sha256,
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "generated_at_utc": generated_at_utc,
    }


def run(
    truefx_path: Path,
    dukascopy_path: Path,
    output_root: Path,
) -> Path:
    validate_protocol_constants()

    analysis_script_path = Path(__file__).resolve()
    script_sha_before = sha256_file(analysis_script_path)

    truefx_path = truefx_path.expanduser()
    dukascopy_path = dukascopy_path.expanduser()

    if not truefx_path.is_file():
        raise FileNotFoundError(f"TrueFX input not found: {truefx_path}")
    if not dukascopy_path.is_file():
        raise FileNotFoundError(
            f"Dukascopy input not found: {dukascopy_path}"
        )

    truefx, truefx_metadata = stable_load(truefx_path, load_truefx)
    dukascopy, dukascopy_metadata = stable_load(
        dukascopy_path,
        load_dukascopy,
    )

    print("=== INPUTS ===")
    print(f"TrueFX rows in interval: {len(truefx)}")
    print(f"Dukascopy rows in interval: {len(dukascopy)}")
    print(
        f"TrueFX first/last: {fmt_utc_ms(truefx[0].epoch_ms)} -> "
        f"{fmt_utc_ms(truefx[-1].epoch_ms)}"
    )
    print(
        f"Dukascopy first/last: {fmt_utc_ms(dukascopy[0].epoch_ms)} -> "
        f"{fmt_utc_ms(dukascopy[-1].epoch_ms)}"
    )

    directions = (
        ("truefx_to_dukascopy", truefx, dukascopy),
        ("dukascopy_to_truefx", dukascopy, truefx),
    )
    modes: tuple[
        tuple[
            str,
            Callable[
                [Sequence[Quote], Sequence[Quote], int],
                list[Match | None],
            ],
        ],
        ...,
    ] = (
        ("causal_reusable", causal_reusable),
        ("causal_one_to_one", causal_one_to_one),
        ("symmetric_nearest", symmetric_nearest),
    )

    summary_rows: list[dict[str, object]] = []

    for direction, monitored, peers in directions:
        for mode_name, matcher in modes:
            for tolerance_ms in TOLERANCES_MS:
                matches = matcher(monitored, peers, tolerance_ms)
                validate_matches(
                    mode_name,
                    tolerance_ms,
                    monitored,
                    peers,
                    matches,
                )

                row = summarize_matches(
                    direction=direction,
                    mode=mode_name,
                    tolerance_ms=tolerance_ms,
                    monitored=monitored,
                    peers=peers,
                    matches=matches,
                )
                summary_rows.append(row)

                print(
                    f"{direction:22s} "
                    f"{mode_name:20s} "
                    f"tol={tolerance_ms:4d}ms "
                    f"coverage={row['coverage_pct']:.3f}% "
                    f"p95={row['separation_p95_ms']}"
                )

    expected_rows = len(directions) * len(modes) * len(TOLERANCES_MS)
    if len(summary_rows) != expected_rows:
        raise AssertionError(
            "Unexpected number of compatibility summary rows."
        )

    directories = create_run_directories(output_root)
    coverage_temp = directories.temporary / "match_coverage.csv"
    summary_temp = directories.temporary / "summary.json"

    try:
        write_coverage_csv(coverage_temp, summary_rows)
        coverage_sha256 = sha256_file(coverage_temp)

        summary = build_summary(
            truefx_metadata=truefx_metadata,
            dukascopy_metadata=dukascopy_metadata,
            truefx=truefx,
            dukascopy=dukascopy,
            coverage_sha256=coverage_sha256,
            coverage_rows=len(summary_rows),
            analysis_script_sha256=script_sha_before,
        )
        write_summary_json(summary_temp, summary)

        # Verify the written JSON before marking the run complete.
        with summary_temp.open("r", encoding="utf-8") as source:
            parsed_summary = json.load(source)

        if parsed_summary.get("status") != "completed":
            raise RuntimeError("Summary postcondition failed.")

        script_sha_after = sha256_file(analysis_script_path)
        if script_sha_after != script_sha_before:
            raise RuntimeError(
                "Analysis script changed while the run was executing."
            )

        promote_run_directory(directories)

    except Exception as exc:
        raise RuntimeError(
            "Compatibility run failed. Incomplete evidence, if created, "
            f"remains at: {directories.temporary}"
        ) from exc

    final_coverage = directories.final / "match_coverage.csv"
    final_summary = directories.final / "summary.json"

    final_coverage_sha256 = sha256_file(final_coverage)
    if final_coverage_sha256 != coverage_sha256:
        raise RuntimeError(
            "Coverage artifact hash changed after run promotion."
        )

    print()
    print("=== OUTPUT ===")
    print(f"Run directory: {directories.final}")
    print(f"Coverage matrix: {final_coverage}")
    print(f"Coverage SHA-256: {final_coverage_sha256}")
    print(f"Summary: {final_summary}")
    print(f"Summary SHA-256: {sha256_file(final_summary)}")

    return directories.final


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    run(
        truefx_path=args.truefx,
        dukascopy_path=args.dukascopy,
        output_root=args.output_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
