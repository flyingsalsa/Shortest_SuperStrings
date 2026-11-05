#!/usr/bin/env bash
# Real-sequencing-data extension: bounded download, extraction, run, analysis.
set -euo pipefail
PY="${1:-.venv/Scripts/python}"
[ -x "$PY" ] || PY=python
"$PY" -m scs.bio.fetch --max-mb 5
"$PY" -m scs.bio.extract --config configs/bio_extract.json
"$PY" -m scs.cli run configs/bio.json --force
"$PY" analysis/analyze.py results/bio
# combined deep-dive (needs results/standard from scripts/reproduce.sh)
[ -f results/standard/results.jsonl ] || gzip -dk results/standard/results.jsonl.gz results/standard/instances.jsonl.gz
"$PY" analysis/deep_dive.py results/standard results/bio --out results/deep_dive
gzip -kf -9 results/bio/results.jsonl
