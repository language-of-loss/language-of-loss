# Results headline: core outputs 1–9

> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold label and rating: machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator without change unless a correction is logged. Agreement is between two machine runs, not independent human coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.

Template: `docs/paper/Paper_Draft_v4_Full.md`. One line per output of the core pipeline (`make core`); nothing else is reported here. Tables: `results/tables/Output<k>_*.md`.

## Outputs

1. **Gold-set α per field**: α computed for 8 fields (Output1_agreement.md)
2. **Dictionary precision / recall; corrected rates**: see Output2_validation.md
3. **Run 1 / 2 / 2b odds ratios; decomposition**: choice share +8.3 [6.7, 10.0]; odds ratios see Output3_hypothesis.md
4. **Second-language rival (rival check)**: not estimable from text-internal evidence (registered); rival check with diaspora + platform: pending (R --run refused by the guard)
5. **Audit**: see Output5_audit.md
6. **Chosen-dative rate vs forced baseline**: chosen-dative rate 0.291 [0.226, 0.346] vs forced baseline 0.433 [0.328, 0.557]; binomial test p < 0.0001
7. **Component-profile JSD**: JSD 0.122 [0.104, 0.146]
8. **NRC-Hindi vs native lexicon; MuRIL pair**: resource recall: see Output8_translation.md; McNemar: see Output8_translation.md
9. **Collocation network figures**: both figures present

## Section 4.2, filled (sign-neutral; output 3)

Each term is stated with its sign and 95% interval and described by what that sign means; no direction is presupposed.

Relational marking was 23.9 per 100 clauses in Hindi and 11.1 in English; the gap Δ was +12.8 [10.3, 15.4], meaning relational marking is more frequent in Hindi. The forced share was +8.3 [7.0, 9.4], meaning Hindi has more grammatically forced relational markers per 100 clauses than English. The opportunity share was −3.7 [−5.2, −2.3], meaning Hindi offers fewer unforced relational choice sites per 100 clauses once its forced sites are removed. The choice share was +8.3 [6.7, 10.0], meaning Hindi writers take the relational option at a larger share of the choice sites available to them.

## Pre-registered directions that the current numbers contradict

- **P1** (output 6): dative chosen more often than grammar requires: choice rate − forced baseline; expected +, observed -0.14.
- **A1** (output 8): native lexicon recall above NRC-Hindi on native-only items (lexicon − nrc_hi); expected +, observed 0.00.
- **A2** (output 5): systems under-read Hindi at equal human intensity (hindi coefficient); expected −, observed 0.29 [0.03, 0.55].

## All pre-registered directions within outputs 1–9

Expected sign: + = Hindi higher (or the quantity > 0), − = Hindi lower.

| ID | Output | Expectation | Sign | Observed [95% CI] | Verdict | Note |
|---|---|---|---|---|---|---|
| H-1 | 3 | relational marking higher in Hindi: Δ = r_hi − r_en | + | 12.84 [10.28, 15.43] | as expected |  |
| H-2 | 3 | relational choice share > 0 (falsified if its CI includes 0) | + | 8.28 [6.67, 9.97] | as expected | headline statistic |
| P1 | 6 | dative chosen more often than grammar requires: choice rate − forced baseline | + | -0.14 | DIFFERS | difference of point estimates |
| A1 | 8 | native lexicon recall above NRC-Hindi on native-only items (lexicon − nrc_hi) | + | 0.00 | zero | difference of point estimates |
| A2 | 5 | systems under-read Hindi at equal human intensity (hindi coefficient) | − | 0.29 [0.03, 0.55] | DIFFERS | first system listed |
