"""Step 1: simulate a batch of telescope frames.

Real data is not public, so we simulate it. Each frame contains:
  - a sky background with read noise,
  - a fixed sensor "dark" pattern: a brightness gradient plus hot pixels,
  - 20 to 35 stars (round point sources),
  - in about 60% of frames, one faint satellite streak (a line).

Ground truth is saved next to each frame so the report can score the detector.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from .common import Layout, log, save_array, save_json

SKY_LEVEL = 100.0
READ_NOISE = 6.0
STREAK_PROBABILITY = 0.6


def make_dark(rng: np.random.Generator, size: int) -> np.ndarray:
    """Sensor offset that is the same in every frame: a gradient plus hot pixels."""
    yy, xx = np.mgrid[0:size, 0:size]
    dark = 20.0 + 15.0 * (xx / size) + 8.0 * (yy / size)
    hot = rng.integers(0, size, size=(60, 2))
    dark[hot[:, 0], hot[:, 1]] += 800.0
    return dark.astype(np.float32)


def add_star(img: np.ndarray, x: float, y: float, amp: float, sigma: float = 1.3) -> None:
    r = int(4 * sigma) + 1
    x0, x1 = max(0, int(x) - r), min(img.shape[1], int(x) + r + 1)
    y0, y1 = max(0, int(y) - r), min(img.shape[0], int(y) + r + 1)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    img[y0:y1, x0:x1] += amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))


def add_streak(img: np.ndarray, x0: float, y0: float, x1: float, y1: float,
               amp: float, sigma: float = 1.0) -> None:
    """Add a line segment with a Gaussian cross-section."""
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    dx, dy = x1 - x0, y1 - y0
    t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    d2 = (xx - (x0 + t * dx)) ** 2 + (yy - (y0 + t * dy)) ** 2
    img += amp * np.exp(-d2 / (2 * sigma**2))


def make_frame(rng: np.random.Generator, dark: np.ndarray, with_streak: bool | None = None):
    """Return (raw_frame, truth_dict)."""
    size = dark.shape[0]
    sources = np.zeros_like(dark, dtype=np.float64)

    n_stars = int(rng.integers(20, 36))
    for _ in range(n_stars):
        add_star(sources, rng.uniform(5, size - 5), rng.uniform(5, size - 5), rng.uniform(40, 250))

    if with_streak is None:
        with_streak = bool(rng.random() < STREAK_PROBABILITY)

    truth: dict = {"n_stars": n_stars, "streak": with_streak}
    if with_streak:
        length = rng.uniform(50, 140)
        angle = rng.uniform(0, 180)
        cx, cy = rng.uniform(70, size - 70, size=2)
        dx = 0.5 * length * np.cos(np.radians(angle))
        dy = 0.5 * length * np.sin(np.radians(angle))
        x0, y0, x1, y1 = cx - dx, cy - dy, cx + dx, cy + dy
        add_streak(sources, x0, y0, x1, y1, amp=rng.uniform(25, 45))
        truth.update(x0=round(x0, 1), y0=round(y0, 1), x1=round(x1, 1), y1=round(y1, 1),
                     angle_deg=round(angle % 180, 1), length=round(length, 1))

    noise = rng.normal(0.0, READ_NOISE, size=dark.shape)
    raw = dark + SKY_LEVEL + sources + noise
    return raw.astype(np.float32), truth


def save_preview(path, img: np.ndarray) -> None:
    """Stretch the image like an astronomer would (asinh) and save a PNG."""
    lo, hi = np.percentile(img, [1, 99.7])
    scaled = np.arcsinh(np.clip((img - lo) / max(hi - lo, 1e-6), 0, None) * 10) / np.arcsinh(10)
    Image.fromarray((np.clip(scaled, 0, 1) * 255).astype(np.uint8)).save(path)


def run(data_dir: str, n_frames: int, seed: int, size: int = 256) -> list[str]:
    layout = Layout(data_dir)
    dark = make_dark(np.random.default_rng(seed), size)
    save_array(layout.dark, dark)

    frames = []
    for i in range(n_frames):
        name = f"frame-{i:03d}"
        raw, truth = make_frame(np.random.default_rng([seed, i]), dark)
        save_array(layout.raw(name), raw)
        save_preview(layout.preview(name), raw)
        save_json(layout.truth(name), {"frame": name, **truth})
        frames.append(name)
        log(f"generated {name}: {truth['n_stars']} stars, streak={truth['streak']}")

    save_json(layout.frames_index, frames)
    return frames
