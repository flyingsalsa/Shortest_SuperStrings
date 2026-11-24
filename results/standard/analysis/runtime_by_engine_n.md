# Exact DP runtime by engine and n

Per instance, t_solve_s is the median over `repeats_per_instance` timed repeats of the same input (1 = single timing). Across-instance median/min/max are over those per-instance values. `within_instance_cv_median` = median coefficient of variation (sd/mean) of the repeats: measurement noise, separate from instance-to-instance variation.

| engine | n | N_ok | t_solve_median_s | t_solve_min_s | t_solve_max_s | repeats_per_instance | within_instance_cv_median | N_not_ok |
|---|---|---|---|---|---|---|---|---|
| numpy | 1 | 1 | 3.3e-06 | 3.3e-06 | 3.3e-06 | 1 |  | 0 |
| numpy | 2 | 1 | 6.79e-05 | 6.79e-05 | 6.79e-05 | 1 |  | 0 |
| numpy | 3 | 15 | 9.54e-05 | 8.85e-05 | 0.0001546 | 1 |  | 0 |
| numpy | 4 | 1 | 0.0001994 | 0.0001994 | 0.0001994 | 1 |  | 0 |
| numpy | 5 | 705 | 0.0001814 | 0.0001636 | 0.0003955 | 1 |  | 0 |
| numpy | 8 | 705 | 0.000459 | 0.0004095 | 0.0007939 | 1 |  | 0 |
| numpy | 10 | 705 | 0.0008447 | 0.0007178 | 0.001341 | 1 |  | 0 |
| numpy | 12 | 705 | 0.001673 | 0.0015 | 0.002603 | 1 |  | 0 |
| numpy | 15 | 705 | 0.009512 | 0.00862 | 0.01611 | 1 |  | 0 |
| numpy | 18 | 705 | 0.1188 | 0.09661 | 0.1988 | 1 |  | 0 |
| numpy | 20 | 705 | 0.7032 | 0.4975 | 1.233 | 1 |  | 0 |
