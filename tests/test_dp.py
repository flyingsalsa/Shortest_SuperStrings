import random

import pytest

from conftest import random_strings, rich_instances
from helpers import retained_of
from scs.exact_dp import exact_dp, exact_dp_numpy
from scs.oracle import brute_force_permutations, brute_force_superstring, shortest_superstring_bfs
from scs.validate import check_superstring, check_order

ENGINES = [exact_dp, exact_dp_numpy]


def _instances(count, seed):
    rng = random.Random(seed)
    # 600 "raw random" (many collapse in preprocessing) + count//2 "rich" (retained n in 3..7)
    return ([random_strings(rng, n_max=7, alph=(1, 3), len_range=(1, 6)) for _ in range(count)]
            + rich_instances(count // 2, 17))


@pytest.mark.parametrize("engine", ENGINES, ids=["python", "numpy"])
def test_dp_equals_brute_force_permutations(engine):
    for s in _instances(600, 101):
        r = retained_of(s)
        res = engine(r)
        assert res.length == brute_force_permutations(s), s
        assert res.length == len(res.superstring)
        assert check_superstring(s, res.superstring) == [], s
        assert check_order(r, res.order, res.length) == [], s
        assert res.n == len(r)


def test_dp_engines_agree_exactly():
    for s in _instances(300, 202):
        r = retained_of(s)
        a, b = exact_dp(r), exact_dp_numpy(r)
        assert a.length == b.length
        assert a.engine == "python" and b.engine == "numpy"
        assert a.order == b.order and a.superstring == b.superstring, s  # same tie-breaking


def test_dp_with_precomputed_overlaps():
    from scs.overlap import overlap_matrix
    for s in _instances(50, 303):
        r = retained_of(s)
        M = overlap_matrix(r)
        assert exact_dp(r, overlaps=M).length == exact_dp(r).length
        assert exact_dp_numpy(r, overlaps=M).length == exact_dp(r).length


@pytest.mark.parametrize("engine", ENGINES, ids=["python", "numpy"])
def test_dp_vs_direct_enumeration_and_bfs(engine):
    rng = random.Random(404)
    checked = 0
    while checked < 60:
        s = random_strings(rng, n_max=5, alph=(2, 2), len_range=(1, 4))
        r = retained_of(s)
        res = engine(r)
        if res.length > 11:
            continue
        assert brute_force_superstring(s, "AB", 11) == res.length, s
        assert shortest_superstring_bfs(s) == res.length, s
        checked += 1


@pytest.mark.parametrize("engine", ENGINES, ids=["python", "numpy"])
def test_dp_edge_cases(engine):
    assert engine(()).superstring == "" and engine(()).length == 0
    r = engine(("ABC",))
    assert r.superstring == "ABC" and r.length == 3 and r.order == [0]
    r = engine(("AAA", "BBB", "CCC"))
    assert r.length == 9 and sorted(r.order) == [0, 1, 2]


def test_estimate_memory_monotone():
    from scs.exact_dp import estimate_dp_memory_bytes
    for eng in ("python", "numpy"):
        vals = [estimate_dp_memory_bytes(n, eng) for n in range(1, 17)]
        assert all(v >= 0 for v in vals) and vals[-1] > 0
        assert vals == sorted(vals)


@pytest.mark.slow
def test_dp_medium_n_numpy_vs_python_vs_oracle():
    rng = random.Random(909)
    for _ in range(12):
        s = ["".join(rng.choice("AB") for _ in range(rng.randint(3, 7))) for _ in range(9)]
        r = retained_of(s)
        a, b = exact_dp(r), exact_dp_numpy(r)
        assert a.length == b.length
        if len(r) <= 7:
            assert a.length == brute_force_permutations(s)
        assert check_superstring(s, a.superstring) == [] and check_superstring(s, b.superstring) == []
