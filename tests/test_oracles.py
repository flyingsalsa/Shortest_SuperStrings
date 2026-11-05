"""Self-consistency of the three independent oracles (no project algorithm used)."""
import random

import pytest

from conftest import random_strings
from scs.oracle import brute_force_permutations, brute_force_superstring, shortest_superstring_bfs
from scs.validate import is_substring_free, check_superstring, check_order


@pytest.mark.parametrize("strings,opt", [
    ([], 0), ([""], 0), (["", ""], 0), (["ABC"], 3), (["A", "A"], 1),
    (["ATT", "TTA", "TAC"], 5), (["BAB", "AABA", "ABAA"], 7), (["ABC", "BCDE"], 5),
    (["AAA", "BBB", "CCC"], 9), (["AB", "ABC", "B"], 3),
])
def test_known_values_all_oracles(strings, opt):
    assert brute_force_permutations(strings) == opt
    assert shortest_superstring_bfs(strings) == opt
    alpha = "".join(sorted(set("".join(strings)))) or "A"
    assert brute_force_superstring(strings, alpha, 12) == opt


def test_brute_force_superstring_returns_none_when_too_short():
    assert brute_force_superstring(["AAA", "BBB"], "AB", 5) is None
    assert brute_force_superstring(["AAA", "BBB"], "AB", 6) == 6


def test_three_oracles_agree_on_random_tiny():
    rng = random.Random(2024)
    checked = 0
    while checked < 80:
        s = random_strings(rng, n_max=4, alph=(1, 2), len_range=(1, 4))
        perm = brute_force_permutations(s)
        if perm > 11:
            continue
        alpha = "AB"
        assert brute_force_superstring(s, alpha, 11) == perm, s
        assert shortest_superstring_bfs(s) == perm, s
        checked += 1


def test_bfs_vs_perm_larger_alphabet():
    rng = random.Random(77)
    for _ in range(150):
        s = random_strings(rng, n_max=5, alph=(2, 4), len_range=(1, 5))
        assert shortest_superstring_bfs(s) == brute_force_permutations(s), s


def test_validator_helpers():
    assert check_superstring(["AB", "BC"], "ABC") == []
    assert len(check_superstring(["AB", "CA"], "ABC")) == 1
    assert check_superstring(["", "A"], "A") == []
    assert is_substring_free(["AB", "BA"]) and not is_substring_free(["AB", "ABA"])
    assert not is_substring_free(["AB", "AB"]) and not is_substring_free([""])
    assert check_order(["AB", "BC"], [0, 1], 3) == []
    assert check_order(["AB", "BC"], [1, 0], 4) == []   # BC then AB: no overlap -> 4
    assert check_order(["AB", "BC"], [0, 1], 4) != []
    assert check_order(["AB", "BC"], [0, 0], 3) != []
