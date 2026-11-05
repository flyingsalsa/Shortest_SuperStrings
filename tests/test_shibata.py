"""Shibata S_{k,t} construction (optional extension, coordinator-written)."""
import pytest

from scs.shibata import build_instance, replay_scripted, opt_certificate
from scs.preprocess import preprocess
from scs.exact_dp import exact_dp_numpy
from scs.validate import check_superstring


@pytest.mark.parametrize("k,t", [(10, 1), (10, 2), (12, 1), (12, 3)])
def test_scripted_run_is_legal_and_matches_paper(k, t):
    inst = build_instance(k, t)
    s = k // 2
    assert len(inst["strings"]) == t * (4 * s + 2)
    rep = replay_scripted(inst)
    assert rep["problems"] == []
    assert rep["length"] == t * (9 * s + 1) + 1
    assert check_superstring(inst["strings"], rep["superstring"]) == []
    cert = opt_certificate(inst["strings"])
    assert cert["certified_opt"] == t * (4 * s + 2) + k - 1


@pytest.mark.slow
def test_opt_by_exact_dp_k10_t1():
    inst = build_instance(10, 1)
    R = list(preprocess(inst["strings"]).retained)
    assert len(R) == 22
    assert exact_dp_numpy(R).length == 31
