"""Reproducible extraction of small read subsets from the downloaded phiX data.

Usage (repo root, after ``python -m scs.bio.fetch``):
    python -m scs.bio.extract --config configs/bio_extract.json

Reads the raw FASTQ/FASTA unchanged and writes
  data/bio/bio_instances.jsonl   one Instance per sampled subset (ORIGINAL read
                                 strings + read IDs + positions in metadata)
  data/bio/extraction_record.json  all filtering choices, pool sizes, checksums,
                                 read-length distribution

Pipeline (all choices fixed in configs/bio_extract.json before any algorithm
was run; nothing here looks at greedy/DP outcomes):

1. Parse every FASTQ record (ID, sequence).  Quality strings are not used
   (no quality filtering, no trimming, no cropping).
2. Eligibility: length == ``read_length`` and no ambiguous base (anything
   other than A/C/G/T, e.g. N).  Reads are kept in the orientation supplied by
   the sequencer (fixed-orientation strings).  The run is single-end, so there
   is no mate information to handle.
3. Reference-assisted placement (used ONLY for the local-region condition and
   for descriptive statistics): exact string search of the read in the
   circular reference (the linear RefSeq sequence plus its first
   read_length-1 bases appended, so reads spanning the origin are found).
   Strand "+" = read occurs as given; "-" = its reverse complement occurs;
   "unplaced" = neither (in practice: reads with >= 1 sequencing error).  This
   is an exact-match "aligner"; no mismatches or indels are allowed.
4. Conditions (each subset gets its own seed derived from the master seed):
   * ``bio_unconditioned``: draw reads uniformly at random (without
     replacement) from ALL eligible reads, including unplaced ones.
   * ``bio_local``: pick a window start uniformly on the circular genome; the
     candidate pool is the "+"-strand exactly placed reads whose start lies in
     [w, w + window - read_length].  If the pool has fewer than ``min_pool``
     reads a new window start is drawn (recorded in metadata).  Reads are then
     drawn uniformly from the pool.  This condition is deliberately enriched
     for overlapping reads and uses only error-free reads, so it is NOT
     representative of all sequencing reads.
   In both conditions reads are drawn one at a time until the retained set
   (after duplicate/containment removal) reaches the target size n, exactly as
   in the synthetic generators' "retained" mode; all drawn reads are kept as
   the original input.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import random
from pathlib import Path

from ..preprocess import preprocess
from ..schema import Instance, to_dict
from ..seeds import derive_seed, sha256_strings

_COMP = str.maketrans("ACGT", "TGCA")


def revcomp(s: str) -> str:
    return s.translate(_COMP)[::-1]


def read_fastq(path: Path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        while True:
            h = f.readline()
            if not h:
                return
            seq = f.readline().strip()
            f.readline()
            f.readline()
            yield h.strip()[1:].split()[0], seq


def read_fasta(path: Path) -> str:
    return "".join(l.strip() for l in open(path) if not l.startswith(">")).upper()


def place(seq: str, circ: str, genome_len: int):
    p = circ.find(seq)
    if p != -1 and p < genome_len:
        return "+", p
    p = circ.find(revcomp(seq))
    if p != -1 and p < genome_len:
        return "-", p
    return "unplaced", None


def draw_until_retained(rng: random.Random, pool: list, n: int, max_draws: int):
    """Draw pool items without replacement until the retained set has size n."""
    order = list(range(len(pool)))
    rng.shuffle(order)
    drawn = []
    for k, idx in enumerate(order[:max_draws]):
        drawn.append(pool[idx])
        if len(preprocess([r["seq"] for r in drawn]).retained) == n:
            return drawn, True
    return drawn, False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/bio_extract.json")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    fq, fa = Path(cfg["reads"]), Path(cfg["reference"])
    ref = read_fasta(fa)
    G, RL = len(ref), cfg["read_length"]
    circ = ref + ref[: RL - 1]

    all_reads = list(read_fastq(fq))
    len_hist = collections.Counter(len(s) for _, s in all_reads)
    eligible, reasons = [], collections.Counter()
    for rid, s in all_reads:
        if len(s) != RL:
            reasons["wrong_length"] += 1
        elif set(s) - set("ACGT"):
            reasons["ambiguous_base"] += 1
        else:
            strand, pos = place(s, circ, G)
            eligible.append({"id": rid, "seq": s, "strand": strand, "pos": pos})
    strand_counts = collections.Counter(r["strand"] for r in eligible)
    plus = sorted((r for r in eligible if r["strand"] == "+"), key=lambda r: (r["pos"], r["id"]))

    master = cfg["master_seed"]
    insts = []
    for cond in cfg["conditions"]:
        for n in cfg["n_values"]:
            for rep in range(cfg["reps"]):
                seed = derive_seed(master, "bio", cond, n, rep)
                rng = random.Random(seed)
                meta = {"condition": cond, "accession": cfg["accession"], "rep": rep,
                        "reference": cfg["reference_accession"]}
                if cond == "bio_unconditioned":
                    pool = eligible
                else:
                    W = cfg["window"]
                    tries = 0
                    while True:
                        tries += 1
                        w = rng.randrange(G)
                        pool = [r for r in plus
                                if (r["pos"] - w) % G <= W - RL]
                        if len(pool) >= cfg["min_pool"]:
                            break
                    meta.update({"window_start": w, "window": W, "window_tries": tries,
                                 "pool_size": len(pool)})
                drawn, ok = draw_until_retained(rng, pool, n, cfg["max_draws_factor"] * n)
                meta.update({"read_ids": [r["id"] for r in drawn],
                             "strands": [r["strand"] for r in drawn],
                             "positions": [r["pos"] for r in drawn],
                             "n_draws": len(drawn), "n_target_reached": ok})
                params = {"n": n, "condition": cond, "read_length": RL}
                if cond == "bio_local":
                    params["window"] = cfg["window"]
                insts.append(Instance(instance_id=f"{cond}-n{n}-r{rep}", family=cond, label="bio",
                                      params=params, seed=seed,
                                      strings=[r["seq"] for r in drawn], metadata=meta))
    out = Path(cfg["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "bio_instances.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for inst in insts:
            f.write(json.dumps(to_dict(inst)) + "\n")
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    record = {
        "config": cfg,
        "raw_files": {fq.as_posix(): sha(fq), fa.as_posix(): sha(fa)},
        "reference_length": G,
        "n_reads_total": len(all_reads),
        "read_length_histogram": dict(sorted(len_hist.items())),
        "excluded": dict(reasons),
        "n_eligible": len(eligible),
        "eligible_strand_counts": dict(strand_counts),
        "quality_filtering": "none", "trimming": "none",
        "orientation": "as supplied (fixed orientation); reverse complements NOT added",
        "paired_end": "not applicable (single-end run)",
        "placement": "exact match in circularised RefSeq sequence; no mismatches/indels",
        "n_instances": len(insts),
        "n_target_missed": sum(not i.metadata["n_target_reached"] for i in insts),
        "instances_sha256": sha(out / "bio_instances.jsonl"),
    }
    (out / "extraction_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "config"}, indent=1))


if __name__ == "__main__":
    main()
