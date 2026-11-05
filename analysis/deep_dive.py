"""Targeted analyses for the research questions (coordinator).

    python analysis/deep_dive.py results/standard [results/bio ...] --out results/deep_dive

Produces Markdown tables + figures:
  * sub-configuration breakdown (alphabet, length regime, coverage, motif, mutation)
  * features of instances where greedy (lowest_id) is suboptimal vs optimal,
    stratified by n (RQ2)
  * tie-breaking: instances with/without ties, best-of-policies (RQ3)
  * compression ratio extremes (RQ4)
  * synthetic vs bio comparison
  * step-by-step case studies with merge traces vs optimal order
Only stdlib + numpy + matplotlib.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scs.preprocess import preprocess          # noqa: E402
from scs.overlap import overlap_matrix         # noqa: E402
from scs.greedy import greedy                  # noqa: E402
from scs.exact_dp import exact_dp_numpy        # noqa: E402

DET = ["lowest_id", "highest_id", "lex_merged"]


def load(dirs):
    rows, insts = [], {}
    for d in dirs:
        d = Path(d)
        for line in open(d / "results.jsonl", encoding="utf-8"):
            rows.append(json.loads(line))
        for line in open(d / "instances.jsonl", encoding="utf-8"):
            r = json.loads(line)
            insts[r["instance_id"]] = r
    return rows, insts


def per_instance(rows):
    """instance_id -> dict with OPT, features, G per deterministic policy, random Gs."""
    by = defaultdict(lambda: {"random": []})
    for r in rows:
        if r["status"] != "ok" or not r.get("valid"):
            continue
        d = by[r["instance_id"]]
        for k in ("family", "label", "params", "n", "L", "ell", "n_raw", "alphabet_size",
                  "frac_pos_overlap_pairs", "mean_overlap", "max_overlap"):
            d[k] = r[k]
        if r["algorithm"] == "exact_dp":
            d["OPT"] = r["length"]
        elif r["policy"] == "random":
            d["random"].append(r["length"])
        else:
            d[r["policy"]] = r["length"]
            if r["policy"] == "lowest_id":
                d["tie_steps"] = r["n_tie_steps"]
                d["max_tied"] = r["max_tied"]
    return {k: v for k, v in by.items() if "OPT" in v and "lowest_id" in v}


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(fmt(x) for x in r) + " |")
    return "\n".join(out)


def fmt(x):
    if isinstance(x, float):
        return f"{x:.3f}"
    return str(x)


def subconfig_key(d):
    p = d["params"]
    f = d["family"]
    if f == "random":
        return f"alph={p['alphabet']}, len {p['len_min']}-{p['len_max']}" + (" fixed" if p.get("len_dist") == "fixed" else "")
    if f == "fragments":
        return f"alph={p['alphabet']}, len {p['len_min']}-{p['len_max']}, cov={p['coverage']}"
    if f == "repetitive":
        return f"motif={p['motif_len']}, mut={p['mutation_rate']}"
    if f.startswith("bio"):
        return f
    return f


def summarize(group, pol="lowest_id"):
    ratios = [d[pol] / d["OPT"] for d in group]
    opt = [d[pol] == d["OPT"] for d in group]
    return len(group), float(np.mean(opt)), float(np.median(ratios)), float(np.mean(ratios)), float(max(ratios))


def section_subconfig(inst, out):
    lines = ["## 1. Breakdown by generator sub-configuration (policy lowest_id, all n pooled)\n",
             "Pooled over n = 5..20 (benchmark) or 5..18 (bio); N = instances. "
             "Larger n lowers optimality rates, so compare rows within a family only "
             "(each sub-configuration has the same n mix).\n"]
    for fam in ("random", "fragments", "repetitive", "bio_unconditioned", "bio_local"):
        groups = defaultdict(list)
        for d in inst.values():
            if d["family"] == fam:
                groups[subconfig_key(d)].append(d)
        if not groups:
            continue
        rows = []
        for k in sorted(groups):
            g = groups[k]
            N, rate, med, mean, mx = summarize(g)
            fpos = st.median(d["frac_pos_overlap_pairs"] for d in g)
            red = st.mean(1 - d["n"] / d["n_raw"] for d in g)
            rows.append([k, N, rate, mean, mx, fpos, red])
        lines.append(f"### {fam}\n")
        lines.append(md_table(["sub-config", "N", "opt_rate", "mean G/OPT", "max G/OPT",
                               "median frac pairs ov>0", "mean preprocessing reduction"], rows))
        lines.append("")
    out.append("\n".join(lines))


def section_features(inst, out, figdir):
    lines = ["## 2. Which input properties go with suboptimal greedy? (lowest_id)\n",
             "Within each (generator sub-configuration, n) stratum we compare suboptimal (G > OPT) and optimal "
             "instances. Values are medians of the stratum medians (so differences are not "
             "driven by n). `tie_frac` = fraction of merges with >1 maximal pair. "
             "Association only; no causal claim.\n"]
    feats = ["frac_pos_overlap_pairs", "mean_overlap", "max_overlap", "tie_frac", "max_tied", "ell"]
    rows = []
    for fam in ("random", "fragments", "repetitive", "bio_unconditioned", "bio_local"):
        strata = defaultdict(lambda: ([], []))
        for d in inst.values():
            if d["family"] != fam or d["n"] < 2:
                continue
            d["tie_frac"] = d["tie_steps"] / (d["n"] - 1)
            strata[(subconfig_key(d), d["n"])][0 if d["lowest_id"] > d["OPT"] else 1].append(d)
        if not strata:
            continue
        for f in feats:
            sub, opt = [], []
            for n, (a, b) in strata.items():
                if a and b:
                    sub.append(st.median(x[f] for x in a))
                    opt.append(st.median(x[f] for x in b))
            if sub:
                rows.append([fam, f, len(sub), st.median(sub), st.median(opt)])
    lines.append(md_table(["family", "feature", "#strata", "suboptimal (median)", "optimal (median)"], rows))
    lines.append("")
    # ties vs optimality
    rows2 = []
    for fam in ("random", "fragments", "repetitive", "bio_unconditioned", "bio_local"):
        g = [d for d in inst.values() if d["family"] == fam and d["n"] >= 2]
        if not g:
            continue
        no_tie = [d for d in g if d["tie_steps"] == 0]
        tie = [d for d in g if d["tie_steps"] > 0]
        r = lambda grp: (float(np.mean([d["lowest_id"] == d["OPT"] for d in grp])) if grp else float("nan"))
        rows2.append([fam, len(no_tie), r(no_tie), len(tie), r(tie)])
    lines.append("### Optimality with vs without any tie during the run (lowest_id)\n")
    lines.append("Instances with no tie at all have a unique greedy output. Note: tie-free runs "
                 "are concentrated at small n, so this comparison is confounded by n.\n")
    lines.append(md_table(["family", "N no ties", "opt_rate no ties", "N with ties", "opt_rate with ties"], rows2))
    lines.append("")
    out.append("\n".join(lines))

    # figure: gap vs frac_pos_overlap, per family at n=15
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
    for ax, fam in zip(axes, ("random", "fragments", "repetitive")):
        g = [d for d in inst.values() if d["family"] == fam and d["n"] == 15]
        x = [d["frac_pos_overlap_pairs"] for d in g]
        y = [d["lowest_id"] / d["OPT"] for d in g]
        ax.scatter(x, y, s=10, alpha=0.5)
        ax.set_title(f"{fam}, n=15 (N={len(g)})")
        ax.set_xlabel("fraction of ordered pairs with overlap > 0")
    axes[0].set_ylabel("G/OPT (lowest_id)")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(figdir / f"fig_ratio_vs_overlap_density.{ext}", dpi=150)
    plt.close(fig)


def section_ties(inst, out, figdir):
    lines = ["## 3. Tie-breaking effect\n",
             "`best` = min G over the 3 deterministic policies and all random seeds; "
             "`worst` = max over the same runs (a lower bound on the worst tie-breaking). "
             "All on identical instances.\n"]
    rows = []
    for fam in ("random", "fragments", "repetitive", "bio_unconditioned", "bio_local"):
        for n in sorted({d["n"] for d in inst.values() if d["family"] == fam}):
            g = [d for d in inst.values() if d["family"] == fam and d["n"] == n]
            allG = lambda d: [d[p] for p in DET if p in d] + d["random"]
            best = np.mean([min(allG(d)) == d["OPT"] for d in g])
            worst = np.mean([max(allG(d)) == d["OPT"] for d in g])
            low = np.mean([d["lowest_id"] == d["OPT"] for d in g])
            rescue = np.mean([d["lowest_id"] > d["OPT"] and min(allG(d)) == d["OPT"] for d in g])
            wr = max(max(allG(d)) / d["OPT"] for d in g)
            rows.append([fam, n, len(g), low, best, worst, rescue, wr])
    lines.append(md_table(["family", "n", "N", "opt_rate lowest_id", "opt_rate best-of-runs",
                           "opt_rate worst-of-runs", "frac lowest_id suboptimal but some run optimal",
                           "max worst-run G/OPT"], rows))
    lines.append("")
    out.append("\n".join(lines))

    fig, ax = plt.subplots(figsize=(6.5, 4))
    for fam, mk, col in (("random", "o", "C0"), ("fragments", "s", "C1"), ("repetitive", "^", "C2")):
        ns = sorted({d["n"] for d in inst.values() if d["family"] == fam})
        for key, ls in (("best", "-"), ("lowest", "--"), ("worst", ":")):
            ys = []
            for n in ns:
                g = [d for d in inst.values() if d["family"] == fam and d["n"] == n]
                allG = lambda d: [d[p] for p in DET] + d["random"]
                f = {"best": lambda d: min(allG(d)), "worst": lambda d: max(allG(d)),
                     "lowest": lambda d: d["lowest_id"]}[key]
                ys.append(np.mean([f(d) == d["OPT"] for d in g]))
            ax.plot(ns, ys, ls, marker=mk, color=col, label=f"{fam} ({key})", ms=4)
    ax.set_xlabel("retained strings n")
    ax.set_ylabel("fraction of instances with G = OPT")
    ax.set_title("G = OPT rate: best / lowest_id / worst of 13 tie-breaking runs\n(N = 180-300 instances per point)", fontsize=10)
    ax.legend(fontsize=7, ncol=3)
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(figdir / f"fig_tie_best_worst.{ext}", dpi=150)
    plt.close(fig)


def section_compression(inst, out):
    lines = ["## 4. Compression ratio (L-G)/(L-OPT) extremes\n",
             "Defined only when L > OPT (all benchmark instances here). Proven bound: >= 1/2 "
             "(Tarhio-Ukkonen / Turner). Minimum over ALL runs (all policies and seeds) per family.\n"]
    rows = []
    for fam in sorted({d["family"] for d in inst.values()}):
        g = [d for d in inst.values() if d["family"] == fam and d["L"] > d["OPT"]]
        if not g:
            continue
        vals = []
        for d in g:
            for G in [d[p] for p in DET if p in d] + d["random"]:
                vals.append((d["L"] - G) / (d["L"] - d["OPT"]))
        und = sum(1 for d in inst.values() if d["family"] == fam and d["L"] == d["OPT"])
        rows.append([fam, len(g), len(vals), min(vals), float(np.quantile(vals, 0.01)),
                     float(np.median(vals)), sum(v < 0.75 for v in vals), und])
    lines.append(md_table(["family", "N instances", "N runs", "min", "1st pct", "median",
                           "#runs < 0.75", "#instances undefined (L=OPT)"], rows))
    lines.append("")
    out.append("\n".join(lines))


def section_bio(inst, out):
    lines = ["## 5. Synthetic vs bio (phiX174 reads), policy lowest_id\n",
             "Bio results are kept separate. Matched n only. `ell` = read length (76) for bio.\n"]
    rows = []
    for n in (5, 8, 10, 12, 15, 18):
        for fam in ("random", "fragments", "repetitive", "bio_unconditioned", "bio_local"):
            g = [d for d in inst.values() if d["family"] == fam and d["n"] == n]
            if not g:
                continue
            N, rate, med, mean, mx = summarize(g)
            rows.append([n, fam, N, rate, mean, mx,
                         st.median(d["frac_pos_overlap_pairs"] for d in g),
                         st.median(d["mean_overlap"] for d in g),
                         st.mean(1 - d["n"] / d["n_raw"] for d in g),
                         st.mean(d["tie_steps"] / (d["n"] - 1) for d in g)])
    lines.append(md_table(["n", "family", "N", "opt_rate", "mean G/OPT", "max G/OPT",
                           "median frac pairs ov>0", "median mean ov", "mean prepro reduction",
                           "mean tie_frac"], rows))
    lines.append("")
    out.append("\n".join(lines))


def explain(strings, title, out, note="", extra_runs=()):
    pre = preprocess(strings)
    R = list(pre.retained)
    M = overlap_matrix(R)
    ex = exact_dp_numpy(R, M)
    L = sum(map(len, R))
    lines = [f"### {title}\n", note,
             (f"Original inputs ({len(strings)}): `{', '.join(strings)}`  " if len(strings) <= 20 else f"Original inputs: {len(strings)} strings (see instances.jsonl)  "),
             f"Retained (ID: string): " + ", ".join(f"{i}:`{s}`" for i, s in enumerate(R)) +
             f"  (removed {len(pre.removals)}: " +
             ", ".join(f"{sum(r.reason == k for r in pre.removals)} {k}" for k in ("empty", "duplicate", "contained")) + ")  ",
             f"L = {L}, OPT = {ex.length}, optimal order {ex.order} → `{ex.superstring}`  ",
             "Optimal consecutive overlaps: " +
             ", ".join(f"ov({a},{b})={M[a][b]}" for a, b in zip(ex.order, ex.order[1:])) + "\n"]
    for pol, seed in (("lowest_id", None), ("highest_id", None), ("lex_merged", None)) + tuple(extra_runs):
        g = greedy(R, pol, seed, trace=True, overlaps=M)
        lines.append(f"**greedy {pol}" + (f" (tie seed {seed})" if seed is not None else "") + f"**: G = {g.length}, G/OPT = {g.length / ex.length:.3f}, "
                     f"compression (L-G)/(L-OPT) = " +
                     (f"{(L - g.length) / (L - ex.length):.3f}" if L > ex.length else "undefined") + "  ")
        for s in g.trace:
            lines.append(f"  - step {s.step}: max overlap {s.max_overlap}, {s.n_tied} tied pair(s); "
                         f"merge {s.left_id}+{s.right_id} → id {s.new_id} = `{s.merged}`")
        lines.append("")
    out.append("\n".join(lines))


def section_cases(inst, raw_insts, rows, out):
    out.append("## 6. Case studies (step-by-step)\n")
    explain(["BAB", "AABA", "ABAA"], "Regression case BAB, AABA, ABAA", out,
            "The unique maximum overlap (3) locks greedy into a merge that destroys two "
            "overlaps of size 2.\n")
    explain(["CABAB", "BABA", "ABABC"], "Blum-style family c(ab)^k, (ba)^k, (ab)^k c with k=2", out,
            "(letters C,A,B). Greedy's max-overlap pair joins the two ends and leaves the middle "
            "string with no overlap.\n")
    disc = [d for d in raw_insts.values() if d.get("label") == "discovered"]
    if disc:
        # the discovered instance with largest lowest_id ratio
        best = max((d for d in disc if d["instance_id"] in inst),
                   key=lambda d: inst[d["instance_id"]]["lowest_id"] / inst[d["instance_id"]]["OPT"])
        explain(best["strings"], f"Discovered (search output, not a benchmark sample): {best['instance_id']}",
                out, "Found by `scripts/search_counterexamples.py`; selected for being bad, so "
                     "NOT representative.\n")
    # tightest benchmark compression ratio over all runs (incl. random seeds)
    tight = None
    for r in rows:
        if (r["algorithm"] == "greedy" and r["status"] == "ok" and r["label"] == "benchmark"
                and r["instance_id"] in inst and r["L"] > inst[r["instance_id"]]["OPT"]):
            c = (r["L"] - r["length"]) / (r["L"] - inst[r["instance_id"]]["OPT"])
            key = (c, r["instance_id"], r["policy"], r["tie_run"] if r["tie_run"] is not None else -1)
            if tight is None or key < tight[0]:
                tight = (key, r)
    if tight:
        (c, iid, pol, _), r = tight
        explain(raw_insts[iid]["strings"],
                f"Smallest compression ratio among benchmark runs: {iid}, policy {pol} ({c:.3f})", out,
                "Here L - OPT is tiny, so the ratio is coarse: one character of lost overlap halves it.\n",
                extra_runs=[(pol, r["tie_seed"])] if pol == "random" else [])
    for fam in ("random", "fragments", "repetitive", "bio_unconditioned"):
        g = [d for k, d in inst.items() if d["family"] == fam]
        if not g:
            continue
        worst_id = max((k for k, d in inst.items() if d["family"] == fam),
                       key=lambda k: (inst[k]["lowest_id"] / inst[k]["OPT"], k))
        d = inst[worst_id]
        explain(raw_insts[worst_id]["strings"],
                f"Worst {fam} instance for lowest_id: {worst_id} (n={d['n']})", out,
                f"Chosen as the maximum G/OPT among {len(g)} {fam} instances; this is the "
                "tail, not a typical case (typical G/OPT is 1.0).\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", default="results/deep_dive")
    a = ap.parse_args()
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    rows, raw = load(a.dirs)
    inst = per_instance(rows)
    out = ["# Deep-dive analysis\n",
           f"Sources: {', '.join(a.dirs)}. Instances with certified OPT: {len(inst)}. "
           "Generated by `analysis/deep_dive.py`.\n"]
    section_subconfig(inst, out)
    section_features(inst, out, outdir)
    section_ties(inst, out, outdir)
    section_compression(inst, out)
    section_bio(inst, out)
    section_cases(inst, raw, rows, out)
    (outdir / "deep_dive.md").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {outdir / 'deep_dive.md'}")


if __name__ == "__main__":
    main()
