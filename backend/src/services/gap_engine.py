"""B. 缺口填补、置信度与质量评分引擎（真算）。

输入：对齐通道序列（统一网格桶值 + 观测掩码 + 逐桶来源 provenance）。
口径要点（本版修订）：
  1. 连续未观测桶（长度 ≥ 2 桶）识别为缺口事件——只有真实回传能点亮观测掩码，
     网关掉线形成的空档不会被任何填补值当成观测；
  2. 按 job 的填补策略 locf / linear / seasonal_naive 填补
     （seasonal_naive 周期 = 24h 网格数，窗口不足回退 locf），填补值仅作展示，
     输出里逐桶标注 observed / gap_filled / source；
  3. 缺口置信度 = exp(-len/τ) × min(1, 邻域方差比)，τ = 10 桶；
  4. 异常率 = 对齐后 |稳健 z| > 3 的比例（z 用窗口稳健中位数 / MAD）；
  5. 质量分（口径固定）：
       score = 100 × (0.5×coverage + 0.3×(1-异常率) + 0.2×drift_score)
       drift_score = exp(-max|drift_ms|/1000)

失败态：对齐窗口内没有任何观测 → ``no_data``（不评分）。
"""
from __future__ import annotations

import math

import numpy as np

from src.constants.enums import FailureReason, FillStrategy, GapSeverity
from src.utils.stats import anomaly_flags

TAU_BUCKETS = 10.0
NEIGHBOUR_BUCKETS = 10
SEASONAL_PERIOD_S = 24 * 3600
QUALITY_FORMULA = (
    "score = 100 × (0.5×coverage + 0.3×(1-异常率) + 0.2×drift_score)；"
    "drift_score = exp(-max|drift_ms|/1000)；异常率 = |稳健 z|>3 的比例"
)


def _severity(duration_s: float) -> str:
    if duration_s >= 30.0:
        return GapSeverity.HIGH.value
    if duration_s >= 15.0:
        return GapSeverity.MEDIUM.value
    return GapSeverity.LOW.value


def _gap_confidence(
    values: np.ndarray,
    observed: np.ndarray,
    start: int,
    end: int,
    global_std: float,
) -> float:
    length = end - start
    left = values[max(0, start - NEIGHBOUR_BUCKETS) : start]
    right = values[end : min(values.size, end + NEIGHBOUR_BUCKETS)]
    neighbours = np.concatenate([left, right])
    neighbours = neighbours[~np.isnan(neighbours)]
    if neighbours.size >= 2 and global_std > 1e-9:
        neighbour_std = float(np.std(neighbours))
        variance_ratio = min(1.0, neighbour_std / global_std)
    else:
        variance_ratio = 0.3
    decay = math.exp(-length / TAU_BUCKETS)
    return max(0.02, min(1.0, decay * variance_ratio))


def _fill_gap(
    values: np.ndarray,
    start: int,
    end: int,
    grid_s: int,
    strategy: str,
    fallback_value: float,
) -> np.ndarray:
    length = end - start
    if strategy == FillStrategy.LOCF.value:
        previous = values[start - 1] if start > 0 else fallback_value
        return np.full(length, previous)
    if strategy == FillStrategy.SEASONAL_NAIVE.value:
        period = int(round(SEASONAL_PERIOD_S / grid_s))
        source = start - period
        if source >= 0 and not np.isnan(values[source : source + length]).any():
            return values[source : source + length].copy()
        previous = values[start - 1] if start > 0 else fallback_value
        return np.full(length, previous)
    # linear (default): interpolate both sides, fall back to locf at the edges
    left = values[start - 1] if start > 0 else np.nan
    right = values[end] if end < values.size else np.nan
    if not np.isnan(left) and not np.isnan(right):
        return np.linspace(left, right, length + 2)[1:-1]
    edge = left if not np.isnan(left) else right
    if np.isnan(edge):
        edge = fallback_value
    return np.full(length, edge)


def analyze(
    aligned: dict,
    fill_strategy: str,
) -> dict:
    """Return gaps, filled series, coverage/anomaly/quality components."""
    grid_s = int(aligned["grid_s"])
    t0 = float(aligned["t0"])
    channels: list[dict] = aligned.get("channels") or []
    total_observed = 0
    total_buckets = 0
    total_flags = 0
    total_scored = 0
    gap_payload: list[dict] = []
    series_payload: list[dict] = []

    for signal_index, signal in enumerate(channels):
        # raw_values hold only real observations (NaN where no gateway reported);
        # values may already carry display-only linear interpolation
        raw_source = signal.get("raw_values")
        if raw_source is None:
            raw_source = signal.get("values") or []
        raw_values = np.asarray(
            [np.nan if value is None else float(value) for value in raw_source],
            dtype=float,
        )
        observed = np.asarray(signal["observed"], dtype=bool)
        bucket_count = int(raw_values.size)
        total_buckets += bucket_count
        total_observed += int(observed.sum())
        if bucket_count == 0:
            continue
        observed_values = raw_values[observed]
        fallback = float(np.nanmean(observed_values)) if observed_values.size else 0.0
        global_std = float(np.std(observed_values)) if observed_values.size >= 2 else 0.0
        filled = raw_values.copy()
        gap_filled = np.zeros(bucket_count, dtype=bool)
        provenance = list(signal.get("provenance") or [""] * bucket_count)
        contributors = [list(item) for item in (signal.get("contributors") or [])]
        if len(provenance) < bucket_count:
            provenance += [""] * (bucket_count - len(provenance))
        if len(contributors) < bucket_count:
            contributors += [[] for _ in range(bucket_count - len(contributors))]
        index = 0
        while index < bucket_count:
            if observed[index]:
                index += 1
                continue
            end = index
            while end < bucket_count and not observed[end]:
                end += 1
            length = end - index
            if length >= 2:
                fill_values = _fill_gap(raw_values, index, end, grid_s, fill_strategy, fallback)
                filled[index:end] = fill_values
                gap_filled[index:end] = True
                duration_s = round(length * grid_s, 3)
                confidence = _gap_confidence(raw_values, observed, index, end, global_std)
                signal_start = float(signal.get("start_ts") or t0)
                start_ts = signal_start + index * grid_s
                end_ts = signal_start + end * grid_s
                gap_payload.append(
                    {
                        "signal_index": signal_index,
                        "signal_code": signal["signal_code"],
                        "device_code": signal["device_code"],
                        "measure_name": signal["measure_name"],
                        "unit": signal["unit"],
                        "source_code": signal.get("source_code", ""),
                        "source_codes": signal.get("source_codes") or [signal.get("source_code", "")],
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "start_bucket": index,
                        "bucket_length": length,
                        "duration_s": duration_s,
                        "fill_strategy": fill_strategy,
                        "confidence": round(confidence, 4),
                        "severity": _severity(duration_s),
                    }
                )
            index = end

        # filled buckets never carry an observing source: provenance explicitly blanks
        for slot in range(bucket_count):
            if gap_filled[slot]:
                provenance[slot] = ""
                contributors[slot] = []

        flags, scored = anomaly_flags(filled)
        total_flags += flags
        total_scored += scored
        series_payload.append(
            {
                "signal_index": signal_index,
                "signal_code": signal["signal_code"],
                "device_code": signal["device_code"],
                "device_name": signal.get("device_name", ""),
                "measure_name": signal["measure_name"],
                "unit": signal["unit"],
                "source_code": signal.get("source_code", ""),
                "source_codes": signal.get("source_codes") or [signal.get("source_code", "")],
                "member_signal_codes": signal.get("member_signal_codes") or [signal["signal_code"]],
                "bucket_count": bucket_count,
                "start_ts": float(signal.get("start_ts") or t0),
                "observed_count": int(observed.sum()),
                "coverage": signal.get("coverage", 0.0),
                "values": [None if math.isnan(v) else round(float(v), 4) for v in filled],
                "observed": observed.tolist(),
                "gap_filled": gap_filled.tolist(),
                "provenance": provenance,
                "contributors": contributors,
            }
        )

    if total_scored == 0 or total_observed == 0:
        return {
            "failure": FailureReason.NO_DATA.value,
            "gaps": [],
            "series": [],
            "components": {},
        }

    coverage = total_observed / total_buckets if total_buckets else 0.0
    anomaly_rate = total_flags / total_scored
    drifts = aligned.get("drift") or []
    max_abs_drift = max((abs(item["drift_ms"]) for item in drifts), default=0.0)
    drift_score = math.exp(-max_abs_drift / 1000.0)
    quality_score = 100.0 * (0.5 * coverage + 0.3 * (1.0 - anomaly_rate) + 0.2 * drift_score)
    return {
        "failure": None,
        "gaps": gap_payload,
        "series": series_payload,
        "components": {
            "coverage": round(coverage, 6),
            "anomaly_rate": round(anomaly_rate, 6),
            "drift_score": round(drift_score, 6),
            "max_abs_drift_ms": round(max_abs_drift, 1),
            "quality_score": round(quality_score, 2),
            "gap_count": len(gap_payload),
            "gap_total_s": round(sum(item["duration_s"] for item in gap_payload), 3),
            "formula": QUALITY_FORMULA,
        },
    }
