# Real-world dataset manifest (sequencing-derived strings)

STATUS: **INCOMPLETE - nothing below is verified.**

The metadata fetch for this task (the ENA `filereport` API for a candidate run,
via the WebFetch tool) was refused by the tool's content filter ("can't help with
this", flagged `[bio]`). No other route was tried to avoid working around that
restriction. No accession, file size or URL has therefore been verified, and
**no accession is recommended** here. The coordinator should either fetch the
metadata themselves or decide how to proceed.

## What is known from the task brief only (unverified by us)

| Item | Value given in brief | Verified? |
|---|---|---|
| Reference: phiX174 | NC_001422.1, genome 5386 bp | No |
| Reference: E. coli K-12 MG1655 | NC_000913.3 | No |
| FASTA download template | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=<ACC>&rettype=fasta` | No |
| Run metadata template | `https://www.ebi.ac.uk/ena/portal/api/filereport?accession=<RUN>&result=read_run&fields=run_accession,experiment_accession,study_accession,fastq_ftp,fastq_bytes,read_count,base_count,instrument_platform,instrument_model,library_layout,scientific_name` | No |

## Checklist to complete when metadata is available

For each candidate: dataset name; organism; run/experiment/study accessions;
source links (ENA and SRA); platform and instrument; read length and layout;
`fastq_bytes` and `read_count` from the ENA filereport; format; usage terms;
associated publication; reference assembly accession; and whether a bounded
extraction is possible (first N reads of a gzipped FASTQ via an HTTP range
request or `head -n 4N` of a streamed file, or a small run).

Design notes (independent of any specific dataset): reads must be
preprocessed like all instances (duplicates and contained reads removed; reads
with N removed or split); n must be sub-sampled to the exact-DP range (n <= 16-20)
for any greedy-vs-OPT comparison, while larger subsets can only be used for
greedy-vs-reference-length comparisons (no OPT).
