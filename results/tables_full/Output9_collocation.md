# Output 9. Collocation networks (appendix exhibit of the lexicon candidate-generation step)

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

collocation.py, dev split: PMI in a ±5-word window around every lexicon entry with ≥ 10 matched clauses. Exploratory: an instrument description, not a test.

Figure: `figures/final/F9a_collocation_hi.pdf`, `figures/final/F9b_collocation_en.pdf` (figures.py).


## Hindi: top 8 collocates per entry (PMI, log2)

| Entry | Headword | Matched clauses | Collocates (PMI) |
|---|---|---|---|
| L-HI-01 | दुख | 36 | सुख (5.75), लोग (2.11), मिलना (1.79), देखना (1.76), बनना (1.59) |
| L-HI-05 | पीड़ा | 21 | देना (1.38) |
| L-HI-07 | याद आना | 48 | बचपन (3.34), आज (1.96), माँ (1.42), दिन (1.02) |
| L-HI-08 | याद | 211 | अनमोल (4.99), धुँधला (4.58), बँसी (3.99), तस्वीर (2.77), बचपन (2.73), पंक्ति (2.33), घटना (2.18), आना (2.15) |
| L-HI-09 | याद करना | 36 | बँसी (6.52), याद (1.93), लोग (1.69), पिता (1.31), देना (0.53), लेना (0.46) |
| L-HI-10 | कमी | 14 | आत्मविश्वास (8.96), करना (0.33) |
| L-HI-11 | खालीपन | 19 | भरना (5.78), समाज (5.20), शायद (3.76), घर (3.04), जाना (1.91), करना (0.89) |
| L-HI-13 | चले गए | 48 | छोडना (3.56), अम्मा (2.44), घर (1.68) |
| L-HI-15 | देहांत | 32 | माँ (2.37) |
| L-HI-19 | सेवा | 31 | मानव (6.94), समाज (5.36), जीवन (2.15), लेना (0.62) |
| L-HI-20 | ज़िम्मेदारी | 19 | पारिवारिक (7.71), निभाना (6.71), करना (0.30) |
| L-HI-24 | प्रेम | 31 | पिता (1.56), देना (0.36), करना (0.36) |
| L-HI-C2 | उन्होंने | 801 | पेन (2.72), सम्राज्ञी (2.72), असल (2.72), सीट (2.63), कठोरता (2.63), दिनचर्या (2.31), समर्पण (2.31), सुर्ती (2.23) |
| P-HI-01 | रोना | 36 | खुलना (4.54), शुरू (3.71), मन (2.92), लगना (1.91), बडा (1.32), कहना (0.98), रहना (0.66) |
| P-HI-08 | अकेला | 22 | छोडना (3.72), देखना (2.14), करना (0.09) |
| P-HI-11 | हिम्मत | 18 | देना (2.11), करना (0.62) |
| P-HI-13 | साथ देना | 12 | कुटुंब (7.96), पूरा (4.08), करना (0.55) |
| P-HI-31 | अपने | 296 | सीमित (4.46), ससुराल (4.13), साधन (3.46), भैया (3.13), साहित्यिक (3.00), पति (2.87), बाजार (2.72), समाजवादी (2.72) |
| P-HI-32 | परिवार | 315 | संयुक्त (4.39), सदमा (4.13), जन (3.23), अजीब (3.23), सदस्य (3.17), इंतजाम (3.17), खाली (3.13), पालन (2.98) |
| P-HI-33 | बड़े | 83 | -बडा (6.34), भाई (3.60), सबसे (1.77), पिताजी (1.25), रहना (1.11), देखना (0.17) |
| P-HI-34 | जान | 21 | लेना (1.73) |
| P-HI-39 | प्रेरणा | 17 | जीवन (3.66), पिता (2.56), रहना (2.04), देना (1.46) |
| P-HI-42 | भरोसा | 35 | हिम्मत (5.64), रखना (2.10), अम्मा (1.93), करना (0.59) |
| P-HI-45 | अस्पताल | 34 | पहुंचना (4.43), माँ (2.33), घर (1.47), लेना (1.04), आना (0.91) |
| P-HI-47 | बोझ | 15 | सर (5.49), उठाना (5.12), रखना (2.90) |

## English: top 8 collocates per entry (PMI, log2)

| Entry | Headword | Matched clauses | Collocates (PMI) |
|---|---|---|---|
| L-EN-02 | pain | 66 | suffering (4.79), memory (1.75), even (0.99), time (0.71) |
| L-EN-03 | grief | 121 | process (4.29), deeply (3.35), arrive (3.14), loss (2.94), deal (2.88), experience (2.57), close (2.29), end (1.85) |
| L-EN-04 | mourning | 16 | loss (4.50) |
| L-EN-07 | miss | 35 | person (1.91) |
| L-EN-08 | remember | 62 | still (1.75), feel (1.60), way (1.58), good (1.53), day (0.94), mother (0.78) |
| L-EN-09 | memory | 74 | fond (5.42), painful (3.81), letter (2.39), now (1.97), keep (1.88), leave (1.31), grief (1.20), life (0.50) |
| L-EN-10 | absence | 15 | feel (4.23) |
| L-EN-11 | void | 24 | grow (4.23), leave (2.93), life (2.13) |
| L-EN-12 | passed away | 39 | month (3.12), father (2.81), much (2.47), day (2.42), mother (1.45) |
| L-EN-14 | gone | 33 | back (2.50), come (2.19), father (2.05) |
| L-EN-16 | passing | 47 | follow (3.71), month (3.59), write (2.01), year (1.37), life (1.16) |
| L-EN-17 | lose | 57 | job (4.19), year (1.83), think (1.67), grief (1.58), love (1.49), person (1.20) |
| L-EN-18 | loss | 46 | mourn (4.53), grieve (4.27), face (3.01), grief (2.56), love (1.74) |
| L-EN-20 | took care of | 25 | husband (4.43) |
| L-EN-21 | love | 175 | patience (3.73), affection (3.73), respect (3.28), express (3.22), pour (3.22), show (2.56), remain (2.28), much (2.15) |
| L-EN-26 | broken | 14 | ankle (8.63) |
| L-EN-30 | guilt | 14 | feel (3.75) |
| L-EN-32 | soul | 27 | body (4.41) |
| L-EN-36 | process | 19 | end (4.58) |
| L-EN-39 | move on | 22 | life (3.36), way (3.01), feel (2.62) |
| L-EN-46 | peace | 20 | give (3.67) |
| P-EN-01 | cry | 35 | make (2.27), even (1.93), day (1.77) |
| P-EN-02 | tears | 24 | stream (7.12), eye (5.27) |
| P-EN-07 | quiet | 24 | always (2.48) |
| P-EN-08 | alone | 24 | leave (2.87) |
| P-EN-10 | bear it | 12 | family (3.92), love (3.42) |
| P-EN-15 | funeral | 32 | home (2.70), mother (1.74), day (1.49) |
| P-EN-21 | meant to be | 24 | letter (4.43) |
| P-EN-24 | goodbye | 10 | bid (8.24), say (3.69) |
| P-EN-32 | family | 104 | member (5.45), entire (3.30), friend (3.11), close (2.96), matter (2.65), child (2.23), call (0.99), good (0.76) |
| P-EN-44 | the last time | 11 | speak (5.14), see (3.91) |
| P-EN-45 | hospital | 76 | admit (5.64), level (5.42), emergency (5.42), take (2.28), day (0.61), come (0.54) |
| P-EN-47 | weight | 18 | feel (3.42), moment (3.32) |
| P-EN-60 | died | 155 | suicide (3.04), relationship (2.72), bear (2.40), follow (2.38), month (2.33), early (2.20), ritual (2.08), mother (2.02) |
