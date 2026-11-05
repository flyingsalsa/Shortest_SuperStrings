"""Mutation tests: the validator must notice corrupted traces."""
import copy

import pytest

from conftest import POLICIES
from helpers import run_greedy
from scs.validate import replay_greedy_trace


def _base(policy):
    s = ["AAB", "ABB", "BBA", "BAA", "ABA", "BAB"]  # lots of overlap ties
    return run_greedy(s, policy, seed=5)


@pytest.mark.parametrize("policy", POLICIES)
def test_clean_trace_passes(policy):
    r, res = _base(policy)
    assert replay_greedy_trace(r, res) == []


@pytest.mark.parametrize("policy", POLICIES)
def test_mutations_detected(policy):
    r, res = _base(policy)
    assert len(res.trace) >= 4
    muts = {
        "n_tied": lambda x: setattr(x.trace[0], "n_tied", x.trace[0].n_tied + 1),
        "overlap": lambda x: setattr(x.trace[1], "overlap", x.trace[1].overlap + 1),
        "max_overlap": lambda x: setattr(x.trace[1], "max_overlap", x.trace[1].max_overlap + 1),
        "merged": lambda x: setattr(x.trace[2], "merged", x.trace[2].merged + "A"),
        "superstring": lambda x: setattr(x, "superstring", x.superstring + "A"),
        "length": lambda x: setattr(x, "length", x.length + 1),
        "order": lambda x: setattr(x, "order", list(reversed(x.order))),
        "sum_overlap": lambda x: setattr(x, "sum_overlap", x.sum_overlap + 1),
        "n_tie_steps": lambda x: setattr(x, "n_tie_steps", x.n_tie_steps + 1),
        "max_tied": lambda x: setattr(x, "max_tied", x.max_tied + 1),
        "active_before": lambda x: x.trace[1].active_before.pop(),
        "new_id": lambda x: setattr(x.trace[1], "new_id", 99),
        "inactive_pair": lambda x: setattr(x.trace[-1], "left_id", 0),
        "same_pair": lambda x: setattr(x.trace[0], "right_id", x.trace[0].left_id),
        "drop_step": lambda x: x.trace.pop(),
    }
    for name, mut in muts.items():
        bad = copy.deepcopy(res)
        mut(bad)
        assert replay_greedy_trace(r, bad) != [], (policy, name)


def test_wrong_pair_choice_detected():
    r, res = run_greedy(["AAA", "BBB", "CCC"], "lowest_id")
    bad = copy.deepcopy(res)
    bad.trace[0].left_id, bad.trace[0].right_id = 1, 2     # tied but not the lowest
    assert replay_greedy_trace(r, bad) != []
    r, res = run_greedy(["AAB", "ABC", "BCA"], "lowest_id")
    bad = copy.deepcopy(res)
    st = bad.trace[0]
    st.left_id, st.right_id = st.right_id, st.left_id      # reversed pair
    assert replay_greedy_trace(r, bad) != []


def test_wrong_policy_label_detected():
    r, res = run_greedy(["AAA", "BBB", "CCC"], "highest_id")
    bad = copy.deepcopy(res)
    bad.policy = "lowest_id"
    assert replay_greedy_trace(r, bad) != []


def test_random_seed_mismatch_detected():
    r = ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")
    _, res = run_greedy(list(r), "random", seed=1)
    assert replay_greedy_trace(r, res) == []
    detected = 0
    for sd in range(2, 12):
        bad = copy.deepcopy(res)
        bad.seed = sd
        detected += replay_greedy_trace(r, bad) != []
    assert detected >= 8   # a different seed almost always gives a different choice sequence


def test_no_trace_reported():
    r, res = run_greedy(["AB", "BC", "CD"], "lowest_id", trace=False)
    assert replay_greedy_trace(r, res) != []
