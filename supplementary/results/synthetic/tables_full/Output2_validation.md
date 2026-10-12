# Output 2. Dictionary channel: precision and recall per category per language; Rogan–Gladen corrected rates

> **SYNTHETIC PLACEHOLDER, NOT DATA.** Every number below was drawn by `src/analysis/synthetic_results.py` from a seeded random generator so that the table layout can be checked before any result exists. None of it may be quoted anywhere.

Figure: `figures/synthetic/F2_validation.pdf` (figures.py).

Sources: `results/validation_table.csv` (validate.py, channel = dict, against the adjudicated gold set), `results/corrected_rates.csv` (corrected_rates.py → rae.py: π = (o − φ)/(s − φ), double bootstrap).

## 2a. Precision, recall (sensitivity), false-positive rate

Source status: SYNTHETIC placeholder, not data.

| Variable | Category | Language | Gold n | Precision | Recall | F1 | False-positive rate |
|---|---|---|---|---|---|---|---|
| orientation | I | Hindi | 52 | 0.76 (synthetic) | 0.71 (synthetic) | 0.73 (synthetic) | 0.05 (synthetic) |
| orientation | I | English | 8 | 0.18 (synthetic) | 0.50 (synthetic) | 0.27 (synthetic) | 0.06 (synthetic) |
| orientation | F | Hindi | 44 | 0.37 (synthetic) | 0.34 (synthetic) | 0.35 (synthetic) | 0.10 (synthetic) |
| orientation | F | English | 32 | 0.61 (synthetic) | 0.88 (synthetic) | 0.72 (synthetic) | 0.07 (synthetic) |
| orientation | C | Hindi | 114 | 0.82 (synthetic) | 0.77 (synthetic) | 0.80 (synthetic) | 0.10 (synthetic) |
| orientation | C | English | 112 | 0.87 (synthetic) | 0.88 (synthetic) | 0.88 (synthetic) | 0.08 (synthetic) |
| orientation | R | Hindi | 62 | 0.58 (synthetic) | 0.60 (synthetic) | 0.59 (synthetic) | 0.11 (synthetic) |
| orientation | R | English | 61 | 0.73 (synthetic) | 0.74 (synthetic) | 0.73 (synthetic) | 0.07 (synthetic) |
| orientation | NA | Hindi | 12 | 0.17 (synthetic) | 0.42 (synthetic) | 0.24 (synthetic) | 0.09 (synthetic) |
| orientation | NA | English | 29 | 0.40 (synthetic) | 0.76 (synthetic) | 0.52 (synthetic) | 0.12 (synthetic) |
| experiencer | self | Hindi | 70 | 0.67 (synthetic) | 0.50 (synthetic) | 0.57 (synthetic) | 0.07 (synthetic) |
| experiencer | self | English | 54 | 0.87 (synthetic) | 0.83 (synthetic) | 0.85 (synthetic) | 0.03 (synthetic) |
| experiencer | kin | Hindi | 14 | 0.29 (synthetic) | 0.71 (synthetic) | 0.41 (synthetic) | 0.09 (synthetic) |
| experiencer | kin | English | 60 | 0.53 (synthetic) | 0.45 (synthetic) | 0.49 (synthetic) | 0.10 (synthetic) |
| experiencer | community | Hindi | 118 | 0.94 (synthetic) | 0.41 (synthetic) | 0.57 (synthetic) | 0.02 (synthetic) |
| experiencer | community | English | 52 | 0.58 (synthetic) | 0.81 (synthetic) | 0.67 (synthetic) | 0.12 (synthetic) |
| experiencer | deceased | Hindi | 27 | 0.31 (synthetic) | 0.37 (synthetic) | 0.34 (synthetic) | 0.08 (synthetic) |
| experiencer | deceased | English | 40 | 0.76 (synthetic) | 0.70 (synthetic) | 0.73 (synthetic) | 0.03 (synthetic) |
| experiencer | God | Hindi | 91 | 0.78 (synthetic) | 0.68 (synthetic) | 0.73 (synthetic) | 0.09 (synthetic) |
| experiencer | God | English | 95 | 0.69 (synthetic) | 0.39 (synthetic) | 0.50 (synthetic) | 0.08 (synthetic) |
| experiencer | impersonal | Hindi | 84 | 0.89 (synthetic) | 0.46 (synthetic) | 0.61 (synthetic) | 0.02 (synthetic) |
| experiencer | impersonal | English | 105 | 0.77 (synthetic) | 0.50 (synthetic) | 0.61 (synthetic) | 0.08 (synthetic) |
| experiencer | other | Hindi | 62 | 0.77 (synthetic) | 0.95 (synthetic) | 0.85 (synthetic) | 0.08 (synthetic) |
| experiencer | other | English | 9 | 0.57 (synthetic) | 0.89 (synthetic) | 0.70 (synthetic) | 0.02 (synthetic) |
| predicate_type | state | Hindi | 103 | 0.89 (synthetic) | 0.50 (synthetic) | 0.64 (synthetic) | 0.03 (synthetic) |
| predicate_type | state | English | 48 | 0.59 (synthetic) | 0.73 (synthetic) | 0.65 (synthetic) | 0.10 (synthetic) |
| predicate_type | action | Hindi | 22 | 0.32 (synthetic) | 0.41 (synthetic) | 0.36 (synthetic) | 0.07 (synthetic) |
| predicate_type | action | English | 97 | 0.82 (synthetic) | 0.56 (synthetic) | 0.66 (synthetic) | 0.06 (synthetic) |
| predicate_type | event_befalling | Hindi | 60 | 0.51 (synthetic) | 0.50 (synthetic) | 0.50 (synthetic) | 0.12 (synthetic) |
| predicate_type | event_befalling | English | 90 | 0.87 (synthetic) | 0.46 (synthetic) | 0.60 (synthetic) | 0.03 (synthetic) |
| predicate_type | speech | Hindi | 41 | 0.58 (synthetic) | 0.85 (synthetic) | 0.69 (synthetic) | 0.10 (synthetic) |
| predicate_type | speech | English | 101 | 0.85 (synthetic) | 0.75 (synthetic) | 0.80 (synthetic) | 0.07 (synthetic) |
| predicate_type | other | Hindi | 115 | 0.93 (synthetic) | 0.98 (synthetic) | 0.96 (synthetic) | 0.04 (synthetic) |
| predicate_type | other | English | 21 | 0.67 (synthetic) | 0.76 (synthetic) | 0.71 (synthetic) | 0.03 (synthetic) |
| target | self | Hindi | 12 | 0.41 (synthetic) | 1.00 (synthetic) | 0.59 (synthetic) | 0.06 (synthetic) |
| target | self | English | 104 | 0.76 (synthetic) | 0.62 (synthetic) | 0.69 (synthetic) | 0.10 (synthetic) |
| target | kin | Hindi | 19 | 0.59 (synthetic) | 0.68 (synthetic) | 0.63 (synthetic) | 0.03 (synthetic) |
| target | kin | English | 37 | 0.47 (synthetic) | 0.78 (synthetic) | 0.59 (synthetic) | 0.13 (synthetic) |
| target | community | Hindi | 102 | 0.91 (synthetic) | 0.49 (synthetic) | 0.64 (synthetic) | 0.03 (synthetic) |
| target | community | English | 47 | 0.69 (synthetic) | 0.38 (synthetic) | 0.49 (synthetic) | 0.03 (synthetic) |
| target | deceased | Hindi | 14 | 0.62 (synthetic) | 0.71 (synthetic) | 0.67 (synthetic) | 0.02 (synthetic) |
| target | deceased | English | 58 | 0.55 (synthetic) | 0.29 (synthetic) | 0.38 (synthetic) | 0.06 (synthetic) |
| target | God | Hindi | 93 | 0.88 (synthetic) | 0.56 (synthetic) | 0.68 (synthetic) | 0.03 (synthetic) |
| target | God | English | 93 | 0.67 (synthetic) | 0.34 (synthetic) | 0.45 (synthetic) | 0.08 (synthetic) |
| target | impersonal | Hindi | 13 | 0.25 (synthetic) | 0.15 (synthetic) | 0.19 (synthetic) | 0.02 (synthetic) |
| target | impersonal | English | 37 | 0.79 (synthetic) | 0.81 (synthetic) | 0.80 (synthetic) | 0.03 (synthetic) |
| target | other | Hindi | 57 | 0.74 (synthetic) | 0.54 (synthetic) | 0.63 (synthetic) | 0.05 (synthetic) |
| target | other | English | 41 | 0.56 (synthetic) | 0.85 (synthetic) | 0.67 (synthetic) | 0.11 (synthetic) |
| target | none | Hindi | 34 | 0.57 (synthetic) | 0.71 (synthetic) | 0.63 (synthetic) | 0.07 (synthetic) |
| target | none | English | 41 | 0.51 (synthetic) | 0.66 (synthetic) | 0.57 (synthetic) | 0.10 (synthetic) |
| process | L | Hindi | 81 | 0.69 (synthetic) | 0.44 (synthetic) | 0.54 (synthetic) | 0.07 (synthetic) |
| process | L | English | 17 | 0.33 (synthetic) | 0.65 (synthetic) | 0.44 (synthetic) | 0.08 (synthetic) |
| process | Rs | Hindi | 46 | 0.53 (synthetic) | 0.61 (synthetic) | 0.57 (synthetic) | 0.10 (synthetic) |
| process | Rs | English | 53 | 0.67 (synthetic) | 0.72 (synthetic) | 0.69 (synthetic) | 0.08 (synthetic) |
| process | NA | Hindi | 11 | 0.33 (synthetic) | 0.45 (synthetic) | 0.38 (synthetic) | 0.03 (synthetic) |
| process | NA | English | 106 | 0.91 (synthetic) | 0.82 (synthetic) | 0.86 (synthetic) | 0.05 (synthetic) |
| function | Sk | Hindi | 36 | 0.69 (synthetic) | 0.94 (synthetic) | 0.80 (synthetic) | 0.06 (synthetic) |
| function | Sk | English | 113 | 0.94 (synthetic) | 0.88 (synthetic) | 0.91 (synthetic) | 0.03 (synthetic) |
| function | Of | Hindi | 62 | 0.81 (synthetic) | 0.55 (synthetic) | 0.65 (synthetic) | 0.03 (synthetic) |
| function | Of | English | 53 | 0.90 (synthetic) | 0.68 (synthetic) | 0.77 (synthetic) | 0.02 (synthetic) |
| function | NA | Hindi | 35 | 0.52 (synthetic) | 0.89 (synthetic) | 0.65 (synthetic) | 0.11 (synthetic) |
| function | NA | English | 106 | 0.98 (synthetic) | 0.83 (synthetic) | 0.90 (synthetic) | 0.01 (synthetic) |
| grammar_forced | Y | Hindi | 99 | 0.76 (synthetic) | 0.52 (synthetic) | 0.61 (synthetic) | 0.08 (synthetic) |
| grammar_forced | Y | English | 19 | 0.70 (synthetic) | 0.84 (synthetic) | 0.76 (synthetic) | 0.02 (synthetic) |
| grammar_forced | N | Hindi | 84 | 0.62 (synthetic) | 0.42 (synthetic) | 0.50 (synthetic) | 0.10 (synthetic) |
| grammar_forced | N | English | 84 | 0.77 (synthetic) | 0.39 (synthetic) | 0.52 (synthetic) | 0.05 (synthetic) |
| grammar_forced | context | Hindi | 118 | 0.78 (synthetic) | 0.40 (synthetic) | 0.53 (synthetic) | 0.07 (synthetic) |
| grammar_forced | context | English | 37 | 0.64 (synthetic) | 0.92 (synthetic) | 0.76 (synthetic) | 0.07 (synthetic) |
| dative_alternative_available | Y | Hindi | 57 | 0.71 (synthetic) | 0.89 (synthetic) | 0.79 (synthetic) | 0.09 (synthetic) |
| dative_alternative_available | Y | English | 20 | 0.32 (synthetic) | 0.30 (synthetic) | 0.31 (synthetic) | 0.05 (synthetic) |
| dative_alternative_available | N | Hindi | 64 | 0.85 (synthetic) | 0.86 (synthetic) | 0.85 (synthetic) | 0.04 (synthetic) |
| dative_alternative_available | N | English | 41 | 0.76 (synthetic) | 0.78 (synthetic) | 0.77 (synthetic) | 0.04 (synthetic) |
| dative_alternative_available | NA | Hindi | 63 | 0.69 (synthetic) | 0.57 (synthetic) | 0.63 (synthetic) | 0.07 (synthetic) |
| dative_alternative_available | NA | English | 41 | 0.51 (synthetic) | 0.71 (synthetic) | 0.59 (synthetic) | 0.11 (synthetic) |

## 2b. Corrected rates (Rogan–Gladen)

| Measure | Language | Observed o | Corrected π [95% CI] | s | φ | Flags | Status |
|---|---|---|---|---|---|---|---|
| dict:orientation=I | hi | 0.044 (synthetic) | -0.007 [-0.099, 0.077] (synthetic) | 0.712 (synthetic) | 0.048 (synthetic) | out_of_range | SYNTHETIC placeholder, not data |
| dict:orientation=I | en | 0.157 (synthetic) | 0.216 [0.146, 0.293] (synthetic) | 0.500 (synthetic) | 0.062 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:orientation=F | hi | 0.277 (synthetic) | 0.734 [0.676, 0.817] (synthetic) | 0.341 (synthetic) | 0.102 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:orientation=F | en | 0.272 (synthetic) | 0.253 [0.188, 0.336] (synthetic) | 0.875 (synthetic) | 0.067 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:orientation=C | hi | 0.212 (synthetic) | 0.164 [0.066, 0.243] (synthetic) | 0.772 (synthetic) | 0.102 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:orientation=C | en | 0.202 (synthetic) | 0.151 [0.075, 0.209] (synthetic) | 0.884 (synthetic) | 0.080 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:orientation=R | hi | 0.210 (synthetic) | 0.200 [0.104, 0.288] (synthetic) | 0.597 (synthetic) | 0.113 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:orientation=R | en | 0.296 (synthetic) | 0.337 [0.259, 0.403] (synthetic) | 0.738 (synthetic) | 0.071 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=self | hi | 0.077 (synthetic) | 0.007 [-0.064, 0.081] (synthetic) | 0.500 (synthetic) | 0.074 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=self | en | 0.231 (synthetic) | 0.252 [0.177, 0.327] (synthetic) | 0.833 (synthetic) | 0.028 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=kin | hi | 0.120 (synthetic) | 0.053 [-0.029, 0.142] (synthetic) | 0.714 (synthetic) | 0.087 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=kin | en | 0.281 (synthetic) | 0.517 [0.415, 0.592] (synthetic) | 0.450 (synthetic) | 0.100 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=community | hi | 0.208 (synthetic) | 0.492 [0.421, 0.579] (synthetic) | 0.407 (synthetic) | 0.016 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=community | en | 0.194 (synthetic) | 0.101 [0.017, 0.199] (synthetic) | 0.808 (synthetic) | 0.125 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=deceased | hi | 0.175 (synthetic) | 0.325 [0.265, 0.425] (synthetic) | 0.370 (synthetic) | 0.081 (synthetic) |  | SYNTHETIC placeholder, not data |
| dict:experiencer=deceased | en | 0.065 (synthetic) | 0.045 [-0.045, 0.141] (synthetic) | 0.700 (synthetic) | 0.035 (synthetic) |  | SYNTHETIC placeholder, not data |

## 2c. Hindi − English, observed and corrected

| Measure | Observed difference | Corrected difference [95% CI] | Sign flip | p(flip) | Recall gap | Gap ≤ 0.10 |
|---|---|---|---|---|---|---|
| dict:orientation=I | -0.113 (synthetic) | -0.224 [-0.330, -0.125] (synthetic) | False | 0.186 (synthetic) | 0.212 (synthetic) | False |
| dict:orientation=F | 0.006 (synthetic) | 0.481 [0.383, 0.572] (synthetic) | False | 0.124 (synthetic) | 0.534 (synthetic) | False |
| dict:orientation=C | 0.010 (synthetic) | 0.013 [-0.086, 0.142] (synthetic) | False | 0.390 (synthetic) | 0.112 (synthetic) | False |
| dict:orientation=R | -0.086 (synthetic) | -0.138 [-0.219, -0.061] (synthetic) | False | 0.357 (synthetic) | 0.141 (synthetic) | False |
| dict:experiencer=self | -0.154 (synthetic) | -0.245 [-0.346, -0.148] (synthetic) | False | 0.261 (synthetic) | 0.333 (synthetic) | False |
| dict:experiencer=kin | -0.160 (synthetic) | -0.464 [-0.557, -0.350] (synthetic) | False | 0.212 (synthetic) | 0.264 (synthetic) | False |
| dict:experiencer=community | 0.015 (synthetic) | 0.391 [0.266, 0.487] (synthetic) | False | 0.378 (synthetic) | 0.401 (synthetic) | False |
| dict:experiencer=deceased | 0.110 (synthetic) | 0.279 [0.162, 0.386] (synthetic) | False | 0.077 (synthetic) | 0.330 (synthetic) | False |
