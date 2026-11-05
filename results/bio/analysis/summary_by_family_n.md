# Greedy vs exact by family and n

Benchmark (and bio, labelled) instances only; `known`/`discovered` are in `summary_special`. Per instance one value: deterministic policy = its G; `random` = mean G over tie seeds (`opt_rate` = mean over instances of the per-instance fraction of optimal runs). CI = 95% percentile bootstrap over instances (blank if fewer than 5 instances). `comp_*` is (L-G)/(L-OPT), only where L-OPT>0; those with L-OPT=0 are counted in `n_no_compression`.

| policy | family | n | N | ratio_mean | ratio_median | ratio_q1 | ratio_q3 | ratio_p90 | ratio_p95 | ratio_max | gap_mean | gap_max | opt_rate | opt_ci_lo | opt_ci_hi | comp_N | comp_median | comp_min | n_no_compression |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lowest_id | bio_local (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lowest_id | bio_local (bio) | 8 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lowest_id | bio_local (bio) | 10 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lowest_id | bio_local (bio) | 12 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lowest_id | bio_local (bio) | 15 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lowest_id | bio_local (bio) | 18 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lowest_id | bio_unconditioned (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1 | 1.003 | 1.003 | 0.1 | 1 | 0.9 | 0.8 | 1 | 30 | 1 | 0.8333 | 0 |
| lowest_id | bio_unconditioned (bio) | 8 | 30 | 1 | 1 | 1 | 1 | 1 | 1.002 | 1.002 | 0.1 | 1 | 0.9 | 0.7667 | 1 | 30 | 1 | 0.9091 | 0 |
| lowest_id | bio_unconditioned (bio) | 10 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.002 | 1.003 | 0.3 | 2 | 0.7333 | 0.5667 | 0.8667 | 30 | 1 | 0.9333 | 0 |
| lowest_id | bio_unconditioned (bio) | 12 | 30 | 1 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 0.1667 | 1 | 0.8333 | 0.7 | 0.9667 | 30 | 1 | 0.9524 | 0 |
| lowest_id | bio_unconditioned (bio) | 15 | 30 | 1 | 1 | 1 | 1 | 1 | 1.001 | 1.001 | 0.1 | 1 | 0.9 | 0.7992 | 1 | 30 | 1 | 0.9808 | 0 |
| lowest_id | bio_unconditioned (bio) | 18 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.002 | 0.5 | 3 | 0.6 | 0.4333 | 0.7667 | 30 | 1 | 0.9741 | 0 |
| highest_id | bio_local (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| highest_id | bio_local (bio) | 8 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| highest_id | bio_local (bio) | 10 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| highest_id | bio_local (bio) | 12 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| highest_id | bio_local (bio) | 15 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| highest_id | bio_local (bio) | 18 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| highest_id | bio_unconditioned (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1 | 1.001 | 1.003 | 0.06667 | 1 | 0.9333 | 0.8333 | 1 | 30 | 1 | 0.8 | 0 |
| highest_id | bio_unconditioned (bio) | 8 | 30 | 1 | 1 | 1 | 1 | 1.002 | 1.002 | 1.003 | 0.2 | 2 | 0.8333 | 0.7 | 0.9667 | 30 | 1 | 0.8182 | 0 |
| highest_id | bio_unconditioned (bio) | 10 | 30 | 1 | 1 | 1 | 1.001 | 1.002 | 1.002 | 1.002 | 0.3 | 1 | 0.7 | 0.5333 | 0.8667 | 30 | 1 | 0.9545 | 0 |
| highest_id | bio_unconditioned (bio) | 12 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.003 | 0.3 | 2 | 0.7333 | 0.5667 | 0.9 | 30 | 1 | 0.9444 | 0 |
| highest_id | bio_unconditioned (bio) | 15 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.001 | 0.3 | 1 | 0.7 | 0.5333 | 0.8667 | 30 | 1 | 0.96 | 0 |
| highest_id | bio_unconditioned (bio) | 18 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.002 | 1.003 | 0.5333 | 4 | 0.6333 | 0.4658 | 0.8 | 30 | 1 | 0.9655 | 0 |
| lex_merged | bio_local (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lex_merged | bio_local (bio) | 8 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lex_merged | bio_local (bio) | 10 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lex_merged | bio_local (bio) | 12 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lex_merged | bio_local (bio) | 15 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lex_merged | bio_local (bio) | 18 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| lex_merged | bio_unconditioned (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1.003 | 1.003 | 1.003 | 0.1333 | 1 | 0.8667 | 0.7333 | 0.9667 | 30 | 1 | 0.8333 | 0 |
| lex_merged | bio_unconditioned (bio) | 8 | 30 | 1 | 1 | 1 | 1 | 1.002 | 1.002 | 1.002 | 0.2333 | 1 | 0.7667 | 0.6 | 0.9 | 30 | 1 | 0.875 | 0 |
| lex_merged | bio_unconditioned (bio) | 10 | 30 | 1 | 1 | 1 | 1 | 1.001 | 1.001 | 1.002 | 0.1667 | 1 | 0.8333 | 0.6667 | 0.9333 | 30 | 1 | 0.9231 | 0 |
| lex_merged | bio_unconditioned (bio) | 12 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.001 | 0.2667 | 1 | 0.7333 | 0.5667 | 0.9 | 30 | 1 | 0.9444 | 0 |
| lex_merged | bio_unconditioned (bio) | 15 | 30 | 1 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 0.2333 | 1 | 0.7667 | 0.6 | 0.9 | 30 | 1 | 0.9655 | 0 |
| lex_merged | bio_unconditioned (bio) | 18 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.002 | 0.4 | 3 | 0.7 | 0.5333 | 0.8667 | 30 | 1 | 0.9814 | 0 |
| random | bio_local (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| random | bio_local (bio) | 8 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| random | bio_local (bio) | 10 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| random | bio_local (bio) | 12 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| random | bio_local (bio) | 15 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| random | bio_local (bio) | 18 | 30 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 30 | 1 | 1 | 0 |
| random | bio_unconditioned (bio) | 5 | 30 | 1 | 1 | 1 | 1 | 1.001 | 1.002 | 1.002 | 0.11 | 0.9 | 0.89 | 0.8067 | 0.9633 | 30 | 1 | 0.85 | 0 |
| random | bio_unconditioned (bio) | 8 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.002 | 0.2067 | 1.3 | 0.8167 | 0.7267 | 0.9 | 30 | 0.9985 | 0.8818 | 0 |
| random | bio_unconditioned (bio) | 10 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.001 | 0.2533 | 0.9 | 0.76 | 0.6667 | 0.8533 | 30 | 0.9987 | 0.9444 | 0 |
| random | bio_unconditioned (bio) | 12 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.002 | 0.2933 | 1.5 | 0.75 | 0.62 | 0.87 | 30 | 1 | 0.9586 | 0 |
| random | bio_unconditioned (bio) | 15 | 30 | 1 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 0.2467 | 1 | 0.7633 | 0.6432 | 0.8667 | 30 | 0.9994 | 0.9793 | 0 |
| random | bio_unconditioned (bio) | 18 | 30 | 1 | 1 | 1 | 1.001 | 1.001 | 1.001 | 1.002 | 0.53 | 2.6 | 0.6667 | 0.5467 | 0.7833 | 30 | 0.9976 | 0.9776 | 0 |
