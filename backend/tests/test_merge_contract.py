"""Regression tests for the night-batch merge contract.

Covers the four requirements behind the offline merge:
  1. per-source clock correction happens before grid placement;
  2. redundant gateways of the same device + measure share one grid and one channel;
  3. overlapping buckets record every contributor and the selected source;
  4. gateway-offline gaps stay unobserved and fill values never masquerade as data.

Run directly: python backend/tests/test_merge_contract.py
(the test_* functions are also plain-assert pytest cases if pytest is installed).
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src.services.align_engine import SignalInput, align_job
from src.services.gap_engine import analyze as analyze_gaps

T0 = 1_000_000.0
GRID = 5


def _physical(t: float) -> float:
    """Shared process with steep edges so sub-cadence clock offsets are resolvable."""
    phase = (t % 40.0) / 40.0
    plateau = 1.0 if 0.25 <= phase < 0.5 else 0.0
    edge = sum(math.exp(-((phase - center) ** 2) / 0.0008) for center in (0.25, 0.5))
    return 10.0 + 4.0 * plateau + 3.0 * edge + math.sin(t / 7.0)


def _sample(clock_ts: np.ndarray, seed: int):
    rng = np.random.default_rng(seed)
    return [
        (round(float(t), 4), round(_physical(t) + float(rng.normal(0, 0.05)), 5), i)
        for i, t in enumerate(clock_ts)
    ]


def _build_signals() -> list[SignalInput]:
    base = np.arange(121) * 5.0
    signals = [
        SignalInput(1, "DEV.VIB-GW1", "DEV", "Device", "VIB", "mm/s", 1, "GW-1", _sample(T0 + base, 11)),
        SignalInput(2, "DEV.VIB-GW2", "DEV", "Device", "VIB", "mm/s", 2, "GW-2", _sample(T0 + base + 1.5, 22)),
        SignalInput(3, "DEV.VIB-GW3", "DEV", "Device", "VIB", "mm/s", 3, "GW-3", _sample(T0 + base + 0.8, 33)),
    ]
    outage = set(range(40, 45))  # 25s gateway-1 outage on a single-source channel
    cur = [
        (round(T0 + t, 4), float(20 + (i % 3)), i)
        for i, t in enumerate(base)
        if i not in outage
    ]
    signals.append(SignalInput(4, "DEV.CUR", "DEV", "Device", "CUR", "A", 1, "GW-1", cur))
    return signals


def test_clock_correction_precedes_grid() -> None:
    result = align_job(_build_signals(), T0 - 10, T0 + 620, GRID, "mean")
    drift = {item["source_code"]: item for item in result.drift}
    assert result.failure is None
    assert drift["GW-1"]["is_anchor"] is True
    assert abs(drift["GW-2"]["drift_ms"] - 1500.0) < 150
    assert abs(drift["GW-3"]["drift_ms"] - 800.0) < 150
    for item in result.corrections:
        assert abs(item["correction_ms"] + item["drift_ms"]) < 0.1
    # shared grid origin is aligned to a wall-clock grid boundary
    assert abs(result.t0 % GRID) < 1e-9


def test_redundant_gateways_merge_into_one_channel() -> None:
    result = align_job(_build_signals(), T0 - 10, T0 + 620, GRID, "mean")
    channels = {(c["device_code"], c["measure_name"]): c for c in result.channels}
    vib = channels[("DEV", "VIB")]
    assert sorted(vib["source_codes"]) == ["GW-1", "GW-2", "GW-3"]
    assert len(vib["member_signal_codes"]) == 3
    # every observed bucket carries provenance and contributors
    for i, is_observed in enumerate(vib["observed"]):
        if is_observed:
            assert vib["provenance"][i]
            assert vib["contributors"][i]


def test_overlap_ledger_records_selection() -> None:
    result = align_job(_build_signals(), T0 - 10, T0 + 620, GRID, "mean")
    assert result.overlaps, "three-way redundancy must produce an overlap ledger"
    event = result.overlaps[0]["events"][0]
    assert len(event["sources"]) >= 2
    assert event["selected_source"] in event["sources"]


def test_gap_fill_never_pretends_to_be_observed() -> None:
    aligned = align_job(_build_signals(), T0 - 10, T0 + 620, GRID, "mean").to_dict()
    gaps = analyze_gaps(aligned, "linear")
    assert gaps["failure"] is None
    cur = next(s for s in gaps["series"] if s["measure_name"] == "CUR")
    cur_gaps = [g for g in gaps["gaps"] if g["measure_name"] == "CUR"]
    longest = max(cur_gaps, key=lambda g: g["duration_s"])
    assert abs(longest["duration_s"] - 25.0) < 0.01
    for i in range(cur["bucket_count"]):
        if cur["gap_filled"][i]:
            assert cur["observed"][i] is False
            assert cur["provenance"][i] == ""
            assert cur["values"][i] is not None  # display value still present
        if cur["observed"][i]:
            assert cur["gap_filled"][i] is False


def _run_all() -> int:
    tests = [
        test_clock_correction_precedes_grid,
        test_redundant_gateways_merge_into_one_channel,
        test_overlap_ledger_records_selection,
        test_gap_fill_never_pretends_to_be_observed,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"ALL {len(tests)} TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
