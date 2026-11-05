You are the lead research engineer for:
“Shortest Superstring: How Good Is Greedy?”
Build the code, run the experiments, and produce the evidence needed to finish our research project. Use multiple agents efficiently if your environment supports them. 
1. Project objective and scope
We are studying maximum-overlap greedy for the Shortest Common Superstring problem.
Our central research questions are:

How close does greedy come to the optimal output length on different input families?
Which input properties are associated with poor greedy decisions?
How much does tie-breaking affect the result?
How do empirical compression savings relate to the established half-compression guarantee?
How quickly does the exact subset-DP benchmark become impractical?
The core project consists of:

Understanding the half-compression theorem.
Implementing greedy and an exact subset-DP solver.
Running controlled, reproducible experiments.
Explaining observed behaviour using concrete merge traces and input structure.
Recent Shibata and Chukhin manuscripts mentioned in our presentation are literature context. Reproducing Shibata’s construction is an optional extension after the core project works.

Agent organization
Use one coordinator and up to four specialist workers. If fewer workers are available, combine responsibilities. Do not create extra agents merely to increase parallelism. Spin up agents using sonnet where appropriate to save costs
Before parallel implementation, the coordinator must define:
Public function signatures and result schemas.
Input normalization and pre-processing conventions.
Tie-breaking semantics.
Experiment configuration format.
File ownership.
The initial runtime and memory budget.
Suggested division:
Agent A — Core algorithms

Own preprocessing, overlap calculation, greedy, and exact DP.
Document their correctness arguments and actual implementation complexity.
Return merge traces and reconstructed superstrings.
Agent B — Data generation and experiment runner

Own generators, configuration files, persistence, resource limits, and CLI experiment execution.
Work against agreed interfaces.
Ensure reproducible seeds and matched input instances across algorithms.
Agent C — Independent verification

Own tests, a tiny exhaustive reference solver, and adversarial cases.
Independently check the algorithms and data validity.
Do not simply copy Agent A’s recurrence into a second implementation and call that independent verification.
Agent D — Literature and analysis

Verify primary sources, theorem assumptions, publication status, and relevant claims.
Specify metrics, aggregation, and plots.
Implement analysis against the agreed result schema.
Write findings only after actual experiment outputs are available.
Coordinator responsibilities:

Own shared configuration, integration, packaging, README, and final synthesis.
Prevent multiple agents from editing the same files.
Resolve interface disagreements before dependent work expands.
Integrate and run correctness checks before large experiments.
Review workers’ evidence rather than accepting completion claims at face value.
Parallelize independent implementation, generator design, tests, and literature checks. Keep these dependencies sequential:
interfaces → integration → correctness gate → pilot → main experiments → interpretation.
After tests are stable, Agent C may audit suspicious instances and Agent D may analyze completed batches. Avoid repeated full-repository reviews and duplicate implementations without a clear verification purpose.
If agent tools are unavailable, perform these roles sequentially and state that limitation.
3. Mathematical definitions
Inputs may have different lengths. Equal-length strings are not required.
Preprocess by removing duplicates and strings contained in other inputs. Preserve original inputs and a record of removals.
Use:

n: number of retained strings.
ell: maximum retained string length.
L: sum of retained string lengths.
G: greedy output length.
OPT: exact minimum superstring length.
Define ov(i,j) as the longest suffix of s_i matching a prefix of s_j.
Exact DP:
D[{j},j] = |s_j|
D[M,j] = min over i in M excluding j:
D[M excluding j,i] + |s_j| - ov(i,j)
OPT = min_j D[all,j]
Store predecessors and reconstruct a valid optimal superstring.
The DP has O(n² 2^n) time and O(n 2^n) space after overlap computation, under the usual word-RAM accounting. State overlap/preprocessing costs separately. Do not claim a linear-time overlap routine if the implemented routine uses quadratic scanning.
Explain why preprocessing permits the ordering formulation and why remembering the subset and last string is sufficient.
The compression theorem to study is:
L - G >= (L - OPT)/2.
Do not confuse this with G <= 2 OPT. Verify the theorem’s assumptions and the proof’s nontrivial steps from primary sources.
4. Implementation requirements
Use Python and a small, understandable dependency set. Prefer readable undergraduate-level code over unnecessary frameworks.
Provide:

Deterministic preprocessing.
Directed overlap calculation.
Maximum-overlap greedy.
Exact subset DP with reconstruction.
A tiny exhaustive permutation oracle.
Output and trace validators.
Dataset generators.
Experiment CLI.
Analysis and plotting scripts.
Tests and documentation.
Greedy must select a globally maximum-overlap ordered pair of current strings at each merge. Tie policies must choose only among pairs attaining that maximum.
Implement at least:

A fully specified deterministic tie rule.
A second deterministic rule.
Uniform random selection among tied maximum pairs, using a local seeded RNG.
Specify stable identifiers or canonical ordering so hash iteration and process scheduling cannot change deterministic results.
Record each greedy merge:

The selected strings or stable IDs.
Overlap length.
Number of tied maximum pairs.
Resulting merged string.
Enough state information to replay and validate the choice.
Use traces for selected examples; avoid imposing unnecessary trace overhead on timing measurements.
Handle empty input, empty strings, singleton input, duplicates, contained strings, zero overlaps, unequal lengths, and extensive ties. Every final answer must contain every original input string.
5. Correctness gate
Do not run the main benchmark until:

Greedy and DP outputs pass containment checks.
Reconstructed lengths match reported lengths.
DP agrees with exhaustive permutation enumeration on many tiny instances.
Selected very small alphabet cases also receive direct candidate-superstring enumeration if feasible, to independently check the ordering formulation.
Overlap calculations agree with a simple reference routine.
Every recorded greedy choice attains the maximum available overlap.
Fixed seeds reproduce inputs and random tie choices.
Tests include input-order permutations and documented tie-policy behaviour.
Include these regression cases:

ATT, TTA, TAC: OPT = 5.
BAB, AABA, ABAA: greedy length = 8 and OPT = 7.
ABC, BCDE: OPT = 5.
Cases with no positive overlaps.
Cases where preprocessing removes most inputs.
Check the half-compression inequality on exact-solvable cases. A violation is a debugging or assumption-checking signal; passing finite tests is not a proof.
6. Experimental design
Use four input families:
A. Independent random strings
Vary alphabet size, string count, and length distribution.
B. Fragments sampled from a shared random source
Record the source and sampled positions. Control fragment lengths and sampling density. The source is a feasible upper bound, not an OPT certificate.
C. Repetitive inputs
Use documented generators based on repeated motifs, controlled perturbations, or fragments of repetitive sources. Make repetition strength configurable. Avoid generators that mostly collapse to one string after preprocessing.
D. Known and discovered counterexamples
Include verified examples and optionally search small instances for poor greedy ratios. Label discovered examples separately from unbiased benchmark samples.
Keep comparisons interpretable:

Use identical instances for all algorithms and tie policies.
Record both raw and retained counts and lengths.
Report preprocessing reduction rates.
Do not silently resample until a desired outcome occurs.
Keep independent instance seeds separate from tie-breaking seeds.
Use matched parameters where meaningful and discuss remaining differences.
Do not assume repetition must make greedy worse.
Start with a pilot, rather than an enormous Cartesian product. Candidate retained sizes are around 5, 8, 10, 12, and 15; expand only if measured costs permit.
Provide:

A tiny smoke configuration.
A manageable standard configuration.
An optional extended configuration.
Use configurable process-level timeouts and memory safeguards for exact DP. Record timeouts and failures explicitly. Never treat an incomplete exact run as OPT.
Run actual experiments within the available budget. If the extended study is too expensive, deliver completed smaller results plus an executable extended configuration.
7. Metrics and statistical handling
For instances with certified OPT, record:

G/OPT when OPT > 0.
G - OPT.
Whether greedy is optimal.
Greedy savings L - G.
Optimal savings L - OPT.
Compression ratio (L - G)/(L - OPT) when its denominator is positive.
Runtime and clearly defined timing boundaries.
Tie counts and variation across tie policies/seeds.
Define zero-denominator cases explicitly; do not silently assign ratios.
For larger instances without OPT:

Report runtime and feasible output lengths separately.
If using a proved lower bound B, label G/B as an upper bound on the unknown ratio G/OPT.
Do not describe G/source_length as an approximation ratio.
Report distributions and sample counts, not only means. Include medians, relevant quantiles, maximum observed ratios, and optimality rates.
Treat random tie runs on the same input as repeated measurements, not independent instances. If using confidence intervals, resample at the instance level.
Cache exact solutions across tie-policy runs. Do not time benchmarks while other agents or heavy parallel jobs are competing for the same CPU. Separate preprocessing, overlap calculation, solver time, and end-to-end time where practical.
8. Reproducibility and outputs
Save:

Generated input instances or a complete reproducible generation manifest.
Configuration, seeds, generator version, and content hashes.
Raw results in CSV or JSONL.
Algorithm version or commit identifier.
Python/package versions and machine information.
Explicit timeout/error statuses.
Selected greedy and optimal reconstruction traces.
Checkpoint long runs and support resuming without duplicate rows.
Generate report-ready plots, such as:

Greedy/OPT distributions by input family.
Optimality rate by retained input count.
Runtime versus retained input count.
Tie-breaking variation on identical instances.
Compression ratios where defined.
Save figures as PDF or SVG and PNG. Include units, sample counts, and readable legends.
Write an analysis grounded only in computed results. Explain several representative instances step by step. Separate observations, possible explanations, and proven statements.
9. Literature verification and optional extension
Verify all literature references independently using primary sources. Our earlier presentation mentioned Tarhio–Ukkonen, Kalugin–Nikolaev, Shibata, and Chukhin et al. Treat these as leads, not verified facts.
For each relevant source, record:

Exact title and authors.
URL/DOI and version/date.
Publication or preprint status.
The precise result and assumptions used.
Which claims or code components depend on it.
If a citation or claimed bound cannot be verified, say so and omit it from established conclusions. Do not invent missing references or proofs.
Only after the core study is complete, consider reproducing a verified Shibata construction. Implement the actual parameterized construction and required legal tie choices. Verify optimal lengths using exact DP for small cases or a clearly justified mathematical certificate for larger cases. A feasible constructed superstring alone is insufficient to certify OPT.
Implementing Chukhin’s or the OpenAI manuscript’s separate algorithms is outside the core scope.
10. Completion criteria
Deliver:

A working repository with installation and one-command reproduction instructions.
Passing tests and an independent correctness summary.
Completed smoke and feasible standard experiments.
Raw data, configurations, plots, and selected traces.
A concise methodology and findings document suitable for adaptation into our report.
Verified references and a list of unresolved claims.
A limitations section and an AI-assistance log we can use for our disclosure.
A short walkthrough explaining the code and results to undergraduate presenters.
Do not fabricate measurements, hide failed runs, cherry-pick favourable cases, or claim experimental evidence proves a universal bound.
Begin by inspecting the available materials, defining interfaces and file ownership, and launching the independent work. Continue through implementation, execution, validation, and interpretation. Ask questions only when a missing decision materially blocks progress; otherwise document reasonable assumptions and proceed.
6A. Real-world sequencing dataset extension
Add one real-world DNA sequencing dataset to complement the synthetic experiments, provided the core experiments are already working.
Dataset discovery and selection
Assign dataset discovery to Agent D and downloading/parsing to Agent B. They must agree on a dataset manifest before implementation.
Search reputable public sources such as NCBI SRA, ENA, or an established sequencing benchmark repository. Prefer:

Public microbial sequencing data with no access restrictions.
A small downloadable FASTA/FASTQ file or an officially supported bounded extraction.
Short reads, manageable file sizes, and clear provenance.
A dataset with an associated reference genome if available.
Find two or three candidates, then select one based on relevance, download size, ease of access, and reproducibility. Record:

Dataset name and organism.
Accession identifiers and source links.
Sequencing platform and read characteristics.
Download size, file format, and applicable usage terms.
Associated publication and reference assembly, if available.
Why this dataset was chosen.
Verify these details from the source. Do not invent accession identifiers or download URLs. Inspect metadata before downloading and use a configurable download budget. Do not download a large archive merely to extract a handful of reads.
If real reads cannot be obtained within the resource budget, use fragments sampled from a publicly available reference genome as a fallback. Clearly label these as simulated reads from a real reference sequence, not actual sequencing reads.
Scope and biological limitations
Frame the experiment as:
“Evaluating shortest-superstring algorithms on strings derived from biological sequencing data.”
Do not describe our implementation as a complete genome assembler.
Explain that actual sequencing introduces issues beyond our model:

Sequencing errors.
Reverse-complement orientation.
Repeated genomic regions.
Uneven coverage and missing regions.
Paired-end information.
Biological variation.
Our core algorithms use exact suffix–prefix overlaps. They do not automatically resolve these complications.
Extraction and preprocessing
Preserve downloaded data unchanged and implement a separate, reproducible extraction pipeline.
Support FASTA or FASTQ as appropriate. Record all filtering and transformation choices, including:

Read-length restrictions.
Quality filtering, if used.
Handling ambiguous bases such as N.
Duplicate and contained-read removal.
Treatment of paired-end reads.
Any trimming or cropping.
Use fixed seeds and save the exact selected strings and their original read identifiers.
For the simplest experiment, treat the supplied read sequences as fixed-orientation strings and state this limitation. Do not add every reverse complement as another mandatory input: that changes the optimization problem by requiring both orientations to occur.
If reference alignment is used to orient or select reads, document the aligner, parameters, mapping filters, and reference version. Label the resulting experiment as reference-assisted.
Two sampling conditions
Where feasible, compare:

Unconditioned sampling:
Select reads randomly from the eligible pool. This may produce little overlap and serves as a baseline.
Local-region sampling:
Select reads associated with a small genomic region so that meaningful overlap is more likely. Use verified mapping coordinates or a documented alignment procedure.
Do not select reads based on whether greedy performs poorly. Region selection and eligibility rules must be fixed independently of algorithm outcomes.
A local-region subset is deliberately enriched for related reads. Do not claim it represents the distribution of all sequencing reads.
If local-region selection would require disproportionate tooling or computation, keep the unconditioned sample and explain its limitations.
Experiments and interpretation
Use small subsets that the exact DP can solve, with multiple independently sampled subsets and recorded seeds. Choose subset sizes using the pilot runtime results.
Run the same algorithms, tie policies, validation checks, and metrics as in the synthetic experiments. Report:

Raw and retained input counts.
Read-length distributions.
Preprocessing reduction rates.
Fraction of ordered pairs with positive overlap.
Greedy/OPT ratios and optimality rates.
Runtime and tie sensitivity.
Keep biological results separate from synthetic results in tables and plots. Discuss whether observed differences could arise from read length, overlap density, repetition, errors, or preprocessing.
Do not assume the reference genome length is OPT. A reference may include regions absent from the sampled reads, and sequencing errors can mean the reference does not contain every observed read exactly.
The exact DP certifies OPT only for the actual strings supplied to it. Any cropped, filtered, or reoriented dataset defines a corresponding transformed problem.
Deliverables
Provide:

A verified dataset manifest and citation.
A bounded download/extraction command.
Checksums and a record of extraction parameters.
Saved experimental subsets with provenance.
Completed results and one concise comparison with the synthetic experiments.
A limitations paragraph explaining what the experiment says about shortest superstrings and what it does not establish about genome assembly.
Complete this extension after the core pipeline passes its correctness checks. If it cannot be completed, document the specific obstacle and provide a reproducible next step rather than presenting simulated data as real sequencing reads.
