#!/usr/bin/env python
"""Analysis of shortest-superstring experiment results (metrics: docs/metrics.md).

Usage:
    python analysis/analyze.py results/standard [--out results/standard/analysis]
    python analysis/analyze.py --scaling results/scaling [--out results/scaling/analysis]
    python analysis/analyze.py results/standard --scaling results/scaling

Reads  <dir>/results.jsonl  (+ <dir>/instances.jsonl, optional) and, for the
scaling study, <scaling_dir>/scaling.jsonl (falls back to results.jsonl).
Writes CSV + Markdown tables and PDF/PNG figures. Only stdlib, numpy, matplotlib.
No claim about actual results is made by this script; it only computes metrics.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PRIMARY_POLICY = "lowest_id"
SPECIAL_LABELS = ("known", "discovered")
BOOT_RESAMPLES = 2000
BOOT_SEED = 12345
NAN = float("nan")


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------

def read_jsonl(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"warning: {path}:{ln}: bad JSON line skipped", file=sys.stderr)
    return rows


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def good(row):
    return row.get("status") == "ok" and row.get("valid") is True and is_num(row.get("length"))


def label_of(row, inst):
    lab = row.get("label") or (inst or {}).get("label")
    if lab:
        return lab
    fam = row.get("family") or (inst or {}).get("family") or ""
    if fam in SPECIAL_LABELS:
        return fam
    return "bio" if str(fam).startswith("bio") else "benchmark"


# ----------------------------------------------------------------------------
# Stats helpers
# ----------------------------------------------------------------------------

def dist(vals):
    a = np.asarray([v for v in vals if is_num(v)], dtype=float)
    if a.size == 0:
        return dict(N=0, mean=NAN, median=NAN, q1=NAN, q3=NAN, p90=NAN, p95=NAN, max=NAN)
    q1, med, q3, p90, p95 = np.percentile(a, [25, 50, 75, 90, 95])
    return dict(N=int(a.size), mean=float(a.mean()), median=float(med), q1=float(q1),
                q3=float(q3), p90=float(p90), p95=float(p95), max=float(a.max()))


def boot_ci(flags, rng):
    """95% percentile bootstrap CI of the mean of 0/1 flags, resampling INSTANCES."""
    a = np.asarray(flags, dtype=float)
    if a.size < 5:
        return NAN, NAN
    idx = rng.integers(0, a.size, size=(BOOT_RESAMPLES, a.size))
    means = a[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def fmt(x):
    if isinstance(x, float):
        if math.isnan(x):
            return ""
        return f"{x:.4g}"
    return str(x)


def write_table(outdir: Path, name: str, header, rows, title="", note=""):
    """Write name.csv and name.md."""
    with (outdir / f"{name}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(["" if (isinstance(v, float) and math.isnan(v)) else v for v in r])
    with (outdir / f"{name}.md").open("w", encoding="utf-8") as f:
        if title:
            f.write(f"# {title}\n\n")
        if note:
            f.write(note.rstrip() + "\n\n")
        if not rows:
            f.write("_No data._\n")
            return
        f.write("| " + " | ".join(header) + " |\n")
        f.write("|" + "|".join("---" for _ in header) + "|\n")
        for r in rows:
            f.write("| " + " | ".join(fmt(v) for v in r) + " |\n")


def savefig(fig, outdir: Path, name: str):
    fig.tight_layout()
    fig.savefig(outdir / f"{name}.pdf")
    fig.savefig(outdir / f"{name}.png", dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------
# Building per-instance records
# ----------------------------------------------------------------------------

def build_instances(results, instances):
    inst_meta = {i.get("instance_id"): i for i in instances}
    excluded = defaultdict(int)   # (family, algorithm, status) -> count
    exact = {}
    greedy = defaultdict(lambda: defaultdict(list))   # iid -> policy -> [rows]
    for r in results:
        iid = r.get("instance_id")
        if iid is None:
            continue
        if not good(r):
            excluded[(r.get("family", "?"), r.get("algorithm", "?"),
                      r.get("status") if r.get("status") != "ok" else "invalid")] += 1
            continue
        if r.get("algorithm") == "exact_dp":
            exact[iid] = r
        elif r.get("algorithm") == "greedy" and isinstance(r.get("policy"), str):
            greedy[iid][r.get("policy")].append(r)
    records = []
    for iid, pols in greedy.items():
        any_row = next(iter(pols.values()))[0]
        ex = exact.get(iid)
        inst = inst_meta.get(iid)
        rec = dict(
            instance_id=iid,
            family=any_row.get("family") or (inst or {}).get("family", "?"),
            label=label_of(any_row, inst),
            n=any_row.get("n"), n_raw=any_row.get("n_raw"),
            L=any_row.get("L"), L_raw=any_row.get("L_raw"),
            n_removed_empty=any_row.get("n_removed_empty"),
            n_removed_duplicate=any_row.get("n_removed_duplicate"),
            n_removed_contained=any_row.get("n_removed_contained"),
            opt=ex["length"] if ex else None,
            policies={},
        )
        for pol, rs in pols.items():
            lens = [r["length"] for r in rs]
            rec["policies"][pol] = dict(
                G_mean=float(np.mean(lens)), G_min=min(lens), G_max=max(lens),
                runs=len(lens),
                opt_frac=(float(np.mean([l == rec["opt"] for l in lens])) if ex else None),
                n_tie_steps=max((r.get("n_tie_steps") or 0) for r in rs),
            )
        records.append(rec)
    records.sort(key=lambda r: r["instance_id"])
    return records, excluded


def policy_metrics(rec, pol):
    """Per-instance metrics for one policy; random uses the mean over seeds."""
    p = rec["policies"].get(pol)
    opt, L = rec["opt"], rec["L"]
    if p is None or opt is None:
        return None
    G = p["G_mean"]
    m = dict(G=G, gap=G - opt, opt_frac=p["opt_frac"],
             ratio=(G / opt if opt > 0 else NAN))
    if is_num(L):
        m["savings_g"] = L - G
        m["savings_opt"] = L - opt
        if L - opt > 0:
            m["comp"] = (L - G) / (L - opt)
            # slack on the WORST run (G_max) so a single bad run is not averaged away
            m["slack"] = (L - p["G_max"]) - (L - opt) / 2.0
        else:
            m["comp"] = NAN
            m["slack"] = NAN
        m["no_comp"] = (L - opt) <= 0
    return m


# ----------------------------------------------------------------------------
# Tables
# ----------------------------------------------------------------------------

def summary_tables(records, outdir, policies):
    rng = np.random.default_rng(BOOT_SEED)
    bench = [r for r in records if r["label"] == "benchmark"]
    bio = [r for r in records if r["label"] not in ("benchmark",) + SPECIAL_LABELS]
    special = [r for r in records if r["label"] in SPECIAL_LABELS]

    header = ["policy", "family", "n", "N", "ratio_mean", "ratio_median", "ratio_q1", "ratio_q3",
              "ratio_p90", "ratio_p95", "ratio_max", "gap_mean", "gap_max", "opt_rate",
              "opt_ci_lo", "opt_ci_hi", "comp_N", "comp_median", "comp_min", "n_no_compression"]
    rows = []
    viol = []
    neg_gap = []
    for group_name, group in (("benchmark", bench), ("bio", bio)):
        by = defaultdict(list)
        for r in group:
            by[(r["family"], r["n"])].append(r)
        for pol in policies:
            for (fam, n), recs in sorted(by.items(), key=lambda kv: (str(kv[0][0]), kv[0][1] if is_num(kv[0][1]) else -1)):
                ms = [m for m in (policy_metrics(r, pol) for r in recs) if m is not None]
                if not ms:
                    continue
                d = dist([m["ratio"] for m in ms])
                gaps = [m["gap"] for m in ms]
                flags = [m["opt_frac"] for m in ms]   # per-instance optimal fraction
                lo, hi = boot_ci(flags, rng)
                comps = [m["comp"] for m in ms if "comp" in m and is_num(m["comp"])]
                rows.append([pol, fam if group_name == "benchmark" else f"{fam} (bio)", n, d["N"],
                             d["mean"], d["median"], d["q1"], d["q3"], d["p90"], d["p95"], d["max"],
                             float(np.mean(gaps)), max(gaps), float(np.mean(flags)), lo, hi,
                             len(comps), (float(np.median(comps)) if comps else NAN),
                             (min(comps) if comps else NAN),
                             sum(1 for m in ms if m.get("no_comp"))])
    # violations are checked over ALL labels (also known/discovered)
    for r in records:
        for pol in policies:
            m = policy_metrics(r, pol)
            if m is None:
                continue
            p = r["policies"][pol]
            if is_num(m.get("slack")) and m["slack"] < -1e-9:
                viol.append([r["instance_id"], r["family"], r["label"], pol, r["n"], r["L"], r["opt"],
                             p["G_max"], m["slack"]])
            if p["G_min"] < r["opt"]:
                neg_gap.append([r["instance_id"], r["family"], pol, p["G_min"], r["opt"]])

    banner = ""
    if viol:
        banner += (f"**WARNING: {len(viol)} half-compression violation(s) "
                   f"((L-G) < (L-OPT)/2) - see violations.csv. Investigate before reporting.**\n\n")
    if neg_gap:
        banner += (f"**WARNING: {len(neg_gap)} case(s) with G < OPT (impossible; bug in greedy, DP "
                   f"or validation) - see greedy_below_opt.csv.**\n\n")
    note = (banner + "Benchmark (and bio, labelled) instances only; `known`/`discovered` are in "
            "`summary_special`. Per instance one value: deterministic policy = its G; `random` = mean G "
            "over tie seeds (`opt_rate` = mean over instances of the per-instance fraction of optimal "
            "runs). CI = 95% percentile bootstrap over instances (blank if fewer than 5 instances). "
            "`comp_*` is (L-G)/(L-OPT), only where L-OPT>0; those with L-OPT=0 are counted in "
            "`n_no_compression`.")
    write_table(outdir, "summary_by_family_n", header, rows, "Greedy vs exact by family and n", note)
    write_table(outdir, "violations",
                ["instance_id", "family", "label", "policy", "n", "L", "OPT", "G_max", "slack"],
                viol, "Half-compression violations", banner or "None found.")
    write_table(outdir, "greedy_below_opt", ["instance_id", "family", "policy", "G_min", "OPT"],
                neg_gap, "Greedy shorter than OPT (impossible)", banner or "None found.")
    if viol:
        print(f"!!! WARNING: {len(viol)} HALF-COMPRESSION VIOLATION(S) - see violations.csv", file=sys.stderr)
    if neg_gap:
        print(f"!!! WARNING: {len(neg_gap)} case(s) with G < OPT - see greedy_below_opt.csv", file=sys.stderr)

    # special families
    srows = []
    for r in special:
        for pol in policies:
            m = policy_metrics(r, pol)
            if m is None:
                continue
            p = r["policies"][pol]
            srows.append([r["label"], r["family"], r["instance_id"], r["n"], r["L"], r["opt"], pol,
                          p["G_min"], p["G_max"], m["ratio"], m.get("comp", NAN)])
    write_table(outdir, "summary_special",
                ["label", "family", "instance_id", "n", "L", "OPT", "policy", "G_min", "G_max", "G/OPT",
                 "compression_ratio"], srows,
                "Known / discovered instances (reported separately; NOT part of benchmark aggregates)")
    return bench, bio, special, viol


def tie_table(records, outdir, policies):
    rows = []
    by = defaultdict(list)
    for r in records:
        if r["label"] == "benchmark":
            by[(r["family"], r["n"])].append(r)
    for (fam, n), recs in sorted(by.items(), key=lambda kv: (str(kv[0][0]), kv[0][1] if is_num(kv[0][1]) else -1)):
        ranges, rel, changed, tied_inst, tied_changed = [], [], 0, 0, 0
        pol_diff = {p: [0, 0] for p in policies if p != PRIMARY_POLICY}
        for r in recs:
            gs = [v for p in r["policies"].values() for v in (p["G_min"], p["G_max"])]
            if not gs:
                continue
            rg = max(gs) - min(gs)
            ranges.append(rg)
            if r["opt"]:
                rel.append(rg / r["opt"])
            changed += rg > 0
            has_ties = any(p["n_tie_steps"] > 0 for p in r["policies"].values())
            tied_inst += has_ties
            tied_changed += has_ties and rg > 0
            base = r["policies"].get(PRIMARY_POLICY)
            for p in pol_diff:
                q = r["policies"].get(p)
                if base and q:
                    pol_diff[p][0] += 1
                    pol_diff[p][1] += (q["G_min"] != base["G_min"] or q["G_max"] != base["G_max"]
                                       or q["G_mean"] != base["G_mean"])
        if not ranges:
            continue
        d = dist(ranges)
        rows.append([fam, n, d["N"], changed / d["N"], d["mean"], d["median"], d["max"],
                     float(np.mean(rel)) if rel else NAN, tied_inst,
                     (tied_changed / tied_inst) if tied_inst else NAN]
                    + [(pol_diff[p][1] / pol_diff[p][0]) if pol_diff[p][0] else NAN for p in pol_diff])
    header = (["family", "n", "N", "frac_G_changes", "range_mean", "range_median", "range_max",
               "range_rel_to_OPT_mean", "N_with_ties", "frac_changes_among_tied"]
              + [f"frac_{p}_differs_from_{PRIMARY_POLICY}" for p in policies if p != PRIMARY_POLICY])
    write_table(outdir, "tie_sensitivity", header, rows, "Tie-breaking sensitivity (per instance)",
                "range = max G - min G over all policies and all random seeds of one instance "
                "(lower bound on the worst case over all tie-breakings). Instance-level counts only.")
    return rows


def prep_table(records, outdir):
    rows = []
    by = defaultdict(list)
    for r in records:
        if r["label"] == "benchmark" or r["label"] not in SPECIAL_LABELS:
            by[r["family"]].append(r)
    for fam, recs in sorted(by.items()):
        def frac(key):
            return [(r[key] or 0) / r["n_raw"] for r in recs if is_num(r.get("n_raw")) and r["n_raw"] > 0]
        tot = frac("n_removed_empty")
        removed = [((r["n_raw"] - r["n"]) / r["n_raw"]) for r in recs
                   if is_num(r.get("n_raw")) and r["n_raw"] > 0 and is_num(r.get("n"))]
        lred = [1 - r["L"] / r["L_raw"] for r in recs
                if is_num(r.get("L_raw")) and r["L_raw"] > 0 and is_num(r.get("L"))]
        rows.append([fam, len(recs),
                     float(np.mean(removed)) if removed else NAN, float(np.median(removed)) if removed else NAN,
                     float(np.mean(frac("n_removed_duplicate"))) if recs and frac("n_removed_duplicate") else NAN,
                     float(np.mean(frac("n_removed_contained"))) if recs and frac("n_removed_contained") else NAN,
                     float(np.mean(tot)) if tot else NAN,
                     float(np.mean(lred)) if lred else NAN])
    write_table(outdir, "preprocessing", ["family", "N", "removed_frac_mean", "removed_frac_median",
                                          "duplicate_frac_mean", "contained_frac_mean", "empty_frac_mean",
                                          "L_reduction_mean"], rows, "Preprocessing reduction",
                "Fractions of raw strings removed (n_raw - n)/n_raw; L reduction = 1 - L/L_raw.")
    return rows


def runtime_table(rows_in, outdir, name, title):
    by = defaultdict(list)
    cnt = defaultdict(lambda: defaultdict(int))
    for r in rows_in:
        if r.get("algorithm") != "exact_dp" and r.get("algorithm") is not None:
            continue
        eng = r.get("engine") or (r.get("params") or {}).get("engine") or r.get("algorithm") or "exact_dp"
        n = r.get("n")
        if not is_num(n):
            continue
        cnt[(eng, n)][r.get("status", "?")] += 1
        if r.get("status") == "ok" and is_num(r.get("t_solve_s")):
            by[(eng, n)].append(r["t_solve_s"])
    out = []
    for (eng, n) in sorted(set(by) | set(cnt), key=lambda k: (str(k[0]), k[1])):
        v = by.get((eng, n), [])
        bad = sum(c for s, c in cnt[(eng, n)].items() if s != "ok")
        out.append([eng, n, len(v), float(np.median(v)) if v else NAN, max(v) if v else NAN, bad])
    write_table(outdir, name, ["engine", "n", "N_ok", "t_solve_median_s", "t_solve_max_s", "N_not_ok"], out, title)
    return out


# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------

def jitter(rng, k, w=0.12):
    return rng.uniform(-w, w, size=k)


def fig_ratio(bench, outdir, pol):
    rng = np.random.default_rng(1)
    groups = defaultdict(list)
    for r in bench:
        m = policy_metrics(r, pol)
        if m and is_num(m["ratio"]):
            groups[(r["family"], r["n"])].append(m["ratio"])
    if not groups:
        return
    keys = sorted(groups, key=lambda k: (str(k[0]), k[1] if is_num(k[1]) else -1))
    fams = sorted({k[0] for k in keys})
    cmap = plt.get_cmap("tab10")
    fig, ax = plt.subplots(figsize=(max(6, 0.45 * len(keys) + 2), 4.5))
    for i, k in enumerate(keys):
        v = groups[k]
        c = cmap(fams.index(k[0]) % 10)
        ax.boxplot([v], positions=[i], widths=0.6, showfliers=False,
                   medianprops=dict(color="black"), boxprops=dict(color=c), whiskerprops=dict(color=c),
                   capprops=dict(color=c))
        ax.scatter(i + jitter(rng, len(v)), v, s=8, color=c, alpha=0.5, zorder=3)
    ax.axhline(1, color="gray", lw=0.8, ls=":")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([f"{k[0]}\nn={k[1]}\n(N={len(groups[k])})" for k in keys], fontsize=7)
    ax.set_ylabel("G / OPT  (dimensionless)")
    ax.set_title(f"Greedy ratio G/OPT by family and retained n" + chr(10) + f"(policy: {pol}; benchmark instances; N = instances)", fontsize=9)
    handles = [plt.Line2D([], [], color=cmap(j % 10), marker="s", ls="", label=f) for j, f in enumerate(fams)]
    ax.legend(handles=handles, fontsize=8, title="family")
    savefig(fig, outdir, "fig_ratio_by_family")


def fig_optrate(bench, outdir, pol):
    rng = np.random.default_rng(BOOT_SEED)
    by = defaultdict(lambda: defaultdict(list))
    for r in bench:
        m = policy_metrics(r, pol)
        if m and m["opt_frac"] is not None and is_num(r["n"]):
            by[r["family"]][r["n"]].append(m["opt_frac"])
    if not by:
        return
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for fam in sorted(by):
        ns = sorted(by[fam])
        mean = [np.mean(by[fam][n]) for n in ns]
        ci = [boot_ci(by[fam][n], rng) for n in ns]
        line, = ax.plot(ns, mean, marker="o", label=f"{fam} (N={sum(len(by[fam][n]) for n in ns)})")
        lo = [c[0] if not math.isnan(c[0]) else m for c, m in zip(ci, mean)]
        hi = [c[1] if not math.isnan(c[1]) else m for c, m in zip(ci, mean)]
        ax.fill_between(ns, lo, hi, color=line.get_color(), alpha=0.15)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("retained number of strings n")
    ax.set_ylabel("fraction of instances with G = OPT")
    ax.set_title(f"Greedy optimality rate vs n (policy: {pol}); band = 95% bootstrap CI over instances")
    ax.title.set_fontsize(9)
    ax.legend(fontsize=8)
    savefig(fig, outdir, "fig_optimality_rate")


def fig_runtime(rt_rows, outdir, name, title):
    pts = defaultdict(list)
    for eng, n, nok, med, mx, bad in rt_rows:
        if nok:
            pts[eng].append((n, med, mx, nok))
    if not pts:
        return
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for eng, v in sorted(pts.items()):
        v.sort()
        line, = ax.plot([p[0] for p in v], [p[1] for p in v], marker="o", label=f"{eng}: median")
        ax.plot([p[0] for p in v], [p[2] for p in v], marker="x", ls="--", color=line.get_color(),
                label=f"{eng}: max")
    ax.set_yscale("log")
    ax.set_xlabel("retained number of strings n")
    ax.set_ylabel("solve time t_solve_s  (seconds, log scale)")
    ax.set_title(title, fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    savefig(fig, outdir, name)


def fig_ties(bench, outdir, policies):
    by = defaultdict(list)
    for r in bench:
        gs = [v for p in r["policies"].values() for v in (p["G_min"], p["G_max"])]
        if gs:
            by[(r["family"], r["n"])].append(max(gs) - min(gs))
    if not by:
        return
    keys = sorted(by, key=lambda k: (str(k[0]), k[1] if is_num(k[1]) else -1))
    fig, ax = plt.subplots(figsize=(max(6, 0.5 * len(keys) + 2), 4.2))
    fr = [np.mean([x > 0 for x in by[k]]) for k in keys]
    ax.bar(range(len(keys)), fr, color="tab:orange")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([f"{k[0]}\nn={k[1]}\n(N={len(by[k])})" for k in keys], fontsize=7)
    ax.set_ylim(0, 1)
    ax.set_ylabel("fraction of instances where G differs\nacross tie-breaking policies / seeds")
    ax.set_title("Tie-breaking sensitivity on identical instances (benchmark only)", fontsize=9)
    savefig(fig, outdir, "fig_tie_sensitivity")


def fig_compression(bench, outdir, policies):
    rng = np.random.default_rng(2)
    pol = PRIMARY_POLICY if PRIMARY_POLICY in policies else policies[0]
    groups = defaultdict(list)
    for r in bench:
        m = policy_metrics(r, pol)
        if m and is_num(m.get("comp")):
            groups[r["family"]].append(m["comp"])
    if not groups:
        return
    fams = sorted(groups)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for i, f in enumerate(fams):
        v = groups[f]
        ax.boxplot([v], positions=[i], widths=0.6, showfliers=False, medianprops=dict(color="black"))
        ax.scatter(i + jitter(rng, len(v)), v, s=8, alpha=0.5, zorder=3)
    ax.axhline(0.5, color="red", ls="--", label="proved lower bound 1/2 (Tarhio-Ukkonen / Turner)")
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels([f"{f}\n(N={len(groups[f])})" for f in fams], fontsize=8)
    ax.set_ylabel("compression ratio (L-G)/(L-OPT)")
    ax.set_title(f"Greedy compression ratio (policy: {pol}; instances with L=OPT excluded)", fontsize=9)
    ax.legend(fontsize=8, loc="lower right")
    savefig(fig, outdir, "fig_compression_ratio")


def fig_prep(prep_rows, outdir):
    if not prep_rows:
        return
    fams = [r[0] for r in prep_rows]
    vals = [r[2] if is_num(r[2]) else 0 for r in prep_rows]
    fig, ax = plt.subplots(figsize=(max(5, 0.8 * len(fams) + 2), 4))
    ax.bar(range(len(fams)), vals, color="tab:green")
    ax.set_xticks(range(len(fams)))
    ax.set_xticklabels([f"{r[0]}\n(N={r[1]})" for r in prep_rows], fontsize=8)
    ax.set_ylabel("mean fraction of raw strings removed")
    ax.set_title("Preprocessing reduction (duplicates + contained + empty)", fontsize=9)
    savefig(fig, outdir, "fig_preprocessing")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def analyze_main(indir: Path, outdir: Path, policy_pref: str):
    results = read_jsonl(indir / "results.jsonl")
    instances = read_jsonl(indir / "instances.jsonl")
    if not results:
        print(f"error: no rows in {indir / 'results.jsonl'}", file=sys.stderr)
        return 1
    outdir.mkdir(parents=True, exist_ok=True)
    records, excluded = build_instances(results, instances)
    write_table(outdir, "excluded_counts", ["family", "algorithm", "status", "count"],
                [[*k, v] for k, v in sorted(excluded.items(), key=str)],
                "Rows excluded from metrics (status != ok or invalid)")
    policies = sorted({p for r in records for p in r["policies"]},
                      key=lambda p: (p != PRIMARY_POLICY, str(p)))
    if not policies:
        print("error: no valid greedy rows", file=sys.stderr)
        return 1
    n_with_opt = sum(r["opt"] is not None for r in records)
    print(f"{len(records)} instances with greedy rows; {n_with_opt} with exact OPT; policies: {policies}")
    pol = policy_pref if policy_pref in policies else policies[0]
    bench, bio, special, viol = summary_tables(records, outdir, policies)
    tie_table(records, outdir, policies)
    prep_rows = prep_table(records, outdir)
    rt = runtime_table(results, outdir, "runtime_by_engine_n", "Exact DP runtime by engine and n")
    plot_set = bench + bio
    fig_ratio(plot_set, outdir, pol)
    fig_optrate(plot_set, outdir, pol)
    fig_ties(bench, outdir, policies)
    fig_compression(plot_set, outdir, policies)
    fig_prep(prep_rows, outdir)
    fig_runtime(rt, outdir, "fig_runtime", "Exact DP runtime vs n (this run; median and max)")
    # combined markdown index
    with (outdir / "README.md").open("w", encoding="utf-8") as f:
        f.write("# Analysis outputs\n\nGenerated by analysis/analyze.py. Definitions: docs/metrics.md.\n\n")
        if viol:
            f.write(f"**WARNING: {len(viol)} half-compression violation(s); see violations.csv.**\n\n")
        for t in ("summary_by_family_n", "summary_special", "tie_sensitivity", "preprocessing",
                  "runtime_by_engine_n", "violations", "greedy_below_opt", "excluded_counts"):
            f.write(f"* {t}.md / {t}.csv\n")
    print(f"wrote outputs to {outdir}")
    return 0


def analyze_scaling(sdir: Path, outdir: Path):
    rows = read_jsonl(sdir / "scaling.jsonl") or read_jsonl(sdir / "results.jsonl")
    if not rows:
        print(f"error: no scaling rows in {sdir}", file=sys.stderr)
        return 1
    outdir.mkdir(parents=True, exist_ok=True)
    rt = runtime_table(rows, outdir, "scaling_runtime", "DP runtime scaling")
    fig_runtime(rt, outdir, "fig_scaling_runtime", "Exact DP runtime vs n (scaling study; median and max)")
    print(f"wrote scaling outputs to {outdir}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results_dir", nargs="?", help="directory with results.jsonl / instances.jsonl")
    ap.add_argument("--out", help="output directory (default <dir>/analysis)")
    ap.add_argument("--scaling", help="scaling-study directory with scaling.jsonl")
    ap.add_argument("--policy", default=PRIMARY_POLICY, help="policy used for figures (default lowest_id)")
    a = ap.parse_args(argv)
    if not a.results_dir and not a.scaling:
        ap.error("give a results directory and/or --scaling DIR")
    rc = 0
    if a.results_dir:
        d = Path(a.results_dir)
        rc |= analyze_main(d, Path(a.out) if a.out else d / "analysis", a.policy)
    if a.scaling:
        s = Path(a.scaling)
        out = Path(a.out) if (a.out and not a.results_dir) else s / "analysis"
        rc |= analyze_scaling(s, out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
