# Output 8. NRC-Hindi against the native lexicon; the MuRIL classifier pair

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

## 8a. Recall on native-only versus translatable items

| Native-only definition | Resource | Quantity | Estimate [95% CI] | Items | Status |
|---|---|---|---|---|---|
| strict | lexicon | recall_native_only | 1.000 [1.000, 1.000] | 1 | gold run, unreviewed resources |
| strict | lexicon | recall_translatable | 1.000 [1.000, 1.000] | 21 | gold run, unreviewed resources |
| strict | lexicon | gap_translatable_minus_native | 0.000 [0.000, 0.000] | 22 | gold run, unreviewed resources |
| strict | nrc_hi | recall_native_only | 1.000 [1.000, 1.000] | 1 | gold run, unreviewed resources |
| strict | nrc_hi | recall_translatable | 0.857 [0.700, 1.000] | 21 | gold run, unreviewed resources |
| strict | nrc_hi | gap_translatable_minus_native | -0.143 [-0.300, 0.000] | 22 | gold run, unreviewed resources |
| strict | nrc_hi | gap_minus_lexicon_gap | -0.143 [-0.300, 0.000] | 22 | gold run, unreviewed resources |
| strict | wordnet | recall_native_only | 1.000 [1.000, 1.000] | 1 | gold run, unreviewed resources |
| strict | wordnet | recall_translatable | 0.714 [0.500, 0.905] | 21 | gold run, unreviewed resources |
| strict | wordnet | gap_translatable_minus_native | -0.286 [-0.500, -0.095] | 22 | gold run, unreviewed resources |
| strict | wordnet | gap_minus_lexicon_gap | -0.286 [-0.500, -0.095] | 22 | gold run, unreviewed resources |
| tolerated | lexicon | recall_native_only | 1.000 [1.000, 1.000] | 3 | gold run, unreviewed resources |
| tolerated | lexicon | recall_translatable | 1.000 [1.000, 1.000] | 19 | gold run, unreviewed resources |
| tolerated | lexicon | gap_translatable_minus_native | 0.000 [0.000, 0.000] | 22 | gold run, unreviewed resources |
| tolerated | nrc_hi | recall_native_only | 1.000 [1.000, 1.000] | 3 | gold run, unreviewed resources |
| tolerated | nrc_hi | recall_translatable | 0.842 [0.667, 1.000] | 19 | gold run, unreviewed resources |
| tolerated | nrc_hi | gap_translatable_minus_native | -0.158 [-0.333, 0.000] | 22 | gold run, unreviewed resources |
| tolerated | nrc_hi | gap_minus_lexicon_gap | -0.158 [-0.333, 0.000] | 22 | gold run, unreviewed resources |
| tolerated | wordnet | recall_native_only | 1.000 [1.000, 1.000] | 3 | gold run, unreviewed resources |
| tolerated | wordnet | recall_translatable | 0.684 [0.455, 0.889] | 19 | gold run, unreviewed resources |
| tolerated | wordnet | gap_translatable_minus_native | -0.316 [-0.545, -0.111] | 22 | gold run, unreviewed resources |
| tolerated | wordnet | gap_minus_lexicon_gap | -0.316 [-0.545, -0.111] | 22 | gold run, unreviewed resources |

## 8b. MuRIL trained on translated data versus on native data (McNemar)

| Quantity | Value | Status |
|---|---|---|
| n_clauses | 99 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| gold_positive | 52 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| accuracy_translated | 0.474747 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| f1_translated | 0.0 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| accuracy_native | 0.474747 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| f1_native | 0.0 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| discordant_translated_right_native_wrong | 0 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| discordant_native_right_translated_wrong | 0 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
| mcnemar_exact_p_two_sided | 1.0 | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold (investigators' decision 2026-10-11: not retrained) |
