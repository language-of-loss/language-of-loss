# Output 6. Chosen-dative rate against the forced baseline (P1)

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

predictions.py: chosen_dative / (chosen_dative + chosen_nominative) over Hindi experiencer sites, against forced_dative / (forced_dative + forced_nominative); exact binomial test only behind the agreement guard.

| Quantity | Language | Estimate [95% CI] | k / n | Texts | Test | p | Status |
|---|---|---|---|---|---|---|---|
| dative_choice_rate | hi | 0.291 [0.226, 0.346] | 92 / 316 | 75 | — | — | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); confirmatory; eligibility rules unreviewed (Hindi grammar_forced rule .740 < .80: provisional) |
| forced_baseline_dative_share | hi | 0.433 [0.328, 0.557] | 42 / 97 | 46 | — | — | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); confirmatory; eligibility rules unreviewed (Hindi grammar_forced rule .740 < .80: provisional) |
| binomial_test_vs_forced_baseline | hi | 0.291 | 92 / 316 | 75 | exact binomial, two-sided, H0: p = forced baseline (p0 = 0.4330, text clustering ignored by the binomial model) | 0.0000 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); confirmatory; eligibility rules unreviewed (Hindi grammar_forced rule .740 < .80: provisional) |
