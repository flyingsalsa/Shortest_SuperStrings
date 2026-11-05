# Metrics and aggregation

Notation follows `docs/INTERFACES.md`: `L` = sum of retained lengths, `G` = greedy
length, `OPT` = exact length (retained set). All metrics are computed per
*instance* from rows with `status == "ok"` and `valid == true`; the greedy row
is joined to the `exact_dp` row of the same `instance_id`.

## 1. Per-(instance, policy-run) metrics

| Metric | Definition | Notes |
|---|---|---|
| ratio | `G / OPT` | Defined when `OPT > 0` (i.e. `n >= 1` with non-empty strings). |
| gap | `G - OPT` | Always `>= 0` (a smaller value means a bug; reported loudly). |
| optimal | `1[G == OPT]` | Greedy optimal indicator. |
| savings_greedy | `L - G` | = `sum_overlap` of greedy. |
| savings_opt | `L - OPT` | |
| compression ratio | `(L - G) / (L - OPT)` | **Undefined when `L - OPT = 0`**: such instances are counted in `n_no_compression` and never get a value (not 1, not NaN-filled). |
| half-compression slack | `(L - G) - (L - OPT)/2` | Must be `>= 0` (Tarhio-Ukkonen/Turner). Negative slack = violation = flagged loudly (stderr, `violations.csv`, and a banner in the Markdown summary). Evaluated for every policy including random runs; undefined values excluded. |

## 2. Aggregation across tie runs (per instance first)

An instance has one `exact_dp` row and, per deterministic policy, one greedy row;
for policy `random` there are `k` repeated runs with different tie seeds. Those
runs are **repeated measurements on one instance, not independent instances**.
Therefore:

1. For `random`, first reduce the runs of each instance to
   `G_mean, G_min, G_max` (and per-run optimal indicators to `opt_frac`).
2. Cross-instance statistics (below) use **one value per instance**. For the
   random policy that value is `G_mean` (ratio of mean, `mean_G / OPT`) and, in
   separate tables, `G_min` and `G_max`. Primary reporting policy is
   `lowest_id`; the others are reported alongside, never pooled.
3. "Optimality rate" for random = mean over instances of `opt_frac` (instance-level
   quantity), not a pooled fraction over runs.

## 3. Distributions per (family, n)

Groups are (family, label, retained `n`) or (family, params key) as stated in the
table headers. For the ratio, gap, and compression ratio: count, median, first
and third quartile, 90th and 95th percentiles, max, mean (linear-interpolation
percentiles, `numpy.percentile` default). Families labelled `known` and
`discovered` (hand-written / search outputs) are **never** included in
`benchmark` aggregates; they get their own table `summary_special.md`.

Optimality rate = fraction of instances in the group with `G == OPT`, with a
95% **percentile bootstrap CI over instances** (resample instances with
replacement, 2000 resamples, fixed seed, the statistic recomputed each time;
groups with fewer than 5 instances are reported without CI). Wilson intervals
may be given as a cross-check.

## 4. Tie sensitivity

Per instance, over all greedy runs (all deterministic policies plus all random
seeds): `G_range = max G - min G`; `G_range_rel = G_range / OPT`. Reported:
fraction of instances with `G_range > 0` ("the policy changes G"), and the
distribution of `G_range`. Also pairwise: fraction of instances where policy
`P` differs from `lowest_id`. Only instances that actually had ties
(`n_tie_steps > 0` in the `lowest_id` row) are the denominator of a second,
"tied instances only" fraction. The stored range is a lower bound on the true
worst-case range over *all* tie-breakings.

## 5. Preprocessing reduction

Per instance: `removed_frac = (n_raw - n) / n_raw`, and the three components
(`n_removed_empty`, `_duplicate`, `_contained`) over `n_raw`; also
`L_raw`-to-`L` reduction. Reported as mean/median per family. Instances with
`n_raw = 0` are excluded from fractions.

## 6. Runtime

`t_solve_s` (and `t_total_s`) by engine (exact rows: from `params`/row key `engine`
if present, else `exact_dp`) and `n`: median and max, plus sample count. Scaling
study rows (`results/scaling/scaling.jsonl`) are analysed the same way, with a
log y axis. Rows with `status != "ok"` (timeout, memory) are not averaged; their
counts per `n` are reported separately. Timing is only meaningful for
`workers = 1` runs.

## 7. Exclusions and reporting rules

* Rows with `status != ok` or `valid != true` are excluded from metrics and
  counted per (family, status) in `excluded_counts.csv`.
* Instances where the exact row is missing (`skipped_n_too_large`, timeout) have no
  ratio; they are counted, not imputed.
* Never mix raw and retained `n`; group on retained `n`.
* No finding is claimed without the sample count `N` printed beside it.
