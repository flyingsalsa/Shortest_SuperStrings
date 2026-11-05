"""Command line interface (OWNER: Agent B).

    python -m scs.cli run configs/smoke.json [--resume] [--force] [--workers N]
                                             [--only-family F] [--retry-errors]
    python -m scs.cli scaling configs/scaling.json [--resume] [--force]
"""
from __future__ import annotations

import argparse


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="scs.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run an experiment config")
    r.add_argument("config")
    r.add_argument("--resume", action="store_true", help="continue, skipping finished keys")
    r.add_argument("--force", action="store_true", help="overwrite existing results")
    r.add_argument("--workers", type=int, default=None)
    r.add_argument("--only-family", default=None)
    r.add_argument("--retry-errors", action="store_true",
                   help="with --resume: drop old error rows and recompute them")
    s = sub.add_parser("scaling", help="exact-DP runtime scaling study")
    s.add_argument("config")
    s.add_argument("--resume", action="store_true")
    s.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    from . import runner
    if a.cmd == "run":
        runner.run(a.config, resume=a.resume, workers=a.workers,
                   only_family=a.only_family, force=a.force,
                   retry_errors=a.retry_errors)
    else:
        runner.run_scaling(a.config, resume=a.resume, force=a.force)


if __name__ == "__main__":
    main()
