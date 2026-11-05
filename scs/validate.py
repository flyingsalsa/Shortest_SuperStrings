"""Independent validators (Agent C).

Everything here uses its own naive overlap routine (``_ov``), written
without reference to ``scs.overlap``, so that a bug there cannot hide.
"""
from __future__ import annotations

import random
from typing import Sequence


def _ov(x: str, y: str) -> int:
    """Longest k <= min(|x|,|y|) with x[len(x)-k:] == y[:k] (k = 0 always works)."""
    best = 0
    for k in range(1, min(len(x), len(y)) + 1):
        if x[len(x) - k:] == y[:k]:
            best = k
    return best


def is_substring_free(strings: Sequence[str]) -> bool:
    """True iff no string is empty, duplicated, or contained in another one."""
    for i, s in enumerate(strings):
        if s == "":
            return False
        for j, t in enumerate(strings):
            if i != j and s in t:
                return False
    return True


def check_superstring(original: Sequence[str], superstring: str) -> list[str]:
    """Return a message for each original string NOT contained in ``superstring``."""
    return [f"missing original[{i}]={s!r}" for i, s in enumerate(original)
            if s not in superstring]


def _merge_in_order(retained: Sequence[str], order: Sequence[int]) -> str:
    out = ""
    for idx in order:
        s = retained[idx]
        out = s if out == "" else out + s[_ov(out, s):]
    return out


def check_order(retained: Sequence[str], order: Sequence[int], length: int) -> list[str]:
    """``order`` must be a permutation of range(n); merging consecutive strings
    with their maximum overlap must give a string of ``length`` containing every
    retained string."""
    n = len(retained)
    if sorted(order) != list(range(n)):
        return [f"order is not a permutation of 0..{n - 1}: {list(order)}"]
    problems: list[str] = []
    total = sum(len(s) for s in retained)
    ovs = sum(_ov(retained[a], retained[b]) for a, b in zip(order, order[1:]))
    if total - ovs != length:
        problems.append(f"order gives length {total - ovs} (pairwise overlaps), reported {length}")
    merged = _merge_in_order(retained, order)
    if len(merged) != length:
        problems.append(f"merging order gives length {len(merged)}, reported {length}")
    for s in retained:
        if s not in merged:
            problems.append(f"merged order string misses {s!r}")
    return problems


def replay_greedy_trace(retained: Sequence[str], result) -> list[str]:
    """Replay a greedy trace from scratch, recomputing all overlaps naively on
    the actual current strings. Returns a list of problems ([] = ok)."""
    P: list[str] = []
    n = len(retained)
    policy = result.policy
    if policy not in ("lowest_id", "highest_id", "lex_merged", "random"):
        return [f"unknown policy {policy!r}"]
    if policy == "random" and result.seed is None:
        return ["random policy without seed"]
    if policy != "random" and result.seed is not None:
        P.append("deterministic policy with a seed")
    if not is_substring_free(retained):
        P.append("retained set is not substring-free (precondition violated)")
    if n == 0:
        if result.superstring != "" or result.length != 0:
            P.append("n=0 but output is not empty")
        return P
    if result.trace is None:
        return P + ["no trace recorded"]
    if len(result.trace) != n - 1 or result.n_merges != n - 1:
        P.append(f"expected {n - 1} merges; trace has {len(result.trace)}, n_merges={result.n_merges}")

    rng = random.Random(result.seed) if policy == "random" else None
    active: dict[int, str] = {i: s for i, s in enumerate(retained)}
    orders: dict[int, list[int]] = {i: [i] for i in range(n)}
    n_tie_steps = 0
    max_tied = 0
    sum_ov = 0
    aborted = False

    for t, st in enumerate(result.trace):
        tag = f"step {t}"
        if st.step != t:
            P.append(f"{tag}: step field is {st.step}")
        if st.new_id != n + t:
            P.append(f"{tag}: new_id {st.new_id} != {n + t}")
        ids = sorted(active)
        if list(st.active_before) != ids:
            P.append(f"{tag}: active_before {list(st.active_before)} != {ids}")
        best = -1
        T: list[tuple[int, int]] = []
        ovs: dict[tuple[int, int], int] = {}
        for a in ids:
            for b in ids:
                if a == b:
                    continue
                o = _ov(active[a], active[b])
                ovs[(a, b)] = o
                if o > best:
                    best, T = o, [(a, b)]
                elif o == best:
                    T.append((a, b))
        T.sort()
        a, b = st.left_id, st.right_id
        if a == b or a not in active or b not in active:
            P.append(f"{tag}: chosen pair ({a},{b}) is not two distinct active ids")
            aborted = True
            break
        if st.overlap != ovs[(a, b)]:
            P.append(f"{tag}: reported overlap {st.overlap} != true ov {ovs[(a, b)]}")
        if ovs[(a, b)] != best:
            P.append(f"{tag}: chosen overlap {ovs[(a, b)]} is not the maximum {best}")
        if st.max_overlap != best:
            P.append(f"{tag}: max_overlap {st.max_overlap} != true max {best}")
        if st.n_tied != len(T):
            P.append(f"{tag}: n_tied {st.n_tied} != true tie count {len(T)}")
        if policy == "lowest_id":
            exp = min(T)
        elif policy == "highest_id":
            exp = max(T)
        elif policy == "lex_merged":
            exp = min(T, key=lambda p: (active[p[0]] + active[p[1]][best:], p))
        else:
            exp = T[rng.randrange(len(T))]
        if (a, b) != exp:
            P.append(f"{tag}: policy {policy} should choose {exp}, trace chose ({a},{b})")
        o = ovs[(a, b)]
        merged = active[a] + active[b][o:]
        if st.merged is not None and st.merged != merged:
            P.append(f"{tag}: merged string {st.merged!r} != {merged!r}")
        if len(T) > 1:
            n_tie_steps += 1
        max_tied = max(max_tied, len(T))
        sum_ov += o
        orders[n + t] = orders.pop(a) + orders.pop(b)
        del active[a], active[b]
        active[n + t] = merged

    if aborted:
        return P
    if len(active) == 1:
        (fid, final), = active.items()
        if result.superstring != final:
            P.append(f"final superstring {result.superstring!r} != replayed {final!r}")
        if result.length != len(final):
            P.append(f"length {result.length} != len(replayed) {len(final)}")
        if list(result.order) != orders[fid]:
            P.append(f"order {list(result.order)} != replayed {orders[fid]}")
        if result.length != sum(map(len, retained)) - sum_ov:
            P.append("length != L - sum of overlaps")
        P.extend("order check: " + p for p in check_order(retained, result.order, result.length))
    else:
        P.append(f"replay ended with {len(active)} active strings")
    if result.sum_overlap != sum_ov:
        P.append(f"sum_overlap {result.sum_overlap} != replayed {sum_ov}")
    if result.n_tie_steps != n_tie_steps:
        P.append(f"n_tie_steps {result.n_tie_steps} != replayed {n_tie_steps}")
    if result.max_tied != max_tied:
        P.append(f"max_tied {result.max_tied} != replayed {max_tied}")
    return P
