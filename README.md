# Shortest Superstring: How Good Is Greedy?

Undergraduate research code and evidence for studying the maximum-overlap
greedy algorithm for the Shortest Common Superstring (SCS) problem against an
exact subset-DP benchmark.

## Install

```bash
python -m venv .venv            # Python >= 3.10 (developed on CPython 3.14, Windows 11)
.venv/Scripts/python -m pip install -r requirements.txt   # numpy, matplotlib, psutil, pytest
.venv/Scripts/python -m pip install -e .                  # optional: makes `scs` importable anywhere
```

(On Linux/macOS use `.venv/bin/python`.)

## One-command reproduction

```bash
bash scripts/reproduce.sh
```

Runs, in order: the test suite (correctness gate), the counterexample search,
the smoke and standard experiments, the DP scaling study, and the analysis.
About 15–20 minutes on one core. Run it on an idle machine, because timing
columns are measured. The real-data extension is a separate command:

```bash
bash scripts/reproduce_bio.sh
```

## Layout

| Path | What |
|---|---|
| `scs/preprocess.py` | remove empty / duplicate / contained strings; canonical (sorted) IDs |
| `scs/overlap.py` | KMP suffix–prefix overlap, naive reference, overlap matrix |
| `scs/greedy.py` | maximum-overlap greedy with tie policies `lowest_id`, `highest_id`, `lex_merged`, `random` and merge traces |
| `scs/exact_dp.py` | exact subset DP (pure-Python and numpy engines) with reconstruction |
| `scs/validate.py`, `scs/oracle.py` | independent validators, trace replay, brute-force oracles |
| `scs/generators.py` | input families: random, fragments, repetitive, known, discovered |
| `scs/runner.py`, `scs/cli.py` | experiment runner (child-process DP with timeout/memory guard, checkpoint/resume) |
| `scs/shibata.py`, `scripts/shibata_experiment.py` | Shibata S_{k,t} reproduction: legality replay and OPT certificate |
| `scs/two_approx.py` | OpenAI (2026) preprint's 2-approximation (forced counts, hierarchical graph, Euler tour) with run-time checks of the paper's lemmas; optional runner algorithm `two_approx` |
| `scs/bio/` | bounded download + extraction of the phiX174 sequencing data |
| `configs/` | `smoke`, `pilot`, `standard`, `extended`, `scaling`, `bio*` configurations |
| `analysis/analyze.py` | metrics, tables, figures |
| `results/` | raw results (JSONL, gzipped where large), manifests, traces, analysis outputs |
| `tests/` | pytest suite (`python -m pytest -q`) |
| `docs/` | interfaces, algorithms, verification, literature, metrics, dataset manifest, findings, walkthrough, AI-assistance log |

## Main documents

* [docs/FINDINGS.md](docs/FINDINGS.md): methodology, results, limitations.
* [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md): short guide for presenters.
* [docs/algorithms.md](docs/algorithms.md): correctness arguments and complexity.
* [docs/verification.md](docs/verification.md): independent correctness summary.
* [docs/literature.md](docs/literature.md): verified references and unresolved claims.
* [docs/dataset_manifest.md](docs/dataset_manifest.md): real sequencing dataset provenance.
* [docs/AI_ASSISTANCE.md](docs/AI_ASSISTANCE.md): AI-assistance log for disclosure.

## Individual commands

```bash
python -m pytest -q                                   # correctness gate
python -m scs.cli run configs/smoke.json --force      # tiny end-to-end run
python -m scs.cli run configs/standard.json --resume  # resumable main run
python -m scs.cli scaling configs/scaling.json --force
python analysis/analyze.py results/standard --scaling results/scaling
python scripts/shibata_experiment.py                  # Shibata construction (about 1 min)
python -m scs.cli run configs/two_approx.json --force # greedy vs OPT vs the 2-approximation (~5 s)
python scripts/two_approx_summary.py                  # results/two_approx/summary.md (~15 s; needs results/standard)
python -m scs.cli run configs/extended.json --force   # optional, larger
```
