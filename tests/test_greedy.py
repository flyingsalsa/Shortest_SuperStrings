import random

import pytest

from conftest import random_strings, rich_instances, POLICIES
from helpers import retained_of, run_greedy
from scs.exact_dp import exact_dp_numpy
from scs.greedy import greedy
from scs.validate import (check_superstring, check_order, replay_greedy_trace,
                          is_substring_free, _ov)


def _many(count, seed, **kw):
    rng = random.Random(seed)
    return [random_strings(rng, **kw) for _ in range(count)]


def _tie_heavy(count, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        letters = "ABC"[:rng.choice([1, 2, 2, 3])]
        n = rng.randint(2, 7)
        ln = rng.randint(2, 4)
        out.append(["".join(rng.choice(letters) for _ in range(ln)) for _ in range(n)])
    return out


@pytest.mark.parametrize("policy", POLICIES)
def test_greedy_outputs_valid_and_replay_ok(policy):
    insts = (_many(300, 11, n_max=8, alph=(1, 3), len_range=(0, 6), allow_empty=True)
             + _tie_heavy(200, 12) + rich_instances(200, 13, n_lo=3, n_hi=9))
    for k, s in enumerate(insts):
        r, res = run_greedy(s, policy, seed=1000 + k)
        assert check_superstring(s, res.superstring) == [], (s, policy)
        assert res.length == len(res.superstring)
        assert replay_greedy_trace(r, res) == [], (s, policy)
        assert check_order(r, res.order, res.length) == [], (s, policy)
        assert sorted(res.order) == list(range(len(r)))
        assert res.sum_overlap == sum(map(len, r)) - res.length
        assert res.n_merges == max(len(r) - 1, 0)
        if len(r) == 0:
            assert res.superstring == "" and res.length == 0
        if len(r) == 1:
            assert res.superstring == r[0]


@pytest.mark.parametrize("policy", POLICIES)
def test_greedy_without_trace_matches_with_trace(policy):
    for k, s in enumerate(_tie_heavy(100, 13)):
        r = retained_of(s)
        seed = 5 + k if policy == "random" else None
        a = greedy(r, policy=policy, seed=seed, trace=True)
        b = greedy(r, policy=policy, seed=seed, trace=False)
        assert (a.superstring, a.order, a.n_tie_steps, a.max_tied, a.sum_overlap) == \
               (b.superstring, b.order, b.n_tie_steps, b.max_tied, b.sum_overlap)


@pytest.mark.parametrize("policy", POLICIES)
def test_greedy_invariants_on_traces(policy):
    """Each chosen overlap is the global max over the actual current strings and the
    active set stays substring-free (checked directly, not via the validator)."""
    insts = _tie_heavy(120, 14) + _many(80, 15, n_max=8, alph=(2, 3), len_range=(2, 6))
    for k, s in enumerate(insts):
        r, res = run_greedy(s, policy, seed=k)
        active = dict(enumerate(r))
        for st in res.trace:
            assert is_substring_free(list(active.values()))
            best = max(_ov(active[a], active[b]) for a in active for b in active if a != b)
            assert st.overlap == best == st.max_overlap
            active[st.new_id] = st.merged
            del active[st.left_id], active[st.right_id]
        assert len(active) == (1 if r else 0)


def test_half_compression_all_policies_all_exact_instances():
    """L - G >= (L - OPT)/2 (Tarhio-Ukkonen / Blum et al.). A failure here would be a
    bug or an assumption violation and must NOT be weakened."""
    insts = (_many(500, 21, n_max=7, alph=(1, 3), len_range=(1, 6)) + _tie_heavy(300, 22)
             + rich_instances(600, 23))
    count = 0
    n_gap = 0
    for k, s in enumerate(insts):
        r = retained_of(s)
        if not r:
            continue
        L = sum(map(len, r))
        opt = exact_dp_numpy(r).length
        for pol in POLICIES:
            for seed in ([k, k + 1] if pol == "random" else [None]):
                res = greedy(r, policy=pol, seed=seed, trace=False)
                assert res.length >= opt, (s, pol)
                assert 2 * (L - res.length) >= (L - opt), (s, pol, seed, res.length, opt, L)
                assert res.length <= 4 * opt
                count += 1
                n_gap += res.length > opt
    assert count > 5000
    assert n_gap > 0   # non-vacuous: greedy is strictly suboptimal somewhere in this sample


@pytest.mark.slow
def test_half_compression_large_sample():
    insts = rich_instances(4000, 99, n_lo=4, n_hi=9) + _tie_heavy(2000, 98)
    worst = 1.0
    for k, s in enumerate(insts):
        r = retained_of(s)
        if len(r) < 2:
            continue
        L = sum(map(len, r))
        opt = exact_dp_numpy(r).length
        for pol in POLICIES:
            res = greedy(r, policy=pol, seed=k if pol == "random" else None, trace=False)
            assert 2 * (L - res.length) >= (L - opt), (s, pol)
            if L > opt:
                worst = min(worst, (L - res.length) / (L - opt))
    assert worst >= 0.5


def test_determinism_under_input_permutation():
    rng = random.Random(33)
    for _ in range(150):
        s = random_strings(rng, n_max=7, alph=(1, 3), len_range=(1, 5))
        if not s:
            continue
        t = s[:]
        rng.shuffle(t)
        assert retained_of(s) == retained_of(t)
        r = retained_of(s)
        for pol in POLICIES:
            seed = 3 if pol == "random" else None
            a = greedy(r, policy=pol, seed=seed, trace=True)
            b = greedy(retained_of(t), policy=pol, seed=seed, trace=True)
            assert (a.superstring, a.order, a.length) == (b.superstring, b.order, b.length)


def test_random_policy_seed_behaviour():
    r = retained_of(["AAA", "BBB", "CCC", "DDD", "EEE"])
    first = greedy(r, policy="random", seed=42, trace=True)
    again = greedy(r, policy="random", seed=42, trace=True)
    assert (first.superstring, first.order) == (again.superstring, again.order)
    outs = {greedy(r, policy="random", seed=sd, trace=False).superstring for sd in range(30)}
    assert len(outs) > 1   # fixed seeds 0..29 -> deterministic outcome
    random.seed(999)
    ref = random.random()
    random.seed(999)
    greedy(r, policy="random", seed=1, trace=False)
    assert random.random() == ref   # global RNG untouched


def test_policy_argument_validation():
    r = retained_of(["AB", "BC"])
    with pytest.raises(Exception):
        greedy(r, policy="random", seed=None)
    with pytest.raises(Exception):
        greedy(r, policy="nonsense")
    with pytest.raises(Exception):
        greedy(r, policy="lowest_id", seed=3)


def test_policies_can_differ():
    """Tie-breaking matters: deterministically find an instance where policies give
    different lengths."""
    found = None
    for s in _tie_heavy(2000, 55):
        r = retained_of(s)
        lens = {p: greedy(r, policy=p, seed=0 if p == "random" else None, trace=False).length
                for p in POLICIES}
        if len(set(lens.values())) > 1:
            found = (s, lens)
            break
    assert found is not None, "no instance found where policies differ in length"
