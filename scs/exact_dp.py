"""Exact shortest superstring by Held-Karp style dynamic programming over
(subset, last string).  Contract: docs/INTERFACES.md section 5;
explanation: docs/algorithms.md section 2.

Input must be the retained (substring-free) strings.  Time O(n^2 2^n) after
the overlap matrix, space O(n 2^n).  Ties in the argmin go to the smallest
index in both engines, so they return identical orders.
"""
from __future__ import annotations

from math import comb
from typing import Optional, Sequence

import numpy as np

from .overlap import overlap_matrix
from .schema import ExactResult

_INF = 1 << 29          # fits int32 with room for adding a length


def _finish(strs: list[str], ov: list[list[int]], order: list[int],
            length: int, engine: str) -> ExactResult:
    """Merge the permutation with maximum overlaps and check the length."""
    s = strs[order[0]]
    for prev, cur in zip(order, order[1:]):
        s += strs[cur][ov[prev][cur]:]
    assert len(s) == length, (len(s), length)
    return ExactResult(superstring=s, length=length, order=order, engine=engine,
                       n=len(strs))


def _trivial(strs: list[str], engine: str) -> Optional[ExactResult]:
    if not strs:
        return ExactResult("", 0, [], engine, 0)
    if len(strs) == 1:
        return ExactResult(strs[0], len(strs[0]), [0], engine, 1)
    return None


def exact_dp(strings: Sequence[str],
             overlaps: Optional[list[list[int]]] = None) -> ExactResult:
    """Pure-Python reference implementation."""
    strs = list(strings)
    n = len(strs)
    r = _trivial(strs, "python")
    if r:
        return r
    ov = overlaps if overlaps is not None else overlap_matrix(strs)
    lens = [len(s) for s in strs]
    cost = [[lens[j] - ov[i][j] for i in range(n)] for j in range(n)]  # cost[j][i]
    size = 1 << n
    D = [_INF] * (size * n)            # D[mask*n + j]
    P = [-1] * (size * n)              # predecessor of j in mask
    for j in range(n):
        D[(1 << j) * n + j] = lens[j]
    for mask in range(1, size):
        if mask & (mask - 1) == 0:
            continue
        for j in range(n):
            if not (mask >> j) & 1:
                continue
            prev = mask ^ (1 << j)
            cj = cost[j]
            best, arg = _INF, -1
            for i in range(n):
                if (prev >> i) & 1:
                    v = D[prev * n + i] + cj[i]
                    if v < best:           # strict: smallest index wins ties
                        best, arg = v, i
            D[mask * n + j] = best
            P[mask * n + j] = arg
    full = size - 1
    last = min(range(n), key=lambda j: (D[full * n + j], j))
    length = D[full * n + last]
    order = []
    mask, j = full, last
    while j != -1:
        order.append(j)
        pj = P[mask * n + j]
        mask ^= 1 << j
        j = pj
    order.reverse()
    return _finish(strs, ov, order, length, "python")


def exact_dp_numpy(strings: Sequence[str],
                   overlaps: Optional[list[list[int]]] = None) -> ExactResult:
    """Vectorised DP: masks are processed layer by layer in popcount order and,
    for each last string j, all masks of the layer containing j are updated at
    once (min over the predecessor axis)."""
    strs = list(strings)
    n = len(strs)
    r = _trivial(strs, "numpy")
    if r:
        return r
    ov = overlaps if overlaps is not None else overlap_matrix(strs)
    lens = np.array([len(s) for s in strs], dtype=np.int32)
    ovm = np.array(ov, dtype=np.int32)
    size = 1 << n
    D = np.full((size, n), _INF, dtype=np.int32)
    P = np.full((size, n), -1, dtype=np.int8 if n < 127 else np.int16)
    pc = np.zeros(size, dtype=np.uint8)            # popcount of every mask
    for b in range(n):
        pc[1 << b: 1 << (b + 1)] = pc[: 1 << b] + 1
    for j in range(n):
        D[1 << j, j] = lens[j]
    for p in range(2, n + 1):
        layer = np.nonzero(pc == p)[0]
        for j in range(n):
            sel = layer[(layer >> j) & 1 == 1]
            prev = sel ^ (1 << j)
            cand = D[prev] + (lens[j] - ovm[:, j])[None, :]   # shape (k, n)
            arg = cand.argmin(axis=1)                         # first = smallest
            D[sel, j] = cand[np.arange(len(sel)), arg]
            P[sel, j] = arg
    full = size - 1
    last = int(np.argmin(D[full]))
    length = int(D[full, last])
    order = []
    mask, j = full, last
    while j != -1:
        order.append(j)
        pj = int(P[mask, j])
        mask ^= 1 << j
        j = pj
    order.reverse()
    return _finish(strs, ov, order, length, "numpy")


def estimate_dp_memory_bytes(n: int, engine: str) -> int:
    """Conservative estimate of peak table memory for n strings."""
    if n <= 1:
        return 0
    size = 1 << n
    if engine == "python":
        # two lists of size*n pointers (8 B each) + int objects for D values
        # (~32 B each; predecessors are small cached ints).
        return size * n * (8 + 8 + 32)
    if engine == "numpy":
        pred = 1 if n < 127 else 2
        tables = size * n * (4 + pred) + size            # D, P, popcount
        layer = comb(n, n // 2)                          # largest popcount layer
        temp = layer * n * 4 * 3 + layer * 8 * 3         # cand copies + index arrays
        return tables + temp
    raise ValueError(f"unknown engine {engine!r}")
