"""Step 4: combine the detections of the whole batch and score them against ground truth."""

from __future__ import annotations

from .common import Layout, load_json, log, save_json


def angle_error(a: float, b: float) -> float:
    d = abs(a - b) % 180
    return min(d, 180 - d)


def summarise(rows: list[dict]) -> dict:
    tp = sum(r["truth_streak"] and r["found_streak"] for r in rows)
    fp = sum((not r["truth_streak"]) and r["found_streak"] for r in rows)
    fn = sum(r["truth_streak"] and not r["found_streak"] for r in rows)
    tn = sum((not r["truth_streak"]) and not r["found_streak"] for r in rows)
    errors = [r["angle_error_deg"] for r in rows if r["angle_error_deg"] is not None]
    return {
        "frames": len(rows),
        "true_positive": tp, "false_positive": fp, "false_negative": fn, "true_negative": tn,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "mean_angle_error_deg": round(sum(errors) / len(errors), 2) if errors else None,
        "stars_detected": sum(r["stars_found"] for r in rows),
        "stars_simulated": sum(r["stars_true"] for r in rows),
    }


def to_markdown(rows: list[dict], summary: dict) -> str:
    lines = [
        "| Frame | Streak in truth | Streak found | Angle error (deg) | Stars found / simulated |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        err = "" if r["angle_error_deg"] is None else f"{r['angle_error_deg']:.1f}"
        lines.append(f"| {r['frame']} | {'yes' if r['truth_streak'] else 'no'} | "
                     f"{'yes' if r['found_streak'] else 'no'} | {err} | {r['stars_found']} / {r['stars_true']} |")
    s = summary
    lines += [
        "",
        f"Frames: {s['frames']} · precision: {s['precision']} · recall: {s['recall']} · "
        f"mean angle error: {s['mean_angle_error_deg']} deg",
    ]
    return "\n".join(lines)


def run(data_dir: str) -> dict:
    layout = Layout(data_dir)
    frames = load_json(layout.frames_index)
    rows = []
    for frame in frames:
        truth = load_json(layout.truth(frame))
        objects = load_json(layout.detections(frame))["objects"]
        streaks = [o for o in objects if o["type"] == "streak"]
        err = None
        if truth["streak"] and streaks:
            err = round(min(angle_error(o["angle_deg"], truth["angle_deg"]) for o in streaks), 1)
        rows.append({
            "frame": frame,
            "truth_streak": truth["streak"],
            "found_streak": bool(streaks),
            "angle_error_deg": err,
            "stars_found": sum(o["type"] == "star" for o in objects),
            "stars_true": truth["n_stars"],
        })

    summary = summarise(rows)
    markdown = to_markdown(rows, summary)
    save_json(layout.root / "report.json", {"summary": summary, "frames": rows})
    (layout.root / "report.md").write_text(markdown + "\n")
    log(markdown)
    return summary
