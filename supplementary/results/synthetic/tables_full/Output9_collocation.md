# Output 9. Collocation networks (appendix exhibit of the lexicon candidate-generation step)

> **SYNTHETIC PLACEHOLDER, NOT DATA.** Every number below was drawn by `src/analysis/synthetic_results.py` from a seeded random generator so that the table layout can be checked before any result exists. None of it may be quoted anywhere.

collocation.py, dev split: PMI in a ±5-word window around every lexicon entry with ≥ 10 matched clauses. Exploratory: an instrument description, not a test.

Figure: `figures/synthetic/F9a_collocation_hi.pdf`, `figures/synthetic/F9b_collocation_en.pdf` (figures.py).


## Hindi: top 8 collocates per entry (PMI, log2)

| Entry | Headword | Matched clauses | Collocates (PMI) |
|---|---|---|---|
| L-HI-01 | दुख | 35 | रास्ता (5.00), आँसू (2.60), तस्वीर (2.35), माँ (2.10), दिन (1.90), हाथ (1.16), याद (1.08) |
| L-HI-02 | शोक | 36 | माँ (3.80), सपना (3.27), रोना (3.16), याद (2.42), हाथ (0.78), रात (0.65), दिन (0.43) |
| L-HI-03 | श्रद्धांजलि | 23 | याद (5.29), रास्ता (4.28), फ़ोन (3.54), तस्वीर (2.31), घर (2.06), कमरा (1.45), खाना (0.48) |
| L-HI-04 | ग़म | 49 | शाम (5.38), सपना (5.16), कमरा (4.93), बचपन (3.94), आँसू (3.20), तस्वीर (2.88), सुबह (1.71) |
| L-HI-05 | पीड़ा | 12 | दिल (5.04), बचपन (4.92), चेहरा (3.18), शाम (1.78), दवा (1.62), कमरा (0.92), माँ (0.68) |
| L-HI-06 | वेदना | 59 | शाम (4.49), घर (4.33), अस्पताल (3.21), माँ (2.93), रास्ता (2.67), दिन (2.39), खिड़की (1.31) |
| L-HI-07 | याद आना | 41 | फ़ोन (4.73), दिन (4.05), अस्पताल (2.47), रास्ता (2.39), याद (1.79), बचपन (1.38), घर (1.08) |
| L-HI-08 | याद | 47 | फ़ोन (2.80), आवाज़ (1.74), खाना (1.43), तस्वीर (1.29), बचपन (1.03), घर (0.82), माँ (0.82) |
| L-HI-09 | याद करना | 33 | बारिश (5.11), खाना (3.44), दवा (3.02), रोना (2.71), आँसू (1.18), दिन (1.15), बचपन (0.99) |

## English: top 8 collocates per entry (PMI, log2)

| Entry | Headword | Matched clauses | Collocates (PMI) |
|---|---|---|---|
| L-EN-01 | sadness | 29 | morning (5.20), phone (5.04), evening (3.24), tears (2.29), window (1.01), room (0.99), face (0.85) |
| L-EN-02 | pain | 29 | face (4.89), day (4.84), night (4.66), hospital (3.59), voice (3.04), photo (1.33), tears (0.61) |
| L-EN-03 | grief | 33 | window (4.52), hand (4.28), phone (2.73), food (2.00), memory (1.76), morning (1.31), night (1.14) |
| L-EN-04 | mourning | 41 | childhood (4.89), tears (4.39), photo (3.06), hand (2.88), home (2.60), day (1.15), mother (0.58) |
| L-EN-05 | sorrow | 19 | morning (5.47), hospital (4.10), rain (3.86), food (2.35), face (2.01), road (1.85), voice (1.12) |
| L-EN-06 | anguish | 15 | evening (5.31), mother (4.85), voice (1.68), tears (1.17), day (1.01), childhood (0.87), dream (0.66) |
| L-EN-07 | miss | 54 | rain (5.18), medicine (4.99), memory (4.58), dream (4.04), childhood (3.41), day (2.65), mother (2.41) |
| L-EN-08 | remember | 26 | voice (4.96), road (4.92), memory (4.58), medicine (4.35), hand (3.40), face (2.38), mother (1.48) |
| L-EN-09 | memory | 14 | hand (5.25), heart (4.93), room (4.79), tears (3.10), home (1.24), night (1.14), voice (1.12) |
