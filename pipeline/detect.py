"""Step 3: find objects in one calibrated frame and classify them.

1. Smooth with a small Gaussian so a faint streak becomes one connected shape.
2. Keep pixels above a signal-to-noise threshold and group touching pixels.
3. For each group, measure its shape from the second moments:
     - stars are round (elongation close to 1),
     - satellite streaks are long and thin.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from .common import Layout, log, robust_sigma, save_json

THRESHOLD = 5.0          # signal-to-noise after smoothing
MIN_PIXELS = 5           # smaller groups are noise
STREAK_ELONGATION = 3.0  # major axis / minor axis
STREAK_MIN_LENGTH = 25.0  # pixels


def measure(weights: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> dict:
    w = weights / weights.sum()
    cx, cy = float((w * xs).sum()), float((w * ys).sum())
    cov = np.array([
        [(w * (xs - cx) ** 2).sum(), (w * (xs - cx) * (ys - cy)).sum()],
        [(w * (xs - cx) * (ys - cy)).sum(), (w * (ys - cy) ** 2).sum()],
    ])
    evals, evecs = np.linalg.eigh(cov)
    minor, major = max(evals[0], 1e-6), max(evals[1], 1e-6)
    vx, vy = evecs[:, 1]
    return {
        "x": round(cx, 1),
        "y": round(cy, 1),
        "elongation": round(math.sqrt(major / minor), 2),
        # a uniform line of length L has variance L^2 / 12 along its axis
        "length": round(math.sqrt(12 * major), 1),
        "angle_deg": round(math.degrees(math.atan2(vy, vx)) % 180, 1),
    }


def detect_array(snr: np.ndarray, threshold: float = THRESHOLD) -> list[dict]:
    smooth = ndimage.gaussian_filter(snr, sigma=1.0)
    smooth = (smooth - np.median(smooth)) / max(robust_sigma(smooth), 1e-6)
    labels, n = ndimage.label(smooth > threshold, structure=np.ones((3, 3)))

    objects = []
    for idx, region in enumerate(ndimage.find_objects(labels), start=1):
        sub = labels[region] == idx
        npix = int(sub.sum())
        if npix < MIN_PIXELS:
            continue
        ys, xs = np.nonzero(sub)
        ys = ys + region[0].start
        xs = xs + region[1].start
        shape = measure(smooth[ys, xs], ys, xs)
        is_streak = shape["elongation"] >= STREAK_ELONGATION and shape["length"] >= STREAK_MIN_LENGTH
        objects.append({"type": "streak" if is_streak else "star", "pixels": npix,
                        "peak_snr": round(float(smooth[ys, xs].max()), 1), **shape})
    return objects


def run(data_dir: str, frame: str, threshold: float = THRESHOLD) -> None:
    layout = Layout(data_dir)
    snr = np.load(layout.calibrated(frame))
    objects = detect_array(snr, threshold)
    streaks = [o for o in objects if o["type"] == "streak"]
    save_json(layout.detections(frame), {"frame": frame, "threshold": threshold, "objects": objects})
    log(f"detected {frame}: {len(objects)} objects, {len(streaks)} streak(s)")
