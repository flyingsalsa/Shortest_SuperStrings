import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: slower tests (deselect with -m 'not slow')")


POLICIES = ("lowest_id", "highest_id", "lex_merged", "random")


def random_strings(rng: random.Random, n_max=7, alph=(1, 3), len_range=(1, 6), allow_empty=False):
    """Seeded random RAW input (duplicates / containment / optionally empties allowed)."""
    a = rng.randint(*alph)
    letters = "ABCDEFGH"[:a]
    n = rng.randint(0, n_max)
    lo = 0 if allow_empty else len_range[0]
    return ["".join(rng.choice(letters) for _ in range(rng.randint(lo, len_range[1])))
            for _ in range(n)]


@pytest.fixture
def rng():
    return random.Random(12345)


def rich_instance(rng: random.Random, n_lo=3, n_hi=7):
    """Raw draws (duplicates/containments kept) until the number of retained strings
    (computed with the independent oracle._clean) hits a random target in [n_lo, n_hi].
    Returns the raw list; may fall short of the target after the draw cap."""
    from scs.oracle import _clean
    target = rng.randint(n_lo, n_hi)
    letters = "ABCD"[:rng.randint(2, 4)]
    lo, hi = rng.choice([(2, 4), (3, 6), (2, 7)])
    out = []
    for _ in range(60):
        out.append("".join(rng.choice(letters) for _ in range(rng.randint(lo, hi))))
        if len(_clean(out)) >= target:
            break
    return out


def rich_instances(count, seed, **kw):
    rng = random.Random(seed)
    return [rich_instance(rng, **kw) for _ in range(count)]
