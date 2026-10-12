# CHANGELOG — lexicon v0.1 → v0.2 (2026-09-26)

Scope: extension of *Bilingual Grief Lexicon, version 0.1* (25 Sept 2026). No v0.1 entry was removed. Every v0.1 content line is kept; the only changes to v0.1 text are (a) the four-line Wierzbicka frame wrapped around emotion-word explications, (b) prime-only paraphrases of five non-prime words, each listed below, and (c) added lines, each listed below. Ids: v0.1 entries are L-HI-nn / L-EN-nn; proposals are P-HI-nn / P-EN-nn; constructions L-HI-Cn / P-EN-Cn. Everything is status = proposed.

## Global changes (apply to all v0.1 entries)

1. **Frame.** Emotion-word explications are cast in the template "someone feels something (bad) / because this someone thinks like this: '…' / when this someone thinks like this, this someone feels something bad because of it / like people can feel when they think like this". v0.1's first-person content lines sit inside the quoted thought unchanged. For line-by-line overlap comparison, I/me ≡ this someone.
2. **Prime-only paraphrases** of v0.1 wording (reason: the 2026-09-26 rule that explications contain only primes and marked molecules):
   - "will not come back here" → "will not be here again" (L-HI-13, L-HI-14, L-HI-16, L-EN-12, L-EN-14, L-EN-15, L-EN-19, L-EN-31)
   - "someone I have to speak of with respect" → "someone I have to say things about with respect" (L-HI-12)
   - "I speak of this person as of many" → "I say things about this person as about many people" (L-HI-C2)
   - "like something broken" → "like something broken[m]" (L-HI-29, L-HI-30, L-EN-26, L-EN-27; *broken* recorded as a molecule)
   - "when they speak to many people" → "when they say something to many people" (L-EN-19)
   Tolerated non-prime words kept verbatim from v0.1, listed in molecules.csv: *respect, parent, elder, slowly, finished, towards*; and *have to* as the conventional abbreviation of *can't not*.
3. **Column order** follows Plan v3 L2, with `component_vector` after `nsm_explication` and `lang`, `status` at the end. One deviation: `entry_id` is the first column, because entry_vectors.csv and flag_components.csv key on it (Plan v3 L6 presupposes it).
4. **Corpus frequencies** are blank. v0.1's seed counts are quoted in `source_notes` as "seed n" and are not results.
5. **Orientation R = ritual**, read off a "people say these words at this time" line (RITUAL_WORDS). God-content is `cultural_script` (divine-agency, atma-shanti, divine-place) and the codebook's target role, never R. The earlier provisional tables (tables/entries_provisional.csv, 24 rows) are superseded by lexicon.csv and are kept only for the record.

## Entry-level changes to v0.1 content

| Entry | v0.1 § | Change | Reason |
|---|---|---|---|
| L-HI-01 दुख | 3.1 | all four v0.1 lines kept; added "I cannot do anything now" inside the thought | the 2026-09-26 instruction's "keep it" version of दुख differs from the v0.1 file (drops the body line, adds this line). Both retained; the body line is what separates दुख from *sad* per v0.1's own mapping. Flag for decision. |
| L-HI-02 शोक | 3.2 | verbatim; register literary; orientation C | a RITUAL_WORDS line was tried and removed: शोक names a period, not a formula |
| L-HI-03 श्रद्धांजलि | 3.2 | split out of शोक as its own entry with HONOUR + RITUAL_WORDS | its thought is honouring, not mourning; counted separately in the seed (3) |
| L-HI-04 ग़म | 3.3 | verbatim; overlap with sorrow recorded as *full* (v0.1: near-full) | line-by-line the explications match |
| L-HI-05 / L-HI-06 pain ladder | 3.4 | explications written (v0.1 gave a register note only); split into bodily (पीड़ा/तकलीफ़/कष्ट) and inner (वेदना/व्यथा/संताप) | v0.1 itself states the bodily/inner difference; same-explication entries must be merged or differentiated |
| L-HI-07 याद आना | 3.5 | verbatim; the "good and bad at the same time" line deliberately has no component | no component exists for mixed valence; adding one for one entry is not justified |
| L-HI-08 / L-HI-09 याद, याद करना | 3.5 | split from याद आना | noun has no dative-arrival line; याद करना has an agentive line |
| L-HI-10 कमी | 3.6 | verbatim; grammar_forced = context | कमी महसूस होना is dative |
| L-HI-12 नहीं रहे | 3.7 | verbatim (one paraphrase, above); AVOID_DIE read off line 2 | |
| L-HI-13 चले गए | 3.8 | lines kept; "I don't say the word die" appended to line 3 | makes AVOID_DIE traceable; v0.1 §3.7 states this for all euphemisms |
| L-HI-14 हमें छोड़ गए | 3.8 | split from चले गए | the object "us" adds KIN/WITH_OTHERS lines and shifts orientation to F |
| L-HI-15 देहांत/निधन, L-HI-16 स्वर्गवास | 3.8, 4 | explications written | v0.1 listed them without explications |
| L-HI-19 सेवा | 3.10 | verbatim; matcher rule R3 added: negated opportunity → DUTY_UNDONE | v0.1's own examples (सेवा का अवसर नहीं दिया) are DUTY_UNDONE clauses |
| L-HI-20/21 ज़िम्मेदारी, त्याग; L-HI-23/24 स्नेह, प्रेम | 3.10, 3.11 | explications written | v0.1 gave register notes only |
| L-HI-25 आशीर्वाद | 3.12 | verbatim | |
| L-HI-26 आत्मा को शांति | 3.13 | lines 1–3 verbatim; line 4 "people say these words when someone has died" added | R must be read off a formula line |
| L-HI-27 अधूरा | 3.14 | verbatim; orientation I (v0.1: I/F) | no kin line in the explication; F must be traceable |
| L-HI-29/30 टूटना, बिखरना | 3.15 | v0.1 single line kept; two lines added to reach template length | |
| L-HI-31 सहारा | 3.16 | verbatim; component BOND (not SUPPORT) | the care is the deceased's, in the past |
| L-HI-32/33 छाया, कंधा | 3.16 | explications written; कंधा carries both senses pending split_senses.py | |
| L-EN-33 closure, L-EN-34 healing | 3.17 | v0.1 lines kept; one line added each | template length; agentive line for closure, wound image for healing |
| L-EN-40/41/43 hero, legacy, north star | 3.18 | explications written under the new HONOUR component | v0.1 left the cluster without a category |
| L-HI-C1, L-HI-C2 | 4 | verbatim (one paraphrase each, above) | |
| L-HI-C3 vocative | 4 | explication written; KIN added (the addressee is kin) | F must be traceable |

## Component inventory changes (recommendation list → v0.2)

- Revised glosses: HAPPEN_TO (adds "I could not do anything"), ABOVE (restricted to the divine referent), DUTY_DONE (matches सेवा), DUTY_UNDONE (includes the unfinished-plan sense), BODY (includes v0.1's दुख line), BLESSING (both directions; direction = codebook target role).
- New: AVOID_DIE, BOND, RITUAL_WORDS, HONOUR, EVERYONE. Reasons in components.csv.
- Moved out of the vector: NAME_EMOTION → form flag `names_emotion` (F12), used by H4.
- K = 24. Carrier counts below 3 in a language (merge/prune candidates when the corpus is in): DUTY_DONE (2/2), SUPPORT (2/3), EVERYONE (2/2). DUTY_DONE and SUPPORT are theory-central and kept; EVERYONE is prune-first.

## Counts

96 Hindi entries (33 L + 60 P + 3 constructions), 109 English (46 L + 60 P + 3 constructions). Overlap: 116 full, 63 partial, 26 none (24 entries with no counterpart). Every Hindi exponent, entry and component is proposed until a second native speaker passes it (validation checklist, §6 of the draft document).
