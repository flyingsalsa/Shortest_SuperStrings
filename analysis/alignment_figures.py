"""String-overlap alignment figures for the report (coordinator).

    python analysis/alignment_figures.py [--out results/figures]

For each case, two panels share one character grid:
  * top: a greedy output (named policy, or the scripted legal run for Shibata)
  * bottom: an optimal superstring (exact DP, or a certified witness)
Each input string is drawn as a row of character cells at the position of its
position in the chain the algorithm actually built.  Darker cells are covered by two or more
inputs, i.e. overlap that the superstring exploits; the number at the right of
a row is the overlap actually used with the previous row (red = 0: length lost).
Columns where no overlap is used are where length is lost.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scs.preprocess import preprocess          # noqa: E402
from scs.overlap import overlap_matrix, overlap  # noqa: E402
from scs.greedy import greedy                  # noqa: E402
from scs.exact_dp import exact_dp_numpy        # noqa: E402
from scs.shibata import build_instance, replay_scripted, opt_certificate  # noqa: E402

CELL_BG = "#f3f3f3"
COVER = ["#ffffff", "#cfe3f5", "#7fb2de", "#3f7fbf"]   # by coverage depth 0,1,2,3+


SHIBATA_COLORS = False   # set per panel: True when the alphabet is Shibata's (lowercase x, y, a)


def letter_color(ch):
    if not SHIBATA_COLORS:
        return "#222222"
    if ch.isupper():                       # Shibata b_i markers
        return "#b03030"
    if ch == "a":
        return "#2f7d32"
    return "#222222"


def draw_panel(ax, title, superstring, order, names=None, max_label=None):
    """``order`` = the inputs in the left-to-right order in which the algorithm
    actually chained them; position of each = previous position + len(previous)
    - ov(previous, current).  (Using str.find instead would misplace strings that
    also occur accidentally elsewhere in the output.)"""
    pos, p = [], 0
    for idx, s_ in enumerate(order):
        if idx:
            p += len(order[idx - 1]) - overlap(order[idx - 1], s_)
        pos.append((p, s_))
    rebuilt = order[0] + "".join(b[overlap(a, b):] for a, b in zip(order, order[1:])) if order else ""
    assert rebuilt == superstring, "order does not reproduce the superstring"
    global SHIBATA_COLORS
    SHIBATA_COLORS = any(c.islower() for c in superstring)
    W = len(superstring)
    depth = [0] * W
    for p, s in pos:
        for c in range(p, p + len(s)):
            depth[c] += 1
    small = W > 40
    fs = 6 if small else 9
    # superstring row
    y0 = len(pos) + 1
    for c, ch in enumerate(superstring):
        ax.add_patch(Rectangle((c, y0), 1, 1, fc=COVER[min(depth[c], 3)], ec="#999999", lw=0.3))
        ax.text(c + 0.5, y0 + 0.5, ch, ha="center", va="center", fontsize=fs,
                color=letter_color(ch), family="monospace", weight="bold")
    ax.text(-0.6, y0 + 0.5, f"superstring (length {W})", ha="right", va="center", fontsize=fs + 1)
    # input rows
    prev = None
    for r, (p, s) in enumerate(pos):
        y = len(pos) - r - 0.2
        for c, ch in enumerate(s):
            ax.add_patch(Rectangle((p + c, y), 1, 1, fc=COVER[min(depth[p + c], 3)] if depth[p + c] > 1 else CELL_BG,
                                   ec="#999999", lw=0.3))
            ax.text(p + c + 0.5, y + 0.5, ch, ha="center", va="center", fontsize=fs,
                    color=letter_color(ch), family="monospace")
        label = names.get(s, s) if names else s
        if max_label and len(label) > max_label:
            label = label[:max_label] + "…"
        ax.text(p - 0.4, y + 0.5, label, ha="right", va="center", fontsize=fs - 1, color="#555555")
        if prev is not None:
            o = overlap(prev, s)
            ax.text(p + len(s) + 0.4, y + 0.5, f"ov {o}", ha="left", va="center", fontsize=fs - 1,
                    color="#3f7fbf" if o else "#b03030")
        prev = s
    ax.set_xlim(-12 if not small else -8, W + 5)
    ax.set_ylim(-0.5, y0 + 1.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=10, loc="left")


def case_figure(out, fname, suptitle, strings, top, bottom, names=None, note=""):
    """top/bottom = (title, superstring, order)."""
    W = max(len(top[1]), len(bottom[1]))
    rows = len(strings) + 3
    fig_w = min(18, 3 + 0.32 * (W + 14))
    fig_h = min(22, 2 * (0.32 * rows) + 1.6)
    fig, axes = plt.subplots(2, 1, figsize=(fig_w, fig_h))
    draw_panel(axes[0], top[0], top[1], top[2], names, max_label=14)
    draw_panel(axes[1], bottom[0], bottom[1], bottom[2], names, max_label=14)
    fig.suptitle(suptitle, fontsize=11, x=0.01, ha="left")
    if note:
        fig.text(0.01, 0.005, note, fontsize=8, color="#444444", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    for ext in ("pdf", "png", "svg"):
        fig.savefig(out / f"{fname}.{ext}", dpi=170)
    plt.close(fig)
    print("wrote", out / fname)


def greedy_vs_opt(out, fname, title, raw, policy="lowest_id", note=""):
    R = list(preprocess(raw).retained)
    M = overlap_matrix(R)
    g = greedy(R, policy, overlaps=M)
    ex = exact_dp_numpy(R, M)
    case_figure(out, fname, title, R,
                (f"greedy ({policy}): G = {g.length}", g.superstring, [R[i] for i in g.order]),
                (f"optimal (exact DP): OPT = {ex.length}", ex.superstring, [R[i] for i in ex.order]),
                note=note)
    return g.length, ex.length


def shibata_structure(out, k=10, t=1):
    """The three periodic base strings and their length-k cyclic windows."""
    from scs.shibata import base_strings, csubstr
    global SHIBATA_COLORS
    SHIBATA_COLORS = True
    s = k // 2
    counts = (k, s, s + 2)
    fig, axes = plt.subplots(3, 1, figsize=(10, 0.36 * (sum(counts) + 12)),
                             gridspec_kw={"height_ratios": [c + 2.3 for c in counts]})
    for ax, (tag, base, count) in zip(axes, zip("UVW", base_strings(k, 1), (k, s, s + 2))):
        period = len(base)
        span = count + k - 1
        inf = csubstr(base, span, 1)
        for c, ch in enumerate(inf):
            fc = "#e8e8e8" if (c // period) % 2 == 0 else "#ffffff"
            ax.add_patch(Rectangle((c, count + 1), 1, 1, fc=fc, ec="#999999", lw=0.3))
            ax.text(c + 0.5, count + 1.5, ch, ha="center", va="center", fontsize=7,
                    color=letter_color(ch), family="monospace", weight="bold")
        for j in range(1, count + 1):
            y = count - j + 0.6
            for c in range(k):
                ax.add_patch(Rectangle((j - 1 + c, y), 1, 0.8, fc="#cfe3f5", ec="#999999", lw=0.3))
                ax.text(j - 1 + c + 0.5, y + 0.4, inf[j - 1 + c], ha="center", va="center", fontsize=6,
                        color=letter_color(inf[j - 1 + c]), family="monospace")
            ax.text(j - 1.4, y + 0.4, f"{tag}1,{j}", ha="right", va="center", fontsize=6, color="#555555")
        ax.set_xlim(-6, 2 * k + 1)          # same scale in all three panels
        ax.set_ylim(0, count + 2.3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{tag}1 = {base} (period {period}): its {count} cyclic windows of length k = {k} "
                     f"(consecutive windows overlap by k-1 = {k - 1})", fontsize=9, loc="left")
    fig.suptitle("Shibata S_{10,1}: the 22 input strings are all length-10 cyclic windows of U1, V1, W1 "
                 "(x, y, a lowercase; b_1 shown as red 'A')", fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    for ext in ("pdf", "png", "svg"):
        fig.savefig(out / f"fig_shibata_structure.{ext}", dpi=170)
    plt.close(fig)
    print("wrote", out / "fig_shibata_structure")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/figures")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    greedy_vs_opt(out, "fig_align_bab", "Regression case BAB, AABA, ABAA",
                  ["BAB", "AABA", "ABAA"],
                  note="Greedy takes the unique overlap 3 (AABA→ABAA); afterwards BAB overlaps nothing. "
                       "OPT uses two overlaps of 2 instead.")
    greedy_vs_opt(out, "fig_align_blum_k3", "Blum-style family c(ab)^k, (ba)^k, (ab)^k c, k = 3",
                  ["CABABAB", "BABABA", "ABABABC"],
                  note="Greedy joins the two ends with overlap 2k = 6; the middle string then overlaps 0. "
                       "OPT threads all three with overlaps 2k-1 = 5.")
    greedy_vs_opt(out, "fig_align_discovered", "Discovered instance ABBBB, BBBBA, BBBBB (search output)",
                  ["ABBBB", "BBBBA", "BBBBB"],
                  note="Three pairs tie at overlap 4. lowest_id merges ABBBB→BBBBA first and strands BBBBB; "
                       "highest_id (not shown) reaches OPT. Compression ratio exactly 1/2.")
    rep = ("DAABBB BBDAABB BBDAABBBDAA DAABBBDAAB AABBDAABB BBBDAABBBDA AABBDAABBBDA ABBBDAABB BBBDAAB "
           "BBBDAABBBD BBBDAAB BDAABBBDAAB BBBDAA BDAABBBDAA BBDAABB AABBBDA AABBBD BBBDAABBBDAA "
           "BBDAABBBDAA BDAABB DAABBBDAABBB BDAABB ABBBDAABBBDA ABBBDA BBDAABBBDAA BDAABBBD ABBBDAABBBDA "
           "AABBBDAA BBDAABBBD BBBDAABBB BBBDAAB BBDAAB BBBDAA AABBBDAABBB AABBBDAAB AABBBDAA BBDAABBB "
           "DAABBBDAABBB DAABBB ABBBDAABBBDA DAABBBDAA BDAABB ABBBDAA BBDAABBBD BDAABBBDAABB BBBDAABBBDAA "
           "BBDAABBB ABBBDAA BBDAABBBDAAB BBBDAA ABBBDAABBB BBDAABBBDAA BBDAABBB BBDAABBB BDAABBBDAAB "
           "BDAABBB ABBBDAAA BDAABBB BBDAABBBDAA BBDAABBBD BBDAAABBD").split()
    greedy_vs_opt(out, "fig_align_repetitive_worst",
                  "Worst repetitive benchmark instance (repetitive-2f270e21-r24, n = 8 after preprocessing)",
                  rep, note="Greedy chains the four overlaps of 11 first, leaving two blocks joined with "
                            "overlap 0 (G = 33); OPT = 23 uses one continuous chain.")

    # Shibata S_{10,1}
    inst = build_instance(10, 1)
    rp = replay_scripted(inst)
    cert = opt_certificate(inst["strings"])
    case_figure(out, "fig_align_shibata_k10_t1",
                "Shibata S_{10,1} (n = 22, k = 10): scripted legal greedy run vs certified optimum",
                inst["strings"],
                (f"scripted legal greedy run (paper, Section 5): G = {rp['length']}", rp["superstring"],
                 rp["order"]),
                (f"optimal superstring (Eulerian witness; OPT = {cert['certified_opt']}, = exact DP)",
                 cert["witness"], sorted(inst["strings"], key=cert["witness"].find)),
                names=inst["names"],
                note="Rows labelled U1,j / V1,j / W1,j. Top: the three cyclic blocks are built with overlap 9, "
                     "then Vhat+Uhat with overlap s-3 = 2, then What appended with overlap 0.")
    shibata_structure(out)
    twelve_fifths_figure(out, n=3)


# ---------------------------------------------------------------------------
# adapted 12/5 construction (report Section 4.4): binary gap words
# ---------------------------------------------------------------------------

def _gap_runs(s):
    ones = [i for i, ch in enumerate(s) if ch == "1"]
    return ones


def _gap_label(g, N, M, n):
    if g == M:
        return "M"
    if N + 2 <= g <= N + n:
        return f"p{g - N}"
    return str(g)


def _draw_gap_rows(ax, title, rows, total, N, M, n, top_string=None):
    """rows = [(label, offset, string)], drawn top to bottom."""
    pal = {i: plt.cm.tab10(i - 2) for i in range(2, n + 1)}
    y = len(rows) + (1.6 if top_string else 0.6)
    if top_string is not None:
        ones = _gap_runs(top_string)
        ax.plot([0, len(top_string)], [y, y], color="#333333", lw=1.2)
        ax.vlines(ones, y - 0.25, y + 0.25, color="#333333", lw=0.8)
        ax.text(-2, y, f"superstring ({len(top_string)})", ha="right", va="center", fontsize=8)
        y -= 1.2
    for lab, off, s in rows:
        ones = [off + i for i in _gap_runs(s)]
        i_idx = int(lab[1:]) if lab[1:].isdigit() else None
        col = pal.get(i_idx, "#555555")
        ax.plot([off, ones[0]], [y, y], color="#bbbbbb", lw=1.0, ls=":")          # left pad
        ax.plot([ones[-1], off + len(s)], [y, y], color="#bbbbbb", lw=1.0, ls=":")  # right pad
        for a_, b_ in zip(ones, ones[1:]):
            g = b_ - a_
            is_m = g == M
            ax.plot([a_, b_], [y, y], color="#999999" if is_m else col, lw=2.2 if not is_m else 1.4)
            ax.text((a_ + b_) / 2, y + 0.18, _gap_label(g, N, M, n), ha="center", va="bottom",
                    fontsize=6.5, color="#666666" if is_m else col)
        ax.vlines(ones, y - 0.18, y + 0.18, color="#111111", lw=0.8)
        ax.text(off - 2, y, lab, ha="right", va="center", fontsize=8, color=col)
        y -= 1
    ax.set_xlim(-30, total + 5)
    ax.set_ylim(y - 0.2, len(rows) + 2.6)
    ax.set_yticks([])
    for sp in ("left", "right", "top"):
        ax.spines[sp].set_visible(False)
    ax.set_xlabel("position (characters)", fontsize=8)
    ax.set_title(title, fontsize=9.5, loc="left")


def twelve_fifths_figure(out, n=3):
    from scs.twelve_fifths import build_instance, scripted_sequence, replay
    I = build_instance(n)
    N, M, names, H = I["N"], I["M"], I["names"], I["H"]
    rep = replay(names, scripted_sequence(n))
    # panel 1: inputs inside H_n (first occurrence; asserted unique)
    rows_h = []
    for lab, s in names.items():
        p0 = H.find(s)
        assert p0 >= 0 and H.find(s, p0 + 1) == -1, f"{lab} not unique in H"
        rows_h.append((lab, p0, s))
    rows_h.sort(key=lambda r: (r[1], r[0]))
    # panel 2: greedy output, positions from the actual merge chain
    order = rep["order"]
    rows_g, p = [], 0
    for k, lab in enumerate(order):
        if k:
            p += len(names[order[k - 1]]) - overlap(names[order[k - 1]], names[lab])
        rows_g.append((lab, p, names[lab]))
    total = max(len(H), len(rep["superstring"]))
    fig, axes = plt.subplots(2, 1, figsize=(15, 9.5))
    _draw_gap_rows(axes[0], f"Short superstring H_{n}: |H_{n}| = {len(H)}  "
                   f"(each group's 5 inputs are windows of M,M,p_i,M,p_i,M,M)",
                   rows_h, total, N, M, n, top_string=H)
    c = I["claimed"]
    al = "/".join(str(c["alpha"][i]) for i in range(2, n + 1))
    be = "/".join(str(c["beta"][i]) for i in range(2, n + 1))
    _draw_gap_rows(axes[1], f"Prescribed legal greedy run: G_{n} = {len(rep['superstring'])}.  "
                   f"X_i+Y_i and U_i+V_i use alpha_i = {al}; B_i+Z_i uses beta_i = {be}; "
                   f"A_i+C_i uses gamma = {c['gamma']}; the T_i blocks are joined with overlap 0",
                   rows_g, total, N, M, n, top_string=rep["superstring"])
    fig.suptitle(f"Adapted 12/5 construction (report Sec. 4.4), n = {n}: N = {N}, M = {M}, "
                 f"p_i = N + i. Ticks = 1s, segments = gaps between 1s, dotted = zero pads.",
                 fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for ext in ("pdf", "png", "svg"):
        fig.savefig(out / f"fig_twelve_fifths_n{n}.{ext}", dpi=170)
    plt.close(fig)
    print("wrote", out / f"fig_twelve_fifths_n{n}")


if __name__ == "__main__":
    main()
