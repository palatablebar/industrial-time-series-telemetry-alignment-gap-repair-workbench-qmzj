"""A. 时间对齐与重采样引擎（真算，无第三方时序库依赖）。

输入：多源不规则时间戳原始点 ``(ts_epoch, value, seq)``。
步骤：
  1. 排序并按时间戳去重（同 ts 保留 last，即 seq 最大者）；
  2. 以全局最早点为原点分箱 ``bucket = floor((ts - t0) / grid)``；
  3. 桶内聚合 mean / last / linear（linear 先取桶均值，再对空桶线性插值）；
  4. 时钟漂移：对同一设备在不同源上的测点两两做互相关，±60s 内 250ms 步长
     粗扫、峰值附近 5ms 细化，重叠率不足 75% 的 lag 不计分；
     多对估计按相关系数加权，最后以参考源为锚做一致性校正；
  5. 覆盖率 = 全部信号的非空桶 / 全部信号的总桶（按各信号有效采集跨度裁剪）。

失败态：窗口内点数 < 总桶数 10% → ``insufficient_data``；
时间戳乱序率 > 30% → ``timestamp_disorder``。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from src.constants.enums import AggStrategy, FailureReason, GridSize

GRID_CHOICES: tuple[int, ...] = tuple(GridSize.values())
MAX_LAG_S = 60.0
LAG_STEP_S = 0.25
FINE_STEP_S = 0.005
MIN_OVERLAP_RATIO = 0.75
COARSE_SAMPLE_LIMIT = 20000


@dataclass
class SignalInput:
    signal_id: int
    signal_code: str
    device_code: str
    device_name: str
    measure_name: str
    unit: str
    source_id: int
    source_code: str
    points: list[tuple[float, float, int]] = field(default_factory=list)


@dataclass
class AlignResult:
    grid_s: int
    t0: float
    point_count: int
    bucket_count: int
    coverage: float
    disorder_rate: float
    signals: list[dict]
    drift: list[dict]
    drift_confidence: float
    failure: str | None = None
    failure_detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "grid_s": self.grid_s,
            "t0": self.t0,
            "point_count": self.point_count,
            "bucket_count": self.bucket_count,
            "coverage": round(self.coverage, 6),
            "disorder_rate": round(self.disorder_rate, 4),
            "signals": self.signals,
            "drift": self.drift,
            "drift_confidence": round(self.drift_confidence, 4),
            "failure": self.failure,
            "failure_detail": self.failure_detail,
        }


def _sort_and_dedupe(points: list[tuple[float, float, int]]) -> tuple[np.ndarray, np.ndarray]:
    ordered = sorted(points, key=lambda item: (item[0], item[2]))
    ts: list[float] = []
    values: list[float] = []
    for point_ts, value, _seq in ordered:
        if ts and abs(point_ts - ts[-1]) < 1e-9:
            values[-1] = float(value)
        else:
            ts.append(float(point_ts))
            values.append(float(value))
    return np.asarray(ts, dtype=float), np.asarray(values, dtype=float)


def _disorder_rate(points: list[tuple[float, float, int]]) -> float:
    """Fraction of consecutive capture-order rows whose timestamp goes backwards."""
    if len(points) < 2:
        return 0.0
    by_seq = sorted(points, key=lambda item: item[2])
    inversions = 0
    for previous, current in zip(by_seq, by_seq[1:]):
        if current[0] < previous[0] - 1e-9:
            inversions += 1
    return inversions / (len(by_seq) - 1)


def bucketize(
    ts: np.ndarray,
    values: np.ndarray,
    t0: float,
    grid_s: int,
    agg: str,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Return (bucket values with NaN for empty, observed mask, bucket count)."""
    if ts.size == 0:
        return np.asarray([]), np.asarray([], dtype=bool), 0
    bucket_count = int(math.floor((ts[-1] - t0) / grid_s)) + 1
    bucket_count = max(bucket_count, 1)
    sums = np.zeros(bucket_count, dtype=float)
    counts = np.zeros(bucket_count, dtype=int)
    last_values = np.full(bucket_count, np.nan)
    indices = np.floor((ts - t0) / grid_s).astype(int)
    indices = np.clip(indices, 0, bucket_count - 1)
    for index, value in zip(indices, values):
        sums[index] += value
        counts[index] += 1
        last_values[index] = value
    aggregated = np.full(bucket_count, np.nan)
    has_data = counts > 0
    if agg == AggStrategy.LAST.value:
        aggregated[has_data] = last_values[has_data]
    else:
        aggregated[has_data] = sums[has_data] / counts[has_data]
    if agg == AggStrategy.LINEAR.value:
        known = np.where(~np.isnan(aggregated))[0]
        if known.size >= 2:
            interpolated = np.interp(np.arange(bucket_count), known, aggregated[known])
            aggregated = np.where(np.isnan(aggregated), interpolated, aggregated)
    return aggregated, has_data, bucket_count


def _cubic_eval(ts: np.ndarray, values: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Catmull-Rom cubic interpolation, used for the sub-sample drift search."""
    if ts.size < 2:
        return np.full_like(x, values[0] if values.size else 0.0)
    slopes = np.empty_like(values)
    slopes[0] = (values[1] - values[0]) / (ts[1] - ts[0])
    slopes[-1] = (values[-1] - values[-2]) / (ts[-1] - ts[-2])
    if values.size > 2:
        slopes[1:-1] = (values[2:] - values[:-2]) / (ts[2:] - ts[:-2])
    index = np.clip(np.searchsorted(ts, x) - 1, 0, ts.size - 2)
    t0 = ts[index]
    t1 = ts[index + 1]
    h = t1 - t0
    t = (x - t0) / h
    return (
        (2 * t**3 - 3 * t**2 + 1) * values[index]
        + (t**3 - 2 * t**2 + t) * h * slopes[index]
        + (-2 * t**3 + 3 * t**2) * values[index + 1]
        + (t**3 - t**2) * h * slopes[index + 1]
    )


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 8 or b.size < 8:
        return 0.0
    a_std = float(np.std(a))
    b_std = float(np.std(b))
    if a_std < 1e-12 or b_std < 1e-12:
        return 0.0
    a_norm = (a - a.mean()) / a_std
    b_norm = (b - b.mean()) / b_std
    return float(np.mean(a_norm * b_norm))


def estimate_pair_drift(
    ts_a: np.ndarray,
    value_a: np.ndarray,
    ts_b: np.ndarray,
    value_b: np.ndarray,
) -> tuple[float, float]:
    """Cross-correlate two series; return (lag_ms of B relative to A, peak correlation).

    Positive lag means series B's timestamps are ahead of A (B reports later).
    """
    if ts_a.size < 10 or ts_b.size < 10:
        return 0.0, 0.0
    lo = max(float(ts_a[0]), float(ts_b[0])) + 1.0
    hi = min(float(ts_a[-1]), float(ts_b[-1])) - 1.0
    span = hi - lo
    if span < 120.0:
        return 0.0, 0.0
    coarse_step = LAG_STEP_S
    if span / coarse_step > COARSE_SAMPLE_LIMIT:
        coarse_step = span / COARSE_SAMPLE_LIMIT
    grid = np.arange(lo, hi, coarse_step)
    a = _cubic_eval(ts_a, value_a, grid)
    b = _cubic_eval(ts_b, value_b, grid)
    a_std = float(np.std(a)) or 1.0
    b_std = float(np.std(b)) or 1.0
    a = (a - a.mean()) / a_std
    b = (b - b.mean()) / b_std
    n = grid.size
    lags = np.arange(-MAX_LAG_S, MAX_LAG_S + 1e-9, LAG_STEP_S)
    scores = np.full(lags.size, np.nan)
    for k, lag in enumerate(lags):
        shift = int(round(lag / coarse_step))
        if shift >= 0:
            aa, bb = a[0 : n - shift], b[shift:n]
        else:
            aa, bb = a[-shift:n], b[0 : n + shift]
        if aa.size < MIN_OVERLAP_RATIO * n:
            continue
        scores[k] = _pearson(aa, bb)
    valid = np.where(~np.isnan(scores))[0]
    if valid.size == 0:
        return 0.0, 0.0
    best = valid[int(np.argmax(np.abs(scores[valid])))]
    coarse_lag = float(lags[best])
    # sub-sample refinement on a 5 ms interpolation grid around the coarse peak
    fine_lo = coarse_lag - 0.5
    fine_hi = coarse_lag + 0.5
    fine_grid = np.arange(lo, hi, FINE_STEP_S)
    a_fine = _cubic_eval(ts_a, value_a, fine_grid)
    b_fine = _cubic_eval(ts_b, value_b, fine_grid)
    a_fine = (a_fine - a_fine.mean()) / (float(np.std(a_fine)) or 1.0)
    b_fine = (b_fine - b_fine.mean()) / (float(np.std(b_fine)) or 1.0)
    n_fine = fine_grid.size
    fine_lags = np.arange(fine_lo, fine_hi + 1e-12, FINE_STEP_S)
    fine_scores = np.full(fine_lags.size, -9.0)
    for k, lag in enumerate(fine_lags):
        shift = int(round(lag / FINE_STEP_S))
        if shift >= 0:
            aa, bb = a_fine[0 : n_fine - shift], b_fine[shift:n_fine]
        else:
            aa, bb = a_fine[-shift:n_fine], b_fine[0 : n_fine + shift]
        if aa.size < 0.5 * n_fine:
            continue
        fine_scores[k] = _pearson(aa, bb)
    refined = float(fine_lags[int(np.argmax(fine_scores))]) if fine_scores.size else coarse_lag
    peak = float(np.max(fine_scores)) if fine_scores.size else float(np.max(scores))
    return refined * 1000.0, max(0.0, peak)


def _estimate_source_drift(signals: list[SignalInput]) -> tuple[list[dict], float]:
    prepared: dict[int, list[tuple[SignalInput, np.ndarray, np.ndarray]]] = {}
    for signal in signals:
        ts, values = _sort_and_dedupe(signal.points)
        if ts.size >= 2:
            prepared.setdefault(signal.source_id, []).append((signal, ts, values))
    if not prepared:
        return [], 0.0
    source_ids = sorted(prepared.keys())
    reference = source_ids[0]
    drift: dict[int, float] = {sid: 0.0 for sid in source_ids}
    confidence: dict[int, float] = {sid: 0.0 for sid in source_ids}
    for other in source_ids[1:]:
        weighted_sum = 0.0
        weight_total = 0.0
        best_r = 0.0
        candidates: list[tuple[float, float, float]] = []
        for signal_ref, ts_ref, val_ref in prepared[reference]:
            for signal_other, ts_other, val_other in prepared[other]:
                if signal_ref.device_code != signal_other.device_code:
                    continue
                # the same physical measurement is collected redundantly by both
                # gateways in this plant, so same-name pairs are the primary evidence
                same_measure = signal_ref.measure_name == signal_other.measure_name
                lag_ms, corr = estimate_pair_drift(ts_ref, val_ref, ts_other, val_other)
                if corr <= 0:
                    continue
                candidates.append((lag_ms, corr, 1.0 if same_measure else 0.35))
        if not candidates:
            continue
        same_measure_exists = any(item[2] == 1.0 for item in candidates)
        for lag_ms, corr, kind_weight in candidates:
            if same_measure_exists and kind_weight < 1.0:
                continue
            weight = (corr**6) * kind_weight
            weighted_sum += lag_ms * weight
            weight_total += weight
            best_r = max(best_r, corr)
        if weight_total > 0:
            drift[other] = weighted_sum / weight_total
            confidence[other] = best_r
    result = [
        {
            "source_id": sid,
            "source_code": next(
                (s.source_code for s, _ts, _v in prepared[sid]),
                "",
            ),
            "drift_ms": round(drift.get(sid, 0.0), 1),
            "confidence": round(confidence.get(sid, 0.0), 3),
        }
        for sid in source_ids
    ]
    max_conf = max((item["confidence"] for item in result), default=0.0)
    return result, max_conf


def align_job(
    signals: list[SignalInput],
    window_start: float,
    window_end: float,
    grid_s: int,
    agg: str,
) -> AlignResult:
    if grid_s not in GRID_CHOICES:
        raise ValueError(f"grid_s must be one of {GRID_CHOICES}")
    if agg not in tuple(item.value for item in AggStrategy):
        raise ValueError("unsupported aggregation strategy")

    filtered: list[SignalInput] = []
    disorder_values: list[float] = []
    for signal in signals:
        window_points = [p for p in signal.points if window_start <= p[0] <= window_end]
        copy = SignalInput(
            signal_id=signal.signal_id,
            signal_code=signal.signal_code,
            device_code=signal.device_code,
            device_name=signal.device_name,
            measure_name=signal.measure_name,
            unit=signal.unit,
            source_id=signal.source_id,
            source_code=signal.source_code,
            points=window_points,
        )
        filtered.append(copy)
        disorder_values.append(_disorder_rate(signal.points))

    total_points = sum(len(item.points) for item in filtered)
    disorder_rate = float(np.mean(disorder_values)) if disorder_values else 0.0

    prepared = []
    for signal in filtered:
        ts, values = _sort_and_dedupe(signal.points)
        prepared.append((signal, ts, values))
    all_ts = np.concatenate([ts for _s, ts, _v in prepared]) if prepared else np.asarray([])

    if all_ts.size == 0:
        return AlignResult(
            grid_s=grid_s,
            t0=0.0,
            point_count=0,
            bucket_count=0,
            coverage=0.0,
            disorder_rate=disorder_rate,
            signals=[],
            drift=[],
            drift_confidence=0.0,
            failure=FailureReason.INSUFFICIENT_DATA.value,
            failure_detail={
                "reason": "窗口内没有任何原始点，无法建立对齐网格",
                "point_count": 0,
            },
        )

    t0 = float(np.min(all_ts))
    total_buckets = 0
    observed_buckets = 0
    signal_payloads: list[dict] = []
    for signal, ts, values in prepared:
        # each signal is bucketed from its own first sample, so an offset capture
        # start does not masquerade as leading empty buckets (gaps stay real dropouts)
        signal_t0 = float(ts[0])
        bucket_values, observed, bucket_count = bucketize(ts, values, signal_t0, grid_s, agg)
        total_buckets += bucket_count
        observed_buckets += int(observed.sum())
        signal_payloads.append(
            {
                "signal_id": signal.signal_id,
                "signal_code": signal.signal_code,
                "device_code": signal.device_code,
                "device_name": signal.device_name,
                "measure_name": signal.measure_name,
                "unit": signal.unit,
                "source_id": signal.source_id,
                "source_code": signal.source_code,
                "start_ts": round(float(ts[0]), 3) if ts.size else None,
                "first_ts": round(float(ts[0]), 3) if ts.size else None,
                "last_ts": round(float(ts[-1]), 3) if ts.size else None,
                "point_count": int(ts.size),
                "bucket_count": bucket_count,
                "coverage": round(float(observed.sum()) / bucket_count, 6) if bucket_count else 0.0,
                "values": [None if math.isnan(v) else round(float(v), 4) for v in bucket_values],
                "observed": observed.tolist(),
            }
        )

    coverage = observed_buckets / total_buckets if total_buckets else 0.0
    drift, drift_confidence = _estimate_source_drift(filtered)
    failure = None
    failure_detail: dict = {}
    if total_points < 0.1 * total_buckets:
        failure = FailureReason.INSUFFICIENT_DATA.value
        failure_detail = {
            "reason": "窗口内点数不足网格桶数的 10%",
            "point_count": total_points,
            "bucket_count": total_buckets,
        }
    elif disorder_rate > 0.30:
        failure = FailureReason.TIMESTAMP_DISORDER.value
        failure_detail = {
            "reason": "时间戳乱序率超过 30%",
            "disorder_rate": round(disorder_rate, 4),
        }

    payloads = []
    for item in signal_payloads:
        cleaned = dict(item)
        cleaned.pop("values", None)
        cleaned.pop("observed", None)
        payloads.append(cleaned)

    return AlignResult(
        grid_s=grid_s,
        t0=round(t0, 3),
        point_count=total_points,
        bucket_count=total_buckets,
        coverage=coverage,
        disorder_rate=disorder_rate,
        signals=signal_payloads,
        drift=drift,
        drift_confidence=drift_confidence,
        failure=failure,
        failure_detail=failure_detail,
    )


def summarize_signals(result: AlignResult) -> list[dict]:
    """Small per-signal projection for list/detail API responses."""
    out = []
    for signal in result.signals:
        out.append(
            {
                "signal_id": signal["signal_id"],
                "signal_code": signal["signal_code"],
                "device_code": signal["device_code"],
                "measure_name": signal["measure_name"],
                "unit": signal["unit"],
                "source_code": signal["source_code"],
                "bucket_count": signal["bucket_count"],
                "coverage": signal["coverage"],
                "point_count": signal["point_count"],
            }
        )
    return out
