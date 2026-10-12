# Output 3. Hypothesis: Run 1 / Run 2 / Run 2b odds ratios and the decomposition

> **SYNTHETIC PLACEHOLDER, NOT DATA.** Every number below was drawn by `src/analysis/synthetic_results.py` from a seeded random generator so that the table layout can be checked before any result exists. None of it may be quoted anywhere.

Figure: `figures/synthetic/F3a_decomposition.pdf`, `figures/synthetic/F3b_odds_ratios.pdf` (figures.py).

Draft v4 §3.6: relational ~ hindi + log(clauses) + loss_type + (1 | text) (R/h1_glmm.R; odds ratio for hindi, GLMM and CR2 cluster-robust GLM); decomposition r_L = f_L + q_L·p_L, Δ = forced + opportunity + choice, 95% intervals by bootstrap over texts (2,000). The choice share is the headline statistic.

## Odds ratios (hindi)

| Run | Estimator | Odds ratio [95% CI] | p | Clauses | Texts | Split |
|---|---|---|---|---|---|---|
| Run 1 (all finite clauses) | glmer (conditional, model-based SE) | 1.55 [1.21, 2.00] (synthetic) | 0.0005 (synthetic) | 6400 | 190 | confirmatory |
| Run 1 (all finite clauses) | glm + CR2 cluster-robust (marginal) | 1.67 [1.12, 2.49] (synthetic) | 0.0096 (synthetic) | 6400 | 190 | confirmatory |
| Run 2 (forced relational clauses removed) | glmer (conditional, model-based SE) | 1.47 [1.22, 1.78] (synthetic) | 0.0001 (synthetic) | 6150 | 190 | confirmatory |
| Run 2 (forced relational clauses removed) | glm + CR2 cluster-robust (marginal) | 1.52 [1.02, 2.25] (synthetic) | 0.0349 (synthetic) | 6150 | 190 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | glmer (conditional, model-based SE) | 1.23 [0.84, 1.80] (synthetic) | 0.2951 (synthetic) | 5900 | 190 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | glm + CR2 cluster-robust (marginal) | 1.37 [1.10, 1.71] (synthetic) | 0.0043 (synthetic) | 5900 | 190 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | glmer (conditional, model-based SE) | 1.55 [1.13, 2.11] (synthetic) | 0.0063 (synthetic) | 6020 | 190 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | glm + CR2 cluster-robust (marginal) | 1.64 [1.39, 1.94] (synthetic) | 0.0000 (synthetic) | 6020 | 190 | confirmatory |

## Decomposition (relational marker)

Source: `results/decompose_relational_dev.csv`; split dev, unit site, status SYNTHETIC placeholder, not data.

| Symbol | Quantity | Language | Estimate [95% CI] | Finite clauses (denominator) | Texts |
|---|---|---|---|---|---|
| r_L | markers per 100 finite clauses | Hindi | 20.00 [14.83, 24.83] (synthetic) | 3100 | 15 |
| r_L | markers per 100 finite clauses | English | 12.50 [9.52, 17.21] (synthetic) | 3300 | 23 |
| f_L | forced markers per 100 clauses | Hindi | 7.50 [5.49, 9.41] (synthetic) | 3100 | 15 |
| f_L | forced markers per 100 clauses | English | 0.40 [-1.77, 3.45] (synthetic) | 3300 | 23 |
| q_L | choice sites per 100 clauses | Hindi | 27.00 [20.03, 33.50] (synthetic) | 3100 | 15 |
| q_L | choice sites per 100 clauses | English | 40.00 [32.99, 47.72] (synthetic) | 3300 | 23 |
| p_L | share of choice sites taken relationally | Hindi | 0.46 [0.38, 0.51] (synthetic) | 3100 | 15 |
| p_L | share of choice sites taken relationally | English | 0.30 [0.25, 0.36] (synthetic) | 3300 | 23 |
| Δ | gap r_hi − r_en | Hindi − English | 7.52 [1.69, 14.37] (synthetic) | 3100 / 3300 | 15 / 23 |
| forced | (f_hi − f_en) | Hindi − English | 7.10 [4.71, 9.84] (synthetic) | 3100 / 3300 | 15 / 23 |
| opportunity | (q_hi − q_en)·p̄ | Hindi − English | -4.94 [-8.62, -1.41] (synthetic) | 3100 / 3300 | 15 / 23 |
| choice | q̄·(p_hi − p_en) | Hindi − English | 5.36 [1.36, 8.94] (synthetic) | 3100 / 3300 | 15 / 23 |

## Decomposition without the largest text (sensitivity)

| Variant | Term | Estimate [95% CI] |
|---|---|---|
| drop_largest_hi | delta | +7.45 [1.62, 14.30] (synthetic) |
| drop_largest_hi | forced_share | +6.56 [4.17, 9.30] (synthetic) |
| drop_largest_hi | opportunity_share | −4.51 [−8.19, −0.98] (synthetic) |
| drop_largest_hi | choice_share | +5.94 [1.94, 9.52] (synthetic) |
| drop_largest_en | delta | +8.59 [2.76, 15.44] (synthetic) |
| drop_largest_en | forced_share | +6.58 [4.19, 9.32] (synthetic) |
| drop_largest_en | opportunity_share | −4.65 [−8.33, −1.12] (synthetic) |
| drop_largest_en | choice_share | +5.51 [1.50, 9.09] (synthetic) |
| drop_largest_both | delta | +7.69 [1.86, 14.54] (synthetic) |
| drop_largest_both | forced_share | +7.91 [5.52, 10.65] (synthetic) |
| drop_largest_both | opportunity_share | −4.98 [−8.66, −1.45] (synthetic) |
| drop_largest_both | choice_share | +4.85 [0.85, 8.43] (synthetic) |
