"""Shared test helpers (own code; nothing here duplicates a project algorithm)."""
import random

from scs.preprocess import preprocess
from scs.overlap import overlap_matrix
from scs.greedy import greedy
from scs.exact_dp import exact_dp, exact_dp_numpy

POLICIES = ("lowest_id", "highest_id", "lex_merged", "random")


def retained_of(strings):
    return tuple(preprocess(list(strings)).retained)


def run_greedy(strings, policy, seed=None, trace=True):
    r = retained_of(strings)
    if policy == "random" and seed is None:
        seed = 7
    return r, greedy(r, policy=policy, seed=seed if policy == "random" else None, trace=trace)


def tiny_instances(count, seed, **kw):
    from conftest import random_strings
    rng = random.Random(seed)
    return [random_strings(rng, **kw) for _ in range(count)]
