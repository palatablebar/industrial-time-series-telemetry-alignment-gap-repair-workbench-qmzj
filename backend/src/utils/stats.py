"""Robust statistics used by the gap engine (median / MAD based z-score)."""
import numpy as np


def median_mad(values: np.ndarray) -> tuple[float, float]:
    clean = values[~np.isnan(values)]
    if clean.size == 0:
        return 0.0, 0.0
    median = float(np.median(clean))
    mad = float(np.median(np.abs(clean - median)) * 1.4826)
    if mad < 1e-9:
        mad = float(np.std(clean)) or 1e-9
    return median, mad


def robust_z(values: np.ndarray) -> np.ndarray:
    median, mad = median_mad(values)
    return 0.6745 * (values - median) / mad


def anomaly_flags(values: np.ndarray, threshold: float = 3.0) -> tuple[int, int]:
    mask = ~np.isnan(values)
    total = int(mask.sum())
    if total == 0:
        return 0, 0
    z = robust_z(values[mask])
    return int((np.abs(z) > threshold).sum()), total
