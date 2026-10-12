import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
T = ROOT / "tables"
primes_md = (T / "primes_hi.md").read_text(encoding="utf-8")
import csv
V = ROOT / "v02" / "out"
crows = list(csv.DictReader(open(V / "components.csv", encoding="utf-8")))
comps_md = "| id | gloss (primes) | Hindi example | English example | status | carriers hi / en | note |\n|---|---|---|---|---|---|---|\n" + "\n".join(
    "| " + " | ".join(x.replace("|", "\\|") for x in (r["component_id"], r["gloss_primes"], r["example_hi"], r["example_en"], r["status"], f"{r['n_entries_hi']} / {r['n_entries_en']}", r["note"])) + " |" for r in crows)
lrows = list(csv.DictReader(open(V / "lexicon.csv", encoding="utf-8")))
def render(e):
    return (f"### {e['entry_id']} — {e['headword_deva'] or e['headword_en']}\n\n- **roman / en:** {e['headword_roman_variants']} / {e['headword_en']} · **pos:** {e['pos']} · **register:** {e['register']}\n"
            f"- **orientation / process / function:** {e['orientation']} / {e['process']} / {e['function']} · **components:** {e['component_vector']} · **idiom:** {e['idiom_flag']} · **grammar_forced:** {e['grammar_forced']}\n"
            f"- **counterpart:** {e['counterpart']} ({e['overlap']}) · **script:** {e['cultural_script']}\n- **explication:**\n\n```\n{e['nsm_explication']}\n```\n- **examples:** {e['example_hi']} / {e['example_en']}\n- **notes:** {e['source_notes']}\n")
entries_md = "\n".join(render(e) for e in lrows)
changelog = (V / "CHANGELOG.md").read_text(encoding="utf-8").split("\n", 2)[2].replace("\n## ", "\n#### ")

DOC = f"""# Core grief dictionary, Hindi–English: primes, components, entries, computational support

**Version:** v0.2 (2026-09-26). **Status:** proposed throughout. No Hindi exponent, component or entry in this document has been verified by a second native speaker, and no corpus frequency or result is reported anywhere in it.

## 0. What this document is, and what it is not yet

This document covers five deliverables built on lexicon v0.1, the computational recommendation v3 (Part 2, N1) and methodology v3. The canonical machine-readable outputs are the files in `lexicon/` (Plan v3 layout); this document is the narrative and the rendering.

| Deliverable | State | Depends on v0.1? |
|---|---|---|
| 1. Prime table (65 primes, Hindi exponents) | complete, proposed | no |
| 2. Component inventory | complete: K = 24, audited against every v0.1 explication; 5 glosses revised, 5 components added, NAME_EMOTION moved to a form flag; carrier counts per language | done |
| 3. Dictionary entries | complete: 205 entries (96 Hindi, 109 English) incl. 6 constructions; every v0.1 entry carried as L-*, every change logged in CHANGELOG.md; all checks pass | done |
| 4. Embedding protocol (4 scripts) | complete; smoke-tested end to end on a synthetic corpus with a local stand-in model (MuRIL and LaBSE were not available offline) | no |
| 5. Component classifier spec + training script | complete; smoke-tested the same way; falsification rule fires correctly | no |
| Validation checklist | complete | no |

Conventions fixed on 2026-09-26: orientation **R = ritual** (read off a "people say these words at this time" line; God-content goes to `cultural_script` and the codebook's target role); ids `L-HI-nn`/`L-EN-nn` for v0.1 entries, `P-HI-nn`/`P-EN-nn` for proposals; Plan v3 L2 column order with `component_vector` after `nsm_explication` and `lang`, `status` last; explications in English primes as in v0.1, molecules marked `[m]` and listed in `molecules.csv`.

All tables are CSV-ready and live in `tables/`; the scripts in `scripts/`; the Markdown here is a rendering of the CSVs, not a second copy to maintain.

---

## 1. Prime table: the 65 semantic primes with proposed Hindi exponents

### 1.1 Basis and format

The list and grouping follow Goddard & Wierzbicka's current 65-prime table (the grouping used in the NSM Homepage tables and in Goddard 2018/2021): substantives, relational substantives, determiners, quantifiers, evaluators, descriptors, mental predicates, speech, actions–events–movement, location–existence–specification, possession, life and death, time, space, logical concepts, augmentor–intensifier, similarity. The columns replicate what the published Mandarin (Chappell 2002) and French (Peeters 2006) exponent tables record: the exponent, its allolexes (forms conditioned by grammar or register that carry the same prime), the polysemy of the form (which other prime or non-prime meaning the same word carries, and the frame that disambiguates), and canonical contexts. Two canonical-context test sentences are given per prime in Hindi; a proposed exponent passes only if it can be substituted in both without a change of meaning, in the judgement of two native speakers working independently.

**Published NSM work on Hindi or Urdu.** I know of no published NSM exponent table for Hindi or Urdu, and none for any Indo-Aryan language, in the exponent-table volumes (Goddard & Wierzbicka eds 1994, 2002; Goddard ed. 2008; Peeters ed. 2006) or in the later journal literature that I can recall with confidence. Before claiming the table below as a first, check the "Semantic primes in other languages" page of the NSM Homepage (Griffith University) and search *Language Sciences*, *Intercultural Pragmatics* and the Australian Journal of Linguistics for Hindi/Urdu; a graduate thesis may exist that I cannot cite. Non-NSM resources that bear on individual rows: the literature on Hindi dative-experiencer constructions (relevant to FEEL, KNOW, WANT, THINK) and on honorific number (relevant to YOU and to the deceased-reference entries).

### 1.2 Conventions used in the table

- **Citation form.** Where Hindi splits a prime across register (तू/तुम/आप for YOU) or across frames (सोचना vs लगना for THINK, जीना vs रहना for LIVE), the exponent column gives the form to use when writing explications and the allolex column gives the rest. These choices are conventions, to be fixed once and not revisited entry by entry.
- **Dative allolexes.** Hindi expresses FEEL, KNOW (पता), WANT (चाहिए), THINK-that (लगना) and THINK-OF (याद आना) with a dative experiencer. The dative form is an allolex of the prime, not a different meaning; but it *is* the grammatical shape that the dictionary's `grammar_forced` column exists to record (see §3.2).
- **Cross-prime polysemy that the matcher must handle.** The same Hindi form carries two primes in seven cases: बहुत (MUCH~MANY / VERY), तरह (KIND / LIKE~WAY), कुछ (SOMETHING / SOME), होना (HAPPEN / BE / THERE IS), और (OTHER / MORE / 'and'), लगना (FEEL / THINK-that / non-prime 'seem, touch, cost'), पास (NEAR / possessive 'have'). Each is frame-separable and the frame is stated in the row.
- **Confidence** is high when the form is unmarked, pan-register and frame-separable; medium when the exponent is a construction, is split across frames, or has a competing register form that a second speaker may prefer; low is not used, because every row here has at least a defensible candidate. The reason column says what the second speaker should test.

### 1.3 The table

Rows are in the canonical group order. All Hindi forms are `proposed`. CSV: `tables/primes_hi.csv`.

{primes_md}

### 1.4 Rows most likely to change after verification

FEEL (महसूस होना vs लगना), THINK-that (सोचना कि vs लगना कि), YOU (citation form), THE SAME (वही vs एक ही), MOVE (हिलना vs चलना for displacement), WORDS (शब्द vs बात), the three duration primes (A LONG TIME / A SHORT TIME / FOR SOME TIME, which share देर and समय), SIDE, MORE, and LITTLE~FEW. These are exactly the rows to put first in the second-speaker review.

---

## 2. Component inventory

### 2.1 Purpose

A component is a recurrent cluster of prime-language lines that appears inside many explications. The component vector of an entry is the list of components its explication contains; the matcher scores a clause with the union of the vectors of the entries it matches. Components are therefore *derived from* explications, which is why the inventory cannot be finalised without v0.1: a component that no v0.1 explication contains has no business in the vector, and a line that recurs across many v0.1 explications but is not in the list below should become one.

### 2.2 The inventory (K = 24), audited against v0.1

Each v0.1 explication was read line by line and the components whose gloss it entails were listed; recurrent lines with no component became new components, and glosses that did not match the v0.1 lines that carry them were revised. CSV: `lexicon/components.csv` (with the carrier list per component).

{comps_md}

### 2.3 Changes, with reasons

1. **Five glosses revised** to match the v0.1 lines that carry them: HAPPEN_TO (adds "I could not do anything", from दुख/खोना), ABOVE (restricted to the divine referent, so that "someone above me (a parent)" in सेवा and नहीं रहे maps to KIN + the respect sub-flag, as Plan v3 N1 step 2 says), DUTY_DONE (now the सेवा lines), DUTY_UNDONE (now covers अधूरा's unfinished plan, which is not fault), BODY (now includes दुख's "I feel it like something bad in my body").
2. **Five components added**, each because a line recurs across v0.1 entries without a home: AVOID_DIE ("I don't say the word 'die'", written in v0.1 §3.7 and true of every euphemism; makes `indirect_death_reference` readable off the vector), BOND (the deceased's care and feeling towards the writer: ममता, स्नेह, प्रेम, सहारा, छाया, आशीर्वाद, love, rock), RITUAL_WORDS (the formula line that R is read off), HONOUR (श्रद्धांजलि and v0.1's uncategorised hero/legacy cluster), EVERYONE (सबको जाना है; no v0.1 carrier, prune first).
3. **BLESSING broadened** to both directions (the dead's blessing on me, आशीर्वाद; my wish for the dead's atma, आत्मा को शांति); the direction is the codebook's target role. The recommendation glossed only the first; the closing formulae carry the same thought the other way.
4. **NAME_EMOTION moved out of the vector** to the form flag `names_emotion`: a fact about wording, not meaning; two clauses with identical explications can differ on it. H4 (naming vs narrating) reads the flag.
5. **Not split:** WITH_OTHERS by familial/communal; orientation carries F vs C.
6. **Weak carriers** (fewer than 3 in a language): DUTY_DONE 2/2, SUPPORT 2/3, EVERYONE 2/2. The first two are theory-central and stay; EVERYONE is the first to prune if the corpus does not support it. K = 24 is above the recommendation's "≈ 20"; every component's carriers are listed so pruning is a one-line change.

---

## 3. Dictionary entries

### 3.1 Schema

The table has exactly the columns the specification requires, plus two the scripts need (`lang`, `status`):

`entry_id, headword_deva, headword_roman_variants, headword_en, pos, sense_note, nsm_explication, component_vector, orientation (I/F/C/R), process (loss/restoration/NA), function (seek/offer/NA), register (literary/colloquial/therapeutic/ritual), cultural_script, idiom_flag, grammar_forced (Y/N/context), counterpart_entry_id, overlap (full/partial/none), pattern, example_hi, example_en, source (v0.1/seed corpus/proposed), corpus_freq_hi, corpus_freq_en, lang, status`

### 3.2 Conventions

- **Explications** are 3–8 lines in primes, with X = the writer and Y = the deceased. Hindi entries carry the explication in Hindi primes and an `[EN]` gloss line in English primes so that a reviewer who cannot read Devanagari can still check prime-only-ness. Semantic molecules are marked `[word]m` (only `[family]m` is used so far). No explication uses *sad*, *grief*, *mourn*, *loss* or their Hindi counterparts; DIE is a prime and may be used.
- **Euphemisms** are explicated as *Y died* plus how X chooses to say it and why. The euphemism's meaning is the manner-of-saying, not a different event; this is what makes NOT_HERE, ABOVE and WITH_OTHERS separable across चले गए / चल बसे / हमें छोड़ गए / स्वर्ग सिधार गए.
- **grammar_forced** is Y when the grammar of the language leaves the writer no choice (the dative experiencer for feeling nouns; honorific plural for a parent), N when the form is freely chosen, and *context* when it depends on the referent (honorific plural for a younger deceased). A component tagged `(grammar)` in the vector is not to be scored as evidence of orientation; this is the single most important guard against the "Hindi is more relational because it is pro-drop and dative" artefact described in the research plan.
- **Patterns** carry explicit Devanagari-aware boundary classes on both sides; `\\b` is never used because Python's `\\b` treats matras and the nukta as non-word characters. The left class is `(?<![\\u0900-\\u0963\\u0966-\\u096F\\u0971-\\u097F\\u200C\\u200DA-Za-z0-9_'])` and the right class is the corresponding lookahead; the danda (U+0964/5) is punctuation and stays outside. Text is NFC-normalised before matching, which decomposes precomposed nukta letters (ज़ → ज + ़), so patterns write the nukta as an optional `\\u093C`. Bare `passed` and bare `gone` over-match and are flagged for human review in the sense notes.
- **Frequencies** are left blank. `ground_entries.py` prints `n_matches` per entry from the current corpus; those numbers are copied into `corpus_freq_*` by hand, with the corpus version, after the pattern has been reviewed.

### 3.3 What changed from v0.1 (summary; full list in `lexicon/CHANGELOG.md`)

{changelog}

### 3.4 The entries (205)

96 Hindi (33 from v0.1, 60 proposed, 3 constructions) and 109 English (46 from v0.1, 60 proposed, 3 constructions). Overlap by explication comparison: 116 full, 63 partial, 26 none. CSV: `lexicon/lexicon.csv`; the rendering below is generated from it.

{entries_md}

### 3.5 Next expansion (after the first corpus run)

`ground_entries.py` gives `n_matches` per entry and the collocates; entries with zero matches in both languages are candidates for merging under their nearest explicated entry (v0.1 §7); `expand_candidates.py` neighbours of frequent entries are the source of further headwords; `split_senses.py` decides whether कंधा, याद, पास-type polysemes need two entries. Targets stay as in v0.1 §7.

---

## 4. Embedding protocol

Four scripts in `scripts/`, each under 120 lines, plus a shared helper `lexutil.py` (corpus reader, lexicon reader, Devanagari-aware boundaries, tokeniser). Python 3.11; pins in `requirements-lexicon.txt`. Every script's header states: **embeddings propose candidates, senses and contexts; they never define an entry's meaning; the explication does.**

| Script | Model | Input | Output | What a human does with it |
|---|---|---|---|---|
| `expand_candidates.py` | fastText cc.hi.300 / cc.en.300 (.vec, top 500k) | lexicon CSV | `candidates.csv`: 30 nearest neighbours per seed with cosine, empty `accept` column | accept/reject; accepted forms get an explication before they become entries |
| `split_senses.py` | MuRIL base, mean of subword vectors over the matched span, averaged over the last four layers (9–12) | lexicon + `data/clean` | `senses.csv` and a printout of 5 contexts per cluster (matched span marked ⟦…⟧); HDBSCAN (min 5), agglomerative fallback | name the senses; decide whether an entry splits |
| `ground_entries.py` | none (counts) | lexicon + `data/clean` | `grounding.md`: PMI collocates (±5, count ≥ 5) and the 10 contexts with the highest summed positive PMI, printed beside the explication | check the explication against use; copy `n_matches` into the frequency columns |
| `align_diagnostic.py` | LaBSE | lexicon | `alignment.csv`: cosine to the counterpart (or nearest English entry); `silently_translatable = Y` when overlap = none and cosine > 0.6; sensitivity at 0.5 and 0.7 printed | build the translation-bias table |

Run order: `ground_entries` → `expand_candidates` → (review) → `split_senses` → (review) → `align_diagnostic`. The MuRIL alternative for candidate expansion (token vectors averaged over corpus occurrences) is obtainable from `split_senses.py`'s span vectors by averaging per entry; it was not implemented separately to keep the scripts short.

Smoke test performed here: the full pipeline ran on a six-record synthetic corpus and a four-entry lexicon, using a randomly initialised six-layer BERT trained-tokeniser stand-in for MuRIL and a stubbed encoder for LaBSE, because huggingface.co is not reachable from the build container. This tests the code paths (span offsets, clustering, PMI, flagging), not the models. First real run must be on a local machine.

---

## 5. Lexicon-induced component classifier

**Specification.** Distant supervision. The matcher scores every clause it covers with a K-bit component vector; those clause–vector pairs are the training set. `google/muril-base-cased` is fine-tuned with a K-output multi-label head (BCE-with-logits), lr 2e-5, batch 16, 4 epochs, linear decay with 10 % warm-up, seed 20260926, decision threshold 0.5 (not tuned). Cross-validation is 5-fold **grouped by text** so that no clause of a text is in both folds. The trained model is applied to clauses the matcher does not cover. Evaluation on the 200 component-labelled gold clauses reports per-component precision, recall and F1 for the classifier *and for the matcher*, side by side. Coverage gain = share of all clauses that the classifier scores with at least one component and the matcher scored with none.

**Falsification condition, fixed in advance.** If the classifier's F1 on gold is below the matcher's for a component, the classifier is not used for that component; if its macro-F1 is below the matcher's, it is not used at all and the paper reports the matcher only. No re-tuning after the gold scores are seen.

**Inputs.** `clauses.csv` (clause_id, text_id, lang, text, matcher_covered, c_<id> …), `gold.csv` (200 rows, same component columns, human labels), `components.csv` (the K ids). Clause segmentation is upstream of this script (the matcher's segmenter); the classifier consumes whatever unit the matcher scored.

**Outputs.** `cv_metrics.csv`, `gold_eval.csv` (with a `use_classifier` flag per component), `predictions_uncovered.csv` (only components that passed), `coverage.json`.

Script: `scripts/train_component_classifier.py` (134 lines). Smoke-tested with 60 synthetic clauses over 12 texts and K = 3 using the stand-in model; the falsification rule fired (macro-F1 0.09 vs matcher 0.92 → "classifier NOT USED"), which is the correct outcome for a random model.

---

## 6. Validation checklist for the whole dictionary

Each item has a pass condition and a record. Nothing is "verified" without the record.

1. **Second-speaker verification of exponents.** A second native speaker, not shown the proposer's choices, writes their own Hindi exponent for each of the 65 primes from the English exponent and the two test sentences. Agreement is counted per prime; disagreements are discussed and the resolution is recorded in a `verification` column with the speaker's initials and date. Pass: every row has a recorded second judgement; unresolved rows stay `proposed` and the entries that depend on them are marked.
2. **Canonical-context tests.** For every exponent (and every allolex claimed), both test sentences are read by two speakers who judge (a) naturalness and (b) whether substituting the allolex changes meaning. Pass: both sentences natural, no meaning change, for both speakers. Fail on either → the row is reworked and re-tested; the failed sentence is kept in the record.
3. **Explication review: no non-prime words.** Automated: every token of every explication (English lines; Hindi lines via the exponent list plus its allolexes) must be a prime exponent, an allolex, a variable (X, Y, Z), a marked molecule `[…]m`, or a listed function word. The check run for this draft is in `scripts/build_components_and_entries.py`'s companion check; it is re-run on every table build and the offending words are printed. Manual: a reviewer reads each explication for entailment (does it say what the word means and nothing more), and specifically rejects any explication that uses *sad*, *grief*, *mourn*, *loss*, दुख, ग़म, शोक, or any other emotion word.
4. **Agreement on component labels.** Two annotators label the 200 gold clauses with the K components independently, after a training round on 40 other clauses. Krippendorff's α (nominal, per component; also on the full vector using Jaccard distance) must be ≥ 0.70 for a component to be used in analysis. Components below 0.70 are re-glossed and re-annotated once; if still below, they are dropped from the vector and reported as dropped. α is computed with the annotators' raw labels, before adjudication.
5. **Measurement invariance across languages.** On the gold clauses, compute the matcher's recall per component separately for Hindi and English clauses. The per-language recall gap must be ≤ 0.10 for every component *before* the recall-adjusted estimator is applied; the estimator corrects for a known, small gap, not for a lexicon that covers one language better. A gap above 0.10 sends the component back to §3.4 (expand entries in the under-covered language), not to the estimator. Report the gaps in a table, with both recalls and their Wilson intervals (n ≈ 100 per language, so intervals are wide; say so).
6. **Regression on every change.** Any edit to an exponent, explication, component or pattern re-runs items 3 and 5 automatically and flags items 1, 2 and 4 for the affected rows.

---

## Files

```
lexicon/
  grief-dictionary-core-v0.2-DRAFT.md      this document (generated)
  requirements-lexicon.txt
  tables/primes_hi.csv, primes_hi.md       Deliverable 1
  lexicon.csv, components.csv, entry_vectors.csv, flag_components.csv,
  constructions.yaml, molecules.csv, CHANGELOG.md   Deliverables 2–3 (Plan v3 layout)
  src/                                     regenerates all of the above (python src/build_v02.py)
  scripts/lexutil.py                       shared helper
  scripts/expand_candidates.py             Deliverable 4a
  scripts/split_senses.py                  Deliverable 4b
  scripts/ground_entries.py                Deliverable 4c
  scripts/align_diagnostic.py              Deliverable 4d
  scripts/train_component_classifier.py    Deliverable 5
  scripts/build_prime_table.py             regenerates tables/primes_hi.*
  scripts/build_components_and_entries.py  regenerates the component and entry tables
  scripts/assemble_document.py             regenerates this document
```
"""
(ROOT / "grief-dictionary-core-v0.2.md").write_text(DOC, encoding="utf-8")
print("document assembled:", len(DOC), "chars")
