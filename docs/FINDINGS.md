# Shortest Superstring: How Good Is Greedy? Methodology and findings

All numbers below come from the committed outputs:
`results/standard/` (synthetic benchmark), `results/bio/` (phiX174 reads),
`results/scaling/` (DP runtime), `results/deep_dive/deep_dive.md` (targeted
analyses and case studies), `results/shibata/` and `results/two_approx/`
(optional extensions, sections 3b and 3c). The machine was Windows 11 with an AMD CPU (32
logical cores, 31 GB RAM) running CPython 3.14.7 and numpy 2.5.4. All
benchmarks ran single-process on an otherwise idle machine.

Labels used in this document:
* **[Observed]** is an empirical result from our data.
* **[Explanation?]** is a possible explanation that we have not tested.
* **[Proven]** is a mathematical statement, with its source.

## 1. Setup in brief

### 1.1 Problem and preprocessing

**Preprocessing.** We first remove empty strings, duplicates and strings
contained in another input; a record of every removal is kept. The retained
strings are sorted lexicographically, and their positions give stable IDs.

* *n* = number of retained strings.
* *L* = total length of the retained strings.
* *OPT* = the exact optimum length, computed by the Held–Karp-style subset DP
  over (set of strings, last string).
* *G* = the length that greedy outputs.

**[Proven]** Preprocessing does not change OPT. It also makes the permutation
formulation and the DP exact. The argument is in `docs/algorithms.md`.

### 1.2 Greedy and tie-breaking

At every step, greedy merges a pair of current strings with the globally
maximum overlap. We implemented four ways to choose among tied pairs:
* **`lowest_id`**: smallest (left, right) ID pair.
* **`highest_id`**: largest ID pair. Merged strings get new, higher IDs, so this
  prefers strings formed in recent merges.
* **`lex_merged`**: the pair whose merged string is lexicographically smallest.
* **`random`**: uniform choice among the tied pairs, using a seeded local RNG.

Each instance is solved once by `lowest_id`, `highest_id` and `lex_merged`, and
10 times by `random`. That is **13 greedy runs per instance**, all on the same
input.

### 1.3 Input families (`configs/standard.json`)

All 4,953 instances have n ∈ {5, 8, 10, 12, 15, 18, 20}. "Retained-size
control" means strings are drawn until exactly n survive preprocessing; all
draws are kept as the original input.

| Family | Construction | Varied parameters | Instances |
|---|---|---|---|
| **A, random** | Independent random strings | Alphabet 2 or 4; lengths uniform 3–8, uniform 8–14, or fixed 7 | 1,260 |
| **B, fragments** | Substrings of one random source string | Alphabet 2 or 4; lengths 4–8 or 8–14; nominal coverage 0.5, 1 or 2 | 2,100 |
| **C, repetitive** | Fragments of a source built from a repeated motif, with each copy mutated | Motif length 6, 12 or 24; mutation rate 0.05, 0.10 or 0.25 | 1,575 |
| **D, known and discovered** | Verified regression cases, the Blum-style family c(ab)^k, (ba)^k, (ab)^k c for k = 1..6, and 7 instances from a recorded random search | — | 18 |

Family D is reported separately and never pooled with the benchmark families.

### 1.4 Correctness gate

The main runs started only after the following passed. Details are in
`docs/verification.md`.
* All 100 pytest tests passed.
* The DP agreed with an independent permutation brute force on 900 instances.
* On 60 instances, the DP also agreed with direct enumeration of all candidate
  strings and with a separate BFS oracle.
* Every greedy trace was replayed with naive overlap recomputation.
* Half-compression was checked on 1,400 instances in the default suite and
  6,000 more in the slow test.
* During the experiment itself, every output (69,342 synthetic rows and 4,680
  bio rows) passed a containment check against the original inputs. No run
  timed out or failed.

### 1.5 Metrics (`docs/metrics.md`)

* **Ratio and gap:** G/OPT and G − OPT.
* **Optimality rate:** the fraction of instances with G = OPT.
* **Compression ratio:** (L − G)/(L − OPT). It is undefined when L = OPT; that
  happened in no benchmark instance.
* **Aggregation:** random-tie runs are repeated measurements of one instance, so
  each instance contributes one value before any statistic across instances.
  For `random`, that value is the mean G over the seeds.
* **Confidence intervals:** 95% bootstrap intervals that resample instances.

## 2. Results by research question

### RQ1: How close does greedy come to OPT?

Results for `lowest_id` (`results/standard/analysis/summary_by_family_n.md`,
`fig_ratio_by_family`):

| Family | Instances | Optimality rate | Mean G/OPT | Max G/OPT |
|---|---|---|---|---|
| random | 1,260 | 0.712 | 1.009 | 1.222 |
| fragments | 2,100 | 0.727 | 1.010 | 1.583 |
| repetitive | 1,575 | 0.648 | 1.017 | 1.435 |

* **[Observed]** The median G/OPT is 1.000 in every family-by-n cell except one:
  repetitive at n = 20, where it is 1.008.
* **[Observed]** The 95th percentile of G/OPT stays at or below about 1.10 in
  every cell.
* **[Observed]** The optimality rate falls steadily as n grows, while the mean
  ratio barely moves. For `lowest_id`, from n = 5 to n = 20:
  * random: 0.88 → 0.61
  * fragments: 0.92 → 0.63
  * repetitive: 0.84 → 0.49

  The mean absolute gap G − OPT grows from about 0.1–0.3 to about 0.7–1.3
  characters.
* **[Observed]** The largest benchmark ratio, 1.583, comes from a fragments
  instance: binary alphabet, n = 5, nominal coverage 2. Preprocessing removed
  124 of its 129 drawn strings. Its walkthrough is in deep_dive section 6.
* **[Observed]** Family D gives the largest ratios overall:
  * The Blum-style family reaches G/OPT = (4k+2)/(2k+4), which is 1.625 at
    k = 6, under all four policies.
  * The discovered instances reach 1.571 under some deterministic policies.
* **[Proven, literature]** The worst case is far worse than anything we observed.
  Blum-style inputs push greedy towards ratio 2. Recent preprints claim worse
  examples with suitable tie-breaking: ≥ 2 for every fixed string length k ≥ 6
  (Chukhin et al.) and ≥ 9/4 overall (Shibata; our machine-checked
  reproduction in section 3b reaches G/OPT = 2.109). Those preprints are not peer
  reviewed; see `docs/literature.md`.
* Our random samples **do not** approach those bounds. Bad cases need
  structure, so these results say nothing about worst-case behaviour.

### RQ2: Which input properties are associated with poor greedy decisions?

Tables are in deep_dive sections 1–2. Figure: `fig_ratio_vs_overlap_density`.

**[Observed] Generator settings separate good and bad cases clearly.**

* Alphabet size (random family):

  | Alphabet | Optimality rate |
  |---|---|
  | 2 | 0.61–0.63 |
  | 4 | 0.79–0.82 |

* Repetition strength (repetitive family):

  | Motif length | Mutation rate | Optimality rate | Mean G/OPT | Max G/OPT |
  |---|---|---|---|---|
  | 6 | 0.05 | 0.451 | 1.044 | 1.435 |
  | 24 | 0.25 | 0.806 | 1.004 | — |

  Short motifs with few mutations, which give the strongest repetition, are the
  worst setting. At every motif length, a lower mutation rate gives a lower
  optimality rate.
* Fragments: longer fragments over a 4-letter alphabet at coverage 2 are almost
  always optimal (0.983). The worst cells are binary-alphabet with short
  fragments.

**[Observed] Per-instance summary features add little once the setting is fixed.**

Within each (generator setting, n) stratum, we compared suboptimal and optimal
instances on:
* the fraction of ordered pairs with positive overlap;
* the mean and maximum overlap;
* the fraction of merges that faced a tie.

Their medians are close. The clearest gaps are:
* repetitive, tie fraction: 0.56 for suboptimal vs 0.48 for optimal instances;
* random, fraction of pairs with positive overlap: 0.55 vs 0.50.

These are associations, not causes.

**[Observed] The case studies show one recurring mechanism.**

* Greedy makes a maximum-overlap merge that joins two strings each of which
  had good partners elsewhere.
* Later the leftover strings can only be appended with overlap 0.
* Examples:
  * In BAB/AABA/ABAA, the unique overlap of 3 is taken, which destroys two
    overlaps of 2.
  * In the worst repetitive instance, greedy builds a long chain from four
    overlaps of 11. That leaves two blocks it can only join with overlap 0,
    while OPT strings everything into one chain.

**[Explanation?]** Low-entropy inputs make it likely that several strings share
equally long overlaps. Small alphabets and strong repetition do exactly that.
Greedy then has many plausible-looking merges and no information about which
one keeps the future overlap structure intact.

**[Observed] Repetition does not uniformly hurt.** The repetitive family with
motif 24 and mutation 0.25 does about as well as the random family over a
4-letter alphabet.

### RQ3: How much does tie-breaking matter?

Sources: deep_dive section 3, `tie_sensitivity.md`, `fig_tie_best_worst`,
`fig_tie_sensitivity`.

* **[Observed] Ties are the norm.** Almost every instance with n ≥ 8 has at
  least one tied maximal step.
* **[Observed] Ties often change the output length.** The share of instances
  where the 13 runs do not all produce the same length grows with n:

  | n | random | fragments | repetitive |
  |---|---|---|---|
  | 5 | 0.28 | 0.20 | 0.15 |
  | 20 | 0.73 | 0.68 | 0.72 |

* **[Observed] The spread is a few characters.** The largest observed difference
  between a run's G and the best run's G is 11 characters, on a repetitive
  instance at n = 20. On average it is about 2% of OPT.
* **[Observed] The best and worst run differ greatly in optimality rate** at
  n = 20:

  | Family | Best of 13 runs | `lowest_id` | Worst of 13 runs |
  |---|---|---|---|
  | random | 0.89 | 0.61 | 0.23 |
  | fragments | 0.90 | 0.63 | 0.30 |
  | repetitive | 0.80 | 0.49 | 0.20 |

  In 7–33% of all instances (depending on family and n), `lowest_id` is
  suboptimal but some other tie choice reaches OPT.
* **[Observed] No deterministic rule wins overall.** Optimality rates of the
  three rules are within each other's bootstrap CIs in almost every cell.
* **[Observed] The bad family D cases are tie-driven.** All seven discovered
  instances are ones where one rule reaches OPT and another produces
  G/OPT ≈ 1.43–1.57. For example, on ABBBB, BBBBA, BBBBB:
  * `highest_id` finds OPT = 7;
  * `lowest_id` gives 11.
  The Blum-style cases are the opposite: the bad merge is the unique maximum,
  so every rule gives the same result.
* Our 13 runs are only a sample of the possible tie choices. The true worst
  case over all tie-breakings can be larger than what we report.

### RQ4: Empirical compression vs the half-compression theorem

* **[Proven]** For maximum-overlap greedy on any input,
  L − G ≥ (L − OPT)/2 (Tarhio & Ukkonen 1988; Turner 1989; simple proof by
  Kalugin & Nikolaev, SOSA 2024).
  * This is a statement about compression, i.e. the characters saved. It is
    **not** the G ≤ 2·OPT conjecture. The assumptions and the parts we could
    not check are in `docs/literature.md`. In particular, we could not read the
    1988 paper's exact handling of tie-breaking.
* **[Observed]** The bound held in all 64,155 benchmark greedy runs and in every
  bio and family D run. The empirical minimum compression ratio is:

  | Family | Minimum compression ratio |
  |---|---|
  | random | 0.500 |
  | fragments | 0.667 |
  | repetitive | 0.739 |
  | bio, unconditioned | 0.667 |
  | known (family D) | 0.545 |
  | discovered (family D) | 0.500 |

  * 68% of benchmark runs have ratio exactly 1, meaning greedy was optimal.
* **[Observed] The bound is attained exactly in two kinds of case:**
  * Discovered three-string instances, e.g. L = 15, OPT = 7, G = 11, so
    L − G = 4 = (L − OPT)/2.
  * A random-family instance where L − OPT = 2 and one random-tie run lost one
    character of overlap (deep_dive section 6). The ratio is coarse when
    L − OPT is small.

  So the 1/2 constant cannot be improved even on tiny inputs. **[Proven]** by
  these explicit examples, which we verified exactly.
* **[Observed]** Away from such small-compression instances, typical greedy
  compression is ≥ 0.9 of optimal.
* Finite tests do not prove the theorem. A violation would have meant a bug or
  an assumption failure; we found none.

### RQ5: When does the exact DP become impractical?

Source: `results/scaling/analysis/scaling_runtime.md`, `fig_scaling_runtime`.
Each point is the median of 5 instances (alphabet 4, lengths 5–12). Times are
solve time only, excluding preprocessing, the overlap matrix and process start.

| n | numpy DP | pure-Python DP | Greedy |
|---|---|---|---|
| 10 | 0.8 ms | 3.3 ms | 22 µs |
| 15 | 8.6 ms | 0.22 s | 55 µs |
| 18 | 0.11 s | 2.5 s | 81 µs |
| 20 | 0.66 s (160 MB) | 11.6 s (354 MB) | 0.1 ms |
| 22 | 3.4 s (0.58 GB) | not run (capped at n = 20) | — |
| 24 | 15 s (2.4 GB peak RSS) | — | 0.17 ms |
| 25 | refused: memory estimate 5.6 GB > 4 GB budget | — | — |

The greedy times are the minimum of 5 repeats.

* **[Observed]** Time roughly doubles or more for each added string, matching
  O(n² 2ⁿ). Memory, O(n 2ⁿ), is the binding constraint first. Under our 4 GB
  budget, the limit is n ≈ 24 for the vectorised engine and around n ≈ 20 for
  readable pure Python, where one run takes about 12 s.
* In the standard experiment, the DP solve time at n = 20 had median 0.70 s and
  maximum 1.23 s.

## 3. Real sequencing data (phiX174, ERR098007)

Provenance and choices are in `docs/dataset_manifest.md` and
`data/bio/extraction_record.json`.

* **Data:** 76 bp single-end Illumina GA IIx reads, kept in the orientation the
  sequencer reported. No quality filtering was applied.
* **Two sampling conditions,** with 30 subsets for each n ∈ {5, 8, 10, 12, 15, 18}:
  * **unconditioned:** reads drawn at random from all eligible reads, including
    those with errors;
  * **local-region:** reads that match the "+" strand of the reference exactly
    and start inside a random 250 bp window. This is reference-assisted and
    deliberately enriched for overlapping reads.

Results for `lowest_id` (deep_dive section 5):

| Condition | Instances | Optimality rate | Max G/OPT | Max G − OPT | Median fraction of pairs with overlap > 0 | Median OPT |
|---|---|---|---|---|---|---|
| bio_unconditioned | 180 | 0.811 | 1.003 | 3 chars | 0.33 | 745 |
| bio_local | 180 | 1.000 | 1.000 | 0 | 0.57 | 210 |

**[Observed]**
* In the unconditioned condition, preprocessing removed almost nothing (0.1%).
  Most read pairs either do not overlap or overlap by a few characters by
  chance.
* Even so, tie-breaking mattered: the 13 runs disagreed on G for 46% of
  unconditioned instances.
* In the local condition, overlaps are long (mean overlap about 16, maximum up
  to about 68) and ties are rarer. Greedy was optimal in all 180 subsets under
  every policy and seed.

**[Explanation?]**
* Exact, error-free reads from a short non-repetitive window form a simple path
  with long, unique overlaps. Greedy's maximum-overlap choices then coincide
  with the true layout.
* The unconditioned suboptimality comes from spurious 1–3 character overlaps
  between unrelated reads. That is why G/OPT is tiny, at most 1.003, even
  though about 19% of instances are not optimal.
* Long reads make the ratio small but do not make greedy optimal.

**Comparison with the synthetic families at matched n:**
* The unconditioned reads behave like the random family over a 4-letter
  alphabet: similar overlap density and optimality rates of 0.6–0.9.
* Ratios are far closer to 1, because OPT is in the hundreds of characters
  rather than tens.
* The local reads behave like high-coverage fragments with long strings and a
  4-letter alphabet, which is our best synthetic cell (0.983).

**Limitations of the bio experiment.** It is about shortest superstrings of the
supplied strings, not genome assembly.
* **Sequencing errors.** 50% of eligible reads do not occur exactly in the
  reference. Errors break true overlaps and create spurious ones.
* **Orientation.** About 17% of exactly placed reads come from the reverse
  strand. We kept reads as given, and did not add reverse complements, because
  that would change the optimisation problem.
* **Coverage, pairing, repeats and variation.**
  * Coverage is uneven.
  * The run is single-end, so there is no pairing information.
  * phiX is short and has few repeats.
  * A local window says nothing about repeat-rich genomes.
* **Exact matching and local sampling.** Our exact-match placement is a toy,
  not an aligner. The local condition keeps only error-free reads, so it is
  not representative of all reads.
* **OPT is not the genome length.** The reference genome length is never OPT:
  it can include regions no sampled read covers, and reads with errors are not
  substrings of it. The DP certifies OPT only for the exact strings supplied.

## 3b. Optional extension: reproducing Shibata's construction

Source: H. Shibata, arXiv:2609.01365v1 (1 Sep 2026). This is a preprint and
has not been peer reviewed. We read the construction from the arXiv HTML
(Sections 3.1 and 5) and implemented it in `scs/shibata.py`. The experiment is
`scripts/shibata_experiment.py`; its outputs are `results/shibata/shibata.md`,
`shibata.jsonl`, and `trace_k10_t1.json`, which is a full step-by-step trace for
k = 10, t = 1.

### The instance

* **Strings.** S_{k,t} contains every length-k cyclic substring of 3t periodic
  base strings U_i, V_i, W_i, over the alphabet {x, y, a, b_1..b_t}. In total
  that is n = t(2k+2) distinct strings, each of length k.
* **The "bad" run.** First, the cyclic substrings of each base string are merged
  around the cycle; each of these merges uses overlap k − 1. The paper chooses a
  specific starting point for each cycle. Then come
  * V̂_i ⊙ Û_i, with overlap s − 3, where s = k/2;
  * M_1 ⊙ … ⊙ M_t, with overlap 1;
  * the Ŵ_i blocks appended with overlap 0.

### What we checked

None of these checks relies on the paper's proofs.

1. **Legality.** We replayed the paper's scripted merge sequence. At every step
   we used a naive routine to recompute the overlaps of all ordered pairs of
   current strings, and checked that the chosen pair attains the current
   maximum. **[Observed]** All steps are legal greedy choices for all 15
   (k, t) combinations we tried, k ∈ {10, 12, 16, 20} and t up to 16. The first
   step faces many tied pairs.
2. **The output.** It contains every input, and its length equals the paper's
   formula t(9s+1)+1.
3. **OPT certificate.**
   * Lower bound: n distinct strings of length k need at least n distinct
     length-k windows, so OPT ≥ n + k − 1.
   * Upper bound: we built an explicit superstring of exactly that length from
     an Eulerian circuit of the order-(k−1) de Bruijn graph, and checked that
     it contains every input.
   * **[Proven]** for each instance by this pair of bounds, which match the
     paper's OPT = t(4s+2)+k−1.
   * For k = 10, t = 1 (n = 22) the exact subset DP independently gives
     OPT = 31.

### Results (excerpt from `results/shibata/shibata.md`)

| k | t | n | OPT | Scripted greedy G | G/OPT | Compression (L−G)/(L−OPT) |
|---|---|---|---|---|---|---|
| 10 | 1 | 22 | 31 | 47 | 1.516 | 0.915 |
| 10 | 8 | 176 | 185 | 369 | 1.995 | 0.883 |
| 10 | 9 | 198 | 207 | 415 | **2.005** | 0.883 |
| 10 | 16 | 352 | 361 | 737 | 2.042 | 0.881 |
| 20 | 16 | 672 | 691 | 1457 | **2.109** | 0.940 |

**[Observed]** On these explicit instances, a legal maximum-overlap greedy run
exceeds G = 2·OPT. The first such case among our grid is k = 10, t = 9, at
n = 198. The paper's limit (9k+2)/(4k+4) is approached as t grows.

This is a finite, machine-checked confirmation of the paper's construction for
these parameters. **[Proven]** for these specific inputs: G/OPT > 2 for some
legal greedy run, so the conjecture "every greedy run is within 2·OPT" fails on
them. That conclusion is only as strong as our checker and certificate code,
which are covered by tests (`tests/test_shibata.py`).

### What else the reproduction shows

* **Tie-breaking.** Our own tie rules do much better on the same inputs. For
  k = 10, t = 9:
  * `lowest_id` gives 334, `highest_id` 378 and `lex_merged` 387, i.e. G/OPT
    1.61–1.87;
  * 50 random-tie runs give 245–322.
  * At t = 1, some random seeds even reach OPT.

  The 9/4 lower bound is a statement about the worst legal tie-breaking, not
  about typical greedy runs. This matches what we saw in RQ3.
* **Compression vs length ratio.** Even at G/OPT > 2, the compression ratio
  stays around 0.88–0.94, far above the proven 1/2. This is a concrete example
  of why the half-compression theorem and the G ≤ 2·OPT conjecture are
  different statements.

## 3c. Optional extension: OpenAI's 2-approximation compared with greedy

Source: OpenAI, "A Polynomial-Time 2-Approximation for Shortest Common
Superstring", preprint dated 24 Sep 2026 (`openai/math` on GitHub; not peer
reviewed; `docs/literature.md` source 12). The paper claims a deterministic
polynomial-time algorithm whose output is never longer than 2·OPT. That claim
is about its own algorithm, not greedy, so it is consistent with Shibata's
result in section 3b.

`docs/algorithms.md`, section 5, explains the algorithm. In short:
* it computes, for every substring, a minimum number of times it must occur in
  any superstring;
* from these counts it builds a graph of cost W, and **[Proven, paper Lemma
  2.1]** W ≤ OPT;
* it connects the pieces of that graph at an extra cost of at most W;
* it reads the output off an Euler tour, so the output length is at most
  2W ≤ 2·OPT.

Our implementation is `scs/two_approx.py`. Every step the paper proves is
checked again while the code runs.

Outputs:
* `results/two_approx/` holds the runner output of `configs/two_approx.json`
  (91 instances).
* `results/two_approx/summary.md` and `standard_rescore.jsonl` come from
  `scripts/two_approx_summary.py`. That script also runs the algorithm on all
  4,953 instances of `results/standard` that have an exact OPT, reusing the
  stored OPT and greedy lengths.

### What we checked

* **[Observed]** On all 4,953 standard instances, the 91 instances of the new
  config, and 8 Shibata instances:
  * no run-time check failed;
  * every output contains every input;
  * W ≤ OPT and the output is ≤ 2·OPT in every case.

  The random tests in section 5 of `docs/verification.md` add about 100k
  smaller inputs, also with no failure. This is evidence for the preprint on
  small inputs, not a proof. Two of the paper's connection cases never came up
  (`docs/verification.md`).

### Results (from `results/two_approx/summary.md`)

Standard instances, lengths divided by exact OPT ("worst run" is the longest
of an instance's 13 greedy runs):

| family | instances | 2-approx mean / max | W/OPT mean | greedy `lowest_id` mean | greedy worst run mean / max |
|---|---|---|---|---|---|
| random | 1260 | 1.281 / 1.897 | 0.991 | 1.009 | 1.022 / 1.222 |
| fragments | 2100 | 1.259 / 1.800 | 0.983 | 1.010 | 1.022 / 1.583 |
| repetitive | 1575 | 1.270 / 1.824 | 0.981 | 1.017 | 1.031 / 1.435 |
| all (incl. known, discovered) | 4953 | 1.268 / 1.897 | 0.984 | 1.012 | 1.026 / 1.625 |

Blum-style family `c(ab)^k, (ba)^k, (ab)^k c` (known instances):

| k | OPT | W | 2-approx | greedy (every run) |
|---|---|---|---|---|
| 2 | 8 | 7 | 10 | 10 |
| 4 | 12 | 11 | 14 | 18 |
| 6 | 16 | 15 | 18 | 26 |

Shibata's S_{k,t} (OPT certified, section 3b):

| k | t | OPT | W | 2-approx | scripted greedy |
|---|---|---|---|---|---|
| 10 | 1 | 31 | 22 | 43 (1.387) | 47 (1.516) |
| 10 | 9 | 207 | 198 | 387 (1.870) | 415 (2.005) |
| 12 | 8 | 219 | 208 | 408 (1.863) | 441 (2.014) |

### What the results show

* **[Observed] On typical inputs, greedy is much better.** The 2-approximation
  averages 1.27·OPT, against 1.01 for `lowest_id` and 1.03 for the worst
  greedy run. On 4,868 of the 4,953 instances it is longer than every greedy
  run. It is never shorter than the best greedy run, except on 4 Blum-style
  instances.
  * **[Explanation?]** The method does not adapt to the input. It adds a
    connecting walk for every layer, even when the graph is already connected.
    That extra cost averages 0.29·W. Its ratio falls with n, from 1.32 at n = 5
    to 1.22 at n = 20, perhaps because pieces share more of their cost on
    larger inputs.
* **[Observed] Its advantage shows up only on adversarial inputs.**
  * On the Blum-style family, greedy is forced to about 2·OPT, but the
    2-approximation stays at OPT + 2.
  * On S_{k,t} it beats the paper's scripted greedy run and stays under 2·OPT
    where that run exceeds it (k = 10, t = 9: 1.870 vs 2.005). Its ratio still
    rises toward 2 as t grows, because W = n there is well below OPT.
  * Our ordinary tie rules do better still on S_{10,9}: `lowest_id` gives 334
    (section 3b).
* **[Observed] W is a strong lower bound.** W equals OPT exactly on 3,086 of
  the 4,953 standard instances (62%), and averages 0.984·OPT; the lowest seen
  was 0.60·OPT. W takes polynomial time to compute, so wherever a heuristic
  finds a superstring of length W, that superstring is certified optimal with
  no DP. On S_{k,t}, though, W = n is far below OPT = n + k − 1.

## 4. Limitations of the study

* **Size and scope.** Exact OPT exists only for n ≤ 20 here (≤ 24 is feasible).
  Conclusions about larger n, or about the worst case, do not follow.
* **Instance families.** These are our own design choices; other generators
  could behave differently.
* **Sampling of inputs.** Retained-size control makes the raw input count
  random, and binary short-string cells keep many more draws than they retain
  (up to about 26 draws per retained string). The mix of contained and
  duplicate strings therefore differs between cells.
* **Tie-breaking.** 13 runs sample the space of tie choices; they do not bound
  it. The deterministic rules depend on our ID convention (lexicographic
  order of retained strings).
* **Timing.** Timings come from one Windows machine under Python, and only
  their relative scaling is meaningful. Greedy times are the best of 5 repeats;
  DP times come from a single run each.
* **Literature.** For several older sources and all 2026 preprints, only the
  abstract or bibliographic record was checked. Unresolved items are listed in
  `docs/literature.md`, section 3.
* **Shibata reproduction.** It checks the paper's construction only for the
  listed (k, t). It does not check the general proofs, the 9/4 limit itself,
  or peer-review status. We implemented the construction from our reading of
  the arXiv HTML; a misreading would show up as an illegal step or a length
  mismatch, and neither occurred.

* **2-approximation (section 3c).** We implemented the algorithm from our
  reading of the preprint's PDF text, and some mathematical symbols were lost
  in text extraction. A misreading would most likely trip one of the run-time
  checks, but a misreading that still passes them cannot be ruled out. OPT
  comparisons cover only n ≤ 20 and the certified S_{k,t}.

## 5. Unresolved items and next steps

* **W as a certificate.** Cases where the best greedy run reaches W are
  certified optimal without a DP. That could extend exact-OPT comparisons
  beyond n = 20 for some instances; not yet measured.

* **Larger extended study.** `configs/extended.json` (n up to 20, more reps) is
  executable but was not run. Its estimated cost is 20–25 minutes.
* The unresolved literature claims in `docs/literature.md`, section 3.
