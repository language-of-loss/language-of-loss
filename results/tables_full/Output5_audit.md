# Output 5. Audit: under-reading per system, cue interaction, stable under-read components

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

Figure: `figures/final/F5a_audit_underreading.pdf`, `figures/final/F5b_audit_components.pdf` (figures.py).

R/audit.R: score_z ~ intensity_c × hindi × cue + (1 | pair) per system (intensity = mean human rating, centred; cue 0 = none, 1 = 'the writer is in India'); the hindi coefficient is the under-reading at mean intensity without the cue, hindi:cue the cue interaction. Re-run on the agreed pairs (both raters within 1 point). Stable under-read components: lasso + stability selection of the error on the component profile.

## Under-reading and cue interaction

| System | Pairs | Term | Estimate [95% CI] | p | Pairs (n) | Status |
|---|---|---|---|---|---|---|
| xlm_emo | all | hindi | 0.291 [0.030, 0.552] | 0.0322 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| xlm_emo | agreed | hindi | 0.291 [0.030, 0.552] | 0.0322 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| muril_sent | all | hindi | 0.124 [-0.185, 0.433] | 0.4348 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| muril_sent | agreed | hindi | 0.124 [-0.185, 0.433] | 0.4348 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| ollama:llama3.1:8b-instruct-q4_K_M | all | hindi | 0.752 [0.563, 0.942] | 0.0000 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| ollama:llama3.1:8b-instruct-q4_K_M | all | hindi:cue | -0.163 [-0.431, 0.105] | 0.2351 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| ollama:llama3.1:8b-instruct-q4_K_M | agreed | hindi | 0.752 [0.563, 0.942] | 0.0000 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| ollama:llama3.1:8b-instruct-q4_K_M | agreed | hindi:cue | -0.163 [-0.431, 0.105] | 0.2351 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_A | all | hindi | 0.004 [-0.158, 0.167] | 0.9569 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_A | all | hindi:cue | -0.010 [-0.239, 0.220] | 0.9348 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_A | agreed | hindi | 0.004 [-0.158, 0.167] | 0.9569 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_A | agreed | hindi:cue | -0.010 [-0.239, 0.220] | 0.9348 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_B | all | hindi | -0.099 [-0.254, 0.055] | 0.2082 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_B | all | hindi:cue | -0.066 [-0.284, 0.152] | 0.5545 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_B | agreed | hindi | -0.099 [-0.254, 0.055] | 0.2082 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |
| commercial_llm_B | agreed | hindi:cue | -0.066 [-0.284, 0.152] | 0.5545 | 77 | machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels |

## Stable under-read components (Hindi)

| System | Component | Selection frequency | Coefficient (full data) | Stable |
|---|---|---|---|---|
| commercial_llm_A | DUTY_UNDONE | 0.47 | 0.000 | FALSE |
| commercial_llm_A | WANT_BE_WITH | 0.43 | 0.000 | FALSE |
| commercial_llm_A | WITH_OTHERS | 0.31 | 0.000 | FALSE |
| commercial_llm_A | DO_BECAUSE | 0.27 | 0.000 | FALSE |
| commercial_llm_A | FEEL_BAD | 0.12 | 0.000 | FALSE |
| commercial_llm_A | KIN | 0.08 | 0.000 | FALSE |
| commercial_llm_A | SPEAK_TO_DEAD | 0.08 | 0.000 | FALSE |
| commercial_llm_A | NOT_HERE | 0.03 | 0.000 | FALSE |
| commercial_llm_A | ABOVE | 0.03 | 0.000 | FALSE |
| commercial_llm_A | RITUAL_WORDS | 0.03 | 0.000 | FALSE |
| commercial_llm_A | DUTY_DONE | 0.02 | 0.000 | FALSE |
| commercial_llm_A | AFTER_GOOD | 0.02 | 0.000 | FALSE |
| commercial_llm_A | BODY | 0.01 | 0.000 | FALSE |
| commercial_llm_A | OTHERS_SAY | 0.01 | 0.000 | FALSE |
| commercial_llm_A | AVOID_DIE | 0.01 | 0.000 | FALSE |
| commercial_llm_A | HAPPEN_TO | 0.00 | 0.000 | FALSE |
| commercial_llm_A | THINK_OF | 0.00 | 0.000 | FALSE |
| commercial_llm_A | BROKEN | 0.00 | 0.000 | FALSE |
| commercial_llm_A | SUPPORT | 0.00 | 0.000 | FALSE |
| commercial_llm_A | BLESSING | 0.00 | 0.000 | FALSE |
| commercial_llm_A | LONG_TIME | 0.00 | 0.000 | FALSE |
| commercial_llm_A | BOND | 0.00 | 0.000 | FALSE |
| commercial_llm_A | HONOUR | 0.00 | 0.000 | FALSE |
| commercial_llm_B | FEEL_BAD | 0.41 | 0.000 | FALSE |
| commercial_llm_B | BODY | 0.16 | 0.000 | FALSE |
| commercial_llm_B | WANT_BE_WITH | 0.13 | 0.000 | FALSE |
| commercial_llm_B | KIN | 0.09 | 0.000 | FALSE |
| commercial_llm_B | WITH_OTHERS | 0.08 | 0.000 | FALSE |
| commercial_llm_B | HAPPEN_TO | 0.07 | 0.000 | FALSE |
| commercial_llm_B | DO_BECAUSE | 0.06 | 0.000 | FALSE |
| commercial_llm_B | AVOID_DIE | 0.06 | 0.000 | FALSE |
| commercial_llm_B | NOT_HERE | 0.05 | 0.000 | FALSE |
| commercial_llm_B | ABOVE | 0.05 | 0.000 | FALSE |
| commercial_llm_B | BLESSING | 0.05 | 0.000 | FALSE |
| commercial_llm_B | DUTY_DONE | 0.04 | 0.000 | FALSE |
| commercial_llm_B | OTHERS_SAY | 0.04 | 0.000 | FALSE |
| commercial_llm_B | BOND | 0.03 | 0.000 | FALSE |
| commercial_llm_B | THINK_OF | 0.02 | 0.000 | FALSE |
| commercial_llm_B | AFTER_GOOD | 0.02 | 0.000 | FALSE |
| commercial_llm_B | RITUAL_WORDS | 0.02 | 0.000 | FALSE |
| commercial_llm_B | DUTY_UNDONE | 0.01 | 0.000 | FALSE |
| commercial_llm_B | SPEAK_TO_DEAD | 0.01 | 0.000 | FALSE |
| commercial_llm_B | BROKEN | 0.00 | 0.000 | FALSE |
| commercial_llm_B | SUPPORT | 0.00 | 0.000 | FALSE |
| commercial_llm_B | LONG_TIME | 0.00 | 0.000 | FALSE |
| commercial_llm_B | HONOUR | 0.00 | 0.000 | FALSE |
| muril_sent | HONOUR | 0.38 | 0.000 | FALSE |
| muril_sent | THINK_OF | 0.37 | 0.000 | FALSE |
| muril_sent | NOT_HERE | 0.21 | 0.000 | FALSE |
| muril_sent | WANT_BE_WITH | 0.18 | 0.000 | FALSE |
| muril_sent | BOND | 0.10 | 0.000 | FALSE |
| muril_sent | FEEL_BAD | 0.09 | 0.000 | FALSE |
| muril_sent | DO_BECAUSE | 0.07 | 0.000 | FALSE |
| muril_sent | AFTER_GOOD | 0.03 | 0.000 | FALSE |
| muril_sent | BODY | 0.01 | 0.000 | FALSE |
| muril_sent | AVOID_DIE | 0.01 | 0.000 | FALSE |
| muril_sent | HAPPEN_TO | 0.00 | 0.000 | FALSE |
| muril_sent | WITH_OTHERS | 0.00 | 0.000 | FALSE |
| muril_sent | KIN | 0.00 | 0.000 | FALSE |
| muril_sent | ABOVE | 0.00 | 0.000 | FALSE |
| muril_sent | DUTY_DONE | 0.00 | 0.000 | FALSE |
| muril_sent | DUTY_UNDONE | 0.00 | 0.000 | FALSE |
| muril_sent | BROKEN | 0.00 | 0.000 | FALSE |
| muril_sent | SUPPORT | 0.00 | 0.000 | FALSE |
| muril_sent | BLESSING | 0.00 | 0.000 | FALSE |
| muril_sent | SPEAK_TO_DEAD | 0.00 | 0.000 | FALSE |
| muril_sent | LONG_TIME | 0.00 | 0.000 | FALSE |
| muril_sent | OTHERS_SAY | 0.00 | 0.000 | FALSE |
| muril_sent | RITUAL_WORDS | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | FEEL_BAD | 0.64 | -1.051 | TRUE |
| ollama:llama3.1:8b-instruct-q4_K_M | WANT_BE_WITH | 0.41 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | BODY | 0.05 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | THINK_OF | 0.02 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | NOT_HERE | 0.01 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | DUTY_DONE | 0.01 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | AFTER_GOOD | 0.01 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | DO_BECAUSE | 0.01 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | HAPPEN_TO | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | WITH_OTHERS | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | KIN | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | ABOVE | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | DUTY_UNDONE | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | BROKEN | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | SUPPORT | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | BLESSING | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | SPEAK_TO_DEAD | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | LONG_TIME | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | OTHERS_SAY | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | AVOID_DIE | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | BOND | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | RITUAL_WORDS | 0.00 | 0.000 | FALSE |
| ollama:llama3.1:8b-instruct-q4_K_M | HONOUR | 0.00 | 0.000 | FALSE |
| xlm_emo | HONOUR | 0.65 | -3.032 | TRUE |
| xlm_emo | THINK_OF | 0.10 | 0.000 | FALSE |
| xlm_emo | RITUAL_WORDS | 0.05 | 0.000 | FALSE |
| xlm_emo | FEEL_BAD | 0.00 | 0.000 | FALSE |
| xlm_emo | NOT_HERE | 0.00 | 0.000 | FALSE |
| xlm_emo | HAPPEN_TO | 0.00 | 0.000 | FALSE |
| xlm_emo | WANT_BE_WITH | 0.00 | 0.000 | FALSE |
| xlm_emo | WITH_OTHERS | 0.00 | 0.000 | FALSE |
| xlm_emo | KIN | 0.00 | 0.000 | FALSE |
| xlm_emo | ABOVE | 0.00 | 0.000 | FALSE |
| xlm_emo | DUTY_DONE | 0.00 | 0.000 | FALSE |
| xlm_emo | DUTY_UNDONE | 0.00 | 0.000 | FALSE |
| xlm_emo | BODY | 0.00 | 0.000 | FALSE |
| xlm_emo | BROKEN | 0.00 | 0.000 | FALSE |
| xlm_emo | SUPPORT | 0.00 | 0.000 | FALSE |
| xlm_emo | BLESSING | 0.00 | 0.000 | FALSE |
| xlm_emo | AFTER_GOOD | 0.00 | 0.000 | FALSE |
| xlm_emo | SPEAK_TO_DEAD | 0.00 | 0.000 | FALSE |
| xlm_emo | LONG_TIME | 0.00 | 0.000 | FALSE |
| xlm_emo | OTHERS_SAY | 0.00 | 0.000 | FALSE |
| xlm_emo | DO_BECAUSE | 0.00 | 0.000 | FALSE |
| xlm_emo | AVOID_DIE | 0.00 | 0.000 | FALSE |
| xlm_emo | BOND | 0.00 | 0.000 | FALSE |
