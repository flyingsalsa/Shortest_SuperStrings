# Independent verification summary (Agent C)

Run: `.venv/Scripts/python -m pytest -q` (100 tests, about 5 s; `-m "not slow"`
skips 2 slow tests). All 100 passed against the implementation delivered by
Agents A and B at the time of writing. No violation of the half-compression
inequality was found and no implementation bug was found.

## Why the oracles are independent

The verification code lives in `scs/validate.py` and `scs/oracle.py` and imports
nothing from `overlap.py`, `preprocess.py`, `greedy.py` or `exact_dp.py`.

* `_ov` (validate/oracle): a separate, deliberately naive overlap routine.
  Production uses KMP; tests also compare against `overlap_naive`.
* `oracle._clean`: separate preprocessing (drop empties, set-dedupe, drop
  strings contained in another) written with `in` and sets.
* `brute_force_permutations`: tries every permutation of the cleaned strings and
  merges consecutive strings by maximum pairwise overlap. No subset DP, no
  recurrence.
* `brute_force_superstring`: enumerates every string over the alphabet in
  increasing length and tests containment of every input with `in`. It does not
  use the overlap/ordering formulation, so it checks that formulation itself.
* `shortest_superstring_bfs`: a third, structurally different exact method:
  BFS over states (set of covered inputs, last ell-1 characters), appending one
  letter at a time. The three oracles agree on 80 + 150 random instances
  (`tests/test_oracles.py`) and on the hand-checked known values.
* `replay_greedy_trace`: replays a trace from the initial strings; at every step
  recomputes ALL ordered pair overlaps naively on the ACTUAL current strings (so
  the `ov(c,x)=ov(b,x)` shortcut of the implementation is not trusted), and
  derives the true max, tie set, policy choice (including the `random.Random(seed)`
  stream with one `randrange(len(T))` per step), merged strings, final
  superstring, order, `sum_overlap`, `n_tie_steps`, `max_tied`.

## What each check verifies and how many instances

| Test file | Check | Scale |
|---|---|---|
| `test_oracles.py` | oracles agree with each other and with hand-computed values | 10 known cases, 80 + 150 random |
| `test_preprocess_overlap.py` | overlap (KMP) == `overlap_naive` == own naive on random pairs (incl. empty, unequal, periodic, separator characters); `overlap_matrix`; preprocess == independent cleaning, reasons/witnesses valid, every input accounted for, input-order invariance | 4000 pairs, ~1100 instances |
| `test_dp.py` | `exact_dp` and `exact_dp_numpy` == `brute_force_permutations` | 900 instances each (600 raw-random with n<=7 plus 300 "rich" instances whose retained size is 3..7); two engines identical in length, order and string |
| `test_dp.py` | DP == direct enumeration == BFS on alphabet {A,B}, OPT <= 11 | 60 instances per engine |
| `test_dp.py` | output contains every ORIGINAL input; reported length == len(superstring); order valid (`check_order`) | all of the above |
| `test_greedy.py` | all 4 policies: output contains originals, trace replays with no problem, order valid, `length == L - sum_overlap`, trace/no-trace give same results | 700 instances x 4 policies |
| `test_greedy.py` | invariants checked directly (chosen overlap is the global max, active set substring-free at each step) | 200 instances x 4 policies |
| `test_greedy.py` | half-compression `L - G >= (L - OPT)/2`, all policies (random: 2 seeds), and `G >= OPT`, `G <= 4 OPT` | 1400 instances (>5000 greedy runs) in the default suite, plus 6000 instances (larger n up to 9) in the slow test. Non-vacuous: the sample contains instances with `G > OPT`; no violation found |
| `test_greedy.py` | determinism under input permutation; random policy reproducible per seed, differs across seeds, never touches the global RNG; argument validation | 150 permutations |
| `test_validators.py` | mutation tests: 15 corruptions (n_tied, overlap, max_overlap, merged, superstring, length, order, counters, active_before, ids, inactive pair, dropped step, wrong tied pair, wrong policy, wrong seed, missing trace) are all reported | 4 policies |
| `test_regression.py` | ATT/TTA/TAC OPT 5; BAB/AABA/ABAA OPT 7, greedy 8 (all four policies give 8: the first maximum, overlap 3, is unique); ABC/BCDE; AAA/BBB/CCC (greedy = OPT = 9, tie counts 6 then 2); heavy preprocessing; empty / all-empty / singleton / duplicates; unequal lengths; all binary strings of length 2 and 3; unary strings; Blum-style family | hand-checked |
| `test_two_approx.py` (added 2026-11-06) | OpenAI 2-approximation (`docs/algorithms.md` section 5): blocking functional == brute force over definition (2.1)-(2.3); the paper's `a^h` example; Lemma 2.1 (`m(s) <= N_T(s)` for a DP-optimal `T`, so `W <= OPT`); base graph balanced with cost `W`; layers reproduce the base edges, pointwise ordered, budgets sum to `W` (Lemma 3.2); Lemma 4.1 walks (cost, closure, short vertex); band join (4.2) and a hand-built two-child host (4.4); end to end: superstring of the ORIGINAL inputs, `W <= OPT`, `length <= 2 OPT`, `added_cost <= W`; one regression input per connection branch; known instances; Shibata S_{k,t}; runner rows and guards | 60 random sets of blocking cases, 80 instances for Lemma 2.1, ~450 random/periodic end-to-end instances, 3 Shibata instances |
| `test_generators.py` | same (family, params, seed) -> identical Instance; different seeds differ; retained mode hits n exactly iff `n_target_reached`; fragments are substrings of the source at the stated positions; unreachable target flagged; `known_instances` expected values equal DP and brute force | 7 configurations x 40 seeds |

## What passing finite tests does NOT prove

* They are sampling tests on tiny instances (retained n <= 9, alphabets <= 4,
  lengths <= 7). A bug that only appears for large n, long strings, large
  alphabets (e.g. DNA at scale), or memory/time limit behaviour could remain.
* Agreement of two engines or oracles shows consistency, not truth. Truth rests
  on three structurally different oracles agreeing and on hand-checked values;
  all share Python's `in`/slicing semantics.
* The half-compression bound is a theorem; a finite sample cannot prove it for
  the implementation, only fail to refute it. It does not constrain the actual
  approximation ratio for length (the 4x and 3.5x guarantees are not tested).
* The replay validator checks one run's trace against the policy specification
  in `docs/INTERFACES.md`; it does not validate the specification itself, nor
  runs without `trace=True` (those are compared only through final results).
* The runner, CLI, timeouts, memory refusal, resume logic and result-row
  schema are not covered by these tests.
* `two_approx`: a seeded search over ~100k small inputs never reached two
  connection branches: the link below a baseline (Sec. 5.1) and the band join
  of upper layers (Sec. 5.2). The band join is unit-tested in isolation; the
  first has no test. The `<= 2 OPT` guarantee is only checked where the DP
  gives OPT (n <= 12 in tests), plus the certified OPT of S_{k,t}.
* Random-instance sampling is biased toward small retained sets; "rich"
  instances were added to counter this, but adversarial structure (for example
  larger Blum-style gaps) is only covered by the hand-written family.
