"""Suffix/prefix overlaps.  ov(x, y) = length of the longest suffix of x that
equals a prefix of y (0 <= ov <= min(|x|, |y|)).  See docs/algorithms.md."""
from __future__ import annotations

from typing import Sequence


def _prefix_function(y: str) -> list[int]:
    """KMP failure table: pi[k] = length of the longest proper prefix of
    y[:k+1] that is also a suffix of y[:k+1]."""
    pi = [0] * len(y)
    k = 0
    for q in range(1, len(y)):
        while k > 0 and y[q] != y[k]:
            k = pi[k - 1]
        if y[q] == y[k]:
            k += 1
        pi[q] = k
    return pi


def _overlap_with_pi(x: str, y: str, pi: list[int]) -> int:
    """Scan x with the KMP automaton of y.  After the last character of x the
    state k is the longest prefix of y that is a suffix of x, i.e. ov(x, y)."""
    m = len(y)
    if m == 0:
        return 0
    k = 0
    for ch in x:
        if k == m:              # full match of y: fall back before extending
            k = pi[k - 1]
        while k > 0 and ch != y[k]:
            k = pi[k - 1]
        if ch == y[k]:
            k += 1
    return k


def overlap(x: str, y: str) -> int:
    """Longest suffix of x equal to a prefix of y.  O(|x| + |y|)."""
    return _overlap_with_pi(x, y, _prefix_function(y))


def overlap_naive(x: str, y: str) -> int:
    """Reference implementation by slicing, O(min(|x|,|y|)^2)."""
    for k in range(min(len(x), len(y)), 0, -1):
        if x[len(x) - k:] == y[:k]:
            return k
    return 0


def overlap_matrix(strings: Sequence[str]) -> list[list[int]]:
    """M[i][j] = ov(strings[i], strings[j]) for i != j, M[i][i] = 0.
    The prefix function of each y is computed once.  O(n^2 * ell)."""
    n = len(strings)
    M = [[0] * n for _ in range(n)]
    for j in range(n):
        y = strings[j]
        pi = _prefix_function(y)
        for i in range(n):
            if i != j:
                M[i][j] = _overlap_with_pi(strings[i], y, pi)
    return M
