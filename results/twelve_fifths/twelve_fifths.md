# Adapted 12/5 construction (report Section 4.4) - computational check

n = 2..100: substring-free True, |H_n| = claim True, H_n contains all inputs True, G_n = claim True, overlaps alpha/beta/gamma/0 as claimed True.  
Full legality replay (every prescribed pair is a current maximum) for n = 2..20: True.

| n | strings | OPT (exact DP) | \|H_n\| | scripted G_n | G_n/\|H_n\| | G_n/OPT | lowest_id | highest_id | lex_merged | random min-max (50) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 5 | 83 | 83 | 109 | 1.313 | 1.313 | 83 | 83 | 83 | 83-109 |
| 3 | 10 | 236 | 236 | 393 | 1.665 | 1.665 | 236 | 289 | 236 | 236-381 |
| 4 | 15 | 503 | 503 | 924 | 1.837 | 1.837 | 503 | 668 | 503 | 504-805 |
| 5 | 20 | 914 | 914 | 1774 | 1.941 | 1.941 | 914 | 1268 | 914 | 914-1506 |
| 6 | 25 |  | 1499 | 3015 | 2.011 |  |  |  |  |  |
| 7 | 30 |  | 2288 | 4719 | 2.062 |  |  |  |  |  |
| 8 | 35 |  | 3311 | 6958 | 2.101 |  |  |  |  |  |
| 9 | 40 |  | 4598 | 9804 | 2.132 |  |  |  |  |  |
| 10 | 45 |  | 6179 | 13329 | 2.157 |  |  |  |  |  |
| 15 | 70 |  | 19544 | 43659 | 2.234 |  |  |  |  |  |
| 20 | 95 |  | 44759 | 101764 | 2.274 |  |  |  |  |  |
| 30 | 145 |  | 145739 | 337299 | 2.314 |  |  |  |  |  |
| 50 | 245 |  | 654899 | 1537669 | 2.348 |  |  |  |  |  |
| 100 | 495 |  | 5119799 | 12152844 | 2.374 |  |  |  |  |  |
