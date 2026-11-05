"""OpenAI (2026) 2-approximation (scs/two_approx.py).

Checks the paper's claims computationally: the counts are occurrence lower
bounds (Lemma 2.1, hence W <= OPT), the layers reproduce the base graph
(Lemma 3.2), the connection walks cost at most W (Theorem 6.3), and the output
is a superstring of length <= 2 OPT (Theorem 1.1).  Exact OPT comes from the
project's DP; blocking functionals are compared with a brute-force evaluation
of their definition (2.1)-(2.3).
"""
import random
from collections import Counter

import pytest

from conftest import random_strings, rich_instances
from scs.exact_dp import exact_dp, exact_dp_numpy
from scs.generators import known_instances
from scs.preprocess import preprocess
from scs.shibata import build_instance
from scs.two_approx import (
    Group, Layer, Record, Text, TwoApproxError, _Connector, _layers, base_graph, blocking,
    follow, forced_counts, proper_periods, round_trip, substring_closure, two_approx, walk_cost,
)
from scs.validate import check_superstring


def retained(strings):
    return tuple(preprocess(list(strings)).retained)


def occurrences(T, s):
    return sum(1 for i in range(len(T) - len(s) + 1) if T.startswith(s, i))


def check_run(raw, opt=None):
    R = retained(raw)
    res = two_approx(R)
    assert check_superstring(raw, res.superstring) == []
    assert res.length == len(res.superstring) == res.W + res.added_cost
    assert res.added_cost <= res.W
    if opt is None and 0 < len(R) <= 12:
        opt = exact_dp_numpy(list(R)).length
    if opt is not None:
        assert res.W <= opt
        assert res.length <= 2 * opt
    return res


# ---------------------------------------------------------------------------
# Section 2 building blocks
# ---------------------------------------------------------------------------

def test_proper_periods_brute_force(rng):
    for _ in range(300):
        v = "".join(rng.choice("ab") for _ in range(rng.randint(0, 12)))
        want = [p for p in range(1, len(v)) if all(v[i] == v[i - p] for i in range(p, len(v)))]
        assert sorted(proper_periods(v)) == want


def _blocking_by_definition(s, P, m, V):
    """b_{A,s}(r) straight from (2.1)-(2.2), summed with weights m(r) as in (2.3)."""
    p = len(P)
    A = lambda i: P[i % p]
    total = 0
    for r in V:
        if not r:
            continue
        for j in range(1, len(r) - len(s)):          # 1 <= j and j + |s| <= |r| - 1
            if r[j:j + len(s)] != s:
                continue
            if all(r[h] == A(h - j) for h in range(1, len(r) - 1)) \
                    and r[0] != A(-j) and r[-1] != A(len(r) - 1 - j):
                total += m.get(r, 0)
    return total


def test_blocking_functional_matches_definition(rng):
    for _ in range(60):
        strs = [s for s in random_strings(rng, n_max=4, alph=(2, 3), len_range=(3, 9)) if s] or ["ab"]
        V = substring_closure(strs)
        alphabet = sorted(set("".join(strs)))
        maxlen = max(map(len, strs))
        m = {w: rng.randint(0, 3) for w in V if w}
        for s in sorted(w for w in V if w):
            Ps = [s[:p] for p in proper_periods(s)] + [s, s + rng.choice(alphabet)]
            for P in Ps:
                assert blocking(s, P, m, V, alphabet, maxlen) == _blocking_by_definition(s, P, m, V)


@pytest.mark.parametrize("h", [1, 2, 3, 5, 8])
def test_power_example_from_section_2_3(h):
    """Single required word a^h: the period-one rule forces m(a^j) = h - j + 1."""
    m, W = forced_counts(["a" * h])
    assert {w: m[w] for w in m} == {"a" * j: h - j + 1 for j in range(1, h + 1)}
    assert W == h


def test_counts_are_occurrence_lower_bounds(rng):
    """Lemma 2.1 against an optimal superstring T: m(s) <= N_T(s), so W <= OPT."""
    for raw in rich_instances(80, seed=2026, n_lo=1, n_hi=7):
        R = retained(raw)
        if not R:
            continue
        m, W = forced_counts(R)
        T = exact_dp(list(R)).superstring
        for s, c in m.items():
            assert c <= occurrences(T, s), (R, s, c, T)
        assert W <= len(T)


def test_base_graph_is_balanced_and_costs_W(rng):
    for raw in rich_instances(40, seed=7):
        R = retained(raw)
        m, W = forced_counts(R)
        E = base_graph(m, sorted(set("".join(R))))
        deg = Counter()
        for (u, v), c in E.items():
            deg[u] += c
            deg[v] -= c
        assert all(d == 0 for d in deg.values())
        assert sum(c for (u, v), c in E.items() if len(v) > len(u)) == W
        assert all(s in {v for (_, v) in E} for s in R)      # every required string is used


def test_layers_reproduce_base_graph_and_budgets(rng):
    """Lemma 3.2: sorted one-turn layers use exactly the base edges; budgets total W."""
    for raw in rich_instances(40, seed=11):
        R = retained(raw)
        m, W = forced_counts(R)
        E = base_graph(m, sorted(set("".join(R))))
        groups = _layers(E)
        got = Counter()
        for g in groups:
            assert g.R == min(g.R[i:] + g.R[:i] for i in range(g.p))     # least rotation
            for i, L in enumerate(g.layers):
                got.update(L.edges())
                if i:
                    below = g.layers[i - 1]
                    assert all(below.z[x] <= L.z[x] for x in range(g.p))  # pointwise order
        assert got == E
        assert sum(g.p * len(g.layers) for g in groups) == W


# ---------------------------------------------------------------------------
# Section 4 building blocks
# ---------------------------------------------------------------------------

def _is_walk(path):
    for u, v in zip(path, path[1:]):
        assert (len(v) == len(u) + 1 and v[:-1] == u) or (len(u) == len(v) + 1 and u[1:] == v)


def test_follow_ordered_windows_lemma_4_1(rng):
    for _ in range(300):
        R = "".join(rng.choice("abc") for _ in range(rng.randint(1, 5)))
        T = Text(R, rng.randint(0, 4))
        wins = []
        a, b = rng.randint(-5, 5), 0
        b = a + rng.randint(0, 6)
        wins.append((a, b))
        for _ in range(rng.randint(1, 4)):
            a += rng.randint(0, 4)
            b = max(b, a) + rng.randint(0, 4)
            wins.append((a, b))
        path = follow(T, wins)
        _is_walk(path)
        assert path[0] == T.word(*wins[0]) and path[-1] == T.word(*wins[-1])
        assert walk_cost(path) == wins[-1][1] - wins[0][1]
        for (a1, b1), (c1, d1) in zip(wins, wins[1:]):           # short-vertex claim
            assert min(len(w) for w in follow(T, [(a1, b1), (c1, d1)])) <= max(0, b1 - c1)
        h = len(R) * rng.randint(1, 3)                           # translate closes the walk
        closed = follow(T, wins[:1] + [(wins[0][0] + h, wins[0][1] + h)])
        assert closed[0] == closed[-1] and walk_cost(closed) == h


def test_round_trip():
    assert round_trip("") == [""]
    p = round_trip("abc")
    _is_walk(p)
    assert p[0] == p[-1] == "" and walk_cost(p) == 3 and "abc" in p


def _connected_to_root(edge_lists):
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    verts = {""}
    for u, v in edge_lists:
        verts.update((u, v))
        parent[find(u)] = find(v)
    return all(find(v) == find("") for v in verts)


def test_band_join_lemma_4_2():
    g = Group(gid=0, R="ab", t=1)
    lo = Layer(0, g, 0, [2, 3])
    hi = Layer(1, g, 1, [5, 6])
    g.layers = [lo, hi]
    con = _Connector([g], substring_closure(["ab" * 6]))
    con.band_join("band", g.layers, g.t, 2)
    assert walk_cost(con.walks[0]) == 2
    with pytest.raises(TwoApproxError):
        con.band_join("band", g.layers, g.t, 1)                  # H - E = 2 > 1


def test_host_requests_from_two_child_groups_lemma_4_4():
    """Hand-built Lemma 4.4 setting: two period-1 child groups request at one host of
    period 13 (the random searches never produced a host with two child groups)."""
    ga, gb = Group(0, "a", 0), Group(1, "b", 0)
    la, lb = Layer(0, ga, 0, [3]), Layer(1, gb, 0, [3])        # windows of length 2..3
    ga.layers, gb.layers = [la], [lb]
    gh = Group(2, "aaaaaabbbbbbc", 12)
    z = [6, 6, 6, 6, 6, 6, 12, 12, 12, 12, 12, 12, 13]
    low, host = Layer(2, gh, 0, list(z)), Layer(3, gh, 1, list(z))
    gh.layers = [low, host]
    V = substring_closure([gh.R * 3, "a" * 20, "b" * 20])
    con = _Connector([ga, gb, gh], V)
    ra, rb = Record(host, 0, 0, 6), Record(host, 0, 6, 12)
    reqs = [(ga, ra, la, la.f(0)), (gb, rb, lb, lb.f(6))]
    con.requests[host.lid] = list(reqs)
    con._served[host.lid] = list(reqs)
    con.process_group(gh)
    kinds = [op.kind for op in con.ops]
    assert "host_excursion" in kinds and "host_requester_loop" in kinds and "below_round_trip" in kinds
    assert all(op.cost <= op.budget for op in con.ops)
    assert con.rooted == {0, 1, 2, 3}
    spent = sum(walk_cost(w) for w in con.walks)
    assert spent <= gh.p + ga.p + gb.p + gh.p                  # host + requesters + lower layer
    edges = [e for L in (la, lb, low, host) for e in L.edges()]
    edges += [(u, v) for w in con.walks for u, v in zip(w, w[1:])]
    assert _connected_to_root(edges)


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

def test_edge_cases():
    assert two_approx(()).superstring == ""
    for s in ["a", "ab", "aaaa", "abab"]:
        res = two_approx((s,))
        assert s in res.superstring and res.length <= 2 * len(s)
    with pytest.raises(TwoApproxError):
        two_approx(("b", "a"))                                   # not a retained (sorted) set


def test_deterministic():
    R = retained(["abaab", "babba", "aabab", "bbab"])
    assert two_approx(R) == two_approx(R)


def test_random_instances_within_factor_two():
    for raw in rich_instances(150, seed=31415, n_lo=1, n_hi=8):
        check_run(raw)


def test_random_raw_inputs_with_preprocessing(rng):
    for _ in range(150):
        check_run(random_strings(rng, n_max=7, alph=(1, 3), len_range=(1, 7), allow_empty=True))


def test_periodic_fragment_instances():
    rng = random.Random(4242)
    for _ in range(150):
        motif = "".join(rng.choice("ab") for _ in range(rng.randint(1, 4)))
        src = list(motif * 10)
        for _ in range(rng.randint(0, 3)):
            src[rng.randrange(len(src))] = rng.choice("abc")
        src = "".join(src)
        raw = []
        for _ in range(rng.randint(1, 6)):
            i = rng.randrange(len(src) - 3)
            raw.append(src[i:i + rng.randint(3, 12)])
        check_run(raw)


@pytest.mark.parametrize("raw,kind", [
    (["aca"], "upper_round_trip"),
    (["abaab"], "collective_link"),
    (["aaacaaaaa"], "host_excursion"),
    (["abab", "abbab"], "cycle_round_trip"),
    (["abab", "abbab"], "internal_join"),
    (["ababbbabab"], "short_contact_link"),
    (["bbbbabbbbb", "bbcb"], "individual_round_trip"),
    (["aabaaabaaabaaa", "abaaabaaabaaaba", "abaaabaaabaac", "cabaaabaaabaa"], "individual_link"),
])
def test_branch_regressions(raw, kind):
    """Small inputs (found by seeded search) that reach each connection branch."""
    res = check_run(raw)
    assert kind in res.operations


def test_known_instances():
    for inst in known_instances():
        R = retained(inst.strings)
        if len(R) <= 14:
            check_run(inst.strings)


@pytest.mark.parametrize("k,t", [(10, 1), (12, 1), (10, 2)])
def test_shibata_instances(k, t):
    """Greedy can exceed 2*OPT on S_{k,t}; the paper's algorithm may not."""
    inst = build_instance(k, t)
    s = k // 2
    check_run(inst["strings"], opt=t * (4 * s + 2) + k - 1)    # certified OPT (test_shibata.py)


# ---------------------------------------------------------------------------
# Runner integration
# ---------------------------------------------------------------------------

def _cfg(**two_approx):
    cfg = {"name": "t", "master_seed": 1, "output_dir": "unused",
           "greedy_policies": ["lowest_id"], "random_tie_runs": 0, "include_known": False,
           "exact": {"enabled": False}}
    if two_approx is not None:
        cfg["two_approx"] = two_approx
    return cfg


def test_runner_two_approx_is_opt_in():
    from scs.runner import expected_keys
    assert ("i", "two_approx", None, None) not in expected_keys({**_cfg(), "two_approx": None}, "i")
    assert ("i", "two_approx", None, None) not in expected_keys(_cfg(enabled=False), "i")
    assert ("i", "two_approx", None, None) in expected_keys(_cfg(enabled=True), "i")


def test_runner_process_instance_two_approx_row():
    import dataclasses
    from scs.runner import process_instance, expected_keys
    inst = next(i for i in known_instances() if len(retained(i.strings)) <= 8)
    cfg = _cfg(enabled=True)
    task = {"instance": dataclasses.asdict(inst), "cfg": cfg, "code_version": "test",
            "need": expected_keys(cfg, inst.instance_id), "trace": False, "out_dir": "unused"}
    rows = {r["algorithm"]: r for r in process_instance(task)["rows"]}
    row = rows["two_approx"]
    assert row["status"] == "ok" and row["valid"] is True and row["policy"] is None
    opt = exact_dp_numpy(list(retained(inst.strings))).length
    assert row["lower_bound_W"] <= opt <= row["length"] <= 2 * opt
    assert row["length"] == row["lower_bound_W"] + row["added_cost"]


def test_runner_two_approx_guards():
    from scs.runner import _run_two_approx
    raw = ["abaab", "babba", "aabab"]
    R = retained(raw)
    total = lambda dt: dt
    assert _run_two_approx(raw, R, _cfg(enabled=True, max_L=3), None, total)["status"] == "skipped_n_too_large"
    opt = exact_dp_numpy(list(R)).length
    assert _run_two_approx(raw, R, _cfg(enabled=True), opt, total)["status"] == "ok"
    bad = _run_two_approx(raw, R, _cfg(enabled=True), 1000, total)     # pretend OPT is huge
    assert bad["status"] == "error" and "OPT" in bad["error"]
