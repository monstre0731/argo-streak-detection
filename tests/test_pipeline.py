import json

import numpy as np

from pipeline import calibrate, detect, generate, report
from pipeline.__main__ import main


def _frame(seed: int, with_streak: bool):
    dark = generate.make_dark(np.random.default_rng(0), 256)
    raw, truth = generate.make_frame(np.random.default_rng(seed), dark, with_streak=with_streak)
    return calibrate.calibrate_array(raw, dark), truth


def test_finds_streak_and_its_angle():
    snr, truth = _frame(seed=7, with_streak=True)
    streaks = [o for o in detect.detect_array(snr) if o["type"] == "streak"]
    assert streaks, "expected a streak"
    errors = [report.angle_error(s["angle_deg"], truth["angle_deg"]) for s in streaks]
    assert min(errors) < 5


def test_no_streak_in_star_only_frame():
    snr, _ = _frame(seed=8, with_streak=False)
    assert not [o for o in detect.detect_array(snr) if o["type"] == "streak"]


def test_calibration_removes_hot_pixels():
    dark = generate.make_dark(np.random.default_rng(0), 256)
    blank = dark + generate.SKY_LEVEL + np.random.default_rng(1).normal(0, generate.READ_NOISE, dark.shape)
    assert detect.detect_array(calibrate.calibrate_array(blank, dark)) == []
    # without dark subtraction the hot pixels would show up as detections
    no_dark = calibrate.calibrate_array(blank, np.zeros_like(dark))
    assert detect.detect_array(no_dark)


def test_angle_error_wraps_at_180():
    assert report.angle_error(179, 1) == 2


def test_run_local_end_to_end(tmp_path, capsys):
    main(["--data-dir", str(tmp_path), "run-local", "--n-frames", "6", "--seed", "3"])
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["frames"] == 6
    assert (tmp_path / "report.md").exists()
    assert len(list((tmp_path / "detections").glob("*.json"))) == 6
