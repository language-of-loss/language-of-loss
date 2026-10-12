# Output 4. Second-language rival: not estimable from text-internal evidence; rival check

> **SYNTHETIC PLACEHOLDER, NOT DATA.** Every number below was drawn by `src/analysis/synthetic_results.py` from a seeded random generator so that the table layout can be checked before any result exists. None of it may be quoted anywhere.

Figure: `figures/synthetic/F3b_odds_ratios.pdf` (figures.py).

Registered as not estimable from text-internal evidence (decision 2026-10-10): no text states the writer's home language, so English-dominant writers cannot be identified from the texts. Rival check instead: Runs 1, 2, 2b and R-F6 with diaspora and platform added as covariates. Limitation: the second-language detachment account is not tested directly.

## Odds ratios (hindi), with diaspora + platform covariates

| Run | Estimator | Odds ratio [95% CI] | p | Clauses | Texts | Split |
|---|---|---|---|---|---|---|
| Run 1 (all finite clauses) | glmer (conditional, model-based SE) | 1.59 [1.18, 2.14] (synthetic) | 0.0022 (synthetic) | 6400 | 190 | confirmatory |
| Run 1 (all finite clauses) | glm + CR2 cluster-robust (marginal) | 1.49 [0.93, 2.41] (synthetic) | 0.0939 (synthetic) | 6400 | 190 | confirmatory |
| Run 2 (forced relational clauses removed) | glmer (conditional, model-based SE) | 1.32 [1.04, 1.68] (synthetic) | 0.0220 (synthetic) | 6150 | 190 | confirmatory |
| Run 2 (forced relational clauses removed) | glm + CR2 cluster-robust (marginal) | 1.42 [1.08, 1.87] (synthetic) | 0.0108 (synthetic) | 6150 | 190 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | glmer (conditional, model-based SE) | 1.33 [1.07, 1.64] (synthetic) | 0.0090 (synthetic) | 5900 | 190 | confirmatory |
| Run 2b (Run 2 with honorific reference to elders also treated as forced) | glm + CR2 cluster-robust (marginal) | 1.39 [1.01, 1.90] (synthetic) | 0.0365 (synthetic) | 5900 | 190 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | glmer (conditional, model-based SE) | 1.38 [0.99, 1.94] (synthetic) | 0.0592 (synthetic) | 6020 | 190 | confirmatory |
| R-F6 robustness (Run 2 and closing-formula clauses removed) | glm + CR2 cluster-robust (marginal) | 1.28 [0.92, 1.79] (synthetic) | 0.1359 (synthetic) | 6020 | 190 | confirmatory |
