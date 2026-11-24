"""The adapted 12/5 construction from the team report (Section 4.4, Appendix A
of Super_Strings.tex), a one-parameter simplification of the five-string
construction attributed there to Chukhin et al. [GSC26].

Notation: [L | g_1,...,g_k | R] = 0^L 1 0^{g_1-1} 1 ... 0^{g_k-1} 1 0^R.
For n >= 2: N = n^2, M = N + 4n, p_i = N + i (2 <= i <= n).

    string  left pad  gaps              right pad
    X_i     N+n       p_i, M, p_i, M    N
    Y_i     N         M, p_i, M, p_i    N+2n
    U_i     N         M, M, p_i, M      N
    V_i     N         M, p_i, M, M      N+1
    Z_i     p_i-1     M, M, p_i         0

Superstring H_n: left pad p_n - 1, right pad N + 1, gaps
(M,M,p_n,M,p_n)(M,M,p_{n-1},M,p_{n-1}) ... (M,M,p_2,M,p_2)(M,M).

Prescribed greedy run: A_i = X_i + Y_i and B_i = U_i + V_i (decreasing i),
then C_i = B_i + Z_i (decreasing i), then T_i = A_i + C_i, then the T_i are
concatenated (overlap 0).  Claimed overlaps:
alpha_i = 5N+8n+i+1, beta_i = 4N+8n+i+1, gamma = 2N+2n+1.

This module only BUILDS the objects; ``replay`` re-checks every claim by
direct computation (it does not trust the report's appendix).
"""
from __future__ import annotations

from collections import defaultdict

from .overlap import overlap


def gapword(L: int, gaps, R: int) -> str:
    return "0" * L + "1" + "".join("0" * (g - 1) + "1" for g in gaps) + "0" * R


def params(n: int):
    N = n * n
    M = N + 4 * n
    p = {i: N + i for i in range(2, n + 1)}
    return N, M, p


def build_instance(n: int) -> dict:
    if n < 2:
        raise ValueError("n >= 2")
    N, M, p = params(n)
    names = {}
    for i in range(n, 1, -1):
        rows = {
            f"X{i}": (N + n, (p[i], M, p[i], M), N),
            f"Y{i}": (N, (M, p[i], M, p[i]), N + 2 * n),
            f"U{i}": (N, (M, M, p[i], M), N),
            f"V{i}": (N, (M, p[i], M, M), N + 1),
            f"Z{i}": (p[i] - 1, (M, M, p[i]), 0),
        }
        for lab, (l, g, r) in rows.items():
            names[lab] = gapword(l, g, r)
    gaps = []
    for i in range(n, 1, -1):
        gaps += [M, M, p[i], M, p[i]]
    gaps += [M, M]
    H = gapword(p[n] - 1, gaps, N + 1)
    return {"n": n, "N": N, "M": M, "names": names, "H": H,
            "claimed": {"H_len": 5 * n**3 + 12 * n**2 - 2 * n - 1,
                        "G_len": 12 * n**3 + (31 * n**2 - 43 * n - 12) // 2,
                        "alpha": {i: 5 * N + 8 * n + i + 1 for i in range(2, n + 1)},
                        "beta": {i: 4 * N + 8 * n + i + 1 for i in range(2, n + 1)},
                        "gamma": 2 * N + 2 * n + 1}}


def scripted_sequence(n: int):
    """(phase, left, right, new) in the report's order."""
    seq = []
    for i in range(n, 1, -1):
        seq.append(("1a: A_i = X_i + Y_i (alpha_i)", f"X{i}", f"Y{i}", f"A{i}"))
        seq.append(("1b: B_i = U_i + V_i (alpha_i)", f"U{i}", f"V{i}", f"B{i}"))
    for i in range(n, 1, -1):
        seq.append(("2: C_i = B_i + Z_i (beta_i)", f"B{i}", f"Z{i}", f"C{i}"))
    for i in range(n, 1, -1):
        seq.append(("3: T_i = A_i + C_i (gamma)", f"A{i}", f"C{i}", f"T{i}"))
    acc = f"T{n}"
    for i in range(n - 1, 1, -1):
        new = "OUT" if i == 2 else f"Tacc{i}"
        seq.append(("4: concatenate T_i (overlap 0)", acc, f"T{i}", new))
        acc = new
    return seq


def replay(names: dict, seq, ov_fn=overlap) -> dict:
    """Replay a scripted sequence; every step must attain the current maximum
    overlap over ALL ordered pairs of distinct current strings."""
    cur = dict(names)
    members = {lab: [lab] for lab in names}
    ov, hist = {}, defaultdict(int)

    def put(key, v):
        ov[key] = v
        hist[v] += 1

    labels = list(cur)
    for a in labels:
        for b in labels:
            if a != b:
                put((a, b), ov_fn(cur[a], cur[b]))
    steps, problems = [], []
    for phase, left, right, new in seq:
        m = max(v for v, c in hist.items() if c > 0)
        o = ov[(left, right)]
        steps.append({"phase": phase, "left": left, "right": right, "new": new, "overlap": o,
                      "max_overlap": m, "n_tied": hist[m], "active_before": len(cur)})
        if o != m:
            problems.append(f"{new}: ov({left},{right}) = {o} < current max {m}")
        merged = cur[left] + cur[right][o:]
        for lab in (left, right):
            for other in cur:
                if other != lab:
                    for key in ((lab, other), (other, lab)):
                        if key in ov:
                            hist[ov.pop(key)] -= 1
        del cur[left], cur[right]
        cur[new] = merged
        members[new] = members.pop(left) + members.pop(right)
        for other in cur:
            if other != new:
                put((new, other), ov_fn(merged, cur[other]))
                put((other, new), ov_fn(cur[other], merged))
    out_label = next(iter(cur))
    return {"superstring": cur[out_label], "order": members[out_label],
            "steps": steps, "problems": problems}
