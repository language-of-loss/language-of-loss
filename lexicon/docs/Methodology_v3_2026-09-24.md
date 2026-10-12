# Methodology v3 (24 September 2026) — as stated by the investigators, with notes appended

Supersedes the analysis sections of proposal v2 for the study design; the data inventory and ISEF precedent list still apply.

## Framing

The English side is English in the Indian context (Indian authors, same society, same losses), so the comparison is between two Indian registers of grief and the object of study is the linguistic medium.

## Core grief lexicon

- A broadly defined dictionary of specific grief words with usage examples, built only from the grief-related vocabulary that appears in our own data (not a full dictionary).
- Definitions written from NSM semantic primes (Wierzbicka) so they transfer across Hindi and English.
- This lexicon is the measurement basis for every other method.

## 1. Lexico-semantic analysis (run on the lexicon)

- Component/word alignment with keywords and trends; how fundamental definitions overlap across the two languages.
- Discourse structure and framing: which discourse moves occur in each language and in what order (from long-form texts).
- Cultural-scripts mapping: flagged lexical items tied back to culture-specific display moves (Wierzbicka).
- Rhetorical move analysis for discourse structure (precedent: the French/Mandarin miscarriage-forum study).
- Religious and relational framing.
- Separating linguistic differences from cultural differences.

## 2. Qualitative analysis (what a statement is doing)

Verb vs adjective use (cf. the English–Russian finding that Russian is more embodied, action-oriented and agentic); loss and circumstantial framing cues; emotional description; religious inference; seeking vs offering support; loss-oriented vs restoration-oriented; level of personal engagement; relational framing; culturally bound idioms of distress.

## 3. Quantitative analysis

- Pronoun counts with contextual framing ("I" can be relational, not only individual).
- Keyword density for assigned words (grief, sadness, love, etc.).
- Collocation net: words in vector/co-occurrence space, mapped in 2D or 3D to see how the derived words spread.
- Emotion classifier, optional: Hindi Subjective Lexicon, NRC, IndicBERT fine-tuned on BHAAV, compared with English semantic emotion classifiers (acknowledged as a common method).

Overall aim: triangulate lexical, qualitative and quantitative analyses.

## Timeline

1. Background quantitative stage: pronoun counts and verb/adjective frequency using existing dictionaries (Hindi Subjective Lexicon, NRC) for simple orientational analysis.
2. Central dictionary development: compiled from various sources and explicated for our specific grief keywords, built on NSM primes.
3. Detailed analysis: run the lexico-semantic, qualitative and quantitative components against the custom dictionary.

---

## Notes (advice, not decisions)

- The plan still needs one primary hypothesis with a failure condition. Recommended: the experiencer-dative hypothesis. Hindi grammar encodes emotion as an event befalling a dative experiencer ("mujhe dukh hua"); English encodes it as a state or act of a nominative subject. Test at clause level whether Hindi writers choose dative/event framings beyond what the grammar obliges (nominative options exist: "main dukhi hoon", "main royi"). If the dative appears only where obligatory, the "circumstantial" difference is structure; if it is chosen where a nominative was available, the medium shapes framing. This extends Wierzbicka's verb-vs-adjective contrast with a third strategy.
- Replace pronoun counts with clause coding: grammatical subject/experiencer (self, kin, community, deceased, God, impersonal), predicate type (state, action, event-befalling, speech), object/target. Handles pro-drop, singular "hum", and "I lost my father" (individual subject, relational object). Doubles as the gold set.
- Keyword density: use rates per 1,000 words and weighted log-odds with an informative prior (Monroe, Colaresi and Quinn 2008), not raw density.
- Lexical-semantic core result to aim for: Hindi lexicalises grief along register and religious lines (shok, gham, dukh, shraddhanjali); English along intensity and duration (grief, sorrow, loss, mourning). NSM explications show overlap and gap.
- Collocation net: ~50k words is too small to train embeddings. Use PMI co-occurrence networks from the data, and optionally project both languages into a pre-trained multilingual space (MuRIL/LaBSE), treating the latter as a finding about the tools (Havaldar et al. 2023: these spaces are Anglocentric).
- Discourse moves: fix an inventory before coding (announcement, circumstances, character of the deceased, memory episodes, regret/guilt, address to the dead, ritual reference, lesson/meaning, blessing/closing); code sequences; compare with transition matrices.
- Linguistic vs cultural: count grammar-forced features (dative experiencer, pro-drop, honorific plural, obligatory formulae) separately from chosen ones; use the same-author Hindi/English pair (hi_018/en_019) as a translation control; hold culture constant by sampling Indian English only.
- Priority if time is short: NSM lexicon, clause-level coding with the dative hypothesis, discourse-move sequences, loss/restoration and seek/offer codes. Supporting: collocation nets, cross-lingual projection. Appendix: emotion classifiers.
- Next concrete output: a one-page codebook (clause roles, move inventory, functional codes) with two examples per code from the seed corpus.
