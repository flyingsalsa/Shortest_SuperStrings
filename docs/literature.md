# Literature verification

Checked 2026-11-05. "Verified" below means: bibliographic record (title, authors,
venue, year, DOI/arXiv id) was fetched from a primary or registry page (arXiv
abstract/HTML page, Crossref API, publisher/DOI landing page). It does NOT mean
that the full text of a paywalled paper was read. For every claim we say how it
was checked. Several publisher pages (ScienceDirect, SIAM, ACM, DBLP) refused
automated access (HTTP 403/429 or bot-protection page); those items are marked.

## 0. Two different statements - do not confuse them

* **Compression bound (PROVED, 1988/89).** Let `L` be the sum of the lengths of a
  substring-free input set, `OPT` the optimal superstring length and `G` the greedy
  length. Then `L - G >= (L - OPT) / 2`: greedy achieves at least half of the
  optimal *compression* (total overlap used). This does NOT bound `G / OPT` by 2.
  Compression ratio 1/2 is compatible with `G/OPT` approaching 2 (and, as it turns
  out, more; see below).
* **Greedy conjecture (Tarhio-Ukkonen): `G <= 2 OPT`.** Open for ~40 years;
  **a September 2026 preprint (Shibata, not yet peer reviewed) claims it is false**
  with a lower bound of 9/4. The best *proved* upper bound is a recent preprint (3);
  the best peer-reviewed one found is about 3.425 (3.5 before that; see table).

## 1. Source table

| # | Source | Venue / status | Identifier | Verified how |
|---|---|---|---|---|
| 1 | J. Gallant, D. Maier, J. A. Storer, "On finding minimal length superstrings" | J. Comput. Syst. Sci. 20(1):50-58, Feb 1980 (journal) | doi:10.1016/0022-0000(80)90004-5 | Crossref record fetched (Crossref lists the third author as "James Astorer", evidently an encoding error for Storer; DBLP via search agrees on JCSS 20(1) 50-58). Abstract only partly seen. |
| 2 | J. Tarhio, E. Ukkonen, "A greedy approximation algorithm for constructing shortest common superstrings" | Theoretical Computer Science 57(1):131-145, 1988 (journal) | doi:10.1016/0304-3975(88)90167-3 | Crossref record fetched. Full text NOT read (ScienceDirect 403). |
| 3 | J. S. Turner, "Approximation algorithms for the shortest common superstring problem" | Information and Computation 83(1):1-20, 1989 (journal) | doi:10.1016/0890-5401(89)90044-8 | DOI taken from Scilit listing and an ACM reference list found by search (my first guess at a DOI returned 404 and was discarded). Author PDF link (arl.wustl.edu) now redirects away; full text NOT read. |
| 4 | A. Blum, T. Jiang, M. Li, J. Tromp, M. Yannakakis, "Linear approximation of shortest superstrings" | J. ACM 41(4):630-647, 1994 (journal; extended abstract at STOC 1991) | doi:10.1145/179812.179818 | DBLP/ACM bibliographic data seen via search snippets; DBLP page itself blocked. Full text NOT read. |
| 5 | H. Kaplan, N. Shafrir, "The greedy algorithm for shortest superstrings" | Information Processing Letters 93(1):13-17, 16 Jan 2005 (journal) | doi:10.1016/j.ipl.2004.09.012 | Record seen on Tel Aviv Univ. CRIS page. **Discrepancy:** that page's abstract text says the output is at most "2 times" optimal, whereas Englert et al. (source 6) attribute 3.5 to this paper. We believe 2 is a page/abstract error but could not read the paper; treat the exact constant as UNRESOLVED from primary text (3.5 is the widely cited value). |
| 6 | M. Englert, N. Matsakis, P. Vesely, "Improved Approximation Guarantees for Shortest Superstrings using Cycle Classification by Overlap to Length Ratios" | arXiv:2111.03968 v1, 6 Nov 2021. A conference version is cited by search results as doi:10.1145/3519935.3520001 (STOC 2022) - NOT confirmed from the publisher. | arXiv abs page fetched | arXiv abstract: GREEDY <= (13+sqrt 57)/6 ~ 3.425 OPT; first improvement since 2005; and a (37+sqrt 57)/18 ~ 2.475 approximation for SCS. |
| 7 | P. E. Kalugin, M. S. Nikolaev, "The greedy algorithm for the Shortest Common Superstring problem is a 1/2-approximation in terms of compression: a simple proof" | 2024 Symposium on Simplicity in Algorithms (SOSA), pp. 97-99, 2024 (conference) | doi:10.1137/1.9781611977936.9 | Crossref record fetched (title, authors, pages). SIAM page 403; full text NOT read. |
| 8 | M. Nikolaev, "Greedy Conjecture for the Shortest Common Superstring Problem and its Strengthenings" | arXiv:2407.20422 v1, 29 Jul 2024 (preprint; no journal-ref listed) | arXiv abs page fetched | Proves a Locally Greedy Algorithm is a uniform 4-approximation under a symbol-counting quality metric; shows LGA >= 3 and Greedy >= uniform 2.5 under that metric. Does not settle the conjecture. |
| 9 | N. Chukhin, A. S. Kulikov, I. Mihajlin, A. Smal, "The Greedy Superstring Algorithm Achieves Ratio 2 for Strings of Length 6 Already" | arXiv:2608.20018 v2 (v1 20 Aug 2026, v2 24 Aug 2026) preprint | arXiv abs + HTML fetched | Thm 3.1: for every fixed length k >= 6 the greedy ratio rho_k >= 2 (suprema over alphabets and tie-breaking). Thm 4.1/5.1: rho_3 = 9/5 exactly. Disproves the Cazaux-Rivals conjecture rho_k = 2 - 1/k. Says the general conjecture (ratio 2) is still open (v2, before source 11). Construction: nine length-6 strings, OPT = 9t+5, greedy can reach 18t, with t blocks using fresh symbols. Ties are arbitrary (bound holds for a suitable tie-breaking). Authors "independently verified"; AI assistance disclosed (GPT-5.6 Sol Pro/Ultra). Hand proofs; no peer review known. |
| 10 | N. Chukhin, A. S. Kulikov, I. Mihajlin, A. Smal, "A Tight Cycle-Cover Inequality for Shortest Common Superstring" | arXiv:2609.27921 v2 (v1 listed 21 Aug 2026, v2 24 Sep 2026; the id prefix suggests Sept 2026 - minor inconsistency on the abs page) preprint | arXiv abs + HTML fetched | Improves SCS approximation to 7/3 and proves greedy <= 3 OPT (via (2+gamma) with gamma = 1, shown best possible for that inequality). Input substring-free; tie-breaking not addressed in the text. AI assistance disclosed. Preprint. |
| 11 | H. Shibata, "Disproving the Greedy Superstring Conjecture" | arXiv:2609.01365 v1, 1 Sep 2026, cs.DS, CC BY 4.0, no journal-ref (preprint, not peer reviewed per a tracker page) | arXiv abs + HTML fetched | Cor. 15: greedy ratio >= 9/4 for general SCS. Thm 14: for even k >= 10 inputs all of length k, rho_k >= (9k+2)/(4k+4). Construction S_{k,t} over alphabet {x,y,a,b_1..b_t}; OPT = t(4s+2)+k-1 (k = 2s), some greedy output has length t(9s+1)+1. Substring-free inputs; **ties arbitrary: the bad output is one valid tie-breaking choice** ("we may select any such pair"). Proofs by hand, no computer verification described, no explicit small instance in the text. **Project check (coordinator, 2026-11-05):** construction re-implemented from the arXiv HTML; scripted greedy run machine-checked legal and OPT certified for 15 (k,t) pairs, G/OPT up to 2.109 (see docs/FINDINGS.md section 3b). Discloses that OpenAI's "GPT-5.6 Sol" in a custom harness found the counterexample/strategies; author states he verified everything. |

## 2. Results, assumptions, and project dependencies

### 2.1 NP-hardness / APX-hardness / DP (source 1, 4)
* Gallant-Maier-Storer 1980: deciding whether a superstring of length <= K exists is
  NP-complete (the abstract fragment we saw mentions constructions for strings of
  length 3 and >3, and a linear-time algorithm for length <= 2). Exact wording of the
  theorem not read: **cite for "NP-hard" only after reading the paper.**
* APX-hardness: Nikolaev (source 8) states in its abstract that SCS is APX-hard (this
  is the usual citation to Blum et al. 1994; we did not read the JACM text).
* Exact algorithm: SCS reduces to a minimum-weight Hamiltonian path on the overlap
  graph, solved in O(2^n n^2) time by Held-Karp-style subset DP (Bellman 1962 /
  Held-Karp 1962 for TSP). This is a standard textbook technique; we cite no
  primary source here and the project does not depend on a specific paper. Our own
  implementation is `scs/exact_dp.py`; correctness is checked by the brute-force
  oracles in `scs/oracle.py`.
* Project dependency: motivates why OPT is only computed for small n (exponential).

### 2.2 Compression bound (sources 2, 3, 7)
* Statement: for a substring-free set, `L - G >= (L - OPT)/2`. Equivalently
  `G <= (L + OPT)/2`. This does not give `G <= 2 OPT`: `L` can be far larger
  than `OPT` (e.g. many heavily overlapping strings), so the bound on `G` can be
  much weaker than a factor 2.
* Attribution: Tarhio and Ukkonen (1988) is the usual primary citation; Turner
  (1989) is cited by the Kalugin-Nikolaev-era literature for the same compression
  guarantee for greedy. Whether Turner proved it independently of Tarhio-Ukkonen
  could NOT be verified from a primary text (Turner's PDF unreachable). Treat
  "independently" as UNRESOLVED; cite both. The 2024 SOSA paper (source 7) gives a
  new *simple proof* of the same bound, per its title; a search snippet of a survey
  states the 1/2 compression factor for the greedy algorithm and that the
  Tarhio-Ukkonen proof is complex.
* Assumptions: the standard statement is for substring-free input (our
  `preprocess` guarantees this). Whether it holds for **every** tie-breaking rule:
  consistent with the sources (Shibata and Chukhin et al. define greedy with
  arbitrary tie-breaking, and the compression bound is stated for "the greedy
  algorithm"), but NOT verified from the original proofs. Our experiments check it
  empirically for all four policies; **a violation would be a finding about either a
  bug or the literature.**
* Nontrivial proof ingredient (we verified this lemma ourselves; not read in a
  source): **Monge-like overlap inequality.** For any strings a, b, c, d, if
  `x = ov(a,b) >= max(y, z)` where `y = ov(a,d)`, `z = ov(c,b)`, then
  `ov(a,b) + ov(c,d) >= ov(a,d) + ov(c,b)`.
  *Proof (ours).* Let `P` be the prefix of b of length x; it is also a suffix of a.
  The prefix of d of length y equals the suffix of a of length y, which (since
  y <= x) is the suffix of P of length y. The suffix of c of length z equals the
  prefix of b of length z, i.e. the prefix of P of length z (z <= x). If
  `y + z - x <= 0` the claim is trivial since ov >= 0. Otherwise the prefix of P of
  length z and the suffix of P of length y overlap in `y + z - x` characters, so
  the last `y+z-x` characters of c's suffix equal the first `y+z-x` characters of
  d's prefix. Hence `ov(c,d) >= y + z - x`. QED. No substring-freeness or
  distinctness is needed for this step. We also tested it by random search
  (157,458 qualifying quadruples over alphabets of size 2 and 3, strings up to
  length 7): zero violations.
* How it is used (outline, our reading; the full argument in the papers handles
  cycles carefully and is lengthy): when greedy takes the maximum-overlap edge
  (a,b) of weight w, an optimal solution is changed to contain (a,b): remove the
  edge leaving a, (a,d), and the edge entering b, (c,b); both have weight <= w, so
  the cost of the exchange is at most `y+z`; the Monge inequality says the edge
  (c,d) recovers at least `y+z-w`, so the net loss is at most w - in the best case
  the exchange does not lose compression at all, but closing a cycle can force
  deleting another edge, and bookkeeping this yields: every unit of greedy
  compression "pays" for at most two units of optimal compression, i.e. 1/2.
  **This outline is not a proof and is not verified against the papers.** Do not
  present it as the published argument.
* Project dependency: the "compression ratio vs 1/2" figure and the flag for any
  instance with `(L-G) < (L-OPT)/2` (docs/metrics.md, analysis/analyze.py).

### 2.3 G/OPT upper bounds and the lower-bound family (sources 4, 5, 6, 10)
* Blum et al. 1994: greedy <= 4 OPT is the commonly cited statement (source 6
  attributes the 4-approximation to Blum et al., STOC 1991). We saw a snippet of the
  JACM abstract: constant-factor approximation, with a modified greedy
  reaching 3. Exact statement for plain greedy: not read.
* Kaplan-Shafrir 2005: greedy <= 3.5 OPT (as cited by source 6; see discrepancy
  in the table). Englert-Matsakis-Vesely 2021: <= ~3.425 (arXiv; conference
  version unconfirmed). Chukhin et al. 2026: <= 3 (preprint).
* Lower-bound family with ratio -> 2 (Blum et al.): we have not read the example in
  the paper, but we recomputed the family used in `docs/INTERFACES.md` ("known",
  `c(ab)^k, (ba)^k, (ab)^k c`) ourselves by exhaustive permutation search and by
  running maximum-overlap greedy: OPT = 2k + 4 and greedy = 4k + 2 for
  k = 2..7, so the ratio tends to 2 as k grows. (Greedy merges
  `c(ab)^k` with `(ab)^k c` first, overlap 2k, then the third string has overlap
  0.) **Whether this is exactly the Blum et al. example is UNRESOLVED**; call it
  "Blum-style" in the report.
* Project dependency: `known` family D examples and the discussion in FINDINGS.

### 2.4 Status of the greedy conjecture (sources 8-11)
* Before Aug 2026: open; known only that ratio >= 2 (Blum-style example), and for
  inputs of one fixed length k: ratio 2 - 1/k conjectured by Cazaux and Rivals
  (Discrete Applied Mathematics, 2018; Cazaux-Rivals page fetched: doi
  10.1016/j.dam.2017.04.017, "Relationship between superstring and compression
  measures: New insights on the greedy conjecture"; the 2 - 1/k statement itself
  is as reported by source 9, not read in the original).
* Aug 2026: Chukhin et al. (9): for k >= 6 fixed-length ratio >= 2 (refutes
  2 - 1/k); rho_3 = 9/5.
* Sep 2026: Shibata (11): ratio >= 9/4, hence the conjecture `G <= 2 OPT` is false
  **if the preprint is correct** (hand proofs, AI-discovered, not peer reviewed,
  one author). Our experiments cannot test it: smallest counterexample has
  k >= 10 strings of length >= 10 and t >= 2 blocks (n = 4s+2 per block >= 22 per
  block), beyond our exact DP range (n <= 16-20). Do not claim to confirm or
  refute it. Because Shibata's bad run uses a specific tie-breaking, our
  tie-sensitivity experiment is conceptually related: for a given instance the
  worst case over all tie-breaking can exceed lowest_id / random runs.
* Kalugin-Nikolaev: **not** a result about the G <= 2 OPT conjecture or about 3.425.
  The 3.425 bound is Englert-Matsakis-Vesely. Kalugin-Nikolaev (SOSA 2024) is a
  short simplified proof of the 1/2 *compression* bound. (This corrects the lead
  in the task brief.)
* The "OpenAI manuscript": the only matching item found is Shibata's paper (11),
  which discloses that an OpenAI model ("GPT-5.6 Sol") found the counterexample;
  the Chukhin et al. papers also disclose use of GPT-5.6 Sol models. We found no
  standalone OpenAI-authored manuscript. The Kingy AI tracker page for Shibata's
  result does not itself name OpenAI. Unresolved whether any separate OpenAI
  document exists.

## 3. Unresolved claims (final list)

1. Turner 1989 proved the compression bound independently of Tarhio-Ukkonen
   (full text unreachable).
2. Exact theorem and assumptions in Tarhio-Ukkonen 1988 (arbitrary tie-breaking?
   substring-free?): primary text not read.
3. Kaplan-Shafrir constant: CRIS abstract says 2, later papers say 3.5.
4. Blum et al.: exact statements (greedy <= 4 OPT; ratio-2 example) not read from
   JACM; our recomputation shows the c(ab)^k family achieves 2 asymptotically.
5. Englert et al. conference version (STOC 2022 doi) unconfirmed.
6. Gallant-Maier-Storer: exact NP-completeness statement not read.
7. Correctness and peer-review status of Shibata (9/4), Chukhin et al. (ratio 2 for
   k = 6; greedy <= 3; 7/3 approximation): preprints only. The date mismatch on
   the arXiv page of 2609.27921 (v1 listed in Aug 2026) is unexplained.
8. Existence of an "OpenAI manuscript" distinct from AI-assisted arXiv papers.
9. Compression bound for **every** tie-breaking rule (assumed in the project,
   tested empirically, not verified from the original proofs).
