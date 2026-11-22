"""Adapted 12/5 construction from the team report (Section 4.4)."""
import pytest

from scs.twelve_fifths import build_instance, scripted_sequence, replay
from scs.overlap import overlap_naive
from scs.preprocess import preprocess
from scs.exact_dp import exact_dp_numpy
from scs.validate import check_superstring, is_substring_free


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_claims_hold(n):
    I = build_instance(n)
    S = list(I["names"].values())
    c = I["claimed"]
    assert len(S) == 5 * (n - 1) and is_substring_free(S)
    assert len(I["H"]) == c["H_len"] and check_superstring(S, I["H"]) == []
    rep = replay(I["names"], scripted_sequence(n), overlap_naive)
    assert rep["problems"] == []
    assert len(rep["superstring"]) == c["G_len"]
    assert check_superstring(S, rep["superstring"]) == []
    used = {}
    for st in rep["steps"]:
        used.setdefault(st["phase"][:2], set()).add(st["overlap"])
    assert used["1a"] | used["1b"] == set(c["alpha"].values())
    assert used["2:"] == set(c["beta"].values())
    assert used["3:"] == {c["gamma"]}
    assert n == 2 or used["4:"] == {0}


@pytest.mark.slow
def test_opt_small():
    I = build_instance(3)
    R = list(preprocess(list(I["names"].values())).retained)
    assert exact_dp_numpy(R).length <= len(I["H"])
