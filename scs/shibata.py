"""Shibata's lower-bound instance S_{k,t} (optional extension).

Source: H. Shibata, "Disproving the Greedy Superstring Conjecture",
arXiv:2609.01365v1 (1 Sep 2026), Sections 3.1 and 5. Preprint, not peer
reviewed.  Everything here is re-derived from the paper's definitions and then
CHECKED by computation; nothing is taken on trust:

* ``build_instance(k, t)``       - the input set S_{k,t} (Section 3.1)
* ``scripted_merge_sequence``    - the paper's legal tie choices (Section 5)
* ``replay_scripted``            - replays a scripted sequence and checks, with
                                   a naive overlap routine, that every chosen
                                   pair attains the CURRENT maximum overlap
                                   (i.e. is a legal greedy step)
* ``opt_certificate``            - OPT by a counting lower bound plus an
                                   explicit superstring (Eulerian circuit in the
                                   order-(k-1) de Bruijn graph) of equal length

Alphabet: x, y, a are lowercase letters; b_i is the i-th uppercase letter
(A, B, C, ...), so t <= 26.
"""
from __future__ import annotations

from collections import defaultdict


# ---------------------------------------------------------------------------
# construction (Section 3.1)
# ---------------------------------------------------------------------------

def X(n: int) -> str:
    """X_n = (yx)^{n/2} for even n, x(yx)^{(n-1)/2} for odd n."""
    return "yx" * (n // 2) if n % 2 == 0 else "x" + "yx" * ((n - 1) // 2)


def csubstr(T: str, length: int, i: int) -> str:
    """CSubstr_length(T, i) = T^inf[i .. i+length-1] with 1-based i."""
    reps = (i - 1 + length) // len(T) + 2
    inf = T * reps
    return inf[i - 1: i - 1 + length]


def b(i: int) -> str:
    return chr(ord("A") + i - 1)


def base_strings(k: int, i: int) -> tuple[str, str, str]:
    s = k // 2
    U = "xa" + X(s - 3) + b(i) + "xa" + X(s - 3) + "y"
    V = "xa" + X(s - 3) + b(i)
    W = "xa" + X(s - 1) + b(i)
    assert (len(U), len(V), len(W)) == (k, s, s + 2)
    return U, V, W


def build_instance(k: int, t: int) -> dict:
    """Return {"strings": [...], "names": {string: "U_{i,j}"...}, "U": {...}, ...}."""
    if k % 2 or k < 10 or not 1 <= t <= 26:
        raise ValueError("need even k >= 10 and 1 <= t <= 26")
    s = k // 2
    names, strings = {}, []
    for i in range(1, t + 1):
        U, V, W = base_strings(k, i)
        for base, tag, count in ((U, "U", k), (V, "V", s), (W, "W", s + 2)):
            for j in range(1, count + 1):
                st = csubstr(base, k, j)
                assert st not in names, "Lemma 5 (distinctness) failed"
                names[st] = f"{tag}{i},{j}"
                strings.append(st)
    return {"k": k, "t": t, "s": s, "strings": strings, "names": names}


# ---------------------------------------------------------------------------
# the paper's merge procedure (Section 5)
# ---------------------------------------------------------------------------

def scripted_merge_sequence(k: int, t: int) -> list[tuple[str, str, str]]:
    """List of (phase, left, right) where left/right are *symbolic* labels:
    either an input name like 'U1,4' or a previously created block name.
    Merges are always left (+) right."""
    s = k // 2
    seq = []
    for i in range(1, t + 1):
        orders = {
            "U": [4 + m for m in range(k - 3)] + [1, 2, 3],          # U_{i,4..k}, U_{i,1..3}
            "V": list(range(2, s + 1)) + [1],                         # V_{i,2..s}, V_{i,1}
            "W": list(range(6, s + 3)) + list(range(1, 6)),            # W_{i,6..s+2}, W_{i,1..5}
        }
        for tag, js in orders.items():
            acc = f"{tag}{i},{js[0]}"
            for n_, j in enumerate(js[1:], 1):
                new = f"{tag}hat{i}" if n_ == len(js) - 1 else f"{tag}{i}acc{n_}"
                seq.append(("1:build hats (overlap k-1)", acc, f"{tag}{i},{j}", new))
                acc = new
    for i in range(1, t + 1):
        seq.append(("2:M_i = Vhat_i + Uhat_i (overlap s-3)", f"Vhat{i}", f"Uhat{i}", f"M{i}"))
    acc = "M1"
    for i in range(2, t + 1):
        new = "M" if i == t else f"Macc{i}"
        seq.append(("3:M_1+...+M_t (overlap 1)", acc, f"M{i}", new))
        acc = new
    if t == 1:
        acc = "M1"
    for i in range(1, t + 1):
        new = "T" if i == t else f"Tacc{i}"
        seq.append(("4:append What_i (overlap 0)", acc, f"What{i}", new))
        acc = new
    return seq


def _ov(x: str, y: str) -> int:
    """Naive overlap (independent of scs.overlap)."""
    for m in range(min(len(x), len(y)), 0, -1):
        if x[-m:] == y[:m]:
            return m
    return 0


def replay_scripted(instance: dict) -> dict:
    """Replay the scripted sequence; check every step is a legal greedy step."""
    k, t = instance["k"], instance["t"]
    cur = {name: st for st, name in instance["names"].items()}   # label -> string
    ov = {}                                                     # (a,b) -> overlap, labels

    hist = defaultdict(int)                                     # overlap value -> count

    def put(key, val):
        ov[key] = val
        hist[val] += 1

    def add_pairs(label):
        for other in cur:
            if other != label:
                put((label, other), _ov(cur[label], cur[other]))
                put((other, label), _ov(cur[other], cur[label]))

    labels = list(cur)
    for a in labels:
        for c in labels:
            if a != c:
                put((a, c), _ov(cur[a], cur[c]))

    def partners(lab):
        """All ordered-pair keys involving label ``lab``."""
        return [(lab, o) for o in cur if o != lab] + [(o, lab) for o in cur if o != lab]

    steps, problems = [], []
    for phase, left, right, new in scripted_merge_sequence(k, t):
        if left not in cur or right not in cur or left == right:
            problems.append(f"{new}: operands not active")
            break
        m = max(v for v, c in hist.items() if c > 0)
        n_tied = hist[m]
        o = ov[(left, right)]
        if o != m:
            problems.append(f"{new}: ov({left},{right})={o} < max {m} (ILLEGAL)")
        merged = cur[left] + cur[right][o:]
        steps.append({"phase": phase, "left": left, "right": right, "new": new,
                      "overlap": o, "max_overlap": m, "n_tied": n_tied,
                      "active_before": len(cur)})
        for key in set(partners(left)) | set(partners(right)):
            hist[ov.pop(key)] -= 1
        for lab in (left, right):
            del cur[lab]
        cur[new] = merged
        add_pairs(new)
    assert len(cur) == 1
    T = next(iter(cur.values()))
    missing = [st for st in instance["strings"] if st not in T]
    return {"superstring": T, "length": len(T), "steps": steps,
            "problems": problems + [f"missing {x}" for x in missing],
            "paper_length": t * (9 * (k // 2) + 1) + 1}


# ---------------------------------------------------------------------------
# OPT certificate (independent of the paper's Lemmas 7-9)
# ---------------------------------------------------------------------------

def opt_certificate(strings: list[str]) -> dict:
    """Lower bound: n distinct strings of equal length k need n distinct
    length-k windows, so |T| >= n + k - 1.  Upper bound: explicit superstring
    from an Eulerian circuit (Hierholzer) of the de Bruijn graph whose edges
    are the input strings; verified by containment and length."""
    k = len(strings[0])
    assert all(len(x) == k for x in strings) and len(set(strings)) == len(strings)
    n = len(strings)
    lower = n + k - 1
    out = defaultdict(list)
    for st in sorted(strings):
        out[st[:-1]].append(st)
    indeg = defaultdict(int)
    for st in strings:
        indeg[st[1:]] += 1
    balanced = all(len(out[v]) == indeg[v] for v in set(out) | set(indeg))
    # Hierholzer
    start = sorted(strings)[0][:-1]
    stack, circuit = [(start, None)], []
    ptr = {v: list(reversed(es)) for v, es in out.items()}
    while stack:
        v, e = stack[-1]
        if ptr.get(v):
            edge = ptr[v].pop()
            stack.append((edge[1:], edge))
        else:
            stack.pop()
            if e is not None:
                circuit.append(e)
    circuit.reverse()
    upper_str = None
    if len(circuit) == n:
        upper_str = circuit[0][:-1] + "".join(e[-1] for e in circuit)
    ok = (upper_str is not None and len(upper_str) == lower
          and all(x in upper_str for x in strings))
    return {"lower_bound": lower, "balanced": balanced, "eulerian_edges": len(circuit),
            "witness": upper_str, "certified_opt": lower if ok else None}
