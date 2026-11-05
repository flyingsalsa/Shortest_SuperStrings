"""Hand-checked regression cases and edge cases."""
import itertools

import pytest

from conftest import POLICIES
from helpers import retained_of, run_greedy
from scs.exact_dp import exact_dp, exact_dp_numpy
from scs.oracle import brute_force_permutations, shortest_superstring_bfs
from scs.validate import check_superstring, replay_greedy_trace

ENGINES = [exact_dp, exact_dp_numpy]


def _check_all(strings, opt=None, greedy_len=None):
    r = retained_of(strings)
    if opt is not None:
        assert brute_force_permutations(strings) == opt
        for e in ENGINES:
            assert e(r).length == opt
    got = {}
    for pol in POLICIES:
        rr, res = run_greedy(strings, pol, seed=3)
        assert check_superstring(strings, res.superstring) == []
        assert replay_greedy_trace(rr, res) == []
        got[pol] = res.length
        if greedy_len is not None and pol == "lowest_id":
            assert res.length == greedy_len
    return got


def test_att_tta_tac():
    got = _check_all(["ATT", "TTA", "TAC"], opt=5)
    assert min(got.values()) >= 5


def test_bab_aaba_abaa():
    # unique max overlap 3 (AABA -> ABAA) at the first step, so every policy gives 8
    got = _check_all(["BAB", "AABA", "ABAA"], opt=7, greedy_len=8)
    assert got == {p: 8 for p in POLICIES}, got


def test_abc_bcde():
    got = _check_all(["ABC", "BCDE"], opt=5, greedy_len=5)
    assert set(got.values()) == {5}


def test_no_positive_overlap_all_ties():
    s = ["AAA", "BBB", "CCC"]
    got = _check_all(s, opt=9, greedy_len=9)
    assert set(got.values()) == {9}
    for pol in POLICIES:
        r, res = run_greedy(s, pol, seed=1)
        assert res.n_tie_steps == 2 and res.max_tied == 6 and res.sum_overlap == 0
        assert [st.n_tied for st in res.trace] == [6, 2]


def test_lowest_highest_id_choice_on_all_ties():
    _, lo = run_greedy(["AAA", "BBB", "CCC"], "lowest_id")
    assert (lo.trace[0].left_id, lo.trace[0].right_id) == (0, 1) and lo.superstring == "CCCAAABBB"  # step 2 pair (2,3): CCC first
    _, hi = run_greedy(["AAA", "BBB", "CCC"], "highest_id")
    assert (hi.trace[0].left_id, hi.trace[0].right_id) == (2, 1)


def test_preprocessing_removes_most():
    s = ["A", "AB", "ABC", "ABCD", "BC", "CD", "", "ABCD", "D"]
    r = retained_of(s)
    assert r == ("ABCD",)
    for e in ENGINES:
        assert e(r).superstring == "ABCD"
    for pol in POLICIES:
        _, res = run_greedy(s, pol)
        assert res.superstring == "ABCD" and res.n_merges == 0
        assert check_superstring(s, res.superstring) == []


def test_empty_input_and_only_empty_strings():
    for s in ([], [""], ["", "", ""]):
        assert retained_of(s) == ()
        for e in ENGINES:
            res = e(())
            assert res.superstring == "" and res.length == 0
        for pol in POLICIES:
            _, res = run_greedy(s, pol)
            assert res.superstring == "" and res.length == 0 and res.order == []
            assert res.n_merges == 0 and res.n_tie_steps == 0 and res.max_tied == 0
            assert replay_greedy_trace((), res) == []
        assert check_superstring(s, "") == []


def test_singleton_and_duplicates():
    for s in (["XYZ"], ["XYZ", "XYZ", "XYZ"], ["XYZ", "", "YZ"]):
        assert retained_of(s) == ("XYZ",)
        for pol in POLICIES:
            _, res = run_greedy(s, pol)
            assert res.superstring == "XYZ" and res.order == [0]


def test_unequal_lengths():
    s = ["ABCDEFGH", "GHI", "IJKLMNOPQ", "Q", "PQR"]
    _check_all(s, opt=brute_force_permutations(s))


@pytest.mark.parametrize("k", [2, 3])
@pytest.mark.parametrize("alpha", ["A", "AB"])
def test_all_strings_over_small_alphabet(k, alpha):
    s = ["".join(t) for t in itertools.product(alpha, repeat=k)]
    r = retained_of(s)
    opt = exact_dp_numpy(r).length
    assert opt == shortest_superstring_bfs(s)
    for pol in POLICIES:
        rr, res = run_greedy(s, pol, seed=11)
        assert replay_greedy_trace(rr, res) == []
        assert res.length >= opt
        assert check_superstring(s, res.superstring) == []
    if alpha == "A":
        assert r == ("A" * k,)


def test_all_binary_strings_len3_tie_structure():
    s = ["".join(t) for t in itertools.product("AB", repeat=3)]
    _, res = run_greedy(s, "lowest_id")
    assert res.n_tie_steps >= 1 and res.max_tied > 1


def test_blum_style_family():
    # c(ab)^k, (ba)^k, (ab)^k c; compared against independent oracle only
    for k in (2, 3, 4):
        s = ["C" + "AB" * k, "BA" * k, "AB" * k + "C"]
        opt = brute_force_permutations(s)
        r = retained_of(s)
        L = sum(map(len, r))
        assert exact_dp(r).length == opt
        for pol in POLICIES:
            rr, res = run_greedy(s, pol, seed=2)
            assert replay_greedy_trace(rr, res) == []
            assert 2 * (L - res.length) >= L - opt
