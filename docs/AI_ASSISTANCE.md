# AI-assistance log (for disclosure)

**Tool:** Claude Code desktop app, used on 2026-11-05. The coordinator model
was Claude Opus 5.5. Four worker sub-agents ran on Claude Sonnet, with file
ownership kept separate.

The students supplied the research questions, requirements and constraints in
one long prompt, and later asked for a pull request.

## Who did what

**Coordinator (Opus 5.5)**
* Wrote the interface contract `docs/INTERFACES.md`, plus `scs/schema.py`,
  `scs/seeds.py` and the packaging files.
* Reviewed the workers' code, widened the standard configuration to n ≤ 20 and
  ran all the main experiments.
* Found and verified the sequencing dataset with `curl` against the ENA and
  NCBI APIs.
* Wrote `scs/bio/`, `analysis/deep_dive.py`, `docs/dataset_manifest.md`,
  `docs/FINDINGS.md`, `docs/WALKTHROUGH.md`, the README and this log.

**Agent A (Sonnet)**
* Wrote `scs/preprocess.py`, `scs/overlap.py`, `scs/greedy.py`,
  `scs/exact_dp.py` and `docs/algorithms.md`.

**Agent B (Sonnet)**
* Wrote `scs/generators.py`, `scs/runner.py`, `scs/cli.py`, `scs/sysinfo.py`,
  the configs and `scripts/search_counterexamples.py`.

**Agent C (Sonnet)**
* Wrote `scs/validate.py`, `scs/oracle.py`, `tests/` and
  `docs/verification.md`.
* Was told not to read Agent A's implementation, so that its oracles would be
  independent of it.

**Agent D (Sonnet)**
* Wrote `docs/literature.md`, `docs/metrics.md` and `analysis/analyze.py`.
* Its web tool was refused access to the ENA API, so the dataset search was
  redone by the coordinator.

## How outputs were checked

* **Tests.** The coordinator ran the full test suite itself (100 tests passed).
* **Code review.** It read the greedy, DP, overlap, preprocessing and oracle
  code.
* **Results.** It checked that every result row has `valid = true` and that no
  run failed.
* **Corrections.** It re-derived the regression examples by hand and fixed
  imprecise statements in the findings against the computed tables.
* **Literature.** These checks rely on Agent D's fetches of Crossref, arXiv and
  publisher pages. Several items are marked unverified in
  `docs/literature.md`.
  * The students should re-read the key primary sources themselves before
    citing them, especially Tarhio–Ukkonen 1988, Turner 1989 and the 2026
    preprints.

## What the students should still do

* Read and understand `docs/algorithms.md` and the proofs before presenting
  them.
* Spot-check numbers in `docs/FINDINGS.md` against `results/`.
* Decide on the final framing and wording of the report. The AI-written text is
  a draft.
* Disclose AI assistance according to your course policy. Note that some of the
  cited 2026 papers also disclose AI assistance.
