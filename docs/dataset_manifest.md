# Real-world sequencing dataset manifest (extension 6A)

Framing: *evaluating shortest-superstring algorithms on strings derived from
biological sequencing data.* This is **not** a genome assembler.

All facts below were fetched on 2026-11-05 by the coordinator with `curl`
from the ENA Portal API (`/ena/portal/api/filereport`, `/ena/portal/api/search`),
the ENA Browser XML API, NCBI E-utilities (`esummary`) and Europe PMC.
(Agent D's web-fetch tool refused the ENA API, so this step was done by the
coordinator; see `docs/AI_ASSISTANCE.md`.)

## Candidates considered

| # | Run | Organism | Platform / layout | Reads | FASTQ size | Notes |
|---|---|---|---|---|---|---|
| 1 | **ERR098007** (study PRJEB2910, experiment ERX076017, sample SAMEA1094997) | phiX174 (taxid 10847) | Illumina Genome Analyzer IIx, single-end, 76 bp | 23,332 | 1,836,971 B (gz) | **Selected** |
| 2 | ERR097996 (same study PRJEB2910) | phiX174 | Illumina GA IIx, single-end | 254,092 | 19,654,620 B (gz) | Same source, 10x larger than needed |
| 3 | ERR10806051 (study PRJEB59215, "Deep mutational scanning reveals the molecular determinants of RNA polymerase-mediated adaptation and tradeoffs") | *E. coli* K-12 MG1655 (taxid 511145) | NextSeq 550, paired-end | 6,830 pairs | 42,780 + 45,790 B (gz) | Tiny, but 4.6 Mb genome → random reads almost never overlap; amplicon-style study design; paired |

## Selected dataset

* **Run:** ERR098007 — ENA study PRJEB2910 (secondary ERP001254), title
  "PhiX174", alias "PhiX174_sequencing_error", submitted by the Max Planck
  Institute for Evolutionary Anthropology. Project description (ENA XML):
  data used "in the DREEP ... paper to estimate the sequencing error".
* **Organism / reference:** Escherichia phage phiX174, RefSeq **NC_001422.1**,
  5,386 bp, circular, complete genome (NCBI esummary).
* **Platform:** Illumina Genome Analyzer IIx; library GENOMIC / strategy OTHER;
  single-end. First public 2012-02-28.
* **File:** `https://ftp.sra.ebi.ac.uk/vol1/fastq/ERR098/ERR098007/ERR098007.fastq.gz`,
  1,836,971 bytes, MD5 `6929c1176a8ca06fe303f4d1c9fbb16e` (ENA-reported; matched
  after download). SHA-256 of the downloaded file:
  `636e948fb6680148e4fb030257e74c8421687d4effbd49d207570e893dbae01e`.
* **Reference FASTA:** NCBI efetch
  `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=NC_001422.1&rettype=fasta&retmode=text`,
  SHA-256 `caa155c83967cc080f4f188f14f1f28c18d77448e87c3d00d3579ed348f4de2a`
  (NCBI does not publish an MD5 for this endpoint; we record our own hash).
* **Read characteristics (measured):** 23,332 reads; 23,152 of length 76,
  117 of length 72, the rest shorter; 34 reads contain `N`.
* **Usage terms:** public INSDC/ENA data with no access restrictions (standard
  INSDC open data policy). Cite the run/study accessions.
* **Associated publication:** the ENA project mentions the "DREEP" paper. A
  candidate is Li M., Stoneking M. "A new approach for detecting low-level
  mutations in next-generation sequence data", *Genome Biology* 13:R34 (2012),
  doi:10.1186/gb-2012-13-5-r34 (same institute and topic). **Unverified link:**
  its abstract does not name DREEP or this accession, so we cite the ENA
  accessions as the primary provenance and the paper only as "probably related".

### Why chosen

phiX174 is the standard Illumina control genome; its 5.4 kb genome at ~330x
coverage means even random small subsets of 76 bp reads overlap often, which
makes exact-overlap superstring instances non-trivial. The file is under 2 MB
(no large archive downloaded), single-end (no pairing decisions), has a
complete RefSeq reference, and a published MD5 for integrity checking.

## Reproduction

```bash
python -m scs.bio.fetch --max-mb 5          # bounded download + MD5 check -> data/raw/
python -m scs.bio.extract                   # configs/bio_extract.json -> data/bio/
python -m scs.cli run configs/bio.json --force
python analysis/analyze.py results/bio
```

`data/raw/` is git-ignored (raw data kept unchanged); `data/bio/` (selected
subsets with read IDs, positions, strands, seeds; extraction record with
checksums) is committed.

## Extraction choices (configs/bio_extract.json; fixed before any algorithm run)

* Eligible reads: length exactly 76, only A/C/G/T (34 reads with `N` and 180
  reads of other lengths excluded) → 23,118 eligible reads.
* No quality filtering, trimming or cropping. Orientation as supplied;
  reverse complements are **not** added (that would change the problem by
  requiring both orientations). Single-end: no pairing.
* Reference-assisted placement: exact string match in the circularised
  NC_001422.1 sequence (no mismatches/indels; this is our own trivial exact
  matcher, not a real aligner). Of eligible reads: 9,710 match the "+"
  strand, 1,962 match as reverse complement, 11,446 do not match exactly
  (almost all because of sequencing errors).
* Conditions: `bio_unconditioned` (uniform from all eligible reads) and
  `bio_local` (uniform from "+"-strand exactly placed reads starting within a
  random 250 bp window of the circular genome; window redrawn if the pool has
  < 40 reads). Reads are drawn until the retained (duplicate/containment-free)
  set reaches n ∈ {5, 8, 10, 12, 15, 18}; 30 subsets per (condition, n);
  seeds `derive_seed(20261105, "bio", condition, n, rep)`.
* Duplicate/contained-read removal is the same `preprocess` used everywhere.
