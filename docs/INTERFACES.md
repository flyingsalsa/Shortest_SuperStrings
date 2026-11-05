# Interfaces, conventions and file ownership

Owner: coordinator. This document is the contract between workers. If a worker
needs a change, they report it to the coordinator instead of editing another
worker's files.

Python: `.venv/Scripts/python` (CPython 3.14, Windows). Dependencies: numpy,
matplotlib, pytest, psutil only. Standard library otherwise. Run everything
from the repository root; the package is `scs` (import with the repo root on
`sys.path`; `pyproject.toml` / `pip install -e .` provided by coordinator).

## 1. Notation

* `n` – number of retained strings, `ell` – max retained length,
  `L` – sum of retained lengths, `G` – greedy output length,
  `OPT` – exact minimum superstring length (of the retained set, which equals
  that of the original set).
* `ov(x, y)` – length of the longest suffix of `x` that equals a prefix of `y`,
  with `0 <= k <= min(|x|,|y|)`. (For a substring-free set with `x != y` this is
  automatically `< min(|x|,|y|)`.) `ov` is only ever used on ordered pairs of
  *distinct* strings by greedy / DP.

## 2. Preprocessing (`scs/preprocess.py`, Agent A)

`preprocess(strings: Sequence[str]) -> Preprocessed` (schema in `scs/schema.py`).

1. Empty strings are removed (reason `"empty"`, witness `None`). They are
   contained in every superstring, including the empty string.
2. Exact duplicates: the first occurrence (smallest original index) is kept;
   later ones are removed with reason `"duplicate"`, witness = first index.
3. Containment: a distinct string `s` that is a proper substring of another
   distinct kept string `t` is removed with reason `"contained"`, witness =
   the original index of the representative of the *longest* such `t`
   (ties: smallest original index). Containment is evaluated against the
   set of distinct non-empty strings (so a chain a ⊂ b ⊂ c removes a and b,
   both with a witness that is actually a superstring of them).
4. `retained` = remaining distinct strings sorted with Python's `<` on `str`.
   Stable ID of `retained[k]` is `k`. This makes every deterministic algorithm
   invariant to the order of the original inputs.

Output must be deterministic and must not depend on set/dict iteration order.
Superstring of the original set == superstring of the retained set; the
validators always check against the ORIGINAL inputs.

Edge cases: `preprocess([])` → empty retained. All-empty input → empty retained.
For `n = 0` every algorithm returns `""` (length 0); for `n = 1` it returns the
single string.

## 3. Overlaps (`scs/overlap.py`, Agent A)

* `overlap(x: str, y: str) -> int` – production routine: KMP prefix function of
  `y`, then scan `x` (O(|x|+|y|) time). Must not use a separator character that
  could appear in inputs.
* `overlap_naive(x: str, y: str) -> int` – reference: try `k` from
  `min(|x|,|y|)` down to 0 with slicing (O(min^2)). Used by tests/validators.
* `overlap_matrix(strings: Sequence[str]) -> list[list[int]]` – `M[i][j] =
  overlap(strings[i], strings[j])` for `i != j`, and `M[i][i] = 0`
  (diagonal is never used). Cost O(n^2 · ell) with KMP.

## 4. Greedy (`scs/greedy.py`, Agent A)

```
greedy(strings: Sequence[str], policy: str = "lowest_id", seed: int | None = None,
       trace: bool = False, overlaps: list[list[int]] | None = None) -> GreedyResult
```

* `strings` MUST already be the `retained` tuple of `preprocess` (sorted,
  distinct, substring-free). Greedy may assert this cheaply (e.g. in debug).
  `overlaps` is the precomputed matrix for those strings (computed if None).
* Active strings have integer IDs. Initial IDs `0..n-1`. Merge number `t`
  (0-based) creates a new string with ID `n + t`; both parents become inactive.
* At each step compute `m = max ov(a, b)` over ordered pairs of distinct active
  IDs. The tie set `T` = all ordered pairs attaining `m` (including when
  `m = 0`). The policy chooses ONE pair from `T` only:
  * `lowest_id`  (primary, fully specified): the lexicographically smallest
    `(a, b)` tuple of IDs. Effect: prefers older strings / smaller original
    strings in lexicographic order.
  * `highest_id`: the lexicographically largest `(a, b)` tuple. Effect: prefers
    recently merged strings ("keep extending the newest contig").
  * `lex_merged`: the pair whose merged string `s_a + s_b[m:]` is
    lexicographically smallest; remaining ties by smallest `(a, b)`.
    (Content-based; independent of ID assignment.)
  * `random`: uniform choice from `T` sorted ascending by `(a, b)`, using a
    LOCAL `random.Random(seed)` instance (never the global RNG); exactly one
    `rng.randrange(len(T))` call per merge step, including steps with
    `len(T) == 1` (so the RNG stream position is a simple function of the step
    number). `seed` is required for `random` and must be `None` otherwise.
* Merged string = `s_a + s_b[ov(a,b):]`. Overlaps of the merged string `c` with
  the other active strings `x`: `ov(c, x) = ov(b, x)` and `ov(x, c) = ov(x, a)`.
  This shortcut is valid ONLY because the active set stays substring-free under
  maximum-overlap merging; Agent A documents the proof in
  `docs/algorithms.md`. The validator (Agent C) independently replays the trace
  with direct overlap computation on actual strings, so a wrong shortcut would
  be caught.
* `order`: each active string carries the list of original IDs it was built
  from; merged order = order(a) + order(b). Final `order` is a permutation of
  `0..n-1`.
* `trace=True` records a `MergeStep` per merge including `merged`; with
  `trace=False` steps are not stored (timing runs) but `n_tie_steps`,
  `max_tied`, `sum_overlap` are still reported (cheap).
* Implementation complexity target: O(n^3) pair scanning (+ string building) is
  acceptable and must be stated honestly; n is at most a few hundred.

## 5. Exact DP (`scs/exact_dp.py`, Agent A)

```
exact_dp(strings, overlaps=None) -> ExactResult              # pure Python reference (engine "python")
exact_dp_numpy(strings, overlaps=None) -> ExactResult        # vectorised (engine "numpy")
estimate_dp_memory_bytes(n: int, engine: str) -> int
```

* Same input precondition as greedy (retained, substring-free, sorted).
* Recurrence (subset `M` as bitmask, `j ∈ M` last string):
  `D[{j}, j] = |s_j|`, `D[M, j] = min_{i ∈ M\{j}} D[M\{j}, i] + |s_j| - ov(i, j)`,
  `OPT = min_j D[full, j]`. Store predecessor and reconstruct the order and the
  superstring by merging consecutive strings with their overlaps.
* Deterministic tie-breaking in argmin: smallest index.
* `ExactResult.length` must equal `len(superstring)` (asserted).
* n = 0 → `""`, n = 1 → the string.
* The DP itself performs no timeout handling; the runner wraps it in a child
  process. `estimate_dp_memory_bytes` lets the runner refuse to start a run
  whose tables would exceed the memory budget.

## 5b. OpenAI (2026) 2-approximation (`scs/two_approx.py`, extension)

```
two_approx(strings, check: bool = True) -> TwoApproxResult
forced_counts(strings) -> (m: dict[str, int], W: int)     # Sec. 2 counts, W <= OPT
base_graph(m, alphabet) -> Counter[(from_word, to_word)]  # Sec. 2.3 edge multiset
```

* Same input precondition as greedy (retained, sorted, substring-free); checked
  when `check=True`.
* `TwoApproxResult`: `superstring`, `length`, `W` (lower bound, `W <= OPT`),
  `added_cost` (connection up-cost, `<= W`; `length == W + added_cost`),
  `n_groups`, `n_layers`, `n_blocks`, `n_requests`, `n_cycles`, `operations`
  (connection operation kind -> `[count, total cost]`).
* Deterministic. Any failed run-time check of the paper's claims raises
  `TwoApproxError`.
* n = 0 -> `""`. For n = 1 the algorithm runs as usual, so the output may be
  longer than the single string (`docs/algorithms.md` section 5.6).

## 6. Validators (`scs/validate.py`, Agent C)

```
check_superstring(original: Sequence[str], superstring: str) -> list[str]   # list of missing originals ([] = ok)
replay_greedy_trace(retained: Sequence[str], result: GreedyResult) -> list[str]  # problems ([] = ok)
check_order(retained, order, length) -> list[str]  # order is a permutation & merging it gives `length`
```

`replay_greedy_trace` recomputes all overlaps with `overlap_naive` on the
actual current strings at each step and checks: chosen pair is active and
distinct; chosen overlap equals the true maximum; `n_tied` equals the true tie
count; for deterministic policies the chosen pair equals the policy's choice;
for `random` the choice equals what `random.Random(seed)` reproduces; merged
strings and the final superstring match.

## 7. Oracles (`scs/oracle.py`, Agent C)

* `brute_force_permutations(strings) -> int` – min over all permutations of the
  merged length (independent code path, no DP).
* `brute_force_superstring(strings, alphabet, max_len) -> int | None` – direct
  enumeration of candidate strings in increasing length; returns the minimum
  length of a string containing all inputs, or None if > max_len. This checks
  the ordering formulation itself, not just the DP.

## 8. Generators (`scs/generators.py`, Agent B)

```
generate(family: str, params: dict, seed: int) -> Instance
known_instances() -> list[Instance]   # verified regression / counterexample cases
```

Families:
* `random` (family A): independent random strings; params: `alphabet` (int size),
  `n`, `len_dist` ("fixed" | "uniform"), `len_min`, `len_max`.
* `fragments` (family B): random source of length `source_len` over `alphabet`;
  `n` fragments with length distribution; record source and start positions.
* `repetitive` (family C): source built from a motif repeated with controlled
  perturbation (`motif_len`, `mutation_rate`, ...), then fragments sampled.
  Repetition strength configurable. Document generator in docstring.
* `known` (family D): hand-written verified examples (regression cases + parametrised
  Blum-style family `c(ab)^k, (ba)^k, (ab)^k c`).
* `discovered` (family D): output of a recorded search; labelled `discovered`.

Retained-size control: `n_mode = "retained"` (default) draws strings one by one
from the instance RNG and stops the first time the retained set size reaches
`n` (each draw changes the retained count by at most +1, so `n` is hit
exactly). A draw cap (`max_draws`, default `50*n`) prevents infinite loops; if
hit, the instance is still emitted with `metadata["n_target_reached"] = False`
and the analysis reports it. All draws are kept as the ORIGINAL input.
`n_mode = "raw"` draws exactly `n` strings. Generation never depends on any
algorithm outcome.

Strings use alphabet letters `"ABCDEFGHIJ..."` (first `alphabet` letters;
DNA-like `"ACGT"` when `alphabet == "dna"`).

## 9. Seeds

`scs/seeds.py`: `derive_seed(master_seed, "instance", config_name, family,
param_key, rep)` for instances and `derive_seed(master_seed, "tie",
instance_id, k)` for the `k`-th random tie run. Separate namespaces, no use of
Python `hash()`. `param_key` = JSON of the params dict with sorted keys.

## 10. Experiment configuration (`configs/*.json`, Agent B)

```json
{
  "name": "smoke",
  "master_seed": 20261105,
  "output_dir": "results/smoke",
  "families": [
    {"family": "random", "reps": 3,
     "grid": {"alphabet": [2, 4], "n": [5, 8], "len_dist": ["uniform"], "len_min": [3], "len_max": [8]}}
  ],
  "include_known": true,
  "greedy_policies": ["lowest_id", "highest_id", "lex_merged", "random"],
  "random_tie_runs": 5,
  "exact": {"enabled": true, "engine": "numpy", "max_n": 16,
             "timeout_s": 120, "memory_mb": 4000},
  "trace_instances": 5,
  "workers": 1
}
```

`grid` is a Cartesian product over its lists; every combination gets `reps`
instances.

Optional: `"two_approx": {"enabled": true, "max_L": 2000}` adds one
`two_approx` row per instance. It is off when the key is absent. It runs
in-process; instances with retained `L > max_L` get `skipped_n_too_large`.
`configs/two_approx.json` enables it.

## 11. Result rows (`results/<name>/results.jsonl`, Agent B)

One JSON object per (instance, algorithm, policy, tie_run). Required keys:

| key | meaning |
|---|---|
| `config_name`, `instance_id`, `family`, `label`, `params`, `instance_seed` | provenance |
| `algorithm` | `"greedy"`, `"exact_dp"` or (optional) `"two_approx"` |
| `policy` | greedy policy name, `null` for exact |
| `tie_run`, `tie_seed` | k and seed for random policy, else `null` |
| `status` | `"ok"`, `"timeout"`, `"memory_limit"`, `"skipped_n_too_large"`, `"error"` |
| `error` | message or `null` |
| `n_raw`, `L_raw`, `n`, `L`, `ell`, `min_len`, `alphabet_size` | sizes (retained unless `_raw`) |
| `n_removed_empty`, `n_removed_duplicate`, `n_removed_contained` | preprocessing record |
| `frac_pos_overlap_pairs`, `mean_overlap`, `max_overlap` | overlap-structure features over ordered distinct pairs |
| `length` | output length (null unless ok) |
| `valid` | containment check against ORIGINAL inputs passed (null unless ok) |
| `superstring_sha256` | hash of output |
| `order` | permutation of retained IDs |
| `n_tie_steps`, `max_tied`, `sum_overlap` | greedy only (null for exact) |
| `t_preprocess_s`, `t_overlap_s`, `t_solve_s`, `t_total_s` | `time.perf_counter` seconds; solve excludes preprocess+overlap; total = all three, measured in the process doing the work |
| `code_version`, `timestamp` | git commit hash (+`-dirty`), ISO time |
| `lower_bound_W`, `added_cost`, `two_approx_ops` | `two_approx` rows only: the paper's `W <= OPT`, connection cost (`length = W + added_cost`), operation kind -> `[count, cost]`. The row is `error` if `W > OPT` or `length < OPT` |

`instances.jsonl` holds each `Instance` (as dict) plus `strings_sha256`.
`manifest.json` holds config, seeds, generator version, python/package
versions, machine info, git commit, start/end time.
`traces/` holds JSON greedy traces (all policies) and DP orders for the first
`trace_instances` instances of each family + all known instances.

Resume: a row's key is `(instance_id, algorithm, policy, tie_run)`; the runner
skips keys already present with a terminal status and appends new rows only.
Exact results are computed once per instance and reused for all greedy rows
(analysis joins on `instance_id`).

Timing: benchmarks run with `workers = 1` on an otherwise idle machine.

## 12. File ownership

| Path | Owner |
|---|---|
| `scs/schema.py`, `scs/seeds.py`, `scs/__init__.py`, `pyproject.toml`, `requirements.txt`, `README.md`, `docs/INTERFACES.md`, `docs/FINDINGS.md`, `docs/AI_ASSISTANCE.md`, `docs/WALKTHROUGH.md` | coordinator |
| `scs/shibata.py`, `scs/two_approx.py`, `tests/test_two_approx.py`, `configs/two_approx.json` | coordinator (optional extensions) |
| `scs/preprocess.py`, `scs/overlap.py`, `scs/greedy.py`, `scs/exact_dp.py`, `docs/algorithms.md` | Agent A |
| `scs/generators.py`, `scs/runner.py`, `scs/cli.py`, `scs/sysinfo.py`, `configs/`, `scs/bio/`, `scripts/` | Agent B |
| `scs/validate.py`, `scs/oracle.py`, `tests/`, `docs/verification.md` | Agent C |
| `analysis/`, `docs/literature.md`, `docs/metrics.md`, `docs/dataset_manifest.md` | Agent D |

`results/` is written only by running the CLI (coordinator runs the main
experiments).

## 13. Initial runtime / memory budget

* Exact DP: `max_n` 16 for standard config (pure-Python engine used only up to
  n = 12 for cross-checks and the scaling study), per-run timeout 120 s,
  memory budget 4000 MB (the machine has 32 logical CPUs, 31 GB RAM).
* Standard experiment total wall-clock target: ≤ 1 hour.
* Scaling study: n = 4 … until a run exceeds 120 s or the memory estimate
  exceeds 4000 MB.
