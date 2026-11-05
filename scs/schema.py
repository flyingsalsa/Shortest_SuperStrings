"""Shared data structures (result schemas) for the project.

OWNER: coordinator. Workers must not change field names or meanings without
coordinator agreement; they may only *read* this module.

All structures are plain dataclasses so they serialise easily with
``dataclasses.asdict`` into JSON / JSONL.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Removal:
    """One input string that preprocessing discarded."""
    orig_index: int            # index into Preprocessed.original
    string: str
    reason: str                # "empty" | "duplicate" | "contained"
    witness_orig_index: Optional[int]  # original index of a kept/earlier string that
                                       # equals (duplicate) or contains (contained) it;
                                       # None for "empty"


@dataclass(frozen=True)
class Preprocessed:
    """Result of preprocess(strings).

    Convention (see docs/INTERFACES.md section 2):
      * ``retained`` is sorted lexicographically (Python ``str`` order), so it
        does NOT depend on the order of the original inputs.
      * Retained string ``k`` has stable ID ``k`` for all algorithms.
      * ``retained_orig_index[k]`` = smallest original index whose string
        equals ``retained[k]``.
    """
    original: tuple[str, ...]
    retained: tuple[str, ...]
    retained_orig_index: tuple[int, ...]
    removals: tuple[Removal, ...]


# ---------------------------------------------------------------------------
# Greedy
# ---------------------------------------------------------------------------

@dataclass
class MergeStep:
    """One greedy merge. Enough to replay and validate the choice."""
    step: int                  # 0-based merge number
    left_id: int               # stable ID of the left (suffix-contributing) string
    right_id: int              # stable ID of the right (prefix-contributing) string
    new_id: int                # ID given to the merged string (= n + step)
    overlap: int               # ov(left, right) used for this merge
    max_overlap: int           # maximum ov over all ordered pairs of distinct active strings
    n_tied: int                # number of ordered pairs attaining max_overlap
    active_before: list[int]   # sorted list of active IDs before this merge
    merged: Optional[str] = None  # resulting merged string (only when trace=True)


@dataclass
class GreedyResult:
    superstring: str
    length: int
    policy: str                # "lowest_id" | "highest_id" | "lex_merged" | "random"
    seed: Optional[int]        # tie seed (only for "random"), else None
    order: list[int]           # retained IDs in left-to-right order of first occurrence
                               # as merged blocks (the induced permutation)
    n_merges: int              # = n - 1 for n >= 1, 0 otherwise
    n_tie_steps: int           # number of merges where n_tied > 1
    max_tied: int              # max n_tied over all merges (0 if no merges)
    sum_overlap: int           # total overlap used; length == L - sum_overlap
    trace: Optional[list[MergeStep]] = None


# ---------------------------------------------------------------------------
# Exact DP
# ---------------------------------------------------------------------------

@dataclass
class ExactResult:
    superstring: str
    length: int                # OPT for the retained (substring-free) set
    order: list[int]           # optimal permutation of retained IDs
    engine: str                # "python" | "numpy"
    n: int


# ---------------------------------------------------------------------------
# Instances (generator output)
# ---------------------------------------------------------------------------

@dataclass
class Instance:
    instance_id: str           # stable, unique, deterministic from config + seed
    family: str                # "random" | "fragments" | "repetitive" | "known" | "discovered" | "bio_*"
    label: str                 # "benchmark" | "known" | "discovered" | "bio"
    params: dict               # generator parameters (JSON-serialisable)
    seed: Optional[int]        # instance seed (None for hand-written known examples)
    strings: list[str]         # ORIGINAL inputs (before preprocessing)
    metadata: dict = field(default_factory=dict)  # e.g. source string, sampled positions,
                                                  # raw draws, expected values for known cases


def to_dict(obj) -> dict:
    return asdict(obj)
