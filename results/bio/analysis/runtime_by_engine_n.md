# Exact DP runtime by engine and n

Per instance, t_solve_s is the median over `repeats_per_instance` timed repeats of the same input (1 = single timing). Across-instance median/min/max are over those per-instance values. `within_instance_cv_median` = median coefficient of variation (sd/mean) of the repeats: measurement noise, separate from instance-to-instance variation.

| engine | n | N_ok | t_solve_median_s | t_solve_min_s | t_solve_max_s | repeats_per_instance | within_instance_cv_median | N_not_ok |
|---|---|---|---|---|---|---|---|---|
| numpy | 5 | 60 | 0.0001746 | 0.0001281 | 0.0003018 | 1 |  | 0 |
| numpy | 8 | 60 | 0.0004193 | 0.0003661 | 0.0005915 | 1 |  | 0 |
| numpy | 10 | 60 | 0.0007356 | 0.0006793 | 0.0009352 | 1 |  | 0 |
| numpy | 12 | 60 | 0.001524 | 0.001428 | 0.001835 | 1 |  | 0 |
| numpy | 15 | 60 | 0.008637 | 0.008376 | 0.009604 | 1 |  | 0 |
| numpy | 18 | 60 | 0.1062 | 0.09791 | 0.1279 | 1 |  | 0 |
