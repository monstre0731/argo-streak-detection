"""Shared helpers: data-directory layout, JSON I/O and logging.

Every step reads and writes files under one data directory. In Kubernetes this
directory is a volume shared by all steps of a workflow; locally it is any folder.

    <data>/calib/dark.npy            master dark frame (sensor offset + hot pixels)
    <data>/raw/<frame>.npy           raw frames as the telescope would deliver them
    <data>/raw/<frame>.png           preview images
    <data>/truth/<frame>.json        ground truth (only possible with simulated data)
    <data>/calibrated/<frame>.npy    background-subtracted, noise-normalised frames
    <data>/detections/<frame>.json   objects found in each frame
    <data>/report.json, report.md    batch summary
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


def log(message: str) -> None:
    """Log to stderr so stdout stays free for machine-readable output."""
    print(message, file=sys.stderr, flush=True)


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def save_array(path: Path, arr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, arr.astype(np.float32))


def robust_sigma(values: np.ndarray) -> float:
    """Noise estimate that ignores stars and streaks (median absolute deviation)."""
    med = np.median(values)
    return float(1.4826 * np.median(np.abs(values - med)))


class Layout:
    """Paths for one data directory."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    @property
    def dark(self) -> Path:
        return self.root / "calib" / "dark.npy"

    def raw(self, frame: str) -> Path:
        return self.root / "raw" / f"{frame}.npy"

    def preview(self, frame: str) -> Path:
        return self.root / "raw" / f"{frame}.png"

    def truth(self, frame: str) -> Path:
        return self.root / "truth" / f"{frame}.json"

    def calibrated(self, frame: str) -> Path:
        return self.root / "calibrated" / f"{frame}.npy"

    def detections(self, frame: str) -> Path:
        return self.root / "detections" / f"{frame}.json"

    @property
    def frames_index(self) -> Path:
        return self.root / "frames.json"
