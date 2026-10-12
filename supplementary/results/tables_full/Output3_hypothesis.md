# Output 3. Hypothesis: Run 1 / Run 2 / Run 2b odds ratios and the decomposition

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

Figure: `figures/final/F3a_decomposition.pdf`, `figures/final/F3b_odds_ratios.pdf` (figures.py).

Draft v4 §3.6: relational ~ hindi + log(clauses) + loss_type + (1 | text) (R/h1_glmm.R; odds ratio for hindi, GLMM and CR2 cluster-robust GLM); decomposition r_L = f_L + q_L·p_L, Δ = forced + opportunity + choice, 95% intervals by bootstrap over texts (2,000). The choice share is the headline statistic.

## Odds ratios (hindi)

| Run | Estimator | Odds ratio [95% CI] | p | Clauses | Texts | Split |
|---|---|---|---|---|---|---|
| Run 1 (all finite clauses) | glmer (conditional, model-based SE) | 1.73 [1.41, 2.11] | 0.0000 | 35969 | 200 | confirmatory |
| Run 1 (all finite clauses) | glm + CR2 cluster-robust (marginal) | 1.64 [1.35, 2.00] | 0.0000 | 35969 | 200 | confirmatory |
| Run 1 (all finite clauses) | glmer + domain random intercept (conditional, model-based SE) | 1.73 [1.41, 2.11] | 0.0000 | 35969 | 200 | confirmatory |
| Run 1 (all finite clauses) | permutation over texts (glm coefficient, B = 999) | 1.64 | 0.0010 | 35969 | 200 | confirmatory |
| Run 2 (forced relational clauses removed) | glmer (conditional, model-based SE) | 1.41 [1.16, 1.71] | 0.0006 | 34038 | 200 | confirmatory |
| Run 2 (forced relational clauses removed) | glm + CR2 cluster-robust (marginal) | 1.32 [1.09, 1.61] | 0.0061 | 34038 | 200 | confirmatory |
| Run 2 (forced relational clauses removed) | glmer + domain random intercept (conditional, model-based SE) | 1.41 [1.16, 1.71] | 0.0006 | 34038 | 200 | confirmatory |
| Run 2 (forced relational clauses removed) | permutation over texts (glm coefficient, B = 999) | 1.32 | 0.0010 | 34038 | 200 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | glmer (conditional, model-based SE) | 1.39 [1.14, 1.69] | 0.0009 | 33902 | 200 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | glm + CR2 cluster-robust (marginal) | 1.30 [1.07, 1.58] | 0.0089 | 33902 | 200 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | glmer + domain random intercept (conditional, model-based SE) | 1.39 [1.14, 1.69] | 0.0009 | 33902 | 200 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | permutation over texts (glm coefficient, B = 999) | 1.30 | 0.0020 | 33902 | 200 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | glmer (conditional, model-based SE) | 1.40 [1.15, 1.70] | 0.0007 | 33902 | 200 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | glm + CR2 cluster-robust (marginal) | 1.32 [1.08, 1.60] | 0.0069 | 33902 | 200 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | glmer + domain random intercept (conditional, model-based SE) | 1.40 [1.15, 1.70] | 0.0007 | 33902 | 200 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | permutation over texts (glm coefficient, B = 999) | 1.32 | 0.0010 | 33902 | 200 | confirmatory |

## Decomposition (relational marker)

Source: `results/decompose_relational_dev.csv`; split dev, unit site, status machine-provisional, unreviewed.

| Symbol | Quantity | Language | Estimate [95% CI] | Finite clauses (denominator) | Texts |
|---|---|---|---|---|---|
| r_L | markers per 100 finite clauses | Hindi | 21.92 [18.47, 25.40] | 7752 | 36 |
| r_L | markers per 100 finite clauses | English | 12.57 [10.86, 14.21] | 6653 | 47 |
| f_L | forced markers per 100 clauses | Hindi | 8.31 [6.45, 9.95] | 7752 | 36 |
| f_L | forced markers per 100 clauses | English | 0.00 [0.00, 0.00] | 6653 | 47 |
| q_L | choice sites per 100 clauses | Hindi | 26.47 [23.19, 30.69] | 7752 | 36 |
| q_L | choice sites per 100 clauses | English | 41.44 [37.97, 45.11] | 6653 | 47 |
| p_L | share of choice sites taken relationally | Hindi | 0.51 [0.47, 0.55] | 7752 | 36 |
| p_L | share of choice sites taken relationally | English | 0.30 [0.26, 0.35] | 6653 | 47 |
| Δ | gap r_hi − r_en | Hindi − English | 9.35 [5.72, 13.19] | 7752 / 6653 | 36 / 47 |
| forced | (f_hi − f_en) | Hindi − English | 8.31 [6.45, 9.95] | 7752 / 6653 | 36 / 47 |
| opportunity | (q_hi − q_en)·p̄ | Hindi − English | -6.12 [-8.06, -3.89] | 7752 / 6653 | 36 / 47 |
| choice | q̄·(p_hi − p_en) | Hindi − English | 7.16 [4.85, 9.36] | 7752 / 6653 | 36 / 47 |

## Decomposition without the largest text (sensitivity)

| Variant | Term | Estimate [95% CI] |
|---|---|---|
| drop_largest_hi | delta | +9.77 [5.47, 14.05] |
| drop_largest_hi | forced_share | +8.32 [6.29, 10.22] |
| drop_largest_hi | opportunity_share | −5.61 [−7.63, −3.41] |
| drop_largest_hi | choice_share | +7.05 [4.74, 9.37] |
| drop_largest_en | delta | +9.01 [5.16, 13.04] |
| drop_largest_en | forced_share | +8.31 [6.45, 9.95] |
| drop_largest_en | opportunity_share | −6.26 [−8.22, −3.94] |
| drop_largest_en | choice_share | +6.97 [4.72, 9.28] |
| drop_largest_both | delta | +9.43 [5.09, 13.90] |
| drop_largest_both | forced_share | +8.32 [6.29, 10.22] |
| drop_largest_both | opportunity_share | −5.74 [−7.83, −3.54] |
| drop_largest_both | choice_share | +6.85 [4.54, 9.25] |
