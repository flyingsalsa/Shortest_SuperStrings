"""Preprocessing: remove empty, duplicate and contained strings.

See docs/INTERFACES.md section 2 and docs/algorithms.md section 1.

Cost: the containment check compares every pair of distinct non-empty strings
with Python's ``in`` operator (a C routine, worst case O(|t| * |s|) per pair,
typically close to linear), so the total is O(n^2 * ell^2) worst case and
roughly O(n^2 * ell) in practice.  Only done once per instance.
"""
from __future__ import annotations

from typing import Sequence

from .schema import Preprocessed, Removal


def preprocess(strings: Sequence[str]) -> Preprocessed:
    original = tuple(strings)
    removals: list[Removal] = []

    # Steps 1 and 2: empty strings and exact duplicates.
    first_index: dict[str, int] = {}          # distinct non-empty string -> smallest index
    for idx, s in enumerate(original):
        if s == "":
            removals.append(Removal(idx, s, "empty", None))
        elif s in first_index:
            removals.append(Removal(idx, s, "duplicate", first_index[s]))
        else:
            first_index[s] = idx

    # Step 3: containment among the distinct non-empty strings.
    # Candidate containers are ordered by (longest first, then smallest original
    # index) so the first hit is the required witness.  The container found this
    # way is never itself contained in another string (that string would be a
    # longer container of s), so it is always retained.
    distinct = sorted(first_index.items(), key=lambda kv: (-len(kv[0]), kv[1]))
    kept: list[tuple[str, int]] = []
    for s, idx in distinct:
        witness = None
        for t, tidx in distinct:
            if len(t) <= len(s):
                break                          # sorted by decreasing length
            if s in t:
                witness = tidx
                break
        if witness is None:
            kept.append((s, idx))
        else:
            removals.append(Removal(idx, s, "contained", witness))

    # Step 4: retained strings sorted lexicographically (distinct, so no ties).
    kept.sort(key=lambda kv: kv[0])
    removals.sort(key=lambda r: r.orig_index)
    return Preprocessed(
        original=original,
        retained=tuple(s for s, _ in kept),
        retained_orig_index=tuple(i for _, i in kept),
        removals=tuple(removals),
    )
