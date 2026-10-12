"""Step 2: calibrate one frame.

1. Subtract the master dark: removes the sensor gradient and the hot pixels.
2. Subtract the sky background (median).
3. Divide by the noise (robust sigma), so pixel values become signal-to-noise.
"""

from __future__ import annotations

import numpy as np

from .common import Layout, log, robust_sigma, save_array


def calibrate_array(raw: np.ndarray, dark: np.ndarray) -> np.ndarray:
    img = raw.astype(np.float64) - dark
    img -= np.median(img)
    return img / max(robust_sigma(img), 1e-6)


def run(data_dir: str, frame: str) -> None:
    layout = Layout(data_dir)
    raw = np.load(layout.raw(frame))
    dark = np.load(layout.dark)
    snr = calibrate_array(raw, dark)
    save_array(layout.calibrated(frame), snr)
    log(f"calibrated {frame}: max S/N {snr.max():.1f}")
