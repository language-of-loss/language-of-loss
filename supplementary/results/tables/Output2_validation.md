# Output 2. Dictionary channel: precision and recall per category per language; Rogan–Gladen corrected rates

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

Sources: `results/validation_table.csv` (validate.py, channel = dict, against the adjudicated gold set), `results/corrected_rates.csv` (corrected_rates.py → rae.py: π = (o − φ)/(s − φ), double bootstrap).

## 2a. Precision, recall (sensitivity), false-positive rate

Source status: reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication).

| Variable | Category | Language | Gold n | Precision | Recall | F1 | False-positive rate |
|---|---|---|---|---|---|---|---|
| orientation | I | Hindi | 34 | 0.45 | 0.15 | 0.22 | 0.09 |
| orientation | F | Hindi | 16 | 0.27 | 0.25 | 0.26 | 0.13 |
| orientation | C | Hindi | 2 | — | 0.00 | 0.00 | 0.00 |
| orientation | R | Hindi | 1 | 0.00 | 0.00 | 0.00 | 0.01 |
| orientation | NA | Hindi | 47 | 0.55 | 0.85 | 0.67 | 0.62 |
| orientation | I | English | 41 | 0.56 | 0.37 | 0.44 | 0.20 |
| orientation | F | English | 17 | 0.00 | 0.00 | 0.00 | 0.01 |
| orientation | C | English | 8 | 1.00 | 0.12 | 0.22 | 0.00 |
| orientation | R | English | 1 | 0.00 | 0.00 | 0.00 | 0.01 |
| orientation | NA | English | 33 | 0.44 | 0.94 | 0.60 | 0.58 |
| experiencer | self | Hindi | 34 | 1.00 | 0.50 | 0.67 | 0.00 |
| experiencer | kin | Hindi | 4 | 0.00 | 0.00 | 0.00 | 0.04 |
| experiencer | community | Hindi | 9 | 1.00 | 0.11 | 0.20 | 0.00 |
| experiencer | deceased | Hindi | 30 | 0.73 | 0.37 | 0.49 | 0.06 |
| experiencer | God | Hindi | 1 | — | 0.00 | 0.00 | 0.00 |
| experiencer | impersonal | Hindi | 17 | 0.33 | 0.88 | 0.48 | 0.38 |
| experiencer | other | Hindi | 4 | 0.06 | 0.25 | 0.10 | 0.16 |
| experiencer | self | English | 26 | 0.95 | 0.77 | 0.85 | 0.01 |
| experiencer | kin | English | 7 | 0.33 | 0.29 | 0.31 | 0.04 |
| experiencer | community | English | 14 | 1.00 | 0.71 | 0.83 | 0.00 |
| experiencer | deceased | English | 23 | 0.70 | 0.30 | 0.42 | 0.04 |
| experiencer | impersonal | English | 27 | 0.72 | 0.85 | 0.78 | 0.12 |
| experiencer | other | English | 3 | 0.10 | 0.67 | 0.17 | 0.20 |
| predicate_type | state | Hindi | 38 | 0.73 | 0.63 | 0.68 | 0.15 |
| predicate_type | action | Hindi | 27 | 0.43 | 0.96 | 0.60 | 0.48 |
| predicate_type | event_befalling | Hindi | 24 | 0.00 | 0.00 | 0.00 | 0.01 |
| predicate_type | speech | Hindi | 6 | 1.00 | 0.67 | 0.80 | 0.00 |
| predicate_type | other | Hindi | 3 | — | 0.00 | 0.00 | 0.00 |
| predicate_type | state | English | 52 | 0.96 | 0.50 | 0.66 | 0.02 |
| predicate_type | action | English | 24 | 0.37 | 0.96 | 0.53 | 0.52 |
| predicate_type | event_befalling | English | 18 | 1.00 | 0.28 | 0.43 | 0.00 |
| predicate_type | speech | English | 5 | 0.80 | 0.80 | 0.80 | 0.01 |
| target | self | Hindi | 10 | — | 0.00 | 0.00 | 0.00 |
| target | kin | Hindi | 5 | 0.00 | 0.00 | 0.00 | 0.02 |
| target | community | Hindi | 5 | 0.33 | 0.20 | 0.25 | 0.02 |
| target | deceased | Hindi | 10 | 0.17 | 0.10 | 0.12 | 0.06 |
| target | God | Hindi | 1 | — | 0.00 | 0.00 | 0.00 |
| target | impersonal | Hindi | 28 | 0.34 | 0.68 | 0.45 | 0.52 |
| target | other | Hindi | 2 | 0.00 | 0.00 | 0.00 | 0.04 |
| target | none | Hindi | 38 | 0.61 | 0.45 | 0.52 | 0.18 |
| target | self | English | 6 | 0.83 | 0.83 | 0.83 | 0.01 |
| target | kin | English | 5 | 0.00 | 0.00 | 0.00 | 0.02 |
| target | community | English | 7 | 0.75 | 0.86 | 0.80 | 0.02 |
| target | deceased | English | 9 | 0.25 | 0.11 | 0.15 | 0.03 |
| target | God | English | 0 | 0.00 | — | 0.00 | 0.01 |
| target | impersonal | English | 36 | 0.63 | 0.61 | 0.62 | 0.22 |
| target | other | English | 0 | 0.00 | — | 0.00 | 0.01 |
| target | none | English | 33 | 0.62 | 0.73 | 0.67 | 0.24 |
| process | L | Hindi | 43 | 0.79 | 0.26 | 0.39 | 0.05 |
| process | Rs | Hindi | 9 | 0.25 | 0.11 | 0.15 | 0.03 |
| process | NA | Hindi | 47 | 0.54 | 0.94 | 0.69 | 0.71 |
| process | L | English | 49 | 0.71 | 0.35 | 0.47 | 0.14 |
| process | Rs | English | 17 | 0.67 | 0.12 | 0.20 | 0.01 |
| process | NA | English | 33 | 0.43 | 0.94 | 0.59 | 0.62 |
| function | Sk | Hindi | 2 | — | 0.00 | 0.00 | 0.00 |
| function | Of | Hindi | 4 | 1.00 | 0.25 | 0.40 | 0.00 |
| function | NA | Hindi | 94 | 0.95 | 1.00 | 0.97 | 0.83 |
| function | Of | English | 2 | 0.00 | 0.00 | 0.00 | 0.01 |
| function | NA | English | 98 | 0.98 | 0.99 | 0.98 | 1.00 |
| grammar_forced | Y | Hindi | 30 | 0.86 | 0.20 | 0.32 | 0.01 |
| grammar_forced | N | Hindi | 69 | 0.74 | 0.97 | 0.84 | 0.77 |
| grammar_forced | context | Hindi | 1 | 0.50 | 1.00 | 0.67 | 0.01 |
| grammar_forced | Y | English | 9 | 1.00 | 0.44 | 0.62 | 0.00 |
| grammar_forced | N | English | 91 | 0.95 | 1.00 | 0.97 | 0.56 |
| dative_alternative_available | Y | Hindi | 8 | 0.33 | 0.12 | 0.18 | 0.02 |
| dative_alternative_available | N | Hindi | 8 | — | 0.00 | 0.00 | 0.00 |
| dative_alternative_available | NA | Hindi | 84 | 0.86 | 0.99 | 0.92 | 0.88 |
| dative_alternative_available | Y | English | 0 | 0.00 | — | 0.00 | 0.01 |
| dative_alternative_available | N | English | 0 | 0.00 | — | 0.00 | 0.04 |
| dative_alternative_available | NA | English | 100 | 1.00 | 0.95 | 0.97 | — |

## 2b. Corrected rates (Rogan–Gladen)

| Measure | Language | Observed o | Corrected π [95% CI] | s | φ | Flags | Status |
|---|---|---|---|---|---|---|---|
| dict:dative_alternative_available=N | hi | 0.005 | nan [nan, nan] | 0.000 | 0.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:dative_alternative_available=NA | hi | 0.983 | 0.955 [0.712, 1.421] | 0.988 | 0.875 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:dative_alternative_available=Y | hi | 0.012 | -0.095 [-0.595, 0.097] | 0.125 | 0.022 | out_of_range | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=God | hi | 0.007 | nan [nan, nan] | 0.000 | 0.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=community | en | 0.075 | 0.105 [0.077, 0.162] | 0.714 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=community | hi | 0.045 | 0.402 [0.112, 0.459] | 0.111 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=deceased | en | 0.047 | 0.029 [-0.235, 0.237] | 0.304 | 0.039 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=deceased | hi | 0.069 | 0.035 [-0.263, 0.221] | 0.367 | 0.058 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=impersonal | en | 0.328 | 0.282 [0.181, 0.382] | 0.852 | 0.123 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=impersonal | hi | 0.366 | -0.023 [-0.331, 0.164] | 0.882 | 0.378 | out_of_range | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=kin | en | 0.088 | 0.187 [-0.002, 0.592] | 0.286 | 0.043 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=kin | hi | 0.139 | nan [nan, nan] | 0.000 | 0.042 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=other | en | 0.208 | 0.026 [-0.424, 0.348] | 0.667 | 0.196 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=other | hi | 0.272 | 1.243 [0.136, 1.903] | 0.250 | 0.158 | out_of_range | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=self | en | 0.252 | 0.316 [0.246, 0.414] | 0.769 | 0.013 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:experiencer=self | hi | 0.102 | 0.204 [0.149, 0.309] | 0.500 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:function=NA | en | 0.991 | nan [nan, nan] | 0.990 | 1.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:function=NA | hi | 0.979 | 0.877 [0.847, 0.964] | 1.000 | 0.833 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:function=Of | en | 0.008 | nan [nan, nan] | 0.000 | 0.010 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:function=Of | hi | 0.021 | 0.082 [0.025, 0.101] | 0.250 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:function=Sk | hi | 0.000 | nan [nan, nan] | 0.000 | 0.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:grammar_forced=N | en | 0.969 | 0.931 [0.736, 0.962] | 1.000 | 0.556 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:grammar_forced=N | hi | 0.967 | 0.981 [0.753, 1.437] | 0.971 | 0.774 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:grammar_forced=Y | en | 0.031 | 0.069 [0.038, 0.252] | 0.444 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:grammar_forced=Y | hi | 0.032 | 0.097 [-0.129, 0.393] | 0.200 | 0.014 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:grammar_forced=context | hi | 0.000 | -0.010 [-0.031, 0.001] | 1.000 | 0.010 | out_of_range | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=C | en | 0.003 | 0.022 [0.006, 0.032] | 0.125 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=C | hi | 0.003 | nan [nan, nan] | 0.000 | 0.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=F | en | 0.017 | nan [nan, nan] | 0.000 | 0.012 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=F | hi | 0.106 | -0.210 [-3.185, 0.452] | 0.250 | 0.131 | out_of_range | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=I | en | 0.213 | 0.056 [-2.453, 0.621] | 0.366 | 0.203 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=I | hi | 0.107 | 0.282 [-1.502, 2.381] | 0.147 | 0.091 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=NA | en | 0.761 | 0.500 [0.226, 0.727] | 0.939 | 0.582 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=NA | hi | 0.772 | 0.656 [0.209, 1.250] | 0.851 | 0.623 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=R | en | 0.007 | nan [nan, nan] | 0.000 | 0.010 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:orientation=R | hi | 0.012 | nan [nan, nan] | 0.000 | 0.010 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=action | en | 0.660 | 0.318 [0.093, 0.489] | 0.958 | 0.520 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=action | hi | 0.576 | 0.200 [-0.040, 0.366] | 0.963 | 0.479 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=event_befalling | en | 0.022 | 0.079 [0.043, 0.216] | 0.278 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=event_befalling | hi | 0.012 | nan [nan, nan] | 0.000 | 0.013 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=other | hi | 0.014 | nan [nan, nan] | 0.000 | 0.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=speech | en | 0.048 | 0.047 [0.015, 0.102] | 0.800 | 0.011 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=speech | hi | 0.055 | 0.083 [0.052, 0.181] | 0.667 | 0.000 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=state | en | 0.267 | 0.514 [0.389, 0.721] | 0.500 | 0.021 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:predicate_type=state | hi | 0.343 | 0.400 [0.224, 0.603] | 0.632 | 0.150 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:process=L | en | 0.168 | 0.136 [-1.134, 0.533] | 0.347 | 0.140 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:process=L | hi | 0.097 | 0.215 [-0.226, 0.577] | 0.256 | 0.054 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:process=NA | en | 0.797 | 0.552 [0.286, 0.789] | 0.939 | 0.621 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:process=NA | hi | 0.864 | 0.679 [0.292, 1.062] | 0.936 | 0.712 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:process=Rs | en | 0.035 | 0.218 [-0.059, 0.644] | 0.118 | 0.012 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:process=Rs | hi | 0.039 | 0.071 [-0.669, 0.335] | 0.111 | 0.033 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=God | hi | 0.002 | nan [nan, nan] | 0.000 | 0.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=community | en | 0.024 | 0.001 [-0.042, 0.034] | 0.857 | 0.022 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=community | hi | 0.023 | 0.008 [-0.173, 0.120] | 0.200 | 0.021 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=deceased | en | 0.015 | -0.251 [-1.350, 0.124] | 0.111 | 0.035 | out_of_range | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=deceased | hi | 0.034 | -0.505 [-5.192, 0.214] | 0.100 | 0.056 | out_of_range | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=impersonal | en | 0.400 | 0.464 [0.223, 0.816] | 0.611 | 0.217 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=impersonal | hi | 0.617 | 0.606 [-0.138, 3.660] | 0.679 | 0.521 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=kin | en | 0.029 | nan [nan, nan] | 0.000 | 0.022 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=kin | hi | 0.042 | nan [nan, nan] | 0.000 | 0.021 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=none | en | 0.426 | 0.385 [0.196, 0.596] | 0.727 | 0.238 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=none | hi | 0.228 | 0.178 [-0.367, 0.571] | 0.447 | 0.180 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=other | hi | 0.046 | nan [nan, nan] | 0.000 | 0.041 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=self | en | 0.041 | 0.036 [0.005, 0.074] | 0.833 | 0.011 |  | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
| dict:target=self | hi | 0.008 | nan [nan, nan] | 0.000 | 0.000 | undefined | reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third language-model coder; no human adjudication) |
