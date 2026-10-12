# Output 5. Audit: under-reading per system, cue interaction, stable under-read components

> **SYNTHETIC PLACEHOLDER, NOT DATA.** Every number below was drawn by `src/analysis/synthetic_results.py` from a seeded random generator so that the table layout can be checked before any result exists. None of it may be quoted anywhere.

Figure: `figures/synthetic/F5a_audit_underreading.pdf`, `figures/synthetic/F5b_audit_components.pdf` (figures.py).

R/audit.R: score_z ~ intensity_c × hindi × cue + (1 | pair) per system (intensity = mean human rating, centred; cue 0 = none, 1 = 'the writer is in India'); the hindi coefficient is the under-reading at mean intensity without the cue, hindi:cue the cue interaction. Re-run on the agreed pairs (both raters within 1 point). Stable under-read components: lasso + stability selection of the error on the component profile.

## Under-reading and cue interaction

| System | Pairs | Term | Estimate [95% CI] | p | Pairs (n) | Status |
|---|---|---|---|---|---|---|
| xlm_emo | all | hindi | -0.530 [-0.815, -0.244] (synthetic) | 0.0003 (synthetic) | 150 | SYNTHETIC placeholder, not data |
| xlm_emo | agreed | hindi | -0.366 [-0.670, -0.061] (synthetic) | 0.0186 (synthetic) | 104 | SYNTHETIC placeholder, not data |
| muril_sent | all | hindi | -0.356 [-0.633, -0.080] (synthetic) | 0.0116 (synthetic) | 150 | SYNTHETIC placeholder, not data |
| muril_sent | agreed | hindi | -0.539 [-0.870, -0.208] (synthetic) | 0.0014 (synthetic) | 104 | SYNTHETIC placeholder, not data |
| commercial_llm_A | all | hindi | -0.308 [-0.549, -0.067] (synthetic) | 0.0121 (synthetic) | 150 | SYNTHETIC placeholder, not data |
| commercial_llm_A | all | hindi:cue | 0.106 [-0.127, 0.340] (synthetic) | 0.3725 (synthetic) | 150 | SYNTHETIC placeholder, not data |
| commercial_llm_A | agreed | hindi | -0.286 [-0.481, -0.092] (synthetic) | 0.0039 (synthetic) | 104 | SYNTHETIC placeholder, not data |
| commercial_llm_A | agreed | hindi:cue | 0.131 [-0.140, 0.402] (synthetic) | 0.3427 (synthetic) | 104 | SYNTHETIC placeholder, not data |

## Stable under-read components (Hindi)

| System | Component | Selection frequency | Coefficient (full data) | Stable |
|---|---|---|---|---|
| xlm_emo | FEEL_BAD | 0.05 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | NOT_HERE | 0.14 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | HAPPEN_TO | 0.18 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | THINK_OF | 0.02 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | WANT_BE_WITH | 0.06 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | WITH_OTHERS | 0.52 (synthetic) | -0.099 (synthetic) | False |
| xlm_emo | KIN | 0.08 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | ABOVE | 0.16 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | DUTY_DONE | 0.33 (synthetic) | 0.129 (synthetic) | False |
| xlm_emo | DUTY_UNDONE | 0.06 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | BODY | 0.14 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | BROKEN | 0.47 (synthetic) | 0.023 (synthetic) | False |
| xlm_emo | SUPPORT | 0.11 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | BLESSING | 0.01 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | AFTER_GOOD | 0.09 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | SPEAK_TO_DEAD | 0.01 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | LONG_TIME | 0.48 (synthetic) | -0.053 (synthetic) | False |
| xlm_emo | OTHERS_SAY | 0.37 (synthetic) | 0.037 (synthetic) | False |
| xlm_emo | DO_BECAUSE | 0.15 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | AVOID_DIE | 0.18 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | BOND | 0.16 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | RITUAL_WORDS | 0.01 (synthetic) | 0.000 (synthetic) | False |
| xlm_emo | HONOUR | 0.46 (synthetic) | 0.086 (synthetic) | False |
| xlm_emo | EVERYONE | 0.42 (synthetic) | 0.011 (synthetic) | False |
| muril_sent | FEEL_BAD | 0.06 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | NOT_HERE | 0.09 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | HAPPEN_TO | 0.36 (synthetic) | 0.029 (synthetic) | False |
| muril_sent | THINK_OF | 0.63 (synthetic) | 0.064 (synthetic) | False |
| muril_sent | WANT_BE_WITH | 0.02 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | WITH_OTHERS | 0.26 (synthetic) | 0.047 (synthetic) | False |
| muril_sent | KIN | 0.14 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | ABOVE | 0.00 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | DUTY_DONE | 0.07 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | DUTY_UNDONE | 0.13 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | BODY | 0.36 (synthetic) | -0.158 (synthetic) | False |
| muril_sent | BROKEN | 0.10 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | SUPPORT | 0.09 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | BLESSING | 0.00 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | AFTER_GOOD | 0.34 (synthetic) | 0.098 (synthetic) | False |
| muril_sent | SPEAK_TO_DEAD | 0.03 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | LONG_TIME | 0.45 (synthetic) | 0.103 (synthetic) | False |
| muril_sent | OTHERS_SAY | 0.08 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | DO_BECAUSE | 0.19 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | AVOID_DIE | 0.04 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | BOND | 0.16 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | RITUAL_WORDS | 0.14 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | HONOUR | 0.01 (synthetic) | 0.000 (synthetic) | False |
| muril_sent | EVERYONE | 0.02 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | FEEL_BAD | 0.16 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | NOT_HERE | 0.85 (synthetic) | 0.184 (synthetic) | False |
| commercial_llm_A | HAPPEN_TO | 0.50 (synthetic) | 0.160 (synthetic) | False |
| commercial_llm_A | THINK_OF | 0.28 (synthetic) | 0.027 (synthetic) | False |
| commercial_llm_A | WANT_BE_WITH | 0.18 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | WITH_OTHERS | 0.09 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | KIN | 0.01 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | ABOVE | 0.34 (synthetic) | -0.256 (synthetic) | False |
| commercial_llm_A | DUTY_DONE | 0.06 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | DUTY_UNDONE | 0.10 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | BODY | 0.17 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | BROKEN | 0.13 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | SUPPORT | 0.58 (synthetic) | -0.116 (synthetic) | False |
| commercial_llm_A | BLESSING | 0.12 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | AFTER_GOOD | 0.20 (synthetic) | 0.101 (synthetic) | False |
| commercial_llm_A | SPEAK_TO_DEAD | 0.18 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | LONG_TIME | 0.17 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | OTHERS_SAY | 0.17 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | DO_BECAUSE | 0.71 (synthetic) | -0.024 (synthetic) | True |
| commercial_llm_A | AVOID_DIE | 0.65 (synthetic) | -0.079 (synthetic) | True |
| commercial_llm_A | BOND | 0.74 (synthetic) | -0.031 (synthetic) | True |
| commercial_llm_A | RITUAL_WORDS | 0.50 (synthetic) | 0.036 (synthetic) | False |
| commercial_llm_A | HONOUR | 0.11 (synthetic) | 0.000 (synthetic) | False |
| commercial_llm_A | EVERYONE | 0.03 (synthetic) | 0.000 (synthetic) | False |
