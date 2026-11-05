# Algorithms: preprocessing, overlaps, greedy, exact DP

Notation as in `docs/INTERFACES.md`: `n` retained strings, `ell` maximum
length, `L` total retained length, `ov(x, y)` the longest suffix of `x` that is
a prefix of `y`.

## 1. Preprocessing and the permutation formulation

### 1.1 Why preprocessing preserves OPT

The input is a list of strings; a *superstring* contains each of them as a
substring.

* **Empty strings.** The empty string is a substring of every string, so
  deleting it changes neither the set of valid superstrings nor OPT.
* **Duplicates.** A superstring contains `s` iff it contains any copy of `s`,
  so keeping one copy changes nothing.
* **Contained strings.** If `s` is a proper substring of `t` and `w` contains
  `t`, then `w` contains `s` (substring is transitive). Hence the superstrings
  of `S` and of `S \ {s}` are exactly the same, and OPT is unchanged. Removing
  `s` is safe even if `t` is itself removed later, because the relation is
  transitive: every removed string is contained in a *maximal* string that
  stays. (Our witness is the longest container, which is always such a maximal
  string.)

So after preprocessing, every valid superstring of the retained set `R` is a
valid superstring of the original set and vice versa; OPT(original) = OPT(R).
`R` is *substring-free*: its strings are distinct and none is a substring of
another.

### 1.2 Why a permutation suffices

Let `w` be any superstring of a substring-free set `R`. For each `s` in `R`
fix its first occurrence in `w`, with start position `p(s)` and end position
`e(s) = p(s) + |s|`.

* Start positions are distinct: two strings starting at the same position would
  have the shorter as a prefix of the longer, i.e. contained in it.
* End positions are in the same order as start positions: if `p(s) < p(t)` but
  `e(s) >= e(t)` then `t` lies inside the occurrence of `s`, so `t` is a
  substring of `s`, a contradiction. (For the same reason ends are distinct.)

List the strings in order of start position: `s_1, ..., s_n`. Consecutive
occurrences either overlap or leave a gap (positions of `w` covered by neither
string, or only covered by other strings that occur further on). Define `k_i`
as the length of the overlap of the occurrences of `s_i` and `s_{i+1}` in `w`
(0 if they do not overlap). Because `e(s_i) < e(s_{i+1})` and `p(s_i) <
p(s_{i+1})`, the common part is a suffix of `s_i` that is a prefix of `s_{i+1}`,
so `k_i <= ov(s_i, s_{i+1})`. Intervals sorted by both start and end satisfy
`I_i ∩ I_{i+2} ⊆ I_{i+1}`, so the union of the `n` occurrences has length
exactly `L - sum k_i`; it is at most `|w|`, hence

    |w| >= L - sum_i k_i >= L - sum_i ov(s_i, s_{i+1}).

Conversely, for any permutation `pi`, merging consecutive strings with their
maximum overlaps gives a string of length `L - sum ov(s_pi(i), s_pi(i+1))`
that contains all strings (each `s_pi(i+1)` is appended after removing the
part it shares with the previous string; since the set is substring-free the
merged string really contains every `s`). Therefore

    OPT = L - max over permutations pi of sum of consecutive ov,

and the problem is to choose the best ordering. Both greedy and the DP use this
formulation: greedy builds a permutation by merging, the DP searches all
permutations without enumerating them.

### 1.3 Implementation and cost (`scs/preprocess.py`)

Empty strings and duplicates are found with one pass and a dict
(first occurrence wins). Containment compares every distinct non-empty string
`s` with every strictly longer distinct string `t` using Python's `s in t`
(visiting longer strings first, so the first hit is the longest container with
the smallest original index). Worst case this is O(n^2 * ell^2) time
(`in` can take O(|s||t|) in theory; CPython's search is fast in practice,
roughly O(n^2 * ell)). The retained strings are sorted with `<`, so output does
not depend on input order or hash/set iteration order.

## 2. Exact dynamic programming (`scs/exact_dp.py`)

State `(M, j)`: `M` is a set of strings (bitmask), `j` in `M` is the string
placed last. `D[M, j]` is the minimum length of a string that contains all
strings of `M` and *ends with the merged block ending in `s_j`* (i.e. the best
over orderings of `M` ending in `j` of `sum |s| - sum consecutive ov`).

    D[{j}, j]  = |s_j|
    D[M, j]    = min over i in M \ {j} of  D[M \ {j}, i] + |s_j| - ov(s_i, s_j)
    OPT        = min over j of D[all, j]

**Why `(M, j)` suffices.** In an ordering of `M` ending with `i, j`, the total
length is (length of the ordering of `M \ {j}`) `+ |s_j| - ov(s_i, s_j)`. The
extra cost of appending `j` depends only on the *last* string `i` of the prefix
ordering, not on how the other strings were arranged. So for a fixed `i`, the
best completion is to take the best prefix ordering ending in `i`
(optimal substructure): replacing the prefix by a shorter one with the same set
and same last string never makes the total longer. Taking the minimum over `i`
gives the recurrence. A predecessor table `P[M, j]` stores the argmin (smallest
`i` on ties); the order is recovered by walking back from the best `j` for the
full set, and the superstring is built by merging consecutive strings with
their overlaps. The code asserts `len(superstring) == D`.

**Cost.** There are `2^n * n` states and each is computed in `O(n)` time, so
`O(n^2 2^n)` time and `O(n 2^n)` space, after the `O(n^2 * ell)` overlap matrix
(word-RAM accounting: table entries and arithmetic are O(1)).

Two engines:

* `exact_dp`: pure Python lists, flat index `mask*n + j`. Python's per-operation
  overhead makes it practical only up to about n = 14 (measured ~0.1 s at
  n = 14 on the development machine; time doubles per added string, more
  than doubles with the factor n^2). Each table entry is a Python object, so
  memory is ~48 bytes per state (see `estimate_dp_memory_bytes`).
* `exact_dp_numpy`: `int32` cost table of shape `(2^n, n)`, `int8` predecessor
  table. Masks are processed by popcount layer; for each last string `j`,
  every mask of the layer containing `j` is updated with one array operation
  (`D[prev] + cost_j` then `argmin` along the predecessor axis). Same asymptotic
  work, far smaller constant, 5 bytes per state plus temporaries of the
  largest layer. `argmin` returns the first minimum, so tie-breaking equals
  the pure-Python engine and the two return identical orders.

## 3. Greedy (`scs/greedy.py`)

### 3.1 Description

Start with the `n` retained strings as *active* strings (IDs `0..n-1`).
Repeat `n-1` times: find the maximum `m` of `ov(a, b)` over ordered pairs of
distinct active strings; choose one pair `(a, b)` attaining it; replace `a` and
`b` by the merged string `a + b[m:]`, which gets the new ID `n + t` at merge
number `t`. The result is the single remaining string. Total overlap used
`sum_overlap` gives `length = L - sum_overlap`. Merges with `m = 0` are plain
concatenations and the pair is still chosen by the policy.

### 3.2 Tie policies

The *tie set* `T` is the set of all ordered pairs attaining the maximum
(including all ordered pairs when `m = 0`). Classical greedy descriptions
leave the choice open; the choice can change the output length, so this project
fixes it by policy:

* `lowest_id`: smallest `(a, b)` tuple. Since retained strings are sorted
  lexicographically, ID order is lexicographic order of the original strings,
  and merged strings (newer IDs) lose to older ones.
* `highest_id`: largest `(a, b)`, preferring recently merged strings.
* `lex_merged`: the pair whose merged string is lexicographically smallest,
  then the smallest `(a, b)`; independent of ID assignment.
* `random`: uniform from `T` sorted by `(a, b)`, using a local
  `random.Random(seed)` and exactly one `randrange(len(T))` per merge.

### 3.3 The overlap update shortcut and its proof

After merging `a, b` into `c = a + b[m:]` (with `m = ov(a, b)`), recomputing
all overlaps of `c` from scratch costs `O(n * ell')` each. Instead the code
sets, for every other active string `x`,

    ov(c, x) = ov(b, x)      and      ov(x, c) = ov(x, a).

**Invariant.** The active set is *substring-free* (distinct strings, none a
substring of another). It holds initially (preprocessing). We prove that one
maximum-overlap merge preserves it.

**Lemma 1 (invariant is preserved).** Let the active set `S` be substring-free,
`m = max` over ordered pairs of distinct strings of `S` of `ov`, and
`ov(a, b) = m`, `c = a + b[m:]`. Then `S' = S \ {a, b} + {c}` is substring-free.

*Proof.* Pairs not involving `c` are unchanged. Let `x` in `S \ {a, b}`.

1. *`c` is not a substring of `x`* (nor equal to it): `c` contains `a`
   (as a prefix), so `c` in `x` would give `a` in `x`.
2. *`x` is not a substring of `c`.* In `c`, `a` occupies positions
   `[0, |a|)` and `b` occupies `[|a|-m, |c|)`; the two ranges cover `c` and
   overlap in `m` positions. Suppose `x` occurs at `[p, q)` in `c`. If
   `q <= |a|`, `x` lies inside `a`; if `p >= |a|-m`, `x` lies inside `b`;
   both are impossible by substring-freeness of `S`. So `p < |a|-m` and
   `q > |a|`. Put `l = q - (|a| - m)`; then `l > m`. The block
   `c[|a|-m : q]` is a prefix of `b` (since `b` starts at `|a|-m`) of length
   `l <= |b|` and it is a suffix of `x`'s occurrence `c[p:q]`, with
   `l < q - p = |x|`. Hence `ov(x, b) >= l > m`, contradicting maximality of
   `m` (`x != b` are distinct active strings). ∎

The argument is the same when `m = 0`: then `a` and `b` are just concatenated,
`b` starts at `|a|`, a straddling occurrence needs `l = q - |a| >= 1 > 0`, and
would give a positive overlap `ov(x, b)` although the maximum is 0. (Symmetric
argument with `ov(a, x)` also works.) The case analysis is exhaustive: every occurrence of `x` in `c` lies inside
`a`, inside `b`, or starts before `b` and ends after `a`.

**Lemma 2 (the shortcut).** If `S` is substring-free and `x` in `S \ {a, b}`,
then `ov(c, x) = ov(b, x)` and `ov(x, c) = ov(x, a)`.

*Proof.* `ov(c, x)` is the largest `k <= min(|c|, |x|)` such that the length-`k`
suffix of `c` equals the length-`k` prefix of `x`. We claim any such `k` is
`< |b|`. Otherwise `k >= |b|`, and the length-`k` suffix of `c` ends with `b`
(since `c` ends with `b`), so `x` has `b` as a substring, contradicting
substring-freeness. For `k < |b|` the suffix of `c` of length `k` equals the
suffix of `b` of length `k`, so the set of valid `k` for `(c, x)` equals the
set of valid `k <= min(|b|, |x|)` for `(b, x)`, which is the definition of
`ov(b, x)`. Symmetrically, a valid `k` for `ov(x, c)` that is `>= |a|` would
make `a` (the prefix of `c`) a substring of `x`, so `k < |a|`, the prefix of
`c` of length `k` equals the prefix of `a`, and `ov(x, c) = ov(x, a)`. ∎

(Both lemmas use that `c` is longer than both parents; the overlap-0 case is
covered since `k = 0` is always valid.) By induction over the merges the
invariant holds at every step, so the shortcut is exact. The
validator (`replay_greedy_trace`) re-checks this independently with direct
overlap computation.

### 3.4 Cost

Each step scans all ordered pairs of active strings (`O(n^2)`), keeps the tie
list, and applies the policy: `O(|T|)` extra, or `O(|T| * ell')` for
`lex_merged` where string comparison of merged candidates is built on the fly.
Over `n-1` steps this is `O(n^3)` pair visits in the worst case. Building merged
strings by concatenation costs `O(L)` per merge, `O(nL)` total. The overlap
table has `(2n-1)^2` entries, `O(n^2)` memory; the update shortcut is `O(n)` per
merge. The initial overlap matrix is computed beforehand (section 4) unless
supplied. There is no priority queue; the cubic scan is deliberate for clarity
(n is at most a few hundred in the experiments). Python constant factors
dominate for n in the hundreds (about n^3/3 inner loop iterations).

## 4. Overlap computation (`scs/overlap.py`)

`overlap(x, y)`: compute the KMP prefix function of `y`, then run the KMP
automaton over `x`. After consuming all of `x`, the automaton state is the
longest prefix of `y` that is a suffix of `x`, which is `ov(x, y)`. When the
state reaches `|y|` it falls back through the prefix function before
reading the next character, so no separator character is needed.
Time `O(|x| + |y|)`. `overlap_naive` tries all `k` by slicing in `O(min^2)`.
`overlap_matrix` computes each prefix function once and scans `n-1` strings
against it: `O(n^2 * ell)` total (`O(n * ell)` for the prefix functions plus
`O(n^2 * ell)` for the scans), `O(n^2)` memory.

## 5. Summary

| Step | Time | Memory |
|---|---|---|
| preprocess | O(n^2 ell^2) worst case (Python `in`), about O(n^2 ell) typical | O(L) |
| overlap matrix | O(n^2 ell) | O(n^2) |
| greedy | O(n^3 + nL) | O(n^2 + L) |
| exact DP | O(n^2 2^n) | O(n 2^n) |
