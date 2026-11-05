"""Greedy shortest-superstring heuristic with explicit tie-breaking policies.

Contract: docs/INTERFACES.md section 4.  Correctness of the overlap-update
shortcut: docs/algorithms.md section 3.

Complexity (n strings, total length L): each of the n-1 steps scans all
ordered pairs of active strings, O(n^2), giving O(n^3) pair visits in total,
plus O(n * L) for building merged strings with Python string concatenation and
O(n^2) memory for the overlap table (2n-1 rows).  The initial overlap matrix
(if not supplied) costs O(n^2 * ell).
"""
from __future__ import annotations

import random
from typing import Optional, Sequence

from .overlap import overlap_matrix
from .schema import GreedyResult, MergeStep

POLICIES = ("lowest_id", "highest_id", "lex_merged", "random")


def greedy(strings: Sequence[str], policy: str = "lowest_id",
           seed: Optional[int] = None, trace: bool = False,
           overlaps: Optional[list[list[int]]] = None) -> GreedyResult:
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}; expected one of {POLICIES}")
    if policy == "random" and seed is None:
        raise ValueError("policy 'random' requires a seed")
    if policy != "random" and seed is not None:
        raise ValueError("seed must be None for deterministic policies")

    strs = list(strings)
    n = len(strs)
    if any(strs[i] >= strs[i + 1] for i in range(n - 1)):
        raise ValueError("greedy expects the retained strings: sorted and distinct")
    rng = random.Random(seed) if policy == "random" else None

    if n == 0:
        return GreedyResult("", 0, policy, seed, [], 0, 0, 0, 0, [] if trace else None)
    if n == 1:
        return GreedyResult(strs[0], len(strs[0]), policy, seed, [0], 0, 0, 0, 0,
                            [] if trace else None)

    # ov[a][b] for all IDs; merged strings get IDs n, n+1, ..., 2n-2.
    total_ids = 2 * n - 1
    base = overlaps if overlaps is not None else overlap_matrix(strs)
    ov = [[0] * total_ids for _ in range(total_ids)]
    for i in range(n):
        ov[i][:n] = base[i]
    text = {i: strs[i] for i in range(n)}          # ID -> current string
    order_of = {i: [i] for i in range(n)}          # ID -> original IDs inside it
    active = list(range(n))                        # kept sorted ascending

    steps: list[MergeStep] = []
    n_tie_steps = max_tied = sum_overlap = 0

    for t in range(n - 1):
        # --- find the maximum overlap and the tie set T (ascending (a, b)) ---
        best = -1
        T: list[tuple[int, int]] = []
        for a in active:
            row = ov[a]
            for b in active:
                if a == b:
                    continue
                v = row[b]
                if v > best:
                    best = v
                    T = [(a, b)]
                elif v == best:
                    T.append((a, b))
        m = best

        # --- choose one pair from T according to the policy ---
        if policy == "lowest_id":
            a, b = T[0]
        elif policy == "highest_id":
            a, b = T[-1]
        elif policy == "lex_merged":
            a, b = min(T, key=lambda p: (text[p[0]] + text[p[1]][m:], p))
        else:  # random: exactly one randrange call per merge
            a, b = T[rng.randrange(len(T))]

        # --- merge ---
        c = n + t
        merged = text[a] + text[b][m:]
        text[c] = merged
        order_of[c] = order_of[a] + order_of[b]
        if trace:
            steps.append(MergeStep(t, a, b, c, m, m, len(T), list(active), merged))
        if len(T) > 1:
            n_tie_steps += 1
        max_tied = max(max_tied, len(T))
        sum_overlap += m

        active.remove(a)
        active.remove(b)
        # Shortcut (valid because the active set is substring-free):
        #   ov(c, x) = ov(b, x),  ov(x, c) = ov(x, a).
        for x in active:
            ov[c][x] = ov[b][x]
            ov[x][c] = ov[x][a]
        active.append(c)                           # c is the largest ID so far
        del text[a], text[b], order_of[a], order_of[b]

    final = active[0]
    result_str = text[final]
    total = sum(len(s) for s in strs)
    assert len(result_str) == total - sum_overlap
    return GreedyResult(
        superstring=result_str, length=len(result_str), policy=policy, seed=seed,
        order=order_of[final], n_merges=n - 1, n_tie_steps=n_tie_steps,
        max_tied=max_tied, sum_overlap=sum_overlap,
        trace=steps if trace else None)
