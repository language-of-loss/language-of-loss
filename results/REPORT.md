# REPORT: run of 2026-10-11 on reviewed machine-prefilled labels

**Status of every number below: reviewed machine-prefilled labels.** Every gold label, audit rating, calibration
rating, metadata confirmation and corpus include/exclude decision was machine pre-filled in a two machine runs on
2026-10-11 (two machine runs of one brief) and, by the investigators' decision of 2026-10-11, reviewed and accepted by the
investigators without change unless a correction is logged. **Logged corrections: 0.** Inter-coder agreement is
agreement between the two machine runs, not independent human reliability (study protocol). The paper must state this
provenance and the number of corrections.

Registration: annotated git tag `prereg-v1-20261010` at commit `3009494` (22:57 UTC, 2026-10-10; unsigned, no signing
key configured), `docs/registration.txt`; OSF DOI pending. Every number is in RESULTS_LOG.md with its command and
input hashes (rows dated 2026-10-11, "Step 1" to "Step 9").

Corpus after the review: 283 texts (Hindi 146: 36 dev / 110 confirmatory; English 137: 47 / 90), 53,847 clause units.
Confirmatory analyses use the 200 confirmatory texts.

## Outputs 1-9

> **Adjudication update (investigators' decision 2026-10-11).** The investigators cannot adjudicate, so the 176 gold-set
> disagreements were resolved by majority with a third, independent model coder (commercial_llm_A, blind; no human
> adjudication): 79 sided with coder 1, 86 with coder 2, 11 stayed unresolved (blank). The headline numbers in this
> table for outputs 2 and 8 are the **agreed-only** run (commit 541ad01); the files in `results/` now hold the
> **majority-adjudicated** run. Both are given side by side under "Robustness: majority adjudication" below. Outputs
> 1, 3, 4, 5, 6, 7 and 9 do not read the adjudicated labels and are unchanged.

| Output | Headline (reviewed machine-prefilled labels) | n | File | Figure |
|---|---|---|---|---|
| 1 Agreement | Krippendorff's α (nominal) per codebook field: orientation .824, experiencer .923, predicate_type .845, target .774, process .842, function .836, grammar_forced .775, dative_alternative_available .742; components: 17 of 24 at .73–1.0, six below .70 and OTHERS_SAY undefined (see Limitations). No interval (point α). | 200 clauses (100 hi, 100 en); components 100 | `results/agreement/agreement_summary_gold_sheet_v1.csv`, `…_gold_components_v1.csv` | none |
| 2 Validation | Dictionary channel macro-F1, hi / en: orientation .27 / .26, experiencer .28 / .61, predicate_type .42 / .64, target .20 / .53, process .42 / .44, function .46 / .49, grammar_forced .59 / .89, dative_alt .41 / .97. Rule table: Hindi grammar_forced accuracy .739 [.641, .818] **fails 0.80**; English .979 [.925, .994]; dative_alt hi .870 [.786, .924], en .950 [.888, .979]. Rogan–Gladen (confirmatory): 27 hi − en differences, 7 change sign under correction. | adjudicated: 166–197 items per field (115 clauses agree on all 8) | `results/validation_table.csv`, `table3_validation.md`, `rule_table_check.csv`, `corrected_rates_confirmatory{,_hi_minus_en}.csv` | F2_validation |
| 3 Hypothesis | **After the deceased-detection fix (2bd38d6; see "Deviation" below).** Run 2 (registered test): Hindi odds ratio for relational framing 1.41 [1.16, 1.71], p = 6.0e-4 (GLMM); CR2 GLM 1.32 [1.09, 1.61], p = .0061; domain random intercept 1.41 [1.16, 1.71] (domain variance ≈ 0); permutation over texts p = .001 (the minimum at B = 999). Run 1 1.73 [1.41, 2.11]; Run 2b 1.39 [1.14, 1.69]; R-F6 1.40 [1.15, 1.70]. Decomposition (**provisional**), per 100 finite clauses: choice share +8.28 [6.67, 9.97]; forced +8.26 [7.03, 9.45]; opportunity −3.71 [−5.19, −2.29]; gap Δ +12.84 [10.28, 15.43]; choice share with the largest text dropped 8.48 / 8.57 / 8.77 (hi / en / both). | 200 texts; 34,038 clauses (Run 2) | `results/h1_glmm_{run1,run2,run2b,rF6}.csv`, `decompose_relational_confirmatory{,_drop_largest}.csv` | F3a_decomposition, F3b_odds_ratios |
| 4 Rival check | Registered as not estimable from text-internal evidence; the diaspora + platform rival check **did not run**: the guard refused it (118 confirmatory texts have pre-filled, unconfirmed diaspora). | — | `results/tables/Output4_rival_check.md` | none |
| 5 Audit | Hindi coefficient (standardised score at equal rated intensity, no cue; negative = under-reading): commercial_llm_A +0.004 [−0.158, 0.167]; commercial_llm_B −0.099 [−0.254, 0.055]; Llama 3.1 8B +0.752 [0.563, 0.942]; XLM-EMO +0.291 [0.030, 0.552]; MuRIL +0.124 [−0.185, 0.433]. No system under-reads Hindi; the registered direction (−) is contradicted for every system with a definite sign. Hindi × cue: commercial_llm_A −0.010 [−0.239, 0.220], commercial_llm_B −0.066 [−0.284, 0.152], Llama −0.163 [−0.431, 0.105]. Stable under-read components: Llama FEEL_BAD (selection .64), XLM-EMO HONOUR (.65); none for commercial_llm_A or commercial_llm_B. Rater α (ordinal) .947 (n 358); BRIGHTER calibration point-biserial r1 .568, r2 .503 (n 40). Agreed-pairs re-run identical (all 77 pairs agreed). | 77 pairs (154 passages); 40 calibration items | `results/audit_lmer.csv`, `audit_stability.csv`, `audit_rating_agreement.csv`, `audit_calibration{,_correlation}.csv` | F5a_audit_underreading, F5b_audit_components |
| 6 Dative choice | Hindi chosen-dative rate .291 [.226, .346] vs forced baseline .433 [.328, .557]; exact binomial p = 2.7e-7, Holm p = 5.4e-7 (anti-conservative: clustering ignored, p0 treated as known). The registered direction (choice above baseline) is contradicted. | 316 choice sites in 75 texts; baseline 97 sites in 46 texts | `results/p1_choice.csv` | none |
| 7 Component JSD | JSD (base 2) between the Hindi and English component profiles .122 [.104, .146]; permutation p = .0005 (minimum at B = 2,000), Holm p = .0005. | 24 components; 110 hi + 90 en texts | `results/p2_jsd.csv` | F7_component_profile |
| 8 Translation | **Uninformative.** Native-only gold items: 1 (strict) / 3 (tolerated), so the native-only vs translatable recall gap is not estimable; strict recall on translatable items: NRC-Hindi .85 [.68, 1.0], WordNet route .70 [.48, .89] (n = 20). MuRIL pair: both checkpoints predict "not emotional" for every clause (accuracy .473, F1 0), McNemar discordant 0 / 0, p = 1.0. | 91 Hindi gold clauses (48 emotional) | `results/a1_resource_recall.csv`, `a1_items.csv`, `mcnemar_muril.csv` | none |
| 9 Collocation | PMI networks on the dev split: Hindi 479 edges from 26 lexicon entries, English 175 edges from 34 (an instrument exhibit, not a test). | 83 dev texts | `results/collocation_pmi.csv` | F9a_collocation_hi, F9b_collocation_en |

## Deviation: deceased-detection bug

**What.** `referents.deceased_terms()` returned no kin terms for the category words the 2026-10-11 corpus review
stored as the deceased's relation (parent, grandparent, sibling, spouse, child). In those 156 texts the deceased was
never identified, so `address_to_dead` stayed 0 and the forced honorific rule REL-HON-F could not fire. Found during
the unseen-texts robustness check (dd5581b), fixed in 2bd38d6 by mapping each category word to its members' kin
terms (as `text_meta.py` already did). This is a **post-registration correction of an instrument bug** that changes
confirmatory numbers; the paper must report it as a deviation. Clauses with referent class deceased 3,398 → 7,398;
`address_to_dead` 420 → 779; eligibility rows 102,165 → 103,714. Output 6 is unchanged (.291 vs .433, p = 2.7e-7).
Source: RESULTS_LOG.md rows "FIX of the deceased-detection bug" and the two re-run robustness rows (2026-10-11).

| Analysis | Number | Before the fix | After the fix |
|---|---|---|---|
| Main (200 confirmatory texts) | clauses in Run 2 | 35,127 | 34,038 |
| Main | Run 2 Hindi OR, glmer | 1.50 [1.22, 1.84] | 1.41 [1.16, 1.71] |
| Main | Run 2 Hindi OR, CR2 GLM | 1.44 [1.18, 1.77] | 1.32 [1.09, 1.61] |
| Main | Run 2 Hindi OR, domain random intercept | 1.41 [1.11, 1.79] | 1.41 [1.16, 1.71] |
| Main | Run 2 permutation p (B = 999) | .001 | .001 |
| Main | Run 1 / Run 2b / R-F6 OR, glmer | 1.63 / 1.39 / 1.49 | 1.73 / 1.39 / 1.40 |
| Main | choice share (per 100 finite clauses) | +4.92 [2.91, 6.79] | +8.28 [6.67, 9.97] |
| Main | forced share | +3.60 [1.79, 5.21] | +8.26 [7.03, 9.45] |
| Main | opportunity share | −4.94 [−6.48, −3.48] | −3.71 [−5.19, −2.29] |
| Main | gap Δ | +3.58 [−0.61, 7.30] | +12.84 [10.28, 15.43] |
| Main | choice share, largest text dropped (hi / en / both) | 4.72 / 5.17 / 4.96 | 8.48 / 8.57 / 8.77 |
| Main | Hindi sites forced / chosen / alternative | 842 / 2,120 / 2,594 | 1,931 / 3,663 / 3,171 |
| Unseen texts (69 hi + 46 en) | clauses | 20,195 | 19,106 |
| Unseen texts | Run 2 Hindi OR, glmer | 1.62 [1.19, 2.20] | 1.46 [1.11, 1.92] |
| Unseen texts | Run 2 Hindi OR, CR2 GLM | 1.55 [1.15, 2.09] | 1.37 [1.05, 1.79] |
| Unseen texts | Run 2 Hindi OR, domain random intercept | 1.43 [0.98, 2.09] | 1.46 [1.11, 1.92] |
| Unseen texts | Run 2 permutation p | .001 | .005 |
| Unseen texts | choice share | +0.99 [−0.53, 2.58] (do not cite: bug) | +7.70 [5.47, 10.05] |
| Unseen texts | forced share | 0.00 | +8.05 [6.36, 9.89] |
| Original protocol (44 hi + 50 en) | clauses | 11,917 | 11,813 |
| Original protocol | Run 2 Hindi OR, glmer | 1.37 [1.02, 1.85] | 1.37 [1.02, 1.83] |
| Original protocol | Run 2 Hindi OR, CR2 GLM | 1.25 [0.92, 1.71] | 1.24 [0.92, 1.69] |
| Original protocol | Run 2 Hindi OR, domain random intercept | 1.37 [1.02, 1.85] | 1.37 [1.02, 1.83] |
| Original protocol | Run 2 permutation p | .143 | .147 |
| Original protocol | choice share | +7.39 [4.29, 10.56] | +9.87 [7.24, 12.63] |
| Original protocol | forced share | +3.58 [2.09, 5.60] | +5.42 [3.93, 7.20] |

Effect on conclusions: the Run 2 odds ratio falls (1.50 → 1.41) but its interval stays above 1 under all three
estimators in the main set; the choice share rises and its interval moves further from 0; the gap Δ, whose interval
included 0 before, is now clearly positive. In the original-protocol subset the CR2 interval still includes 1 and the
permutation p is .147. After the fix the domain random intercept gives the same estimate as plain glmer in all Run 2
fits (domain variance ≈ 0).

## Robustness: majority adjudication (output 2 and output 8)

Agreed-only = disagreeing fields left blank (the run above). Majority = agreed fields + majority of coder 1, coder 2
and the third model coder; 11 three-way splits stay blank. Every output-2 number in both versions:
`results/robustness/adjudication_output2.csv` (1,450 numbers; 857 differ), macro-F1 in
`results/robustness/adjudication_macro_f1.csv`. Provenance: reviewed machine-prefilled labels; disagreements resolved
by a third model coder; no human adjudication.

| Output | Number | Agreed-only | Majority-adjudicated | n (agreed-only → majority) |
|---|---|---|---|---|
| 2 | dict macro-F1 orientation hi / en | .27 / .26 | .23 / .25 | items 176 → 200 |
| 2 | dict macro-F1 experiencer hi / en | .28 / .61 | .28 / .56 | 188 → 199 |
| 2 | dict macro-F1 predicate_type hi / en | .42 / .64 | .41 / .61 | 179 → 197 |
| 2 | dict macro-F1 target hi / en | .20 / .53 | .17 / .51 | 166 → 195 |
| 2 | dict macro-F1 process hi / en | .42 / .44 | .41 / .42 | 181 → 198 |
| 2 | dict macro-F1 function hi / en | .46 / .49 | .46 / .49 | 197 → 200 |
| 2 | dict macro-F1 grammar_forced hi / en | .59 / .89 | .61 / .79 | 185 → 200 |
| 2 | dict macro-F1 dative_alt hi / en | .41 / .97 | .37 / .97 | 192 → 200 |
| 2 | rule table grammar_forced hi | .739 [.641, .818] fail | .740 [.646, .816] **fail** | 92 → 100 |
| 2 | rule table grammar_forced en | .979 [.925, .994] | .950 [.888, .979] | 93 → 100 |
| 2 | rule table dative_alt hi | .870 [.786, .924] | .840 [.756, .899] | 92 → 100 |
| 2 | rule table dative_alt en | .950 [.888, .979] | .950 [.888, .979] | 100 → 100 |
| 2 | Rogan–Gladen confirmatory hi − en: sign flips / defined | 7 / 19 | 9 / 19 | 200 texts |
| 8 | strict recall on translatable items, NRC-Hindi | .85 [.68, 1.0] | .857 [.70, 1.0] | 20 → 21 items |
| 8 | strict recall on translatable items, WordNet route | .70 [.48, .89] | .714 [.50, .90] | 20 → 21 |
| 8 | MuRIL McNemar (accuracy both models; p) | .473; p = 1.0 | .475; p = 1.0 | 91 → 99 clauses |

No conclusion changes: Hindi grammar_forced still fails the 0.80 bar; output 8 stays uninformative (1 strict
native-only item; both MuRIL checkpoints predict "not emotional" for every clause).

## What did not run and why

- **Output 4 rival check:** refused by the registered guard (R/common.R): diaspora is confirmed (reviewed pre-fill)
  for 118 of 283 texts; the 161 texts the review added have no metadata review rows, and 5 older texts have blank
  values (sources unrecoverable).
- **Decomposition on corrected rates:** not run as such. The registered decomposition uses the observed eligibility-site
  rates; the Rogan–Gladen corrections exist for the dictionary channel's codebook categories, and the eligibility sites
  have no per-site validation to correct with. Both are reported separately; the decomposition is provisional.
- **MuRIL as registered:** not run. The investigators decided not to retrain; the standalone checkpoints were scored instead, and
  model 2 is the provisional BRIGHTER-only model (registered: BRIGHTER plus native gold, retrained per gold fold).
- **Adjudication:** not done by the investigators. The adjudicated sheets keep the fields both pre-filled sheets agree
  on; 136 codebook and 40 component field disagreements are listed in `docs/adjudication_needed.md`.
- **LLM coding channel (llm_coder.py):** not re-run (no `LLM=1` in `make core`); only the API audit ran.
- **Signed tag / OSF:** the tag is unsigned (no signing key on this machine); the OSF filing is pending.

## Limitations introduced by the data

- **Provenance.** No label in this run was produced by an independent human coder. All gold, ratings, metadata and
  inclusion decisions are machine pre-fill accepted by the investigators with 0 logged corrections. α measures the
  consistency of two machine runs; human reliability is unknown.
- **Alphas below 0.70.** Components THINK_OF .663, DO_BECAUSE .694, WITH_OTHERS −.021, EVERYONE −.005, DUTY_DONE 0.0,
  BROKEN 0.0 (rare categories; 95–99% raw agreement); OTHERS_SAY undefined (never coded 1). Per language: English
  grammar_forced .595 and English function .658. Pilot function 0.0.
- **Blanks.** 20 metadata values (5 texts × genre, home language, diaspora, script mix) are blank. 9 Hindi gold
  clauses have no agreed `process` and are left out of output 8.
- **Agreed-subset gold.** Validation uses only the agreed fields (115 / 200 clauses agree on all eight). The agreed
  subset favours easy items, so precision and recall are likely optimistic.
- **Rule-table failure.** Hindi grammar_forced rule accuracy .739 (lower bound .641) is below the 0.80 bar, so the
  forced share and the decomposition are provisional.
- **Corpus composition.** The review added 161 texts, including over-cap texts (Hindi 69, English 48) that the domain
  cap was meant to keep out; the domain random intercept is the only control for site dominance. For the added texts
  the deceased's relation is a category word ("parent"), so father and mother cannot be told apart; since the fix of
  2bd38d6 the deceased is found by any member's kin term (mother or father), which can over-identify the deceased
  when the other parent is also mentioned.
- **Audit sample.** 77 pairs from dev texts, rated by the same pre-filled raters whose agreement is 0.947; every pair
  counts as agreed, so the agreed-pairs re-run cannot differ from the main fit.
- **Output 6 test.** The binomial test ignores clustering by text and treats the forced baseline as known; its
  p-value is anti-conservative, and the two bootstrap intervals overlap.
- **Output 8.** One strict native-only item; MuRIL checkpoints collapsed to the majority class.
- **Process.** One H1 run read a stale `split.csv` (123 pre-review texts) and used 85 texts; it was discarded and re-run
  on all 200 confirmatory texts after `split.csv` was regenerated with the registered rule. `core.py` and
  `audit_passages.py` were changed after the tag (orchestration only: never redraw rated sheets; confirmatory split and
  provenance label in `make core`); logged in RESULTS_LOG.md.
