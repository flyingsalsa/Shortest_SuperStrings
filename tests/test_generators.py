"""Tests of Agent B's generators against the independent oracles."""
import dataclasses

import pytest

from helpers import retained_of
from scs.generators import generate, known_instances
from scs.exact_dp import exact_dp_numpy
from scs.oracle import brute_force_permutations, _clean

CASES = [
    ("random", {"alphabet": 2, "n": 5, "len_dist": "uniform", "len_min": 2, "len_max": 6}),
    ("random", {"alphabet": 4, "n": 8, "len_dist": "fixed", "len_min": 5}),
    ("random", {"alphabet": "dna", "n": 6, "len_dist": "uniform", "len_min": 3, "len_max": 7}),
    ("random", {"alphabet": 3, "n": 6, "len_dist": "uniform", "len_min": 2, "len_max": 4, "n_mode": "raw"}),
    ("fragments", {"alphabet": 4, "n": 7, "len_dist": "uniform", "len_min": 4, "len_max": 8, "source_len": 40}),
    ("fragments", {"alphabet": 3, "n": 6, "len_dist": "fixed", "len_min": 5, "coverage": 3.0}),
    ("repetitive", {"alphabet": 4, "n": 6, "len_dist": "uniform", "len_min": 4, "len_max": 7,
                    "source_len": 60, "motif_len": 6, "mutation_rate": 0.15}),
]


@pytest.mark.parametrize("family,params", CASES)
def test_same_seed_same_instance_and_seed_sensitivity(family, params):
    for seed in range(5):
        a = generate(family, params, seed)
        b = generate(family, dict(params), seed)
        assert dataclasses.asdict(a) == dataclasses.asdict(b)
        assert a.instance_id == b.instance_id and a.seed == seed
    assert len({tuple(generate(family, params, s).strings) for s in range(8)}) > 1


@pytest.mark.parametrize("family,params", CASES)
def test_retained_mode_hits_n_exactly(family, params):
    for seed in range(40):
        inst = generate(family, params, seed)
        n_ret = len(retained_of(inst.strings))
        assert n_ret == len(_clean(inst.strings))
        mode = params.get("n_mode", "retained")
        if mode == "raw":
            assert len(inst.strings) == params["n"]
        else:
            if inst.metadata["n_target_reached"]:
                assert n_ret == params["n"], (family, params, seed)
            else:
                assert n_ret < params["n"]
        assert inst.metadata["n_retained"] == n_ret
        assert all(isinstance(s, str) and s for s in inst.strings)


def test_alphabet_respected():
    inst = generate("random", {"alphabet": 3, "n": 6, "len_dist": "uniform", "len_min": 2, "len_max": 5}, 1)
    assert set("".join(inst.strings)) <= set("ABC")
    inst = generate("random", {"alphabet": "dna", "n": 6, "len_dist": "fixed", "len_min": 6}, 1)
    assert set("".join(inst.strings)) <= set("ACGT")


def test_fragments_are_substrings_of_source():
    for seed in range(10):
        inst = generate("fragments", CASES[4][1], seed)
        src = inst.metadata["source"]
        assert len(src) == 40
        assert all(s in src for s in inst.strings)
        for s, (start, ln) in zip(inst.strings, inst.metadata["positions"]):
            assert src[start:start + ln] == s


def test_unreachable_target_flagged():
    inst = generate("random", {"alphabet": 1, "n": 5, "len_dist": "uniform", "len_min": 1, "len_max": 3}, 0)
    assert inst.metadata["n_target_reached"] is False
    assert len(retained_of(inst.strings)) == 1


def test_known_instances_expected_values_match_dp():
    kn = known_instances()
    assert len(kn) >= 10
    ids = [k.instance_id for k in kn]
    assert len(set(ids)) == len(ids)
    for inst in kn:
        r = retained_of(inst.strings)
        if "expected_opt" in inst.metadata:
            assert exact_dp_numpy(r).length == inst.metadata["expected_opt"], inst.instance_id
            assert brute_force_permutations(inst.strings) == inst.metadata["expected_opt"]
        if "expected_retained" in inst.metadata:
            assert len(r) == inst.metadata["expected_retained"]
    assert any(k.metadata.get("expected_opt") == 7 for k in kn)
