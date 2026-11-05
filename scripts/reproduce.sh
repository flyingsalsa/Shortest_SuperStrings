#!/usr/bin/env bash
# One-command reproduction of all synthetic experiments + analysis.
# Usage (from repo root):  bash scripts/reproduce.sh [python]
# Run on an otherwise idle machine: timing columns are measured with workers=1.
set -euo pipefail
PY="${1:-.venv/Scripts/python}"
[ -x "$PY" ] || PY=python
"$PY" -m pytest -q
"$PY" scripts/search_counterexamples.py --mode random --samples 300000 --top-k 10 --out results/discovered
"$PY" -m scs.cli run configs/smoke.json --force
"$PY" -m scs.cli run configs/standard.json --force
"$PY" -m scs.cli scaling configs/scaling.json --force
"$PY" analysis/analyze.py results/standard --scaling results/scaling
gzip -kf -9 results/standard/results.jsonl results/standard/instances.jsonl
