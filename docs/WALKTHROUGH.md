# Presenter walkthrough (about 10 minutes)

## 1. The problem in one example

The inputs are `BAB`, `AABA` and `ABAA`. We want the shortest string that
contains all three.

* `ov(x, y)` is the longest suffix of x that is also a prefix of y.
* The overlaps that matter here:
  * ov(AABA, ABAA) = 3
  * ov(BAB, ABAA) = 2
  * ov(ABAA, AABA) = 2
* **Greedy** always merges the pair with the largest overlap:
  * Step 1: AABA + ABAA → `AABAA`, using the overlap of 3.
  * Step 2: nothing overlaps any more, so it concatenates `BAB` → `BABAABAA`.
    Length 8.
* **Optimal:** `BABAABA`, length 7, in the order BAB → ABAA → AABA with
  overlaps 2 and 2.
* **Lesson:** one big overlap can use up two strings that each had a good
  partner elsewhere.

Run it yourself:

```bash
python -c "from scs.preprocess import preprocess; from scs.greedy import greedy; from scs.exact_dp import exact_dp; r=preprocess(['BAB','AABA','ABAA']).retained; print(greedy(r,trace=True)); print(exact_dp(r))"
```

## 2. The code, file by file

1. **`scs/preprocess.py`** removes empty strings, duplicates and strings
   contained in another input. These removals never change the answer.
   * The remaining strings are sorted, and each one's position becomes its ID.
     That way the result does not depend on input order.
2. **`scs/overlap.py`** computes all pairwise overlaps. It uses the KMP failure
   function, which takes time linear in the two string lengths per pair.
3. **`scs/greedy.py`** repeatedly finds every pair that has the maximum
   overlap, picks one with a tie rule and merges the two strings.
   * The four tie rules are `lowest_id`, `highest_id`, `lex_merged` and
     `random`.
   * Each merge can be recorded in a trace.
4. **`scs/exact_dp.py`** computes the exact optimum. The state is "which
   strings have been used, and which came last"; the time is n²·2ⁿ.
   * It has two engines: readable pure Python and a faster numpy version.
5. **`scs/validate.py` and `scs/oracle.py`** check the other modules
   independently:
   * brute force over all permutations;
   * brute force over all candidate strings;
   * a replay of every greedy step that recomputes the overlaps from scratch.
6. **`scs/generators.py`** builds the input families: random, fragments,
   repetitive, known and discovered. **`scs/runner.py`** runs every algorithm on
   the same instances with fixed seeds. It runs the DP in a child process with
   a timeout and a memory limit, and it can resume an interrupted run.
7. **`analysis/analyze.py` and `analysis/deep_dive.py`** produce the tables and
   figures.

## 3. The results in five points

These come from 4,953 synthetic instances with exact OPT, n from 5 to 20. The
full write-up is `docs/FINDINGS.md`.

1. **Greedy is usually optimal or very close.**
   * G = OPT in 65–73% of instances, depending on the family.
   * The median G/OPT is 1.
   * The worst sampled ratio is 1.58.
   * The hand-built bad family reaches 1.625, and published constructions go
     to 2 and beyond. Random sampling does not find the worst cases.
2. **Some inputs make greedy worse:**
   * a small alphabet;
   * strong repetition (short motif, few mutations);
   * more strings.

   Within a fixed setting, simple features such as overlap density barely
   separate the good instances from the bad ones.
3. **Tie-breaking matters a lot.**
   * At n = 20, 68–73% of instances give different lengths under different
     tie choices.
   * At n = 20, the best of the 13 runs is optimal about 80–90% of the time;
     the worst run is optimal only 20–30% of the time.
4. **Half-compression:**
   * Greedy always saved at least half of what the optimum saves.
   * The 1/2 is reached exactly on small instances, so the theorem is tight.
   * Typically greedy saves at least 90% of what the optimum saves.
5. **The exact DP hits a wall:**
   * The numpy engine takes 0.7 s at n = 20 and 15 s at n = 24, using 2.4 GB.
   * n = 25 exceeds our 4 GB memory budget.
   * Pure Python already takes 12 s at n = 20.

**Real reads (phiX174):**
* When reads are sampled from one small region, greedy was optimal in every
  case.
* When reads are sampled at random:
  * greedy was optimal in 81% of cases;
  * when it was not, it lost at most 3 bases, out of 294–1,328.

This is not genome assembly: the model does not handle sequencing errors,
reverse complements or repeats.

## 4. Likely questions and honest answers

* **"Does this prove greedy is a 2-approximation?"** No. Experiments cannot
  prove a bound. A 2026 preprint claims the 2-approximation conjecture is false
  when ties are broken adversarially; it is not peer reviewed yet.
* **"Why trust the DP?"** It matches three independent oracles on hundreds of
  tiny instances. Every output is also checked to contain every input.
* **"Why does preprocessing matter?"** If one string contains another, the
  "order the strings" formulation can produce wrong lengths. Removing contained
  strings makes it exact.
