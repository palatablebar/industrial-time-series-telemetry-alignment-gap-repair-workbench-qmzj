"""Deterministic synthetic telemetry for the TSALIGN demo scene.

Kept free of database / FastAPI imports so the two Python engines and the
seeded numbers can be exercised (and unit-checked) in plain Python.
"""
from __future__ import annotations

import math
from datetime import datetime

import numpy as np

from src.constants.enums import AggStrategy, FillStrategy, JobStatus, SourceProtocol
from src.constants.messages import DEMO_PASSWORD
from src.services.align_engine import SignalInput, align_job
from src.services.gap_engine import analyze as analyze_gaps
from src.utils.timeutil import to_epoch

LOCAL_TZ_OFFSET = 8 * 3600
BASE_DATETIME = datetime(2026, 11, 10, 8, 0, 0)
BASE_EPOCH = to_epoch(BASE_DATETIME)
CYCLE_S = 80.0
POINTS_PER_SIGNAL = 480
DEFAULT_PASSWORD = DEMO_PASSWORD

SEED_SOURCES = [
    {
        "code": "GW-CHZ-01",
        "name": "常州一厂 1# 采集网关",
        "protocol": SourceProtocol.OPCUA.value,
        "sample_interval_s": 1,
        "timezone": "Asia/Shanghai",
        "drift_hint_ms": 0,
        "status": "online",
        "workshop": "注塑一车间",
        "description": "1s 扫描、OPC-UA 直连；作为全厂时钟基准源，最近一次对时偏差 0ms。",
    },
    {
        "code": "GW-CHZ-02",
        "name": "常州一厂 2# 采集网关",
        "protocol": SourceProtocol.DCS.value,
        "sample_interval_s": 5,
        "timezone": "Asia/Shanghai",
        "drift_hint_ms": 312,
        "status": "drift_warning",
        "workshop": "注塑一车间",
        "description": "5s 扫描、DCS 历史站导出；近 7 天与基准源互相关稳定在 +312ms，需在分析前校正。",
    },
    {
        "code": "GW-CHZ-03",
        "name": "常州二厂 3# 采集网关",
        "protocol": SourceProtocol.OPCUA.value,
        "sample_interval_s": 10,
        "timezone": "Asia/Shanghai",
        "drift_hint_ms": -180,
        "status": "online",
        "workshop": "注塑二车间",
        "description": "10s 扫描、OPC-UA 批量上报；时钟偏移约 -180ms，在容差内仅做提示。",
    },
]

# code, source, device, device_name, measure, tag, unit, cadence, base, scale, phase, hi, holes, drops, shuffle_seq, seq_seed
SEED_SIGNALS = [
    {
        "code": "M-07.VIB-X",
        "source": "GW-CHZ-01",
        "device_code": "M-07",
        "device_name": "M-07 注塑机（海天 MA2100）",
        "measure_name": "主轴振动 X",
        "tag_path": "M07/SPINDLE/VIB_X",
        "unit": "mm/s",
        "cadence": 5.0,
        "offset_ms": 0,
        "base": 1.15,
        "scale": 3.4,
        "phase_s": 0.0,
        "hi": 0.26,
        "holes": [],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 101,
    },
    {
        "code": "M-07.VIB-X-GW2",
        "source": "GW-CHZ-02",
        "device_code": "M-07",
        "device_name": "M-07 注塑机（海天 MA2100）",
        "measure_name": "主轴振动 X",
        "tag_path": "M07/SPINDLE/VIB_X",
        "unit": "mm/s",
        "cadence": 5.0,
        "offset_ms": 312,
        "base": 1.15,
        "scale": 3.4,
        "phase_s": 0.0,
        "hi": 0.26,
        "holes": [],
        "drops": [],
        "extra_points": 0,
        "noise": 0.004,
        "rng_seed": 102,
    },
    {
        "code": "M-07.CUR",
        "source": "GW-CHZ-02",
        "device_code": "M-07",
        "device_name": "M-07 注塑机（海天 MA2100）",
        "measure_name": "主轴电流",
        "tag_path": "M07/SPINDLE/CURRENT",
        "unit": "A",
        "cadence": 5.0,
        "offset_ms": 312,
        "base": 42.0,
        "scale": 120.0,
        "phase_s": 0.0,
        "hi": 0.2545,
        "holes": [(300.0, 330.0), (600.0, 625.0), (900.0, 910.0), (1200.0, 1220.0)],
        "drops": [1000.0, 1100.0, 1300.0, 1500.0, 1600.0, 1800.0, 1900.0, 2100.0, 2300.0],
        "extra_points": 0,
        "noise": 0.004,
        "rng_seed": 103,
    },
    {
        "code": "M-08.OIL-TEMP",
        "source": "GW-CHZ-01",
        "device_code": "M-08",
        "device_name": "M-08 注塑机（海天 MA1600）",
        "measure_name": "液压油温",
        "tag_path": "M08/HYD/OIL_TEMP",
        "unit": "℃",
        "cadence": 1.0,
        "offset_ms": 0,
        "base": 46.0,
        "scale": 8.0,
        "phase_s": 11.0,
        "hi": 0.28,
        "holes": [(60.0, 72.0), (180.0, 195.0), (90.0, 93.0)],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 201,
        "extra_points": 17,
    },
    {
        "code": "M-08.PRESS",
        "source": "GW-CHZ-02",
        "device_code": "M-08",
        "device_name": "M-08 注塑机（海天 MA1600）",
        "measure_name": "液压压力",
        "tag_path": "M08/HYD/PRESS",
        "unit": "MPa",
        "cadence": 5.0,
        "offset_ms": 312,
        "base": 12.4,
        "scale": 6.0,
        "phase_s": 11.0,
        "hi": 0.28,
        "holes": [(1200.0, 1215.0)],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 202,
        "extra_points": 17,
    },
    {
        "code": "M-09.VIB-X",
        "source": "GW-CHZ-02",
        "device_code": "M-09",
        "device_name": "M-09 注塑机（震雄 SM1800）",
        "measure_name": "锁模振动 X",
        "tag_path": "M09/CLAMP/VIB_X",
        "unit": "mm/s",
        "cadence": 5.0,
        "offset_ms": 312,
        "base": 1.35,
        "scale": 2.8,
        "phase_s": 23.0,
        "hi": 0.28,
        "holes": [(1800.0, 1810.0)],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 301,
        "extra_points": 17,
    },
    {
        "code": "M-09.CUR",
        "source": "GW-CHZ-03",
        "device_code": "M-09",
        "device_name": "M-09 注塑机（震雄 SM1800）",
        "measure_name": "锁模电流",
        "tag_path": "M09/CLAMP/CURRENT",
        "unit": "A",
        "cadence": 10.0,
        "offset_ms": -180,
        "base": 96.0,
        "scale": 40.0,
        "phase_s": 23.0,
        "hi": 0.28,
        "holes": [],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 302,
        "extra_points": 17,
        "shuffle_seq": True,
    },
    {
        "code": "M-10.OIL-TEMP",
        "source": "GW-CHZ-01",
        "device_code": "M-10",
        "device_name": "M-10 注塑机（海天 MA2100）",
        "measure_name": "液压油温",
        "tag_path": "M10/HYD/OIL_TEMP",
        "unit": "℃",
        "cadence": 1.0,
        "offset_ms": 0,
        "base": 52.0,
        "scale": 9.0,
        "phase_s": 37.0,
        "hi": 0.28,
        "holes": [(60.0, 72.0), (180.0, 195.0), (300.0, 310.0)],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 401,
        "extra_points": 17,
    },
    {
        "code": "M-10.PRESS",
        "source": "GW-CHZ-03",
        "device_code": "M-10",
        "device_name": "M-10 注塑机（海天 MA2100）",
        "measure_name": "液压压力",
        "tag_path": "M10/HYD/PRESS",
        "unit": "MPa",
        "cadence": 10.0,
        "offset_ms": -180,
        "base": 8.6,
        "scale": 4.0,
        "phase_s": 37.0,
        "hi": 0.28,
        "holes": [(3000.0, 3020.0)],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 402,
        "extra_points": 17,
        "shuffle_seq": True,
    },
    {
        "code": "M-11.OIL-TEMP",
        "source": "GW-CHZ-01",
        "device_code": "M-11",
        "device_name": "M-11 注塑机（震雄 SM2200）",
        "measure_name": "液压油温",
        "tag_path": "M11/HYD/OIL_TEMP",
        "unit": "℃",
        "cadence": 1.0,
        "offset_ms": 0,
        "base": 58.0,
        "scale": 10.0,
        "phase_s": 51.0,
        "hi": 0.28,
        "holes": [(60.0, 72.0), (120.0, 130.0), (300.0, 310.0)],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 501,
        "extra_points": 17,
    },
    {
        "code": "M-11.VIB-X",
        "source": "GW-CHZ-02",
        "device_code": "M-11",
        "device_name": "M-11 注塑机（震雄 SM2200）",
        "measure_name": "射台振动 X",
        "tag_path": "M11/INJECT/VIB_X",
        "unit": "mm/s",
        "cadence": 5.0,
        "offset_ms": 312,
        "base": 1.05,
        "scale": 2.6,
        "phase_s": 51.0,
        "hi": 0.28,
        "holes": [(1200.0, 1215.0), (1800.0, 1810.0), (2100.0, 2115.0)],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 502,
        "extra_points": 17,
    },
    {
        "code": "M-12.CUR",
        "source": "GW-CHZ-03",
        "device_code": "M-12",
        "device_name": "M-12 注塑机（海天 MA1200）",
        "measure_name": "加热圈电流",
        "tag_path": "M12/HEAT/CURRENT",
        "unit": "A",
        "cadence": 10.0,
        "offset_ms": -180,
        "base": 88.0,
        "scale": 36.0,
        "phase_s": 65.0,
        "hi": 0.28,
        "holes": [],
        "drops": [],
        "noise": 0.004,
        "rng_seed": 601,
        "extra_points": 4,
        "shuffle_seq": True,
    },
]

SEED_JOBS = [
    {
        "key": "factory",
        "name": "全厂 12 测点夜间对齐 20261110",
        "device_codes": ["M-07", "M-08", "M-09", "M-10", "M-11", "M-12"],
        "window_start": BASE_DATETIME,
        "window_end": datetime(2026, 11, 10, 10, 30, 0),
        "grid_s": 5,
        "agg_strategy": AggStrategy.MEAN.value,
        "fill_strategy": FillStrategy.LINEAR.value,
        "status": JobStatus.COMPLETED.value,
        "note": "夜间批次：12 个测点跨 3 个网关统一到 5s 网格，作为当日质量基线。",
        "engineer": "engineer@tsalign.demo",
    },
    {
        "key": "historical",
        "name": "M-09 历史补数窗口 20261015",
        "device_codes": ["M-09"],
        "window_start": datetime(2026, 10, 15, 0, 0, 0),
        "window_end": datetime(2026, 10, 15, 6, 0, 0),
        "grid_s": 5,
        "agg_strategy": AggStrategy.LAST.value,
        "fill_strategy": FillStrategy.LOCF.value,
        "status": JobStatus.FAILED.value,
        "note": "历史 DCS 导出遗漏了该时段，任务按 insufficient_data 失败留痕。",
        "engineer": "engineer@tsalign.demo",
    },
    {
        "key": "no_gap",
        "name": "M-12 电流单点核查 20261110",
        "device_codes": ["M-12"],
        "window_start": BASE_DATETIME,
        "window_end": datetime(2026, 11, 10, 10, 30, 0),
        "grid_s": 5,
        "agg_strategy": AggStrategy.MEAN.value,
        "fill_strategy": FillStrategy.LOCF.value,
        "status": JobStatus.COMPLETED.value,
        "note": "单测点基线核查，无连续缺口，用于对照填补策略。",
        "engineer": "engineer@tsalign.demo",
    },
    {
        "key": "pending",
        "name": "M-10 周度网格预演 20261111",
        "device_codes": ["M-10"],
        "window_start": datetime(2026, 11, 11, 0, 0, 0),
        "window_end": datetime(2026, 11, 11, 6, 0, 0),
        "grid_s": 60,
        "agg_strategy": AggStrategy.MEAN.value,
        "fill_strategy": FillStrategy.SEASONAL_NAIVE.value,
        "status": JobStatus.PENDING.value,
        "note": "周度 60s 网格预演，等待车间确认后执行。",
        "engineer": "engineer@tsalign.demo",
    },
]


# --------------------------------------------------------------------------
# deterministic synthetic telemetry (the numbers in README/TESTING come from it)
# --------------------------------------------------------------------------
def _load_envelope(ts: np.ndarray, hi: float) -> np.ndarray:
    """80s injection-cycle load envelope with a ~25% high plateau."""
    phase = (ts % CYCLE_S) / CYCLE_S
    ramp = 0.8 / CYCLE_S
    up = np.clip(phase / ramp, 0.0, 1.0)
    down = np.clip((hi - phase) / ramp, 0.0, 1.0)
    bump = np.minimum(up, down)
    bump = bump * bump * (3 - 2 * bump)
    low = (
        0.14
        + 0.05 * np.sin(2 * math.pi * ts / 37.0)
        + 0.03 * np.sin(2 * math.pi * ts / 23.0)
    )
    return low + (0.95 - low) * bump


def _generate_signal(spec: dict) -> list[tuple[float, float, int]]:
    """Always returns exactly POINTS_PER_SIGNAL rows: dropped samples are compensated
    by extending the capture window, so ``12 × 480 = 5,760`` raw rows hold."""
    rng = np.random.default_rng(spec["rng_seed"])
    cadence = float(spec["cadence"])
    phase = float(spec["phase_s"])

    def is_dropped(elapsed: float) -> bool:
        for hole_start, hole_end in spec["holes"]:
            if hole_start <= elapsed < hole_end:
                return True
        for drop_time in spec["drops"]:
            if abs(elapsed - drop_time) < 1e-6:
                return True
        return False

    count = POINTS_PER_SIGNAL + int(spec.get("extra_points", 0))
    true_t = np.arange(count, dtype=float) * cadence + phase
    # nearly-zero jitter that is pinned to 0 on the first sample: the earliest sample
    # of the whole job then anchors t0 and every sample stays inside its nominal bucket
    offsets = (spec["offset_ms"] / 1000.0) + rng.uniform(0.0, 0.02, count)
    offsets[0] = spec["offset_ms"] / 1000.0
    timestamps = BASE_EPOCH + true_t + offsets
    keep = np.ones(count, dtype=bool)
    for index in range(count):
        if is_dropped(index * cadence):
            keep[index] = False
    envelope = _load_envelope(true_t, spec["hi"])
    values = spec["base"] + spec["scale"] * envelope + rng.normal(0.0, spec["noise"], count) * spec["scale"]
    rows: list[tuple[float, float, int]] = []
    for index in range(count):
        if not keep[index]:
            continue
        rows.append((round(float(timestamps[index]), 4), round(float(values[index]), 5), index))
    if spec.get("shuffle_seq"):
        swap_rng = np.random.default_rng(spec["rng_seed"] + 7000)
        order = list(range(len(rows)))
        for _ in range(max(1, len(rows) // 40)):
            a = int(swap_rng.integers(0, len(rows)))
            b = int(swap_rng.integers(0, len(rows)))
            order[a], order[b] = order[b], order[a]
        rows = [(rows[order[position]][0], rows[order[position]][1], position) for position in range(len(rows))]
    return rows


def build_seed_series() -> dict[str, list[tuple[float, float, int]]]:
    return {spec["code"]: _generate_signal(spec) for spec in SEED_SIGNALS}


def _signals_input(
    series: dict[str, list[tuple[float, float, int]]], codes: list[str]
) -> list[SignalInput]:
    by_code = {spec["code"]: spec for spec in SEED_SIGNALS}
    payloads = []
    for code in codes:
        spec = by_code[code]
        payloads.append(
            SignalInput(
                signal_id=list(by_code).index(code) + 1,
                signal_code=code,
                device_code=spec["device_code"],
                device_name=spec["device_name"],
                measure_name=spec["measure_name"],
                unit=spec["unit"],
                source_id=SEED_SOURCES.index(next(s for s in SEED_SOURCES if s["code"] == spec["source"])) + 1,
                source_code=spec["source"],
                points=series[code],
            )
        )
    return payloads


def compute_seed_results(series: dict[str, list[tuple[float, float, int]]]) -> list[dict]:
    """Run the real engines for seeded jobs (deterministic, no DB)."""
    results = []
    for job in SEED_JOBS:
        codes = [spec["code"] for spec in SEED_SIGNALS if spec["device_code"] in job["device_codes"]]
        window_start = to_epoch(job["window_start"])
        window_end = to_epoch(job["window_end"])
        aligned = align_job(
            _signals_input(series, codes),
            window_start=window_start,
            window_end=window_end,
            grid_s=int(job["grid_s"]),
            agg=job["agg_strategy"],
        )
        result = aligned.to_dict()
        if job["key"] == "pending":
            results.append({"job": job, "codes": codes, "aligned": result, "gaps": None})
            continue
        if aligned.failure:
            results.append({"job": job, "codes": codes, "aligned": result, "gaps": None})
            continue
        gap_result = analyze_gaps(result, job["fill_strategy"])
        results.append({"job": job, "codes": codes, "aligned": result, "gaps": gap_result})
    return results


