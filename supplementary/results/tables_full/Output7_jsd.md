# Output 7. Component-profile divergence (Jensen–Shannon, base 2)

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

Figure: `figures/final/F7_component_profile.pdf` (figures.py).

| Quantity | Estimate [95% CI] | Components | Texts hi / en | Note | Status |
|---|---|---|---|---|---|
| jsd_component_profiles_base2 | 0.122 [0.104, 0.146] | 24 | 110 / 90 | plug-in JSD, biased upward in small samples; CI = text bootstrap of the plug-in value | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication); confirmatory; eligibility rules unreviewed (Hindi grammar_forced rule .740 < .80: provisional) |

## Component profile and log-odds (positive δ = more Hindi; interval δ ± 1.96 sd)

| Component | Share hi | Share en | Clauses hi / en | δ [95%] | z |
|---|---|---|---|---|---|
| KIN | 0.420 | 0.155 | 890 / 385 | +1.11 [1.01, 1.22] | 20.71 |
| WITH_OTHERS | 0.118 | 0.036 | 251 / 90 | +1.02 [0.81, 1.23] | 9.60 |
| SPEAK_TO_DEAD | 0.004 | 0.003 | 8 / 8 | +0.13 [−0.76, 1.02] | 0.29 |
| THINK_OF | 0.054 | 0.051 | 115 / 126 | +0.06 [−0.17, 0.29] | 0.50 |
| BROKEN | 0.006 | 0.006 | 13 / 15 | +0.01 [−0.66, 0.69] | 0.04 |
| WANT_BE_WITH | 0.009 | 0.010 | 20 / 26 | −0.09 [−0.61, 0.44] | -0.32 |
| HONOUR | 0.006 | 0.007 | 13 / 18 | −0.14 [−0.78, 0.51] | -0.42 |
| DUTY_DONE | 0.008 | 0.009 | 16 / 23 | −0.17 [−0.74, 0.41] | -0.57 |
| BODY | 0.035 | 0.045 | 75 / 111 | −0.20 [−0.46, 0.07] | -1.47 |
| BLESSING | 0.003 | 0.004 | 7 / 11 | −0.24 [−1.09, 0.61] | -0.55 |
| DO_BECAUSE | 0.023 | 0.035 | 49 / 86 | −0.34 [−0.65, −0.02] | -2.11 |
| NOT_HERE | 0.118 | 0.168 | 249 / 417 | −0.34 [−0.48, −0.20] | -4.71 |
| AVOID_DIE | 0.026 | 0.040 | 56 / 99 | −0.34 [−0.64, −0.05] | -2.31 |
| ABOVE | 0.009 | 0.015 | 20 / 37 | −0.37 [−0.86, 0.11] | -1.51 |
| DUTY_UNDONE | 0.004 | 0.007 | 8 / 18 | −0.53 [−1.26, 0.21] | -1.41 |
| HAPPEN_TO | 0.040 | 0.075 | 84 / 186 | −0.54 [−0.77, −0.31] | -4.67 |
| RITUAL_WORDS | 0.006 | 0.013 | 13 / 32 | −0.60 [−1.16, −0.03] | -2.08 |
| FEEL_BAD | 0.054 | 0.129 | 115 / 321 | −0.76 [−0.94, −0.57] | -8.03 |
| BOND | 0.031 | 0.081 | 66 / 200 | −0.79 [−1.03, −0.55] | -6.49 |
| AFTER_GOOD | 0.016 | 0.042 | 33 / 104 | −0.80 [−1.14, −0.47] | -4.68 |
| OTHERS_SAY | 0.004 | 0.012 | 9 / 31 | −0.85 [−1.48, −0.22] | -2.65 |
| SUPPORT | 0.001 | 0.006 | 3 / 16 | −1.15 [−2.13, −0.16] | -2.28 |
| LONG_TIME | 0.003 | 0.050 | 6 / 123 | −1.83 [−2.30, −1.36] | -7.66 |
| EVERYONE | 0.000 | 0.000 | 0 / 1 | −2.19 [−8.42, 4.04] | -0.69 |
