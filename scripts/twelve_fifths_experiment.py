"""Check the adapted 12/5 construction (report Section 4.4 / Appendix A).

    python scripts/twelve_fifths_experiment.py [--legal-max 20] [--len-max 100] [--dp-max 6]

* n = 2..len-max: build S_n and H_n; check substring-freeness, that H_n
  contains every input, |H_n| = 5n^3+12n^2-2n-1, and the scripted output
  length G_n = 12n^3 + (31n^2-43n-12)/2 (computed by performing the scripted
  merges with their actual overlaps).
* n = 2..legal-max: full legality replay (every prescribed pair attains the
  current maximum over all ordered pairs; overlaps alpha_i, beta_i, gamma).
* n = 2..dp-max: exact OPT by subset DP (5(n-1) strings), plus our own tie
  rules and 50 random-tie runs on the same input.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scs.twelve_fifths import build_instance, scripted_sequence, replay  # noqa: E402
from scs.overlap import overlap, overlap_naive, overlap_matrix           # noqa: E402
from scs.preprocess import preprocess                                    # noqa: E402
from scs.greedy import greedy                                            # noqa: E402
from scs.exact_dp import exact_dp_numpy                                  # noqa: E402
from scs.validate import check_superstring, is_substring_free            # noqa: E402
from scs.seeds import derive_seed                                        # noqa: E402


def scripted_length(I):
    """Perform the scripted merges using actual overlaps (no legality check)."""
    cur = dict(I["names"])
    used = {}
    for phase, l, r, new in scripted_sequence(I["n"]):
        o = overlap(cur[l], cur[r])
        used.setdefault(phase, set()).add(o)
        cur[new] = cur.pop(l) + cur.pop(r)[o:]
    (out,) = cur.values()
    return out, used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--legal-max", type=int, default=20)
    ap.add_argument("--len-max", type=int, default=100)
    ap.add_argument("--dp-max", type=int, default=6)
    ap.add_argument("--out", default="results/twelve_fifths")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in range(2, a.len_max + 1):
        t0 = time.perf_counter()
        I = build_instance(n)
        S = list(I["names"].values())
        c = I["claimed"]
        G_str, used = scripted_length(I)
        row = {"n": n, "strings": len(S), "N": I["N"], "M": I["M"],
               "substring_free": is_substring_free(S),
               "H_len": len(I["H"]), "H_len_claimed": c["H_len"],
               "H_contains_all": not check_superstring(S, I["H"]),
               "G_len": len(G_str), "G_len_claimed": c["G_len"],
               "G_contains_all": not check_superstring(S, G_str),
               "alpha_ok": (used["1a: A_i = X_i + Y_i (alpha_i)"] | used["1b: B_i = U_i + V_i (alpha_i)"])
               == set(c["alpha"].values()),
               "beta_ok": used["2: C_i = B_i + Z_i (beta_i)"] == set(c["beta"].values()),
               "gamma_ok": used["3: T_i = A_i + C_i (gamma)"] == {c["gamma"]},
               "concat_ok": n == 2 or used["4: concatenate T_i (overlap 0)"] == {0},
               "ratio_G_over_H": len(G_str) / len(I["H"])}
        if n <= a.legal_max:
            rep = replay(I["names"], scripted_sequence(n), overlap_naive if n <= 6 else overlap)
            row["legal"] = not rep["problems"]
            row["problems"] = rep["problems"]
            row["max_n_tied"] = max(s["n_tied"] for s in rep["steps"])
            assert rep["superstring"] == G_str
        if n <= a.dp_max:
            R = list(preprocess(S).retained)
            M = overlap_matrix(R)
            ex = exact_dp_numpy(R, M)
            row["OPT"] = ex.length
            row["H_is_optimal"] = ex.length == len(I["H"])
            row["ratio_G_over_OPT"] = len(G_str) / ex.length
            for pol in ("lowest_id", "highest_id", "lex_merged"):
                row[f"G_{pol}"] = greedy(R, pol, overlaps=M).length
            rg = [greedy(R, "random", derive_seed(20261105, "tie", f"twelve-fifths-n{n}", j),
                         overlaps=M).length for j in range(50)]
            row["G_random_min"], row["G_random_max"] = min(rg), max(rg)
            row["random_hits_scripted"] = sum(g == len(G_str) for g in rg)
        row["seconds"] = round(time.perf_counter() - t0, 2)
        rows.append(row)
        print({k: row[k] for k in row if k not in ("problems",)}, flush=True)
        if n == 3:
            rep3 = replay(I["names"], scripted_sequence(3), overlap_naive)
            (out / "trace_n3.json").write_text(json.dumps(
                {"names": I["names"], "H": I["H"], "steps": rep3["steps"],
                 "superstring": rep3["superstring"], "order": rep3["order"]}, indent=1), encoding="utf-8")
    with open(out / "twelve_fifths.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    allok = lambda k: all(r[k] for r in rows if k in r)
    md = ["# Adapted 12/5 construction (report Section 4.4) - computational check\n",
          f"n = 2..{a.len_max}: substring-free {allok('substring_free')}, "
          f"|H_n| = claim {all(r['H_len'] == r['H_len_claimed'] for r in rows)}, "
          f"H_n contains all inputs {allok('H_contains_all')}, "
          f"G_n = claim {all(r['G_len'] == r['G_len_claimed'] for r in rows)}, "
          f"overlaps alpha/beta/gamma/0 as claimed "
          f"{allok('alpha_ok') and allok('beta_ok') and allok('gamma_ok') and allok('concat_ok')}.  ",
          f"Full legality replay (every prescribed pair is a current maximum) for n = 2..{a.legal_max}: "
          f"{allok('legal')}.\n",
          "| n | strings | OPT (exact DP) | \\|H_n\\| | scripted G_n | G_n/\\|H_n\\| | G_n/OPT | lowest_id | highest_id | lex_merged | random min-max (50) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    f3 = lambda x: "" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))
    for r in rows:
        if r["n"] <= 10 or r["n"] in (15, 20, 30, 50, 100):
            md.append("| " + " | ".join(f3(x) for x in [
                r["n"], r["strings"], r.get("OPT"), r["H_len"], r["G_len"], r["ratio_G_over_H"],
                r.get("ratio_G_over_OPT"), r.get("G_lowest_id"), r.get("G_highest_id"), r.get("G_lex_merged"),
                f"{r['G_random_min']}-{r['G_random_max']}" if "G_random_min" in r else None]) + " |")
    (out / "twelve_fifths.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("wrote", out / "twelve_fifths.md")


if __name__ == "__main__":
    main()
