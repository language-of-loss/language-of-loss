# Supplementary material

Supplementary files for *The Language of Loss: Relational Grief in Hindi and Indian English*. Everything here is aggregate or instrument-level: no corpus text, no per-text or per-passage rows. Labels behind the results are reviewed machine-prefilled labels; the provenance is stated inside each table. Every number is traceable to its command in `RESULTS_LOG.md` at the repository root.

| file | description |
|---|---|
| `codebook_v1.md` | Annotation codebook: the eight gold fields with their values and decision rules. |
| `figures/F2_validation.pdf` | Figure (PDF, full resolution): Dictionary channel against the adjudicated gold set: precision (filled) and recall (open triangles) per codebook category and language, with Wilson 95% intervals computed from the tp, fp and fn counts of validation_table.csv (one-vs-rest per category). |
| `figures/F2_validation.png` | Figure (PNG, full resolution): Dictionary channel against the adjudicated gold set: precision (filled) and recall (open triangles) per codebook category and language, with Wilson 95% intervals computed from the tp, fp and fn counts of validation_table.csv (one-vs-rest per category). |
| `figures/F3a_decomposition.pdf` | Figure (PDF, full resolution): Decomposition of the Hindi − English gap in relational marking, Δ = forced + opportunity + choice (per 100 finite clauses; choice = headline statistic), with 95% intervals from 2,000 bootstrap resamples of texts; open diamonds re-estimate each term without the largest Hindi text, the largest English text, and both. |
| `figures/F3a_decomposition.png` | Figure (PNG, full resolution): Decomposition of the Hindi − English gap in relational marking, Δ = forced + opportunity + choice (per 100 finite clauses; choice = headline statistic), with 95% intervals from 2,000 bootstrap resamples of texts; open diamonds re-estimate each term without the largest Hindi text, the largest English text, and both. |
| `figures/F3b_odds_ratios.pdf` | Figure (PDF, full resolution): Odds ratio for Hindi (relational ~ hindi + log clauses + loss type + (1 \| text)) in Run 1, Run 2 (clauses with a forced relational site removed), Run 2b (honorific reference to elders removed as well) and the R-F6 robustness check (Run 2 without closing formulae); right panel, when present: the output-4 rival check with diaspora and platform added. |
| `figures/F3b_odds_ratios.png` | Figure (PNG, full resolution): Odds ratio for Hindi (relational ~ hindi + log clauses + loss type + (1 \| text)) in Run 1, Run 2 (clauses with a forced relational site removed), Run 2b (honorific reference to elders removed as well) and the R-F6 robustness check (Run 2 without closing formulae); right panel, when present: the output-4 rival check with diaspora and platform added. |
| `figures/F5a_audit_underreading.pdf` | Figure (PDF, full resolution): Audit, per system: the Hindi − English difference in standardised score at mean human-rated intensity without the culture cue (left; negative = Hindi under-read) and its change when the cue 'the writer is in India' is given (right), from score_z ~ intensity × hindi × cue + (1 \| pair); Wald 95% intervals. |
| `figures/F5a_audit_underreading.png` | Figure (PNG, full resolution): Audit, per system: the Hindi − English difference in standardised score at mean human-rated intensity without the culture cue (left; negative = Hindi under-read) and its change when the cue 'the writer is in India' is given (right), from score_z ~ intensity × hindi × cue + (1 \| pair); Wald 95% intervals. |
| `figures/F5b_audit_components.pdf` | Figure (PDF, full resolution): Stability selection of the machine error (standardised score − standardised human intensity) on the passage component profile, per system (Hindi passages of the matched pairs, no cue): selection frequency over subsamples; outlined cells are stable under-read components (frequency ≥ 0.6 and negative full-data coefficient; line on the colour bar = threshold). |
| `figures/F5b_audit_components.png` | Figure (PNG, full resolution): Stability selection of the machine error (standardised score − standardised human intensity) on the passage component profile, per system (Hindi passages of the matched pairs, no cue): selection frequency over subsamples; outlined cells are stable under-read components (frequency ≥ 0.6 and negative full-data coefficient; line on the colour bar = threshold). |
| `figures/F7_component_profile.pdf` | Figure (PDF, full resolution): Component profiles of the 24 semantic components by language (left) and the log-odds with an informative Dirichlet prior (right; δ ± 1.96 sd, filled where the interval excludes 0, positive = more frequent in Hindi); components ordered by δ. |
| `figures/F7_component_profile.png` | Figure (PNG, full resolution): Component profiles of the 24 semantic components by language (left) and the log-odds with an informative Dirichlet prior (right; δ ± 1.96 sd, filled where the interval excludes 0, positive = more frequent in Hindi); components ordered by δ. |
| `figures/F9a_collocation_hi.pdf` | Figure (PDF, full resolution): Hindi collocation network (appendix exhibit): lexicon entries and their top 8 collocates by PMI in a ±5-word window; positions from metric MDS of shortest-path distances with edge length 1/PMI. |
| `figures/F9a_collocation_hi.png` | Figure (PNG, full resolution): Hindi collocation network (appendix exhibit): lexicon entries and their top 8 collocates by PMI in a ±5-word window; positions from metric MDS of shortest-path distances with edge length 1/PMI. |
| `figures/F9b_collocation_en.pdf` | Figure (PDF, full resolution): English collocation network (appendix exhibit): lexicon entries and their top 8 collocates by PMI in a ±5-word window; positions from metric MDS of shortest-path distances with edge length 1/PMI. |
| `figures/F9b_collocation_en.png` | Figure (PNG, full resolution): English collocation network (appendix exhibit): lexicon entries and their top 8 collocates by PMI in a ±5-word window; positions from metric MDS of shortest-path distances with edge length 1/PMI. |
| `figures/Figure1_component_space.pdf` | Figure (PDF, full resolution): lexicon entries in component space. |
| `figures/Figure1_component_space.png` | Figure (PNG, full resolution): lexicon entries in component space. |
| `figures/Figure2_collocation.pdf` | Figure (PDF, full resolution): collocation networks, both languages. |
| `figures/Figure2_collocation.png` | Figure (PNG, full resolution): collocation networks, both languages. |
| `figures/Figure2_collocation_en.pdf` | Figure (PDF, full resolution): collocation network, English. |
| `figures/Figure2_collocation_en.png` | Figure (PNG, full resolution): collocation network, English. |
| `figures/Figure2_collocation_hi.pdf` | Figure (PDF, full resolution): collocation network, Hindi. |
| `figures/Figure2_collocation_hi.png` | Figure (PNG, full resolution): collocation network, Hindi. |
| `figures/FigureB1a_collocation_hi.png` | Figure (PNG, full resolution): appendix B: collocates of Hindi headwords. |
| `figures/FigureB1b_collocation_en.png` | Figure (PNG, full resolution): appendix B: collocates of English headwords. |
| `figures/G10_worked_example.pdf` | Figure (PDF, full resolution): worked example of a chosen and a forced dative (constructed sentences). |
| `figures/G10_worked_example.png` | Figure (PNG, full resolution): worked example of a chosen and a forced dative (constructed sentences). |
| `figures/G1_study_design.pdf` | Figure (PDF, full resolution): study design: corpus, development / confirmatory split, instruments, outputs, robustness. |
| `figures/G1_study_design.png` | Figure (PNG, full resolution): study design: corpus, development / confirmatory split, instruments, outputs, robustness. |
| `figures/G2_sankey.pdf` | Figure (PDF, full resolution): flow of clauses from the corpus to eligible relational sites. |
| `figures/G2_sankey.png` | Figure (PNG, full resolution): flow of clauses from the corpus to eligible relational sites. |
| `figures/G3_decomposition_waterfall.pdf` | Figure (PDF, full resolution): waterfall of the gap: forced, opportunity and choice shares. |
| `figures/G3_decomposition_waterfall.png` | Figure (PNG, full resolution): waterfall of the gap: forced, opportunity and choice shares. |
| `figures/G4_choice_bootstrap_density.pdf` | Figure (PDF, full resolution): bootstrap distribution of the choice share. |
| `figures/G4_choice_bootstrap_density.png` | Figure (PNG, full resolution): bootstrap distribution of the choice share. |
| `figures/G5_robustness_forest.pdf` | Figure (PDF, full resolution): Run 2 odds ratio and choice share across the main analysis and robustness checks. |
| `figures/G5_robustness_forest.png` | Figure (PNG, full resolution): Run 2 odds ratio and choice share across the main analysis and robustness checks. |
| `figures/G6_text_component_clustermap.pdf` | Figure (PDF, full resolution): texts by components (column z-scores), clustered. |
| `figures/G6_text_component_clustermap.png` | Figure (PNG, full resolution): texts by components (column z-scores), clustered. |
| `figures/G7_lexicon_overlap_heatmap.pdf` | Figure (PDF, full resolution): overlap of Hindi and English lexicon entries in component space. |
| `figures/G7_lexicon_overlap_heatmap.png` | Figure (PNG, full resolution): overlap of Hindi and English lexicon entries in component space. |
| `figures/G8_component_networks.pdf` | Figure (PDF, full resolution): component co-occurrence networks per language. |
| `figures/G8_component_networks.png` | Figure (PNG, full resolution): component co-occurrence networks per language. |
| `figures/G9_audit_slopes.pdf` | Figure (PDF, full resolution): machine-reader scores against human-rated intensity, by language. |
| `figures/G9_audit_slopes.png` | Figure (PNG, full resolution): machine-reader scores against human-rated intensity, by language. |
| `figures/captions.md` | Captions of figures F2-F9 with their source tables. |
| `lexicon/components.csv` | The K = 24 semantic components: gloss in NSM primes, status, entry counts per language and carrier entries; corpus example sentences removed. |
| `lexicon/entry_vectors.csv` | Binary component vector (24 components + names_emotion) for every lexicon entry. |
| `lexicon/flag_components.csv` | Grammatical flags (dative and related constructions) with the entries and components they carry and the eligibility rule they feed. |
| `lexicon/lexicon.csv` | Lexicon v0.2: 205 entries (96 Hindi, 109 English) with NSM explication, component vector, orientation, process, function, register, cultural script, grammar_forced flag, counterpart and matching pattern; corpus example sentences removed. |
| `lexicon/molecules.csv` | Semantic molecules allowed in explications ([m]), where they are used and why they are needed. |
| `lexicon/primes.csv` | NSM semantic primes with their Hindi exponents, allolexes, polysemy notes, constructed test sentences and confidence. |
| `results/HEADLINE.md` | One-page summary of the headline numbers and pre-registered directions. |
| `results/REPORT.md` | Full results report for outputs 1-9, with deviations and robustness sections. |
| `results/a1_entry_classes.csv` | Audit 1: translatability class of every Hindi lexicon entry (frozen lexicon v0.2). |
| `results/a1_resource_recall.csv` | Audit 1: recall of translation-based resources (NRC-Hindi, WordNet route) against the Hindi gold clauses, per entry class. |
| `results/a1_scoring_summary.csv` | Audit 1: summary of the resource-scoring run (items, pools, status). |
| `results/agreement/agreement_summary_gold_components_v1.csv` | Output 1: agreement on the component sheet, per component. |
| `results/agreement/agreement_summary_gold_pilot.csv` | Output 1: agreement on the pilot sheet. |
| `results/agreement/agreement_summary_gold_sheet_v1.csv` | Output 1: agreement between the two coders on the gold sheet (per field: units, agreement, Krippendorff's alpha). |
| `results/agreement/confusion_gold_components_v1.csv` | Output 1: coder-by-coder confusion counts, component sheet. |
| `results/agreement/confusion_gold_pilot.csv` | Output 1: coder-by-coder confusion counts, pilot sheet. |
| `results/agreement/confusion_gold_sheet_v1.csv` | Output 1: coder-by-coder confusion counts, gold sheet. |
| `results/audit_calibration.csv` | Audit 2: calibration of human intensity ratings (rater means per passage pair, aggregated). |
| `results/audit_calibration_correlation.csv` | Audit 2: correlation between the calibration ratings and the main ratings. |
| `results/audit_lmer.csv` | Audit 2: mixed-model coefficients per machine reader (Hindi under-reading at equal rated intensity; Hindi x cue). |
| `results/audit_rating_agreement.csv` | Audit 2: agreement between the two human intensity ratings. |
| `results/audit_stability.csv` | Audit 2: stability-selection frequencies of the components each machine reader under-reads. |
| `results/collocation_pmi.csv` | Output 9: collocates of grief lexicon headwords with PMI scores (word-level, no sentences). |
| `results/corrected_rates_confirmatory.csv` | Output 2b: observed and Rogan-Gladen corrected rates per measure and language, confirmatory split. |
| `results/corrected_rates_confirmatory_hi_minus_en.csv` | Output 2b: Hindi - English differences in corrected rates, confirmatory split. |
| `results/corrected_rates_dev.csv` | Output 2b: observed and corrected rates per measure and language, development split. |
| `results/corrected_rates_dev_hi_minus_en.csv` | Output 2b: Hindi - English differences in corrected rates, development split. |
| `results/decompose_relational_confirmatory.csv` | Output 3: decomposition of the Hindi - English gap into forced, opportunity and choice shares with bootstrap intervals (confirmatory). |
| `results/decompose_relational_confirmatory_drop_largest.csv` | Output 3: the same decomposition without the largest Hindi text, English text, and both. |
| `results/decompose_relational_dev.csv` | Output 3: decomposition on the development split. |
| `results/decompose_relational_dev_drop_largest.csv` | Output 3: development-split decomposition, largest texts dropped. |
| `results/h1_glmm_rF6.csv` | Output 3: R-F6 robustness check (Run 2 without closing-formula clauses). |
| `results/h1_glmm_run1.csv` | Output 3: H1 Run 1 (all finite clauses): GLMM, CR2 and permutation estimates. |
| `results/h1_glmm_run2.csv` | Output 3: H1 Run 2, the pre-registered model (forced relational clauses removed): GLMM, CR2, domain intercept and permutation estimates. |
| `results/h1_glmm_run2b.csv` | Output 3: H1 Run 2b (honorific reference to elders also treated as forced). |
| `results/mcnemar_muril.csv` | Output 8: McNemar test, translated vs native MuRIL classifier on the Hindi gold clauses. |
| `results/optional/a1_component_recall.csv` | Exploratory (not pre-registered): component recall of the translation route. |
| `results/optional/a1_roundtrip_stripped.csv` | Exploratory (not pre-registered): round-trip translation through two open machine-translation systems: which lexicon matches survive (dry run). |
| `results/optional/a1_topic_agreement.csv` | Exploratory (not pre-registered): topic agreement, native vs translated text. |
| `results/optional/decompose_dev.csv` | Exploratory (not pre-registered): decomposition variant on the development split. |
| `results/optional/decompose_dev_drop_largest.csv` | Exploratory (not pre-registered): the same, largest texts dropped. |
| `results/optional/feel_rates.csv` | Exploratory (not pre-registered): rates of 'feel' constructions per language. |
| `results/optional/p1_pos_logodds.csv` | Exploratory (not pre-registered): part-of-speech log-odds, Hindi vs English. |
| `results/optional/p1_pos_profile.csv` | Exploratory (not pre-registered): part-of-speech profiles per language. |
| `results/optional/p1_we_i.csv` | Exploratory (not pre-registered): first-person plural vs singular rates. |
| `results/optional/p2_beta.csv` | Exploratory (not pre-registered): beta-regression variant of P2. |
| `results/optional/p2_component_logodds.csv` | Exploratory (not pre-registered): component log-odds with an informative Dirichlet prior. |
| `results/optional/p2_component_profile.csv` | Exploratory (not pre-registered): component profiles per language. |
| `results/optional/p2_naming_share.csv` | Exploratory (not pre-registered): share of emotion-naming matches. |
| `results/optional/p2_residue.csv` | Exploratory (not pre-registered): matches outside the component inventory. |
| `results/optional/table3_validation.md` | Exploratory (not pre-registered): validation table variant. |
| `results/optional/validation_alpha.csv` | Exploratory (not pre-registered): alpha variant. |
| `results/optional/validation_table.csv` | Exploratory (not pre-registered): validation variant. |
| `results/p1_choice.csv` | Output 6 (P1): chosen-dative rate against the forced baseline, binomial test with Holm correction. |
| `results/p2_jsd.csv` | Output 7 (P2): Jensen-Shannon divergence between the Hindi and English component profiles. |
| `results/power/choice_share_power.csv` | Power analysis for the choice share (simulation). |
| `results/power/run2_power.csv` | Power analysis for the Run 2 odds ratio (simulation). |
| `results/robustness/adjudication_macro_f1.csv` | Macro-F1 per field and language: agreed-only gold vs majority-adjudicated gold. |
| `results/robustness/adjudication_output2.csv` | Every output-2 number on the agreed-only gold and on the majority-adjudicated gold. |
| `results/robustness/decompose_relational_original_protocol.csv` | Decomposition on the texts sampled under the original protocol (94 texts). |
| `results/robustness/decompose_relational_original_protocol_drop_largest.csv` | Original-protocol decomposition, largest texts dropped. |
| `results/robustness/decompose_relational_unseen_texts.csv` | Decomposition on texts unseen during instrument development (69 Hindi + 46 English). |
| `results/robustness/decompose_relational_unseen_texts_drop_largest.csv` | Unseen-texts decomposition, largest texts dropped. |
| `results/robustness/h1_glmm_run2_original_protocol.csv` | Run 2 on the original-protocol texts. |
| `results/robustness/h1_glmm_run2_unseen_texts.csv` | Run 2 on the texts unseen during instrument development. |
| `results/rule_table_check.csv` | Output 2: accuracy of the grammar_forced and dative_alternative_available rules against the gold set, with 95% intervals. |
| `results/synthetic/SYNTHETIC.md` | Synthetic-data run: how the synthetic inputs were made; numbers here are not results. |
| `results/synthetic/a1_resource_recall.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/agreement/agreement_summary_gold_components_v1.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/agreement/agreement_summary_gold_sheet_v1.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/audit_lmer.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/audit_stability.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/collocation_pmi.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/corrected_rates.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/corrected_rates_hi_minus_en.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/decompose_relational_dev.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/decompose_relational_dev_drop_largest.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_rF6.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_rF6_rival.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_run1.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_run1_rival.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_run2.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_run2_rival.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_run2b.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/h1_glmm_run2b_rival.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/mcnemar_muril.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/p1_choice.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/p2_component_logodds.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/p2_component_profile.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/p2_jsd.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output1_agreement.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output2_validation.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output3_hypothesis.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output4_rival_check.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output5_audit.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output6_dative_choice.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output7_jsd.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output8_translation.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/tables_full/Output9_collocation.md` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/synthetic/validation_table.csv` | Synthetic-data run of the same pipeline (pipeline check, not a result). |
| `results/table3_validation.md` | Table 3: dictionary-channel validation (precision, recall, F1) against the gold set. |
| `results/tables/Output1_agreement.md` | Output table (compact): inter-coder agreement. |
| `results/tables/Output2_validation.md` | Output table (compact): dictionary-channel validation. |
| `results/tables/Output3_hypothesis.md` | Output table (compact): H1 models and decomposition. |
| `results/tables/Output4_rival_check.md` | Output table (compact): rival-explanation check. |
| `results/tables/Output5_audit.md` | Output table (compact): machine-reader audit. |
| `results/tables/Output6_dative_choice.md` | Output table (compact): dative choice (P1). |
| `results/tables/Output7_jsd.md` | Output table (compact): component-profile divergence (P2). |
| `results/tables/Output8_translation.md` | Output table (compact): translation audit. |
| `results/tables/Output9_collocation.md` | Output table (compact): collocations. |
| `results/tables_full/Output1_agreement.md` | Output table (full): inter-coder agreement. |
| `results/tables_full/Output2_validation.md` | Output table (full): dictionary-channel validation. |
| `results/tables_full/Output3_hypothesis.md` | Output table (full): H1 models and decomposition. |
| `results/tables_full/Output4_rival_check.md` | Output table (full): rival-explanation check. |
| `results/tables_full/Output5_audit.md` | Output table (full): machine-reader audit. |
| `results/tables_full/Output6_dative_choice.md` | Output table (full): dative choice (P1). |
| `results/tables_full/Output7_jsd.md` | Output table (full): component-profile divergence (P2). |
| `results/tables_full/Output8_translation.md` | Output table (full): translation audit. |
| `results/tables_full/Output9_collocation.md` | Output table (full): collocations. |
| `results/validation_alpha.csv` | Output 2: Krippendorff's alpha per gold field and language. |
| `results/validation_table.csv` | Output 2: precision, recall, F1 and false-positive rate of the dictionary channel per field, value and language. |
| `rule_table.csv` | Predicate rule table (316 rules: 174 Hindi, 142 English): for each emotion predicate, the site, the forced / chosen decision, the alternative frame, the rule and its source; generated from src/analysis/eligibility.py (predicates first observed in the corpus are not listed). |
