"""Polynomial-time 2-approximation for SCS via forced occurrence counts.

Source: OpenAI, "A Polynomial-Time 2-Approximation for Shortest Common
Superstring" (preprint, 24 Sep 2026), github.com/openai/math, ``preprints/``.
Preprint, not peer reviewed.  As with ``scs/shibata.py``, everything is
re-implemented from the paper's definitions and every claim the construction
relies on is CHECKED at run time; a failed check raises ``TwoApproxError``
instead of silently returning a worse answer.

Pipeline (section numbers refer to the paper):

* Sec. 2   ``forced_counts``  - integer counts m(s) on every substring s of the
           inputs (including the empty word), defined by a descending-length
           recursion: extension sums (2.5), required strings >= 1, and the
           periodicity rule (2.6) with blocking functionals B_A(s; m) (2.3).
           Lemma 2.1: m(s) <= N_T(s) for every superstring T, so
           W = sum_c m(c) <= OPT.
* Sec. 2.3 ``base_graph``     - the balanced hierarchical graph (up edge
           pref(s) -> s with multiplicity u(s), down edge s -> suf(s) with
           multiplicity d(s)); it has W up edges and contains every input.
* Sec. 3   ``_layers``        - decomposition into closed walks, grouping by
           primitive periodic text, and re-sorting of the passages into
           one-turn "layers" (Lemma 3.2).  Each layer of period p gets an extra
           budget p; the budgets total W.
* Sec. 4-6 ``_Connector``     - the connection procedure: ordered-window walks
           (Lemma 4.1), band joins (4.2), collective links (4.3), host requests
           (4.4), per-group processing (Sec. 5) and opening cycles of planned
           links (Sec. 6).  Every added piece is a closed walk, so balance is
           kept; the total added up-cost is asserted to be <= W.
* Sec. 7   Euler tour from the empty word; the letters appended on up steps
           form the output superstring, of length 2W <= 2 OPT at most.

Coordinates.  A periodic text is stored as a primitive word R (the least
rotation of its group's text) and an integer ``shift``: position i of the
text is ``R[(i + shift) % len(R)]``.  A window [x, e) of a text spells the
word at positions x .. e-1.  A layer of period p is stored by one period of
its exit-end function z (Lemma 3.2): at start x its windows are [x, e) for
z(x-1) <= e <= z(x).

Complexity: |V| <= L * ell substrings; the count recursion evaluates
O(|V| ell log ell) periodicity rules, each blocking functional in O(ell^2 sigma^2) dictionary
look-ups.  Everything after the counts is polynomial in W <= L.  This is
reference code for small instances (n up to ~20, ell up to ~15), not tuned.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .preprocess import preprocess


class TwoApproxError(RuntimeError):
    """A property the paper proves failed on this input (or a bug here)."""


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise TwoApproxError(msg)


# ---------------------------------------------------------------------------
# Section 2: forced occurrence counts
# ---------------------------------------------------------------------------

def substring_closure(strings: Sequence[str]) -> set[str]:
    """V: all distinct substrings of the inputs, including the empty word."""
    V = {""}
    for s in strings:
        for i in range(len(s)):
            for j in range(i + 1, len(s) + 1):
                V.add(s[i:j])
    return V


def proper_periods(v: str) -> list[int]:
    """All p with 1 <= p < |v| such that v[i] == v[i-p] for i >= p (KMP borders)."""
    n = len(v)
    if n < 2:
        return []
    pi = [0] * n
    for i in range(1, n):
        k = pi[i - 1]
        while k and v[i] != v[k]:
            k = pi[k - 1]
        if v[i] == v[k]:
            k += 1
        pi[i] = k
    out, b = [], pi[-1]
    while b > 0:
        out.append(n - b)
        b = pi[b - 1]
    return out


def blocking(s: str, P: str, m: dict, V: set, alphabet: Sequence[str], maxlen: int) -> int:
    """B_A(s; m) of (2.3) for the text A(i) = P[i mod |P|], assuming A[0:|s|) = s.

    Sums m(r) * b_{A,s}(r) over bracketing words r = c1 + A[-alpha : |s|+beta) + c2
    with c1 != A(-alpha-1) and c2 != A(|s|+beta) (one term per placement j = alpha+1).
    """
    p = len(P)
    ls = len(s)
    total = 0
    left = ""
    alpha = 0
    while alpha + ls + 2 <= maxlen:
        mid = left + s
        if mid not in V:            # V is substring-closed: longer middles absent too
            break
        beta = 0
        while alpha + ls + beta + 2 <= maxlen and mid in V:
            cl = P[(-alpha - 1) % p]
            cr = P[(ls + beta) % p]
            for c1 in alphabet:
                if c1 == cl:
                    continue
                x = c1 + mid
                if x not in V:
                    continue
                for c2 in alphabet:
                    if c2 != cr:
                        total += m.get(x + c2, 0)
            mid = mid + cr
            beta += 1
        alpha += 1
        left = P[(-alpha) % p] + left
    return total


def forced_counts(retained: Sequence[str]) -> tuple[dict[str, int], int]:
    """Counts m(s) of Section 2.2 (only positive entries stored) and W = sum_c m(c)."""
    if not retained:
        return {}, 0
    V = substring_closure(retained)
    alphabet = sorted(set("".join(retained)))
    maxlen = max(len(s) for s in retained)
    required = set(retained)

    rules: dict[str, list[tuple[str, int, int]]] = defaultdict(list)   # w -> (v, p, k)
    for v in V:
        for p in proper_periods(v):
            k = 1
            while k * p < len(v):
                rules[v[: len(v) - k * p]].append((v, p, k))
                k += 1

    m: dict[str, int] = {}
    bcache: dict[tuple[str, str], int] = {}

    def B(s: str, P: str) -> int:
        key = (s, P)
        if key not in bcache:
            bcache[key] = blocking(s, P, m, V, alphabet, maxlen)
        return bcache[key]

    for s in sorted((w for w in V if w), key=lambda w: (-len(w), w)):
        lb = 1 if s in required else 0
        lb = max(lb, sum(m.get(c + s, 0) for c in alphabet),
                 sum(m.get(s + c, 0) for c in alphabet))
        for v, p, k in sorted(rules.get(s, ())):
            P = v[:p]
            if m.get(v, 0) > B(v, P):
                lb = max(lb, B(s, P) + k + 1)
        if lb:
            m[s] = lb
    W = sum(m.get(c, 0) for c in alphabet)
    return m, W


def base_graph(m: dict[str, int], alphabet: Sequence[str]) -> Counter:
    """Edge multiset {(from_word, to_word): multiplicity} of Section 2.3."""
    E: Counter = Counter()
    for s, ms in m.items():
        u = ms - sum(m.get(c + s, 0) for c in alphabet)
        d = ms - sum(m.get(s + c, 0) for c in alphabet)
        _check(u >= 0 and d >= 0, f"negative edge multiplicity at {s!r}")
        if u:
            E[(s[:-1], s)] += u
        if d:
            E[(s, s[1:])] += d
    return E


# ---------------------------------------------------------------------------
# Texts, layers and walks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Text:
    """Periodic text i -> R[(i + shift) mod |R|]."""
    R: str
    shift: int = 0

    def letter(self, i: int) -> str:
        return self.R[(i + self.shift) % len(self.R)]

    def word(self, x: int, e: int) -> str:
        return "".join(self.letter(i) for i in range(x, e))


def least_rotation(w: str) -> tuple[str, int]:
    """(lexicographically least rotation, its start index); smallest index on ties."""
    best, bi = w, 0
    for i in range(1, len(w)):
        r = w[i:] + w[:i]
        if r < best:
            best, bi = r, i
    return best, bi


def primitive_root_len(w: str) -> int:
    n = len(w)
    for p in range(1, n + 1):
        if n % p == 0 and w[:p] * (n // p) == w:
            return p
    return n


@dataclass
class Group:
    gid: int
    R: str                       # least rotation of the primitive text
    t: int                       # distinguished position: start of the greatest rotation
    layers: list = field(default_factory=list)   # low -> high

    @property
    def p(self) -> int:
        return len(self.R)

    @property
    def text(self) -> Text:
        return Text(self.R, 0)

    @property
    def top_rotation(self) -> str:
        return self.R[self.t:] + self.R[: self.t]


@dataclass(eq=False)
class Layer:
    lid: int
    group: Group
    index: int                   # position in group.layers (0 = lowest)
    z: list[int]                 # z(x) for x in [0, p)

    @property
    def p(self) -> int:
        return self.group.p

    def Z(self, x: int) -> int:
        q, r = divmod(x, self.p)
        return self.z[r] + q * self.p

    def f(self, x: int) -> int:  # first end at start x
        return self.Z(x - 1)

    def l(self, x: int) -> int:  # last end at start x
        return self.Z(x)

    def word(self, x: int, e: int) -> str:
        return self.group.text.word(x, e)

    def windows(self):
        """All windows of one turn: (x, e) for x in [0, p), f(x) <= e <= l(x)."""
        for x in range(self.p):
            for e in range(self.f(x), self.l(x) + 1):
                yield x, e

    def shortest_vertex(self) -> tuple[int, int]:
        x = min(range(self.p), key=lambda y: (self.f(y) - y, y))
        return x, self.f(x)

    def min_len(self) -> int:
        x, e = self.shortest_vertex()
        return e - x

    def edges(self) -> Counter:
        E: Counter = Counter()
        for x in range(self.p):
            for e in range(self.f(x) + 1, self.l(x) + 1):
                E[(self.word(x, e - 1), self.word(x, e))] += 1
            E[(self.word(x, self.l(x)), self.word(x + 1, self.l(x)))] += 1
        return E


def _closed_walks(E: Counter) -> list[list[str]]:
    """Deterministic decomposition of a balanced edge multiset into closed walks."""
    rem = Counter(E)
    out: dict[str, list[str]] = defaultdict(list)
    for (u, v) in sorted(E, key=lambda uv: (len(uv[1]), uv[1])):
        out[u].append(v)
    walks = []
    for v0 in sorted(out, key=lambda w: (len(w), w)):
        while any(rem[(v0, v)] for v in out[v0]):
            walk, cur = [v0], v0
            while True:
                nxt = next((v for v in out[cur] if rem[(cur, v)]), None)
                _check(nxt is not None, "base graph is not balanced")
                rem[(cur, nxt)] -= 1
                walk.append(nxt)
                cur = nxt
                if cur == v0:
                    break
            walks.append(walk)
    return walks


def _layers(E: Counter) -> list[Group]:
    """Section 3: closed walks -> primitive-text groups -> sorted one-turn layers."""
    by_root: dict[str, list[tuple[int, dict[int, int], int]]] = defaultdict(list)
    for walk in _closed_walks(E):
        v0 = walk[0]
        x, e = -len(v0), 0
        letters: list[str] = []
        exits: dict[int, int] = {}
        for cur, nxt in zip(walk, walk[1:]):
            if len(nxt) == len(cur) + 1:
                letters.append(nxt[-1])
                e += 1
            else:
                exits[x] = e
                x += 1
        P = len(letters)
        _check(P > 0 and len(exits) == P, "closed walk without a full turn")
        cyc = "".join(letters)
        # the walk's windows must spell its vertex words (Section 3.1)
        T = Text(cyc, 0)
        xx, ee = -len(v0), 0
        for cur, nxt in zip(walk, walk[1:]):
            _check(T.word(xx, ee) == cur, "walk window does not spell its vertex")
            if len(nxt) > len(cur):
                ee += 1
            else:
                xx += 1
        Zb = {y % P: z + (y % P - y) for y, z in exits.items()}
        p = primitive_root_len(cyc)
        R, delta = least_rotation(cyc[:p])
        # cyc[i] = R[(i + delta') mod p] with cyc[:p] == R[delta':] + R[:delta']
        dprime = (p - delta) % p
        _check(cyc[:p] == R[dprime:] + R[:dprime], "rotation alignment failed")
        by_root[R].append((P, Zb, dprime))

    groups = []
    for R in sorted(by_root, key=lambda r: (len(r), r)):
        p = len(R)
        rots = [R[i:] + R[:i] for i in range(p)]
        t = max(range(p), key=lambda i: (rots[i], -i))
        g = Group(gid=len(groups), R=R, t=t)
        cols = []
        for x in range(p):
            vals = []
            for P, Zb, d in by_root[R]:
                def Zj(y, P=P, Zb=Zb):
                    q, r = divmod(y, P)
                    return Zb[r] + q * P
                for r in range(P // p):
                    # walk coordinates translated by +d into group coordinates
                    vals.append(Zj(x + r * p - d) + d - r * p)
            cols.append(sorted(vals))
        h = len(cols[0])
        for i in range(h):
            g.layers.append(Layer(lid=-1, group=g, index=i, z=[cols[x][i] for x in range(p)]))
        groups.append(g)
    lid = 0
    for g in groups:
        for L in g.layers:
            L.lid = lid
            lid += 1
            for x in range(L.p):
                _check(L.f(x) <= L.l(x) and L.f(x) >= x, "layer violates (3.1)")
    return groups


def follow(text: Text, wins: Sequence[tuple[int, int]]) -> list[str]:
    """Lemma 4.1: hierarchical-graph walk through ordered windows; list of vertex words."""
    path = [text.word(*wins[0])]
    for (a, b), (c, d) in zip(wins, wins[1:]):
        _check(a <= c and b <= d and a <= b and c <= d, f"windows not ordered: {(a, b)} -> {(c, d)}")
        if c <= b:
            for x in range(a + 1, c + 1):
                path.append(text.word(x, b))
            for e in range(b + 1, d + 1):
                path.append(text.word(c, e))
        else:
            for x in range(a + 1, b + 1):
                path.append(text.word(x, b))
            for i in range(b, c):
                path.append(text.letter(i))
                path.append("")
            for e in range(c + 1, d + 1):
                path.append(text.word(c, e))
    return path


def round_trip(word: str) -> list[str]:
    return [word[:i] for i in range(len(word) + 1)] + [word[i:] for i in range(1, len(word) + 1)]


def walk_cost(path: Sequence[str]) -> int:
    return sum(1 for u, v in zip(path, path[1:]) if len(v) > len(u))


# ---------------------------------------------------------------------------
# Sections 4-6: connection procedure
# ---------------------------------------------------------------------------

@dataclass
class Record:
    host: Layer
    sigma: int        # source coordinate = host coordinate + sigma
    a: int            # window [a, b) in source coordinates
    b: int


@dataclass
class Block:
    bid: int
    kind: str                 # "collective" | "individual"
    group: Group
    layers: list              # low -> high
    record: Record
    k: int
    t: int
    H: int


@dataclass
class Operation:
    kind: str
    cost: int
    budget: int


class _Connector:
    def __init__(self, groups: list[Group], V: set[str]):
        self.groups = groups
        self.V = V
        self.all_layers = [L for g in groups for L in g.layers]
        self.rooted: set[int] = set()
        self.requests: dict[int, list] = defaultdict(list)   # host lid -> [(child group, record, layer, e)]
        self._served: dict[int, list] = defaultdict(list)    # every request ever sent to a host
        self.blocks: list[Block] = []
        self.block_of: dict[int, Block] = {}
        self.walks: list[list[str]] = []
        self.ops: list[Operation] = []
        self.n_requests = 0
        self.n_cycles = 0

    # -- bookkeeping --------------------------------------------------------
    def add(self, kind: str, path: list[str], budget: int) -> list[str]:
        _check(path[0] == path[-1], f"{kind}: walk is not closed")
        for u, v in zip(path, path[1:]):
            _check(v in self.V, f"{kind}: vertex {v!r} not a substring of the inputs")
            _check((len(v) == len(u) + 1 and v[:-1] == u) or (len(u) == len(v) + 1 and u[1:] == v),
                   f"{kind}: illegal step {u!r} -> {v!r}")
        cost = walk_cost(path)
        _check(cost <= budget, f"{kind}: cost {cost} exceeds its budget {budget}")
        if len(path) > 1:
            self.walks.append(path)
        self.ops.append(Operation(kind, cost, budget))
        return path

    def root(self, *layers: Layer) -> None:
        for L in layers:
            self.rooted.add(L.lid)

    def band_join(self, kind: str, layers: list[Layer], t: int, h: int) -> None:
        """Lemma 4.2 for ordered layers (low -> high) of one group, closed walk cost <= h."""
        text = layers[0].group.text
        H, E = layers[-1].f(t), layers[0].l(t)
        _check(H - E <= h, f"{kind}: band too wide ({H - E} > {h})")
        if E >= H:
            self.ops.append(Operation(kind, 0, h))
            return
        self.add(kind, follow(text, [(t, E), (t, H), (t + h, E + h)]), h)

    # -- Section 4.4 -----------------------------------------------------------
    def fulfil(self, host: Layer, reqs: list) -> None:
        q = host.p
        htext = host.group.text
        per_child: dict[int, dict] = {}
        for g, rec, L, e in reqs:
            c = per_child.setdefault(g.gid, {"g": g, "rec": rec, "ends": []})
            _check(c["rec"] is rec, "a child group used two records at one host")
            c["ends"].append((e, L))
        kids = []
        for c in per_child.values():
            g, rec = c["g"], c["rec"]
            tau = rec.sigma                  # child coordinate = host coordinate + tau
            kids.append({"g": g, "p": g.p, "a": rec.a - tau, "b": rec.b - tau, "tau": tau,
                         "ends": sorted((e - tau, L.lid, L) for e, L in c["ends"])})
        j = min(kids, key=lambda c: (c["p"], c["g"].gid))
        others = []
        for c in kids:
            if c is j:
                continue
            s = -q * ((c["a"] - j["a"]) // q)
            if (c["a"] + s, c["b"] + s) < (j["a"], j["b"]):
                s += q
            c["a"] += s
            c["b"] += s
            c["tau"] -= s
            c["ends"] = [(e + s, lid, L) for e, lid, L in c["ends"]]
            others.append(c)
        others.sort(key=lambda c: (c["a"], c["b"], c["g"].gid))
        T = j["a"] + q
        for c in others:
            _check(j["a"] <= c["a"] <= T and j["b"] <= c["b"] <= j["b"] + q, "(4.5) failed")
        for c in kids:
            for e, _, _ in c["ends"]:
                _check(c["a"] + c["p"] < e <= c["b"] - c["p"], "(4.2) failed")

        wins = [(j["a"], e) for e, _, _ in j["ends"]] + [(j["a"], j["b"])]
        targets = []
        for c in others:
            for e, _, L in c["ends"]:
                Q = (min(c["a"] + c["p"], T), max(e, j["b"]))
                wins.append(Q)
                targets.append((c, e, L, Q))
        e0 = j["ends"][0][0]
        wins.append((T, e0 + q))
        excursion = self.add("host_excursion", follow(htext, wins), q)
        for c, e, L, (s0, h0) in targets:
            ctext = Text(c["g"].R, c["tau"])
            pi = c["p"]
            path = follow(ctext, [(s0, h0), (c["a"] + pi, e + pi), (s0 + pi, h0 + pi)])
            _check(ctext.word(c["a"] + pi, e + pi) == L.word(c["a"] + c["tau"], e + c["tau"]),
                   "requester window mismatch")
            self.add("host_requester_loop", path, pi)
        contact = min(excursion, key=lambda w: (len(w), w))
        _check(len(contact) < j["p"], "host excursion has no contact shorter than p_j")
        self.add("host_contact_round_trip", round_trip(contact), j["p"])
        self.root(host, *(L for c in kids for _, _, L in c["ends"]))
        self.n_requests += len(reqs)

    # -- Section 5.3: record search -------------------------------------------
    def find_record(self, g: Group, lo: int, hi: int) -> Record:
        A = g.text
        w = A.word(lo, hi)
        for D in self.all_layers:
            for x, e in D.windows():
                word = D.word(x, e)
                o = word.find(w)
                while o != -1:
                    sigma = lo - (x + o)
                    same = D.group is g and sigma % g.p == 0
                    if not same and A.word(x + sigma, e + sigma) == word:
                        return Record(D, sigma, x + sigma, e + sigma)
                    o = word.find(w, o + 1)
        raise TwoApproxError(f"no record on another aligned text for {w!r} (Section 5.3)")

    # -- Section 5 ------------------------------------------------------------
    def process_group(self, g: Group) -> None:
        p, Ls = g.p, g.layers
        A = g.text
        recips = [L for L in Ls if self.requests.get(L.lid)]
        for L in recips:
            self.fulfil(L, self.requests.pop(L.lid))
        base = recips[-1].index if recips else None
        if base is not None:
            B = Ls[base]
            recs = [(r.a - r.sigma, r.b - r.sigma) for _, r, _, _ in self._served[B.lid]]
            a, hh = min(recs, key=lambda w: (w[1] - w[0], w))
            _check(hh - a < 2 * p, "baseline vertex not shorter than 2p")
            _check(B.f(a) <= hh <= B.l(a), "baseline record is not a baseline window")
            for L in Ls[:base]:
                if L.lid in self.rooted:
                    continue
                if L.min_len() <= p:
                    self.add("below_round_trip", round_trip(L.word(*L.shortest_vertex())), p)
                else:
                    e = min(L.l(a), hh)
                    _check(p < e - a, "lower-layer vertex too short")
                    self.add("below_link", follow(A, [(a, hh), (a + p, e + p), (a + p, hh + p)]), p)
                self.root(L)
            upper = Ls[base + 1:]
        else:
            upper = Ls
        n = len(upper)
        if n == 0:
            return
        t, top = g.t, Ls[-1]
        H = top.f(t)
        if H - t <= n * p:
            self.add("upper_round_trip", round_trip(A.word(t, H)), n * p)
            self.root(*upper)
            return
        if base is not None and Ls[base].l(t) >= H - n * p:
            self.band_join("upper_band", Ls[base:], t, n * p)
            self.root(*upper)
            return
        # (5.1) holds: force a record on another aligned text
        k = 1
        while sum(1 for L in Ls if L.l(t) >= H - k * p) > k:
            k += 1
        _check(1 <= k <= n, "threshold search out of range (Lemma 5.1)")
        K = k * p
        Lk = Ls[len(Ls) - k]
        _check(Lk.l(t) >= H - (k - 1) * p, "(5.2) failed")
        rec = self.find_record(g, t, H - K)
        a, b = rec.a, rec.b
        q = rec.host.p
        _check(a <= t and b >= H - K and b - a < p + q, "(5.4) failed")
        rH, rL = top.f(a), Lk.l(a)
        _check(rH - rL <= K and rH <= b + K, "(5.6) failed")
        if rL + K >= b:
            blk = Block(len(self.blocks), "collective", g, Ls[len(Ls) - k:], rec, k, t, H)
            self._new_block(blk)
            rest = upper[: n - k]
        else:
            rest = upper
        for L in rest:
            _check(L.f(a) <= b, "individual layer first end above b")
            if L.min_len() <= p:
                self.add("individual_round_trip", round_trip(L.word(*L.shortest_vertex())), p)
                self.root(L)
            elif L.l(a) + p >= b:
                self._new_block(Block(len(self.blocks), "individual", g, [L], rec, 1, t, H))
            else:
                e = L.f(a)
                _check(a + p < e <= L.l(a) < b - p, "(5.11) failed")
                _check(q > p, "request to a group of no larger period")
                self.requests[rec.host.lid].append((g, rec, L, e))
                self._served[rec.host.lid].append((g, rec, L, e))

    def _new_block(self, blk: Block) -> None:
        self.blocks.append(blk)
        for L in blk.layers:
            self.block_of[L.lid] = blk

    # -- Section 6 ------------------------------------------------------------
    def internal_join(self, blk: Block) -> None:
        """Lemma 6.1: join a block internally for (k-1)p."""
        if blk.kind == "collective" and blk.k > 1:
            self.band_join("internal_join", blk.layers, blk.t, (blk.k - 1) * blk.group.p)
        else:
            self.ops.append(Operation("internal_join", 0, 0))

    def link(self, blk: Block, short_q: Optional[int] = None) -> Optional[str]:
        """Realise a planned link; with short_q, return a contact of length <= short_q (Lemma 6.2)."""
        g, p, A = blk.group, blk.group.p, blk.group.text
        a, b = blk.record.a, blk.record.b
        if blk.kind == "individual":
            L = blk.layers[0]
            e = max(b, L.f(a + p))
            _check(e <= L.l(a + p) and e <= b + p, "(5.9) failed")
            path = self.add("individual_link", follow(A, [(a, b), (a + p, e), (a + p, b + p)]), p)
            return min(path, key=lambda w: (len(w), w))
        K = blk.k * p
        if short_q is not None:
            short = [L for L in blk.layers if L.min_len() <= short_q]
            if not short:
                x = min(blk.t, a + K)
                F = blk.layers[-1].f(x)
                _check(b - x < short_q and b < F <= blk.H <= b + K, "Lemma 6.2 inequalities failed")
                self.add("short_contact_link", follow(A, [(a, b), (x, b), (x, F), (a + K, b + K)]), K)
                return A.word(x, b)
        top, bot = blk.layers[-1], blk.layers[0]
        rH, rL = top.f(a), bot.l(a)
        _check(rH <= b + K and rH - rL <= K and rL + K >= b, "(4.1) failed")
        Y = max(b, rH)
        wins = [(a, b)]
        for L in reversed(blk.layers):
            x = a
            while L.Z(x) < Y:
                x += 1
            _check(x <= a + K and L.f(x) <= Y <= L.l(x), "collective link misses a layer")
            wins.append((x, Y))
        wins.append((a + K, b + K))
        self.add("collective_link", follow(A, wins), K)
        if short_q is not None:
            L = min(short, key=lambda L: (L.min_len(), L.lid))
            return L.word(*L.shortest_vertex())
        return None

    def open_cycles(self) -> None:
        nxt: dict[int, Optional[int]] = {}
        for blk in self.blocks:
            D = blk.record.host
            in_block = D.lid in self.block_of
            _check(in_block != (D.lid in self.rooted), "target layer neither rooted nor in a block")
            nxt[blk.bid] = self.block_of[D.lid].bid if in_block else None
        state: dict[int, int] = {}
        cycles = []
        for b0 in range(len(self.blocks)):
            path, cur = [], b0
            while cur is not None and state.get(cur, 0) == 0:
                state[cur] = 1
                path.append(cur)
                cur = nxt[cur]
            if cur is not None and state[cur] == 1:
                cycles.append(path[path.index(cur):])
            for x in path:
                state[x] = 2
        handled: set[int] = set()
        for cyc in cycles:
            self.n_cycles += 1
            if len(cyc) == 1:
                blk = self.blocks[cyc[0]]
                self.internal_join(blk)
                word = blk.group.text.word(blk.record.a, blk.record.b)
                _check(len(word) < blk.group.p, "(5.5) failed on a one-block cycle")
                self.add("cycle_round_trip", round_trip(word), blk.group.p)
                handled.add(blk.bid)
                continue
            M = 2 * max(self.blocks[i].group.p for i in cyc)

            def key(i):
                U = self.blocks[i].group.top_rotation
                return (U * (M // len(U) + 1))[:M]
            best = max(cyc, key=lambda i: (key(i), -i))
            S = self.blocks[best]
            Tb = self.blocks[nxt[best]]
            q = Tb.group.p
            contact = self.link(S, short_q=q)
            _check(contact is not None and len(contact) <= q, "Lemma 6.2: contact too long")
            self.internal_join(Tb)
            self.add("cycle_round_trip", round_trip(contact), q)
            handled.update((S.bid, Tb.bid))
        for blk in self.blocks:
            if blk.bid not in handled:
                self.link(blk)

    def run(self) -> None:
        for g in self.groups:
            self.process_group(g)
        _check(not any(self.requests.values()), "unfulfilled requests")
        for L in self.all_layers:
            _check((L.lid in self.rooted) != (L.lid in self.block_of),
                   "Proposition 5.2 failed: layer neither rooted nor in exactly one block")
        self.open_cycles()


# ---------------------------------------------------------------------------
# Section 7: Euler tour and driver
# ---------------------------------------------------------------------------

def euler_superstring(E: Counter) -> str:
    """Closed Euler tour from the empty word; letters of the up steps."""
    adj: dict[str, list[str]] = defaultdict(list)
    for (u, v), c in sorted(E.items(), key=lambda kv: (len(kv[0][1]), kv[0][1]), reverse=True):
        adj[u].extend([v] * c)
    total = sum(E.values())
    _check(total == 0 or bool(adj[""]), "empty word is not on the graph")
    stack, circuit = [""], []
    while stack:
        v = stack[-1]
        if adj[v]:
            stack.append(adj[v].pop())
        else:
            circuit.append(stack.pop())
    circuit.reverse()
    _check(len(circuit) - 1 == total, "final graph is not connected (Theorem 6.3 failed)")
    return "".join(v[-1] for u, v in zip(circuit, circuit[1:]) if len(v) > len(u))


@dataclass
class TwoApproxResult:
    superstring: str
    length: int
    W: int                        # lower bound sum_c m(c) <= OPT (Lemma 2.1)
    added_cost: int               # up-cost of the connecting walks (<= W, Theorem 6.3)
    n_groups: int
    n_layers: int
    n_blocks: int
    n_requests: int
    n_cycles: int
    operations: dict              # kind -> [count, total cost]


def two_approx(strings: Sequence[str], check: bool = True) -> TwoApproxResult:
    """Run the paper's algorithm on a RETAINED set (sorted, distinct, substring-free).

    ``check`` additionally verifies that the layer decomposition preserves the
    base-graph edge multiset (Lemma 3.2) and that the output contains every input.
    """
    strings = tuple(strings)
    if check:
        _check(tuple(preprocess(strings).retained) == strings, "input must be a retained set")
    if not strings:
        return TwoApproxResult("", 0, 0, 0, 0, 0, 0, 0, 0, {})
    m, W = forced_counts(strings)
    alphabet = sorted(set("".join(strings)))
    E = base_graph(m, alphabet)
    _check(sum(c for (u, v), c in E.items() if len(v) > len(u)) == W, "base graph cost != W")
    groups = _layers(E)
    _check(sum(g.p * len(g.layers) for g in groups) == W, "layer budgets do not sum to W")
    if check:
        got: Counter = Counter()
        for g in groups:
            for L in g.layers:
                got.update(L.edges())
        _check(got == E, "layers do not reproduce the base graph (Lemma 3.2)")
    V = substring_closure(strings)
    con = _Connector(groups, V)
    con.run()
    total = Counter(E)
    for path in con.walks:
        for u, v in zip(path, path[1:]):
            total[(u, v)] += 1
    added = sum(walk_cost(p) for p in con.walks)
    _check(added <= W, f"connection cost {added} exceeds W = {W}")
    out = euler_superstring(total)
    _check(len(out) == W + added, "output length differs from graph cost")
    if check:
        _check(all(s in out for s in strings), "output is not a superstring")
    ops: dict[str, list[int]] = {}
    for op in con.ops:
        e = ops.setdefault(op.kind, [0, 0])
        e[0] += 1
        e[1] += op.cost
    return TwoApproxResult(out, len(out), W, added, len(groups),
                           sum(len(g.layers) for g in groups), len(con.blocks),
                           con.n_requests, con.n_cycles, ops)
