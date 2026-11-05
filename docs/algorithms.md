# Algorithms: preprocessing, overlaps, greedy, exact DP, 2-approximation

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

## 5. OpenAI (2026) 2-approximation (`scs/two_approx.py`)

Source: OpenAI, "A Polynomial-Time 2-Approximation for Shortest Common
Superstring", preprint dated 24 Sep 2026 (`github.com/openai/math`,
`preprints/`). Not peer reviewed (see `docs/literature.md`, source 12). It
claims a deterministic polynomial-time algorithm whose output length is
`<= 2 OPT` on every input. The guarantee is for this algorithm, **not** for
greedy. Section numbers below are the paper's.

Unlike greedy and the DP, it does not use the permutation formulation. A
superstring is a closed walk in a graph whose vertices are substrings, and
the algorithm builds that walk in two halves, each costing at most `W <= OPT`.

### 5.1 The hierarchical graph

`V` is the set of all distinct substrings of the retained strings, including
the empty word `ε` (`|V| = O(L^2)`). Each nonempty `s` has an **up edge**
`pref(s) -> s` (append the last letter of `s`, cost 1) and a **down edge**
`s -> suf(s)` (delete the first letter, cost 0). Take a balanced edge multiset
(in-degree = out-degree at every vertex) whose support is connected, contains
`ε` and contains every input string. An Euler tour from `ε` writes down the
letter of each up step. At every point the current vertex is a suffix of the
text written so far, so the result is a superstring. Its length is the number
of up edges.

Example: the walk `ε -> a -> ab -> b -> bc -> c -> ε` writes `abc` and visits
`ab` and `bc`.

### 5.2 Forced occurrence counts and the lower bound W (Sec. 2)

For every nonempty `s ∈ V`, in decreasing order of length, `m(s)` is the
smallest integer satisfying all of these:

* `m(s) >= Σ_c m(cs)` and `m(s) >= Σ_c m(sc)`. Occurrences of `cs` for
  different letters `c` are disjoint occurrences of `s`.
* `m(s) >= 1` if `s` is an input.
* **The periodicity rule (2.6).** Let `v ∈ V` have a period `p` (not
  necessarily the least one), let `A` be its two-sided periodic extension, and
  let `w` be the prefix with `|v| = |w| + kp`. If `m(v) > B_A(v; m)`, then
  `m(w) >= B_A(w; m) + k + 1`.

Here `B_A(s; m)` counts occurrences of `s` that are **blocked** relative to
`A`. A blocked occurrence is surrounded by a substring
`r = c1 · A[-α, |s|+β) · c2` with `c1 != A(-α-1)` and `c2 != A(|s|+β)`: a
stretch agreeing with `A`, bracketed by one mismatching letter on each side.
Each such placement adds `m(r)` (2.3). The intuition: if some occurrence of
`v` is unblocked, it contains `k+1` unblocked occurrences of `w` at offsets
`0, p, ..., kp`. The rule records these repeated occurrences, which the
extension inequalities alone miss. For example, the single input `a^h` gets
`m(a^j) = h - j + 1`.

**Lemma 2.1:** `m(s) <= N_T(s)` (the number of occurrences of `s` in `T`) for
every superstring `T`. With `T` optimal, `W = Σ_c m(c) <= OPT`.

The implementation (`forced_counts`) enumerates periods with KMP borders and
evaluates `B_A` by growing the middle stretch `A[-α, |s|+β)` while it stays in
`V`.

### 5.3 The base graph (Sec. 2.3)

The up edge into `s` gets multiplicity `u(s) = m(s) - Σ_c m(cs)`. The down edge
out of `s` gets `d(s) = m(s) - Σ_c m(sc)`. Both are nonnegative by the first
rule. Telescoping shows the graph is balanced and has exactly `W` up edges.
Every input is maximal in `V`, so it has `u = d = m >= 1` and lies on the
graph. If this graph happened to be connected and to contain `ε`, its Euler
tour would already give length `W <= OPT`. In general it is disconnected.

### 5.4 Layers (Sec. 3)

Decompose the base graph into closed walks. Read the letters appended on a
walk's up steps cyclically. That word, repeated both ways, is the walk's
**periodic text**, and every vertex the walk visits is a window `[x, e)` of it.
Walks are grouped by primitive text up to rotation. Each group is stored by
its least rotation `R` (period `p = |R|`).

Within a group, the walks' passages are re-sorted (Lemma 3.2) into **layers**:
one-turn walks of period `p`. Each layer is described by one nondecreasing
function `z`: at start `x` it visits the windows `[x, e)` with
`z(x-1) <= e <= z(x)`, and `z(x+p) = z(x) + p`. The layers of a group are
pointwise ordered, low to high, and together they use exactly the base edges.
Each layer of period `p` costs `p` and receives an extra **budget** `p`. The
budgets add up to `W`, so the whole connection phase must cost at most `W`.

### 5.5 Connecting (Sec. 4–6)

Every connection is a closed walk that follows an ordered list of windows
(starts and ends nondecreasing) in one periodic text (Lemma 4.1). Its cost is
the total increase of the ends. Closed walks keep the graph balanced, so the
only goal is connectivity to `ε`. Groups are processed in increasing period.
For each group:

1. **Incoming requests (4.4).** Earlier, smaller-period groups may have sent
   *requests* to a layer of this group. Each host serves all its requests with
   one excursion paid by its own budget plus the requesters' reserved budgets.
   The highest host becomes a **baseline**. Every remaining layer below it is
   attached for its own budget `p`.
2. **Easy cases (5.2).** At the distinguished position `t` (start of the
   lexicographically greatest rotation), let `H` be the top layer's first end.
   If `H - t <= n p` (n = number of upper layers), a round trip `ε -> [t,H) -> ε`
   touches them all. Otherwise, if the baseline reaches within `n p` of `H`,
   a band join (4.2) attaches them all to it.
3. **Forced record (5.3).** Otherwise choose the smallest `k` for which at most
   `k` layers reach height `H - kp` at `t`. The count rule forces at least
   `k+1` unblocked occurrences of `w = A[t, H - kp)`, and at most `k` of them
   can lie on this text in this alignment. So some layer `D` has a window `R`
   containing `w` on a different aligned text. This window is the **record**.
   Lemma 3.4 (a Fine–Wilf-type bound) gives `|R| < p + q`.
4. **Distributing budgets (5.4).** The top `k` layers either form one
   **collective block** with a planned link to `D` (4.3, cost `kp`). Otherwise
   each upper layer is handled on its own: a round trip if it has a vertex of
   length `<= p`, an **individual block** with a planned cost-`p` link to `D`,
   or a request to `D`. Requests only go to strictly larger periods, so they
   are served later.

Every block has exactly one planned target. Following the targets, a
component either reaches a rooted layer or contains one directed cycle
(Sec. 6). On each cycle, the algorithm keeps the link of the block whose text
has the greatest distinguished rotation. Lemma 3.5 then gives a contact vertex
of length `<= q`, where `q` is the target's period. The target's own outgoing
link is dropped, and the target joins its layers internally for `(k-1)q`
(Lemma 6.1). That frees one period `q`, which pays for a round trip from the
contact to `ε`. The result is connected, balanced, contains `ε`, and has at
most `2W` up edges.

### 5.6 Implementation notes and checks

* Every finite choice is broken deterministically: sorted words, smallest
  index, first admissible window. The output is a function of the retained set.
* Every hypothesis the paper derives is asserted at run time. Failures raise
  `TwoApproxError`, never a silent fallback. Checked: the inequalities
  (3.1), (4.1), (4.2), (4.5), (5.2), (5.4), (5.9), (5.11), Proposition 5.2,
  and the contact lengths of Lemmas 4.4/6.2. Also: each added walk is a legal,
  closed walk in `V` within its budget, total added cost `<= W`, the final
  graph is connected (Euler tour uses every edge), and `|output| = W + added`.
  With `check=True` (the default), it also verifies that the layers reproduce
  the base edge multiset and that the output contains every input.
* For `n = 1` the algorithm is run as usual instead of returning the string.
  Its output can be longer than the input (`abaab -> 9` letters). This is the
  one exception to the `n = 1` convention in `docs/INTERFACES.md`.
* The construction is not adaptive. It adds connection walks even when the
  base graph is already connected (`a^16` gives 31 letters, greedy gives 16).
  So its typical ratio is far worse than greedy's, even though its worst case
  is proved better.
* Cost: `|V| <= L · ell` substrings, `O(|V| · ell log ell)` periodicity rules, each blocking
  functional `O(ell^2 σ^2)` dictionary look-ups. All later steps are
  polynomial in `W <= L`. In practice it takes a few ms per instance with
  `L <= 250` (standard config).

## 6. Summary

| Step | Time | Memory |
|---|---|---|
| preprocess | O(n^2 ell^2) worst case (Python `in`), about O(n^2 ell) typical | O(L) |
| overlap matrix | O(n^2 ell) | O(n^2) |
| greedy | O(n^3 + nL) | O(n^2 + L) |
| exact DP | O(n^2 2^n) | O(n 2^n) |
| two_approx (Sec. 5) | polynomial; dominated by the counts: O(\|V\| ell log ell) rules x O(ell^2 σ^2) look-ups, \|V\| <= L ell | O(\|V\| ell) |
