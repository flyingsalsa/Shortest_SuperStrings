"""Bounded, checksummed download of the real sequencing dataset (section 6A).

Usage (repo root):
    python -m scs.bio.fetch --manifest configs/bio_dataset.json [--max-mb 5]

The manifest (configs/bio_dataset.json) lists each file's URL, expected size
and expected MD5 as reported by the ENA filereport API / NCBI.  A file is only
downloaded if its *advertised* size is within the byte budget, the transfer is
aborted if it exceeds the budget, and the MD5 is checked afterwards.  Raw
files are stored unchanged under data/raw/<accession>/ and never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


def _digest(path: Path, algo: str) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, max_bytes: int, expected_size: int | None = None,
             expected_md5: str | None = None) -> dict:
    if expected_size is not None and expected_size > max_bytes:
        raise RuntimeError(f"{url}: advertised size {expected_size} B exceeds budget {max_bytes} B")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and expected_md5 and _digest(dest, "md5") == expected_md5:
        status = "cached"
    else:
        tmp = dest.with_suffix(dest.suffix + ".part")
        got = 0
        req = urllib.request.Request(url, headers={"User-Agent": "scs-greedy-research/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                got += len(chunk)
                if got > max_bytes:
                    f.close()
                    tmp.unlink()
                    raise RuntimeError(f"{url}: transfer exceeded budget {max_bytes} B; aborted")
                f.write(chunk)
        tmp.replace(dest)
        status = "downloaded"
    md5 = _digest(dest, "md5")
    if expected_md5 and md5 != expected_md5:
        raise RuntimeError(f"{dest}: MD5 {md5} != expected {expected_md5}")
    if expected_size is not None and dest.stat().st_size != expected_size:
        raise RuntimeError(f"{dest}: size {dest.stat().st_size} != expected {expected_size}")
    return {"url": url, "path": str(dest).replace("\\", "/"), "status": status,
            "bytes": dest.stat().st_size, "md5": md5, "sha256": _digest(dest, "sha256")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default="configs/bio_dataset.json")
    ap.add_argument("--max-mb", type=float, default=5.0, help="per-file download budget (MB)")
    ap.add_argument("--out", default="data/raw/checksums.json")
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    budget = int(a.max_mb * 1024 * 1024)
    records = []
    for f in man["files"]:
        rec = download(f["url"], Path(f["dest"]), budget, f.get("bytes"), f.get("md5"))
        rec["role"] = f["role"]
        print(f"{rec['status']:>10}  {rec['bytes']:>9} B  md5 {rec['md5']}  {rec['path']}")
        records.append(rec)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(records, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
