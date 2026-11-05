"""Independent exact oracles (Agent C). No DP, no import of project algorithms."""
from __future__ import annotations

import itertools
from collections import deque
from typing import Sequence


def _ov(x: str, y: str) -> int:
    for k in range(min(len(x), len(y)), 0, -1):
        if x[len(x) - k:] == y[:k]:
            return k
    return 0


def _clean(strings: Sequence[str]) -> list[str]:
    """Drop empties, duplicates, and strings contained in another string."""
    uniq = sorted({s for s in strings if s != ""})
    return [s for s in uniq if not any(s != t and s in t for t in uniq)]


def brute_force_permutations(strings: Sequence[str]) -> int:
    """min over permutations of the length of the consecutive max-overlap merge."""
    S = _clean(strings)
    if not S:
        return 0
    best = None
    for perm in itertools.permutations(range(len(S))):
        cur = len(S[perm[0]])
        for a, b in zip(perm, perm[1:]):
            cur += len(S[b]) - _ov(S[a], S[b])
        if best is None or cur < best:
            best = cur
    return best


def brute_force_superstring(strings: Sequence[str], alphabet: str, max_len: int):
    """Smallest length of a string over ``alphabet`` containing all inputs, by
    enumerating every candidate in increasing length (starting at the longest
    input, since no shorter string can contain it). None if > max_len."""
    items = [s for s in strings if s != ""]
    lo = max((len(s) for s in items), default=0)
    for length in range(lo, max_len + 1):
        for tup in itertools.product(alphabet, repeat=length):
            cand = "".join(tup)
            if all(s in cand for s in items):
                return length
    return None


def shortest_superstring_bfs(strings: Sequence[str]) -> int:
    """Structurally different check: BFS over states (set of covered strings,
    last ell-1 characters), appending one letter per step. Letters are those
    occurring in the inputs (a foreign letter never helps)."""
    items = sorted({s for s in strings if s})
    if not items:
        return 0
    letters = sorted({c for s in items for c in s})
    ell = max(map(len, items))
    full = (1 << len(items)) - 1
    start = (0, "")
    seen = {start}
    q = deque([start])
    length = 0
    while q:
        for _ in range(len(q)):
            mask, tail = q.popleft()
            if mask == full:
                return length
            for c in letters:
                text = tail + c
                nm = mask
                for i, s in enumerate(items):
                    if s in text:
                        nm |= 1 << i
                st = (nm, text[max(0, len(text) - (ell - 1)):] if ell > 1 else "")
                if st not in seen:
                    seen.add(st)
                    q.append(st)
        length += 1
    raise AssertionError("unreachable")
