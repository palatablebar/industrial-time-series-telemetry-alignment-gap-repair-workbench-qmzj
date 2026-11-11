"""A. 时间对齐与重采样引擎（真算，无第三方时序库依赖）。

夜间离线合并口径（本版修订，替代旧的「各信号从自己的起点分箱」）：

输入：多网关回传的不规则时间戳原始点 ``(ts_epoch, value, seq)``，每个信号带
``device_code / measure_name / source_id``。处理顺序固定为：

  1. 窗口过滤、按时间戳排序去重（同 ts 保留 seq 最大者）、乱序率检查；
  2. 时钟漂移估计：同一设备、同一物理量（measure_name 相同）被多个网关冗余
     采集的信号两两互相关，±60s 内 250ms 粗扫、峰值附近 5ms 细化，重叠率
     不足 75% 的 lag 不计分；按相关系数高次幂加权得到每源 ``drift_ms``；
  3. 时钟校正：以漂移绝对值最小的源为锚，``校正后 ts = 原始 ts - drift``，
     每个源的校正量随结果一并落库，可回看；
  4. 统一观测网格：网格原点对齐到墙上时钟的整 ``grid_s`` 边界，所有通道共用
     同一张网格 ``bucket = floor((校正后 ts - t0) / grid_s)``，跨设备可比；
  5. 通道合并：按 (设备, 物理量) 归并多网关成员，桶内按策略聚合；多源重叠桶
     优先采用校正量绝对值最小的源，逐桶记录采用来源与全部贡献源（overlaps）；
  6. 观测掩码与展示值分离：linear 的插值只进展示值，观测掩码仍以真实回传为准，
     网关掉线形成的空档不会被填补值伪装成观测。

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
    channels: list[dict]
    drift: list[dict]
    drift_confidence: float
    corrections: list[dict]
    overlaps: list[dict]
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
            "channels": self.channels,
            "drift": self.drift,
            "drift_confidence": round(self.drift_confidence, 4),
            "corrections": self.corrections,
            "overlaps": self.overlaps,
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


def _estimate_source_drift(
    signals: list[SignalInput],
) -> tuple[list[dict], dict[int, float], float]:
    """Estimate per-source clock drift from redundant (same device + same measure) pairs.

    Returns the drift table, a source_id -> drift_ms map, and the max confidence.
    Only same-physical-quantity pairs are evidence: unlike measures have different
    response shapes and must not pull the clock estimate.
    """
    prepared: dict[int, list[tuple[SignalInput, np.ndarray, np.ndarray]]] = {}
    for signal in signals:
        ts, values = _sort_and_dedupe(signal.points)
        if ts.size >= 2:
            prepared.setdefault(signal.source_id, []).append((signal, ts, values))
    source_ids = sorted(prepared.keys())
    if not source_ids:
        return [], {}, 0.0
    reference = source_ids[0]
    raw_drift: dict[int, float] = {sid: 0.0 for sid in source_ids}
    confidence: dict[int, float] = {sid: 0.0 for sid in source_ids}
    evidence: dict[int, list[dict]] = {sid: [] for sid in source_ids}

    for other in source_ids[1:]:
        weighted_sum = 0.0
        weight_total = 0.0
        best_r = 0.0
        for signal_ref, ts_ref, val_ref in prepared[reference]:
            for signal_other, ts_other, val_other in prepared[other]:
                if signal_ref.device_code != signal_other.device_code:
                    continue
                if signal_ref.measure_name != signal_other.measure_name:
                    continue
                lag_ms, corr = estimate_pair_drift(ts_ref, val_ref, ts_other, val_other)
                if corr <= 0:
                    continue
                evidence[other].append(
                    {
                        "reference_signal": signal_ref.signal_code,
                        "peer_signal": signal_other.signal_code,
                        "peer_source": signal_other.source_code,
                        "lag_ms": round(lag_ms, 1),
                        "correlation": round(corr, 4),
                    }
                )
                weight = corr**6
                weighted_sum += lag_ms * weight
                weight_total += weight
                best_r = max(best_r, corr)
        if weight_total > 0:
            raw_drift[other] = weighted_sum / weight_total
            confidence[other] = best_r

    # anchor = the reference clock: source_ids[0] is the lowest-id source and acts
    # as the plant time base (its own drift is defined as zero; other sources are
    # estimated against it). All corrections are expressed relative to this anchor.
    anchor = reference
    anchor_shift = raw_drift[anchor]
    drift_ms: dict[int, float] = {sid: raw_drift[sid] - anchor_shift for sid in source_ids}

    source_code_by_id = {
        sid: next(s.source_code for s, _ts, _v in prepared[sid]) for sid in source_ids
    }
    table = [
        {
            "source_id": sid,
            "source_code": source_code_by_id[sid],
            "drift_ms": round(drift_ms[sid], 1) + 0.0,
            "confidence": round(confidence[sid], 3),
            "is_anchor": sid == anchor,
            "is_estimated": confidence[sid] > 0 or sid == anchor,
            "correction_ms": round(-(drift_ms[sid]), 1) + 0.0,
            "evidence": evidence[sid],
        }
        for sid in source_ids
    ]
    max_conf = max((item["confidence"] for item in table), default=0.0)
    return table, drift_ms, max_conf


def _member_buckets(
    ts: np.ndarray,
    values: np.ndarray,
    t0: float,
    grid_s: int,
) -> dict[int, dict[str, float]]:
    """Aggregate one gateway member onto the shared grid: bucket -> sum/count/last."""
    buckets: dict[int, dict[str, float]] = {}
    indices = np.floor((ts - t0) / grid_s).astype(int)
    for index, value in zip(indices, values):
        entry = buckets.get(int(index))
        if entry is None:
            buckets[int(index)] = {"sum": float(value), "count": 1.0, "last": float(value)}
        else:
            entry["sum"] += float(value)
            entry["count"] += 1.0
            entry["last"] = float(value)
    return buckets


def _build_channel(
    members: list[tuple[SignalInput, np.ndarray, np.ndarray]],
    t0: float,
    grid_s: int,
    agg: str,
    drift_by_source: dict[int, float],
) -> tuple[dict, dict]:
    """Merge redundant gateway members of one (device, measure) channel on the grid."""
    per_member: list[dict] = []
    bucket_lo = math.inf
    bucket_hi = -math.inf
    for signal, ts, values in members:
        member_buckets = _member_buckets(ts, values, t0, grid_s)
        if member_buckets:
            bucket_lo = min(bucket_lo, min(member_buckets))
            bucket_hi = max(bucket_hi, max(member_buckets))
        per_member.append({"signal": signal, "buckets": member_buckets})

    length = int(bucket_hi - bucket_lo) + 1
    raw_values = np.full(length, np.nan)
    observed = np.zeros(length, dtype=bool)
    provenance: list[str] = ["" for _ in range(length)]
    contributors: list[list[str]] = [[] for _ in range(length)]
    source_bucket_counts: dict[str, int] = {}
    source_selected_counts: dict[str, int] = {}
    overlap_events: list[dict] = []

    for slot in range(length):
        bucket = bucket_lo + slot
        candidates: list[tuple[float, int, str, dict, SignalInput]] = []
        present_sources: list[str] = []
        for item in per_member:
            entry = item["buckets"].get(bucket)
            if entry is None:
                continue
            signal = item["signal"]
            candidates.append(
                (
                    abs(drift_by_source.get(signal.source_id, 0.0)),
                    signal.source_id,
                    signal.source_code,
                    entry,
                    signal,
                )
            )
            present_sources.append(signal.source_code)
            source_bucket_counts[signal.source_code] = source_bucket_counts.get(signal.source_code, 0) + 1
        if not candidates:
            continue
        observed[slot] = True
        contributors[slot] = present_sources
        candidates.sort(key=lambda c: (c[0], c[1]))
        _preference, _sid, chosen_source, entry, chosen_signal = candidates[0]
        if agg == AggStrategy.LAST.value:
            raw_values[slot] = entry["last"]
        else:
            raw_values[slot] = entry["sum"] / entry["count"]
        provenance[slot] = chosen_source
        source_selected_counts[chosen_source] = source_selected_counts.get(chosen_source, 0) + 1
        if len(present_sources) >= 2:
            overlap_events.append(
                {
                    "bucket": int(bucket),
                    "start_ts": round(t0 + bucket * grid_s, 3),
                    "end_ts": round(t0 + (bucket + 1) * grid_s, 3),
                    "sources": present_sources,
                    "selected_source": chosen_source,
                    "selected_signal": chosen_signal.signal_code,
                }
            )

    display_values = raw_values.copy()
    if agg == AggStrategy.LINEAR.value:
        known = np.where(~np.isnan(display_values))[0]
        if known.size >= 2:
            interpolated = np.interp(np.arange(length), known, display_values[known])
            display_values = np.where(np.isnan(display_values), interpolated, display_values)

    anchor = min(
        (item["signal"] for item in per_member),
        key=lambda s: (abs(drift_by_source.get(s.source_id, 0.0)), s.source_id),
    )
    start_ts = t0 + bucket_lo * grid_s
    payload = {
        "signal_id": anchor.signal_id,
        "signal_code": anchor.signal_code,
        "device_code": anchor.device_code,
        "device_name": anchor.device_name,
        "measure_name": anchor.measure_name,
        "unit": anchor.unit,
        "source_id": anchor.source_id,
        "source_code": anchor.source_code,
        "member_signal_ids": [item["signal"].signal_id for item in per_member],
        "member_signal_codes": [item["signal"].signal_code for item in per_member],
        "source_codes": sorted({item["signal"].source_code for item in per_member}),
        "start_ts": round(start_ts, 3),
        "first_ts": round(start_ts, 3),
        "last_ts": round(t0 + bucket_hi * grid_s, 3),
        "point_count": int(sum(len(item["signal"].points) for item in per_member)),
        "bucket_count": length,
        "coverage": round(float(observed.sum()) / length, 6) if length else 0.0,
        "values": [None if math.isnan(v) else round(float(v), 4) for v in display_values],
        "raw_values": [None if math.isnan(v) else round(float(v), 4) for v in raw_values],
        "observed": observed.tolist(),
        "provenance": provenance,
        "contributors": contributors,
    }
    overlap_payload = {
        "signal_code": anchor.signal_code,
        "device_code": anchor.device_code,
        "measure_name": anchor.measure_name,
        "overlap_buckets": len(overlap_events),
        "source_buckets": [
            {"source_code": code, "buckets": source_bucket_counts.get(code, 0),
             "selected_buckets": source_selected_counts.get(code, 0)}
            for code in sorted(source_bucket_counts)
        ],
        "events": overlap_events,
    }
    return payload, overlap_payload


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

    if total_points == 0:
        return AlignResult(
            grid_s=grid_s,
            t0=0.0,
            point_count=0,
            bucket_count=0,
            coverage=0.0,
            disorder_rate=disorder_rate,
            channels=[],
            drift=[],
            drift_confidence=0.0,
            corrections=[],
            overlaps=[],
            failure=FailureReason.INSUFFICIENT_DATA.value,
            failure_detail={
                "reason": "窗口内没有任何原始点，无法建立对齐网格",
                "point_count": 0,
            },
        )

    # step 1-3: drift evidence is taken on the raw (uncorrected) timestamps
    drift_table, drift_by_source, drift_confidence = _estimate_source_drift(filtered)
    corrections = [
        {
            "source_id": item["source_id"],
            "source_code": item["source_code"],
            "drift_ms": item["drift_ms"],
            "correction_ms": item["correction_ms"],
            "confidence": item["confidence"],
            "is_anchor": item["is_anchor"],
        }
        for item in drift_table
    ]

    # step 3 (cont.): correct every gateway clock onto the anchor timeline
    corrected: list[tuple[SignalInput, np.ndarray, np.ndarray]] = []
    corrected_ts_all: list[np.ndarray] = []
    for signal in filtered:
        ts, values = _sort_and_dedupe(signal.points)
        if ts.size == 0:
            continue
        shift_s = drift_by_source.get(signal.source_id, 0.0) / 1000.0
        ts_corrected = ts - shift_s
        corrected.append((signal, ts_corrected, values))
        corrected_ts_all.append(ts_corrected)

    # step 4: one shared, wall-clock-aligned grid for every device / measure
    earliest = float(min(arr[0] for arr in corrected_ts_all))
    t0 = math.floor(earliest / grid_s) * grid_s

    # step 5: group by physical channel (device + measure), merge gateway members
    groups: dict[tuple[str, str], list[tuple[SignalInput, np.ndarray, np.ndarray]]] = {}
    for signal, ts_corrected, values in corrected:
        groups.setdefault((signal.device_code, signal.measure_name), []).append(
            (signal, ts_corrected, values)
        )

    channel_payloads: list[dict] = []
    overlap_payloads: list[dict] = []
    total_buckets = 0
    observed_buckets = 0
    for key in sorted(groups.keys()):
        members = sorted(groups[key], key=lambda item: (item[0].source_id, item[0].signal_id))
        payload, overlap_payload = _build_channel(members, t0, grid_s, agg, drift_by_source)
        total_buckets += payload["bucket_count"]
        observed_buckets += int(sum(payload["observed"]))
        channel_payloads.append(payload)
        if overlap_payload["overlap_buckets"] > 0:
            overlap_payloads.append(overlap_payload)

    coverage = observed_buckets / total_buckets if total_buckets else 0.0
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

    return AlignResult(
        grid_s=grid_s,
        t0=round(t0, 3),
        point_count=total_points,
        bucket_count=total_buckets,
        coverage=coverage,
        disorder_rate=disorder_rate,
        channels=channel_payloads,
        drift=drift_table,
        drift_confidence=drift_confidence,
        corrections=corrections,
        overlaps=overlap_payloads,
        failure=failure,
        failure_detail=failure_detail,
    )
