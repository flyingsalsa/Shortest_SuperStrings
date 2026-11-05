import random

import pytest

from conftest import random_strings
from scs.preprocess import preprocess
from scs.overlap import overlap, overlap_naive, overlap_matrix
from scs.oracle import _clean
from scs.validate import _ov, is_substring_free


def test_overlap_known():
    assert overlap("", "") == 0 and overlap("A", "") == 0 and overlap("", "A") == 0
    assert overlap("A", "A") == 1
    assert overlap("ABAB", "ABAB") == 4
    assert overlap("ABABAB", "BABABA") == 5
    assert overlap("ABC", "BCD") == 2
    assert overlap("ABC", "XYZ") == 0
    assert overlap("AAA", "AA") == 2 and overlap("AA", "AAA") == 2
    assert overlap("ATT", "TTA") == 2


def test_overlap_vs_independent_naive_random_pairs():
    rng = random.Random(5)
    for _ in range(4000):
        a = rng.randint(1, 3)
        letters = "ABC"[:a]
        x = "".join(rng.choice(letters) for _ in range(rng.randint(0, 9)))
        y = "".join(rng.choice(letters) for _ in range(rng.randint(0, 9)))
        assert overlap(x, y) == _ov(x, y) == overlap_naive(x, y), (x, y)


@pytest.mark.parametrize("motif", ["A", "AB", "ABC", "AAB", "ABAB"])
def test_overlap_periodic(motif):
    for i in range(0, 9):
        for j in range(0, 9):
            x, y = motif * i, motif * j
            assert overlap(x, y) == _ov(x, y)
            x2, y2 = (motif * i)[1:], (motif * j) + "A"
            assert overlap(x2, y2) == _ov(x2, y2)


def test_overlap_matrix():
    rng = random.Random(9)
    for _ in range(100):
        s = sorted(set(random_strings(rng, n_max=6, alph=(1, 3), len_range=(1, 6))))
        M = overlap_matrix(s)
        assert len(M) == len(s)
        for i in range(len(s)):
            assert M[i][i] == 0
            for j in range(len(s)):
                if i != j:
                    assert M[i][j] == _ov(s[i], s[j])


def test_overlap_not_fooled_by_separator_chars():
    for sep in "#$%|\x00":
        assert overlap(sep + "A", "A" + sep) == _ov(sep + "A", "A" + sep)
        x, y = "A" + sep, sep + "A"
        assert overlap(x, y) == _ov(x, y)


def test_preprocess_basic():
    p = preprocess(["B", "", "AB", "AB", "ABC", "C", "XY"])
    assert list(p.retained) == ["ABC", "XY"]
    reasons = {r.orig_index: r.reason for r in p.removals}
    assert reasons == {0: "contained", 1: "empty", 2: "contained", 3: "duplicate", 5: "contained"}
    assert preprocess([]).retained == ()
    assert preprocess(["", ""]).retained == ()


def test_preprocess_random_against_independent_clean():
    rng = random.Random(31)
    for _ in range(600):
        s = random_strings(rng, n_max=8, alph=(1, 3), len_range=(0, 6), allow_empty=True)
        p = preprocess(s)
        r = list(p.retained)
        assert r == sorted(_clean(s)), s
        assert r == sorted(r) and len(set(r)) == len(r)
        assert is_substring_free(r) if r else True
        assert tuple(p.original) == tuple(s)
        # every input is accounted for exactly once
        removed = {x.orig_index for x in p.removals}
        kept = set(p.retained_orig_index)
        assert removed.isdisjoint(kept) and removed | kept == set(range(len(s)))
        for k, idx in enumerate(p.retained_orig_index):
            assert s[idx] == r[k] and s.index(r[k]) == idx
        for x in p.removals:
            assert s[x.orig_index] == x.string
            if x.reason == "empty":
                assert x.string == "" and x.witness_orig_index is None
            elif x.reason == "duplicate":
                assert s[x.witness_orig_index] == x.string and x.witness_orig_index < x.orig_index
            else:
                assert x.reason == "contained"
                w = s[x.witness_orig_index]
                assert x.string in w and x.string != w


def test_preprocess_witness_is_longest_container():
    p = preprocess(["A", "AB", "ABC"])
    by = {r.orig_index: r for r in p.removals}
    assert by[0].witness_orig_index == 2 and by[1].witness_orig_index == 2


def test_preprocess_order_invariance():
    rng = random.Random(3)
    for _ in range(200):
        s = random_strings(rng, n_max=7, alph=(1, 3), len_range=(0, 5), allow_empty=True)
        base = preprocess(s).retained
        for _ in range(4):
            t = s[:]
            rng.shuffle(t)
            assert preprocess(t).retained == base
