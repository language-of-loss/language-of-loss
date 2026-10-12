# Output 8. NRC-Hindi against the native lexicon; the MuRIL classifier pair

> **SYNTHETIC PLACEHOLDER, NOT DATA.** Every number below was drawn by `src/analysis/synthetic_results.py` from a seeded random generator so that the table layout can be checked before any result exists. None of it may be quoted anywhere.

## 8a. Recall on native-only versus translatable items

| Native-only definition | Resource | Quantity | Estimate [95% CI] | Items | Status |
|---|---|---|---|---|---|
| strict | lexicon | recall_native_only | 0.777 [0.696, 0.845] (synthetic) | 120 | SYNTHETIC placeholder, not data |
| strict | lexicon | recall_translatable | 0.819 [0.757, 0.885] (synthetic) | 260 | SYNTHETIC placeholder, not data |
| strict | lexicon | gap_translatable_minus_native | 0.030 [-0.047, 0.134] (synthetic) | 380 | SYNTHETIC placeholder, not data |
| strict | nrc_hi | recall_native_only | 0.330 [0.274, 0.383] (synthetic) | 120 | SYNTHETIC placeholder, not data |
| strict | nrc_hi | recall_translatable | 0.609 [0.546, 0.681] (synthetic) | 260 | SYNTHETIC placeholder, not data |
| strict | nrc_hi | gap_translatable_minus_native | 0.310 [0.197, 0.377] (synthetic) | 380 | SYNTHETIC placeholder, not data |
| tolerated | lexicon | recall_native_only | 0.771 [0.695, 0.834] (synthetic) | 120 | SYNTHETIC placeholder, not data |
| tolerated | lexicon | recall_translatable | 0.823 [0.760, 0.897] (synthetic) | 260 | SYNTHETIC placeholder, not data |
| tolerated | lexicon | gap_translatable_minus_native | 0.030 [-0.046, 0.108] (synthetic) | 380 | SYNTHETIC placeholder, not data |
| tolerated | nrc_hi | recall_native_only | 0.306 [0.254, 0.369] (synthetic) | 120 | SYNTHETIC placeholder, not data |
| tolerated | nrc_hi | recall_translatable | 0.616 [0.534, 0.694] (synthetic) | 260 | SYNTHETIC placeholder, not data |
| tolerated | nrc_hi | gap_translatable_minus_native | 0.310 [0.223, 0.413] (synthetic) | 380 | SYNTHETIC placeholder, not data |

## 8b. MuRIL trained on translated data versus on native data (McNemar)

| Quantity | Value | Status |
|---|---|---|
| n_clauses | 400 | SYNTHETIC placeholder, not data |
| gold_positive | 170 | SYNTHETIC placeholder, not data |
| accuracy_translated | 0.71 | SYNTHETIC placeholder, not data |
| f1_translated | 0.62 | SYNTHETIC placeholder, not data |
| accuracy_native | 0.79 | SYNTHETIC placeholder, not data |
| f1_native | 0.73 | SYNTHETIC placeholder, not data |
| discordant_translated_right_native_wrong | 21 | SYNTHETIC placeholder, not data |
| discordant_native_right_translated_wrong | 53 | SYNTHETIC placeholder, not data |
| mcnemar_exact_p_two_sided | 0.0003 | SYNTHETIC placeholder, not data |
