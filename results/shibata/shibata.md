# Shibata S_{k,t} reproduction

Scripted G = the paper's legal tie choices, replayed and checked step by step. OPT certified by counting lower bound + explicit Eulerian superstring (and exact DP for n = 22). Policy columns: our own tie rules on the same input (blank = n > 200, not run).

| k | t | n | OPT (certified) | OPT exact DP | scripted G | G/OPT | limit (9k+2)/(4k+4) | legal | compression | lowest_id | highest_id | lex_merged | random min-max (50 seeds) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 | 1 | 22 | 31 | 31 | 47 | 1.516 | 2.091 | True | 0.915 | 38 | 42 | 43 | 31-44 |
| 10 | 2 | 44 | 53 |  | 93 | 1.755 | 2.091 | True | 0.897 | 75 | 84 | 86 | 53-79 |
| 10 | 4 | 88 | 97 |  | 185 | 1.907 | 2.091 | True | 0.888 | 149 | 168 | 172 | 110-154 |
| 10 | 8 | 176 | 185 |  | 369 | 1.995 | 2.091 | True | 0.883 | 297 | 336 | 344 | 207-273 |
| 10 | 9 | 198 | 207 |  | 415 | 2.005 | 2.091 | True | 0.883 | 334 | 378 | 387 | 245-322 |
| 10 | 12 | 264 | 273 |  | 553 | 2.026 | 2.091 | True | 0.882 |  |  |  |  |
| 10 | 16 | 352 | 361 |  | 737 | 2.042 | 2.091 | True | 0.881 |  |  |  |  |
| 12 | 1 | 26 | 37 |  | 56 | 1.514 | 2.115 | True | 0.931 | 38 | 51 | 51 | 37-53 |
| 12 | 8 | 208 | 219 |  | 441 | 2.014 | 2.115 | True | 0.903 |  |  |  |  |
| 12 | 16 | 416 | 427 |  | 881 | 2.063 | 2.115 | True | 0.901 |  |  |  |  |
| 16 | 1 | 34 | 49 |  | 74 | 1.510 | 2.147 | True | 0.949 | 57 | 67 | 67 | 49-70 |
| 16 | 8 | 272 | 287 |  | 585 | 2.038 | 2.147 | True | 0.927 |  |  |  |  |
| 16 | 16 | 544 | 559 |  | 1169 | 2.091 | 2.147 | True | 0.925 |  |  |  |  |
| 20 | 1 | 42 | 61 |  | 92 | 1.508 | 2.167 | True | 0.960 | 71 | 83 | 83 | 61-86 |
| 20 | 16 | 672 | 691 |  | 1457 | 2.109 | 2.167 | True | 0.940 |  |  |  |  |
