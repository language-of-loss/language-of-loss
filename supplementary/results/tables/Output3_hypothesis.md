# Output 3. Hypothesis: Run 1 / Run 2 / Run 2b odds ratios and the decomposition

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

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

Source: `results/decompose_relational_confirmatory.csv`; split confirmatory, unit site, status machine-provisional, unreviewed.

| Symbol | Quantity | Language | Estimate [95% CI] | Finite clauses (denominator) | Texts |
|---|---|---|---|---|---|
| r_L | markers per 100 finite clauses | Hindi | 23.94 [21.60, 26.27] | 23371 | 110 |
| r_L | markers per 100 finite clauses | English | 11.10 [9.94, 12.37] | 12598 | 90 |
| f_L | forced markers per 100 clauses | Hindi | 8.26 [7.03, 9.45] | 23371 | 110 |
| f_L | forced markers per 100 clauses | English | 0.00 [0.00, 0.00] | 12598 | 90 |
| q_L | choice sites per 100 clauses | Hindi | 29.24 [27.01, 31.36] | 23371 | 110 |
| q_L | choice sites per 100 clauses | English | 38.21 [35.69, 41.05] | 12598 | 90 |
| p_L | share of choice sites taken relationally | Hindi | 0.54 [0.51, 0.57] | 23371 | 110 |
| p_L | share of choice sites taken relationally | English | 0.29 [0.26, 0.32] | 12598 | 90 |
| Δ | gap r_hi − r_en | Hindi − English | 12.84 [10.28, 15.43] | 23371 / 12598 | 110 / 90 |
| forced | (f_hi − f_en) | Hindi − English | 8.26 [7.03, 9.45] | 23371 / 12598 | 110 / 90 |
| opportunity | (q_hi − q_en)·p̄ | Hindi − English | -3.71 [-5.19, -2.29] | 23371 / 12598 | 110 / 90 |
| choice | q̄·(p_hi − p_en) | Hindi − English | 8.28 [6.67, 9.97] | 23371 / 12598 | 110 / 90 |
