"""Reproduce Shibata's S_{k,t} lower-bound instances (optional extension).

    python scripts/shibata_experiment.py [--out results/shibata]

For each (k, t) in the grid:
  1. build S_{k,t} (scs/shibata.py);
  2. replay the paper's scripted merges and check, with naive overlaps, that
     every step attains the current maximum overlap (legal greedy step);
  3. certify OPT: counting lower bound n+k-1 matched by an explicit superstring
     (Eulerian circuit), plus exact subset DP where n <= 22;
  4. run our own tie policies (and random seeds) on the same input to see how
     often ordinary tie-breaking finds the bad output;
  5. check the half-compression inequality for the scripted output.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scs.shibata import build_instance, replay_scripted, opt_certificate  # noqa: E402
from scs.preprocess import preprocess                                     # noqa: E402
from scs.overlap import overlap_matrix                                    # noqa: E402
from scs.greedy import greedy                                             # noqa: E402
from scs.exact_dp import exact_dp_numpy                                   # noqa: E402
from scs.validate import check_superstring                                # noqa: E402
from scs.seeds import derive_seed                                         # noqa: E402

GRID = [(10, 1), (10, 2), (10, 4), (10, 8), (10, 9), (10, 12), (10, 16),
        (12, 1), (12, 8), (12, 16), (16, 1), (16, 8), (16, 16), (20, 1), (20, 16)]
POLICY_MAX_N = 200      # our O(n^3) Python greedy is run only up to this n
RANDOM_SEEDS = 50


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/shibata")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, t in GRID:
        t0 = time.perf_counter()
        inst = build_instance(k, t)
        S = inst["strings"]
        n, L = len(S), sum(map(len, S))
        rep = replay_scripted(inst)
        cert = opt_certificate(S)
        G = rep["length"]
        OPT = cert["certified_opt"]
        row = {"k": k, "t": t, "s": k // 2, "n": n, "L": L,
               "scripted_G": G, "paper_G": rep["paper_length"],
               "scripted_legal": not rep["problems"], "problems": rep["problems"],
               "scripted_valid": not check_superstring(S, rep["superstring"]),
               "OPT_certified": OPT, "paper_OPT": t * (4 * (k // 2) + 2) + k - 1,
               "ratio_scripted": G / OPT if OPT else None,
               "paper_limit_ratio": (9 * k + 2) / (4 * k + 4),
               "compression_scripted": (L - G) / (L - OPT) if OPT else None,
               "half_compression_holds": (L - G) >= (L - OPT) / 2 if OPT else None,
               "max_n_tied_in_script": max(st["n_tied"] for st in rep["steps"]),
               "first_step_n_tied": rep["steps"][0]["n_tied"]}
        pre = preprocess(S)
        assert len(pre.retained) == n
        if n <= 22:
            ex = exact_dp_numpy(list(pre.retained))
            row["OPT_exact_dp"] = ex.length
        if n <= POLICY_MAX_N:
            R = list(pre.retained)
            M = overlap_matrix(R)
            for pol in ("lowest_id", "highest_id", "lex_merged"):
                row[f"G_{pol}"] = greedy(R, pol, overlaps=M).length
            rg = [greedy(R, "random", derive_seed(20261105, "tie", f"shibata-k{k}-t{t}", j),
                         overlaps=M).length for j in range(RANDOM_SEEDS)]
            row["G_random_min"], row["G_random_max"] = min(rg), max(rg)
            row["G_random_mean"] = sum(rg) / len(rg)
            row["random_hits_scripted_G"] = sum(g == G for g in rg)
        row["seconds"] = round(time.perf_counter() - t0, 2)
        rows.append(row)
        print({kk: row[kk] for kk in ("k", "t", "n", "scripted_G", "OPT_certified", "ratio_scripted",
                                      "scripted_legal") if kk in row},
              {kk: row[kk] for kk in row if kk.startswith("G_") or kk == "OPT_exact_dp"})
        if (k, t) == (10, 1):
            (out / "trace_k10_t1.json").write_text(json.dumps({
                "strings": S, "names": inst["names"], "steps": rep["steps"],
                "superstring": rep["superstring"], "opt_witness": cert["witness"]}, indent=1),
                encoding="utf-8")
    with open(out / "shibata.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    hdr = ["k", "t", "n", "OPT (certified)", "OPT exact DP", "scripted G", "G/OPT",
           "limit (9k+2)/(4k+4)", "legal", "compression", "lowest_id", "highest_id",
           "lex_merged", f"random min-max ({RANDOM_SEEDS} seeds)"]
    md = ["# Shibata S_{k,t} reproduction\n",
          "Scripted G = the paper's legal tie choices, replayed and checked step by step. "
          "OPT certified by counting lower bound + explicit Eulerian superstring "
          "(and exact DP for n = 22). Policy columns: our own tie rules on the same input "
          "(blank = n > 200, not run).\n",
          "| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    f3 = lambda x: f"{x:.3f}" if isinstance(x, float) else ("" if x is None else str(x))
    for r in rows:
        md.append("| " + " | ".join(f3(x) for x in [
            r["k"], r["t"], r["n"], r["OPT_certified"], r.get("OPT_exact_dp"), r["scripted_G"],
            r["ratio_scripted"], r["paper_limit_ratio"], r["scripted_legal"],
            r["compression_scripted"], r.get("G_lowest_id"), r.get("G_highest_id"),
            r.get("G_lex_merged"),
            f"{r['G_random_min']}-{r['G_random_max']}" if "G_random_min" in r else None]) + " |")
    (out / "shibata.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote", out / "shibata.md")


if __name__ == "__main__":
    main()
