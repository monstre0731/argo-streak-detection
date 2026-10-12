"""Command-line entry point. Each Argo step runs one of these subcommands.

    python -m pipeline generate  --n-frames 12 --seed 42
    python -m pipeline calibrate --frame frame-000
    python -m pipeline detect    --frame frame-000
    python -m pipeline report
    python -m pipeline run-local --n-frames 12      # whole pipeline, no Kubernetes
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import calibrate, detect, generate, report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pipeline", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", default=os.environ.get("DATA_DIR", "/data"),
                        help="shared data directory (default: $DATA_DIR or /data)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="simulate a batch of frames")
    g.add_argument("--n-frames", type=int, default=12)
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--size", type=int, default=256)
    g.add_argument("--frames-out", default="/tmp/frames.json",
                   help="also write the frame list here (read by Argo as an output parameter)")

    for name in ("calibrate", "detect"):
        p = sub.add_parser(name, help=f"{name} one frame")
        p.add_argument("--frame", required=True)
        if name == "detect":
            p.add_argument("--threshold", type=float, default=detect.THRESHOLD)

    sub.add_parser("report", help="summarise the batch")

    r = sub.add_parser("run-local", help="run every step in order on this machine")
    r.add_argument("--n-frames", type=int, default=12)
    r.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)
    data = args.data_dir

    if args.cmd == "generate":
        frames = generate.run(data, args.n_frames, args.seed, args.size)
        Path(args.frames_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.frames_out).write_text(json.dumps(frames))
        print(json.dumps(frames))
    elif args.cmd == "calibrate":
        calibrate.run(data, args.frame)
    elif args.cmd == "detect":
        detect.run(data, args.frame, args.threshold)
    elif args.cmd == "report":
        print(json.dumps(report.run(data)))
    elif args.cmd == "run-local":
        for frame in generate.run(data, args.n_frames, args.seed):
            calibrate.run(data, frame)
            detect.run(data, frame)
        print(json.dumps(report.run(data)))


if __name__ == "__main__":
    main()
