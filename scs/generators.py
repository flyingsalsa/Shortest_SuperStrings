"""Instance generators (OWNER: Agent B).

Public API (docs/INTERFACES.md section 8)::

    generate(family, params, seed) -> Instance
    known_instances() -> list[Instance]

All randomness comes from a local ``random.Random(seed)``; generation never
depends on any algorithm outcome.  Strings use the first ``alphabet`` capital
letters (``"ABCD..."``), or ``"ACGT"`` when ``alphabet == "dna"``.

Common parameters (families ``random``, ``fragments``, ``repetitive``)
----------------------------------------------------------------------
``alphabet``  int size (or ``"dna"``);  ``n``  target number of strings;
``len_dist``  ``"fixed"`` (every length = ``len_min``) or ``"uniform"``
(integer uniform on ``[len_min, len_max]``);
``n_mode``    ``"retained"`` (default) or ``"raw"``;
``max_draws`` draw cap for retained mode (default ``50 * n``).

Retained-size control
---------------------
``n_mode == "retained"``: strings are drawn one at a time and the generator
tracks the size of the retained set (distinct, non-empty, not a proper
substring of another).  It stops the first time that size equals ``n``.  A
draw raises the retained size by at most one, so ``n`` is hit exactly, unless
the cap ``max_draws`` is reached first; then the instance is still emitted
with ``metadata["n_target_reached"] = False``.  ALL draws are kept as the
original input (so original inputs contain duplicates/contained strings
exactly as a real sampling process would produce).  ``n_mode == "raw"`` draws
exactly ``n`` strings.  The incremental tracker is cross-checked against
``scs.preprocess.preprocess`` at the end of every generation.

Metadata always contains ``n_mode, n_draws, n_target_reached, n_retained``.
"""
from __future__ import annotations

import hashlib
import json
import random
from typing import Optional

from .schema import Instance

GENERATOR_VERSION = "1.0"
FAMILIES = ("random", "fragments", "repetitive")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def param_key(params: dict) -> str:
    """Canonical JSON of the params dict (sorted keys), as in docs section 9."""
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def make_instance_id(family: str, params: dict, seed: int) -> str:
    return f"{family}-{_sha8(param_key(params))}-{seed:x}"


def letters(alphabet) -> str:
    if alphabet == "dna":
        return "ACGT"
    a = int(alphabet)
    if not 1 <= a <= 26:
        raise ValueError("alphabet size must be in 1..26")
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:a]


def _draw_len(rng: random.Random, p: dict) -> int:
    dist = p.get("len_dist", "uniform")
    lo = int(p["len_min"])
    if lo < 1:
        raise ValueError("len_min must be >= 1")
    if dist == "fixed":
        return lo
    if dist == "uniform":
        hi = int(p.get("len_max", lo))
        if hi < lo:
            raise ValueError("len_max < len_min")
        return rng.randint(lo, hi)
    raise ValueError(f"unknown len_dist {dist!r}")


def _mean_len(p: dict) -> float:
    if p.get("len_dist", "uniform") == "fixed":
        return float(p["len_min"])
    return (int(p["len_min"]) + int(p.get("len_max", p["len_min"]))) / 2.0


class _RetainedTracker:
    """Incrementally maintains the retained set of the strings drawn so far.

    Equivalent to ``preprocess(draws).retained`` (containment is transitive, so
    a new string contained in a previously removed one is contained in a kept
    one).  Exists only for speed; verified against preprocess at the end.
    """

    def __init__(self) -> None:
        self.kept: set[str] = set()

    def add(self, s: str) -> None:
        if not s:
            return
        for t in self.kept:
            if s in t:          # equal or proper substring of a kept string
                return
        self.kept = {t for t in self.kept if t not in s}
        self.kept.add(s)

    def __len__(self) -> int:
        return len(self.kept)


def _collect(draw_fn, n: int, p: dict):
    """Run the draw loop under the n_mode rule. Returns (draws, reached, extra)."""
    mode = p.get("n_mode", "retained")
    if mode not in ("retained", "raw"):
        raise ValueError(f"unknown n_mode {mode!r}")
    draws: list[str] = []
    extra: list = []
    if mode == "raw":
        for _ in range(n):
            s, e = draw_fn()
            draws.append(s)
            extra.append(e)
        return draws, None, extra
    max_draws = int(p.get("max_draws", 50 * n))
    tr = _RetainedTracker()
    reached = len(tr) == n
    while not reached and len(draws) < max_draws:
        s, e = draw_fn()
        draws.append(s)
        extra.append(e)
        tr.add(s)
        reached = len(tr) == n
    return draws, reached, extra


def _finish(family, params, seed, draws, reached, p, metadata) -> Instance:
    # cross-check the tracker against the real preprocessing
    from .preprocess import preprocess
    n_retained = len(preprocess(draws).retained)
    mode = p.get("n_mode", "retained")
    if mode == "retained" and reached and n_retained != int(p["n"]):
        raise AssertionError("retained tracker disagrees with preprocess")
    metadata.update({
        "n_mode": mode,
        "n_draws": len(draws),
        "n_target_reached": reached if mode == "retained" else None,
        "n_retained": n_retained,
        "generator_version": GENERATOR_VERSION,
    })
    return Instance(
        instance_id=make_instance_id(family, params, seed),
        family=family, label="benchmark", params=dict(params), seed=seed,
        strings=list(draws), metadata=metadata)


def _rand_string(rng: random.Random, alpha: str, length: int) -> str:
    return "".join(rng.choices(alpha, k=length))


def _mutate(rng: random.Random, alpha: str, s: str, rate: float) -> tuple[str, int]:
    if rate <= 0 or len(alpha) < 2:
        return s, 0
    out = []
    cnt = 0
    for ch in s:
        if rng.random() < rate:
            other = alpha.replace(ch, "")
            out.append(rng.choice(other))
            cnt += 1
        else:
            out.append(ch)
    return "".join(out), cnt


def _source_len(p: dict) -> int:
    """``source_len`` directly, or derived from ``coverage`` (mean total
    fragment length / source length) as round(n * mean_len / coverage)."""
    if p.get("source_len") is not None:
        return int(p["source_len"])
    if p.get("coverage") is not None:
        return max(int(p["len_max"] if p.get("len_dist") != "fixed" else p["len_min"]),
                   int(round(int(p["n"]) * _mean_len(p) / float(p["coverage"]))))
    raise ValueError("fragments/repetitive need source_len or coverage")


def _sample_fragments(rng, source, p, n):
    positions: list[list[int]] = []

    def draw():
        ln = min(_draw_len(rng, p), len(source))
        start = rng.randint(0, len(source) - ln)
        positions.append([start, ln])
        return source[start:start + ln], None

    draws, reached, _ = _collect(draw, n, p)
    return draws, reached, positions


# ---------------------------------------------------------------------------
# family A: random
# ---------------------------------------------------------------------------

def _gen_random(params: dict, seed: int) -> Instance:
    """Independent uniformly random strings.

    params: alphabet, n, len_dist, len_min, len_max (+ n_mode, max_draws).
    """
    rng = random.Random(seed)
    alpha = letters(params["alphabet"])
    n = int(params["n"])

    def draw():
        return _rand_string(rng, alpha, _draw_len(rng, params)), None

    draws, reached, _ = _collect(draw, n, params)
    return _finish("random", params, seed, draws, reached, params, {})


# ---------------------------------------------------------------------------
# family B: fragments
# ---------------------------------------------------------------------------

def _gen_fragments(params: dict, seed: int) -> Instance:
    """Fragments sampled from a random source string (sequencing-like).

    A source of length ``source_len`` (or derived from ``coverage``) is drawn
    uniformly over the alphabet.  Each fragment has a length from the length
    distribution (capped at ``source_len``) and a uniformly random start
    position.  Metadata: ``source``, ``positions`` (start, length per draw, in
    draw order), ``coverage`` = total fragment length of ALL draws divided by
    ``source_len``.

    NOTE: ``len(source)`` is a feasible upper bound on OPT only if every
    fragment lies inside the source (true here) AND the source is itself a
    superstring of the retained set; it is NOT a certificate of optimality
    (the true OPT can be shorter, and positions not covered by any fragment
    still count in ``source_len``).
    """
    rng = random.Random(seed)
    alpha = letters(params["alphabet"])
    n = int(params["n"])
    slen = _source_len(params)
    source = _rand_string(rng, alpha, slen)
    draws, reached, positions = _sample_fragments(rng, source, params, n)
    meta = {
        "source": source, "source_len": slen, "positions": positions,
        "coverage": sum(len(d) for d in draws) / slen,
    }
    return _finish("fragments", params, seed, draws, reached, params, meta)


# ---------------------------------------------------------------------------
# family C: repetitive
# ---------------------------------------------------------------------------

def _gen_repetitive(params: dict, seed: int) -> Instance:
    """Fragments from a repeat-rich source.

    Source construction: draw a random motif of ``motif_len`` letters.  Append
    copies of the motif until the source has ``source_len`` letters (the last
    copy is truncated).  Each copy is perturbed independently: every character
    is substituted by a different random letter with probability
    ``mutation_rate`` (0 = exact tandem repeat).  Optionally
    ``spacer_len`` (default 0) random letters are inserted between copies.
    Fragments are then sampled exactly like family ``fragments``.

    Repetition strength: small ``motif_len`` relative to fragment length and
    small ``mutation_rate`` -> strong repetition -> many distinct fragments
    overlap heavily and many ties.  Caveat: with ``mutation_rate = 0`` and
    fragment length > ``motif_len`` there are at most ``motif_len`` distinct
    fragments per length, so after preprocessing almost everything collapses
    and ``n`` is not reachable (flagged by ``n_target_reached = False``).
    Parameter ranges that keep the retained target reachable: mutation_rate
    >= ~0.05 with motif_len ~ mean fragment length, or motif_len >= ~1.5 *
    fragment length.  Metadata: ``motif``, ``source``, ``positions``,
    ``coverage``, ``n_mutations``.
    """
    rng = random.Random(seed)
    alpha = letters(params["alphabet"])
    n = int(params["n"])
    slen = _source_len(params)
    mlen = int(params["motif_len"])
    rate = float(params.get("mutation_rate", 0.0))
    spacer = int(params.get("spacer_len", 0))
    motif = _rand_string(rng, alpha, mlen)
    parts: list[str] = []
    total = 0
    n_mut = 0
    while total < slen:
        copy, c = _mutate(rng, alpha, motif, rate)
        n_mut += c
        parts.append(copy)
        total += len(copy)
        if spacer > 0 and total < slen:
            parts.append(_rand_string(rng, alpha, spacer))
            total += spacer
    source = "".join(parts)[:slen]
    draws, reached, positions = _sample_fragments(rng, source, params, n)
    meta = {
        "motif": motif, "source": source, "source_len": slen,
        "positions": positions, "n_mutations": n_mut,
        "coverage": sum(len(d) for d in draws) / slen,
    }
    return _finish("repetitive", params, seed, draws, reached, params, meta)


_GENERATORS = {"random": _gen_random, "fragments": _gen_fragments,
               "repetitive": _gen_repetitive}


def generate(family: str, params: dict, seed: int) -> Instance:
    """Generate one instance of ``family`` (see module docstring)."""
    if family not in _GENERATORS:
        raise ValueError(f"unknown family {family!r}; known: {sorted(_GENERATORS)}")
    return _GENERATORS[family](dict(params), int(seed))


# ---------------------------------------------------------------------------
# family D: known (hand-written, verified)
# ---------------------------------------------------------------------------

def _known(name: str, strings: list[str], note: str, **meta) -> Instance:
    return Instance(
        instance_id=f"known-{name}", family="known", label="known",
        params={"name": name}, seed=None, strings=list(strings),
        metadata={"note": note, **meta})


def known_instances() -> list[Instance]:
    """Hand-written instances.  Every ``expected_*`` value below was verified
    by independent brute force over all permutations (and is re-checked by the
    test-suite against the exact DP); nothing unverified is recorded."""
    out = [
        _known("att_tta_tac", ["ATT", "TTA", "TAC"],
               "chain ATT-TTA-TAC; superstring ATTAC", expected_opt=5),
        _known("bab_aaba_abaa", ["BAB", "AABA", "ABAA"],
               "greedy merges AABA+ABAA (overlap 3) first and is forced to 8; "
               "optimum AABABAA has length 7", expected_opt=7,
               # hand-proved: ov(AABA,ABAA)=3 is the unique maximum, after which
               # only zero overlaps remain, so every policy outputs 5 + 3 = 8
               expected_greedy_any_policy=8),
        _known("abc_bcde", ["ABC", "BCDE"], "single overlap of 2", expected_opt=5),
        _known("no_overlap", ["AAA", "BBB", "CCC"],
               "no positive overlap: OPT = sum of lengths (all merges tie at 0)",
               expected_opt=9),
        _known("heavy_preprocessing",
               ["ABCDEF", "ABC", "CDE", "DEF", "B", "F", "ABCDEF", "", "EF",
                "ABCDEF", "BCD", "A"],
               "everything is empty, a duplicate, or a substring of ABCDEF",
               expected_opt=6, expected_retained=1),
    ]
    for k in range(1, 7):
        # c(ab)^k, (ba)^k, (ab)^k c with c = "C", a = "A", b = "B".
        # OPT = 2k + 4 verified by brute force for k = 1..6.
        out.append(_known(
            f"blum_k{k}", ["C" + "AB" * k, "BA" * k, "AB" * k + "C"],
            "Blum-style family c(ab)^k, (ba)^k, (ab)^k c", k=k,
            expected_opt=2 * k + 4))
    return out
