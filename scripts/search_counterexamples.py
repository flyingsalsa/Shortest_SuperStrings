"""Family D "discovered": search small instances for the worst G/OPT.

For every candidate set (substring-free, distinct strings so that
retained == input) the exact optimum is computed with the exact DP and
greedy is run under each DETERMINISTIC policy (lowest_id, highest_id,
lex_merged).  The top-k instances per policy (largest G/OPT, ties -> smaller
total length, then lexicographic) are saved to
``results/discovered/discovered.jsonl`` (one scs.schema.Instance per line,
family "discovered", label "discovered") together with
``discovered_search.json`` recording the search space, seed and number of
instances examined.  These are search outputs and must NOT be mixed with
benchmark samples (they are selected for being bad cases).

Modes
  random      uniform random draws: n in [n_min, n_max], alphabet, lengths in
              [len_min, len_max]; draws that are not substring-free/distinct are
              rejected (counted in ``rejected``).
  exhaustive  every n-subset (n_min..n_max) of all strings with lengths in
              [len_min, len_max] over the alphabet that is substring-free
              (can be huge: guard with --max-instances).

Usage:  python scripts/search_counterexamples.py --mode random --samples 20000
"""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scs.exact_dp import exact_dp                      # noqa: E402
from scs.greedy import greedy                           # noqa: E402
from scs.overlap import overlap_matrix                  # noqa: E402
from scs.schema import Instance                         # noqa: E402
from scs.seeds import sha256_strings                    # noqa: E402
from scs.sysinfo import git_version                     # noqa: E402

POLICIES = ["lowest_id", "highest_id", "lex_merged"]


def substring_free(strs) -> bool:
    for i, a in enumerate(strs):
        for j, b in enumerate(strs):
            if i != j and a in b:
                return False
    return True


def evaluate(strs):
    """strs: distinct, substring-free. Returns (opt, {policy: G})."""
    r = tuple(sorted(strs))
    M = overlap_matrix(r)
    opt = exact_dp(r, M).length
    g = {p: greedy(r, policy=p, seed=None, trace=False, overlaps=M).length
         for p in POLICIES}
    return r, opt, g


def candidates_random(rng, a):
    alpha = "ABCDEFGHIJ"[:a.alphabet]
    while True:
        n = rng.randint(a.n_min, a.n_max)
        strs = ["".join(rng.choices(alpha, k=rng.randint(a.len_min, a.len_max)))
                for _ in range(n)]
        yield strs


def candidates_exhaustive(a):
    alpha = "ABCDEFGHIJ"[:a.alphabet]
    universe = [ "".join(t) for L in range(a.len_min, a.len_max + 1)
                 for t in itertools.product(alpha, repeat=L)]
    for n in range(a.n_min, a.n_max + 1):
        yield from itertools.combinations(universe, n)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["random", "exhaustive"], default="random")
    ap.add_argument("--n-min", type=int, default=3)
    ap.add_argument("--n-max", type=int, default=6)
    ap.add_argument("--alphabet", type=int, default=2)
    ap.add_argument("--len-min", type=int, default=2)
    ap.add_argument("--len-max", type=int, default=6)
    ap.add_argument("--samples", type=int, default=20000,
                    help="random mode: number of valid instances to evaluate")
    ap.add_argument("--max-instances", type=int, default=2_000_000,
                    help="exhaustive mode: stop after this many valid instances")
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--out", default="results/discovered")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    heaps = {p: [] for p in POLICIES}      # min-heaps of (key, strings)
    seen_best: dict[tuple, dict] = {}
    examined = rejected = 0
    limit = a.samples if a.mode == "random" else a.max_instances
    gen = candidates_random(rng, a) if a.mode == "random" else candidates_exhaustive(a)
    t0 = time.time()
    for strs in gen:
        if examined >= limit:
            break
        if len(set(strs)) != len(strs) or not substring_free(strs):
            rejected += 1
            continue
        examined += 1
        r, opt, g = evaluate(strs)
        for p in POLICIES:
            # larger ratio first; then smaller total length, then lexicographic
            key = (g[p] / opt, -sum(map(len, r)), tuple(-ord(c) for c in "".join(r)))
            item = (key, r)
            seen_best[r] = {"opt": opt, "greedy": dict(g)}
            h = heaps[p]
            if len(h) < a.top_k:
                heapq.heappush(h, item)
            elif item > h[0]:
                heapq.heapreplace(h, item)
    # collect union
    chosen: dict[tuple, dict] = {}
    for p in POLICIES:
        for rank, (key, r) in enumerate(sorted(heaps[p], reverse=True), 1):
            d = chosen.setdefault(r, {"top_for": {}})
            d["top_for"][p] = rank
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    insts = []
    for r, d in chosen.items():
        info = seen_best[r]
        ratios = {p: info["greedy"][p] / info["opt"] for p in POLICIES}
        insts.append(Instance(
            instance_id=f"discovered-{sha256_strings(r)[:10]}",
            family="discovered", label="discovered",
            params={"search_mode": a.mode, "alphabet": a.alphabet,
                    "n_min": a.n_min, "n_max": a.n_max,
                    "len_min": a.len_min, "len_max": a.len_max},
            seed=a.seed, strings=list(r),
            metadata={"opt": info["opt"], "greedy_len": info["greedy"],
                      "ratio": ratios, "top_for_policy_rank": d["top_for"],
                      "selected_by": "largest G/OPT per deterministic policy"}))
    insts.sort(key=lambda i: (-max(i.metadata["ratio"].values()), i.instance_id))
    with open(out_dir / "discovered.jsonl", "w", encoding="utf-8") as f:
        for i in insts:
            f.write(json.dumps(i.__dict__) + "\n")
    meta = {"search_space": {k: getattr(a, k) for k in
                             ("mode", "n_min", "n_max", "alphabet", "len_min", "len_max")},
            "seed": a.seed, "samples_requested": a.samples,
            "max_instances": a.max_instances, "top_k_per_policy": a.top_k,
            "instances_examined": examined, "candidates_rejected": rejected,
            "n_saved": len(insts), "policies": POLICIES,
            "best_ratio": {p: max((k[0] for k, _ in heaps[p]), default=None)
                           for p in POLICIES},
            "seconds": time.time() - t0, "code_version": git_version()}
    (out_dir / "discovered_search.json").write_text(json.dumps(meta, indent=2),
                                                    encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
