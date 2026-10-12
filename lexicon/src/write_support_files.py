import csv, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from entries_hi import HI
from entries_en import EN
OUT = pathlib.Path(__file__).resolve().parent / "out"
by = {e["entry_id"]: e for e in HI + EN}

FLAGS = [
 ("F1", "dative_experiencer", "L-HI-C1 L-HI-07 L-HI-10 P-HI-04 P-HI-05 P-HI-09 P-HI-48 P-HI-49 P-HI-50", "HAPPEN_TO", "Y",
  "", "chosen if a nominative predication with the same emotion noun/adjective exists (मैं दुखी हूँ, मैं रोया) and was available in context; forced for याद आना, कमी खलना, नींद न आना (no nominative alternative)", "v0.1 §4"),
 ("F2", "honorific_plural_deceased", "L-HI-C2 L-HI-12", "KIN", "context",
  "respect", "forced for a parent/elder referent; chosen for a younger deceased (sibling, child, friend) where singular agreement was available", "v0.1 §4; Plan v3 N1 step 2"),
 ("F3", "motion_euphemism", "L-HI-13 L-HI-14 L-HI-16 P-HI-52 P-HI-53 P-HI-54 P-HI-58 L-EN-12 L-EN-14 L-EN-15 L-EN-19 P-EN-54 P-EN-58", "NOT_HERE; AVOID_DIE", "N",
  "", "always chosen: a direct verb (मर गए / died) was available", "v0.1 §4"),
 ("F4", "event_noun_death", "L-HI-15 L-EN-16", "NOT_HERE; AVOID_DIE", "N", "", "chosen", "v0.1 §4"),
 ("F5", "negated_existence", "L-HI-12 P-HI-55 P-HI-59 L-EN-13 P-EN-55", "NOT_HERE; AVOID_DIE", "N", "", "chosen", "v0.1 §3.7"),
 ("F6", "closing_formula", "L-HI-26 L-HI-03 P-HI-24 P-HI-25 P-HI-38 P-HI-57 L-EN-23 P-EN-14 P-EN-24 P-EN-38", "RITUAL_WORDS", "N",
  "", "chosen; stripped in the H1 ritual run (A3.1 Run 2)", "v0.1 §4"),
 ("F7", "vocative_address_deceased", "L-HI-C3 P-EN-C3 P-HI-26 P-EN-26", "SPEAK_TO_DEAD", "N", "", "chosen", "v0.1 §4"),
 ("F8", "divine_agency", "P-HI-19 P-HI-20 P-EN-19 P-EN-20", "ABOVE", "N", "target=God", "chosen", "recommendation N1 (script = divine-agency)"),
 ("F9", "kin_term_for_deceased", "(kin lexicon in constructions.yaml)", "KIN", "context",
  "", "forced where Hindi has no neutral alternative to the kin noun for an elder (a bare name for a parent is unavailable); chosen where a pronoun or name was available (English: 'my father' vs 'he')", "Plan v3 P8b"),
 ("F10", "plural_self_reference", "P-EN-71 P-HI-31 P-HI-32", "WITH_OTHERS; KIN", "N",
  "", "chosen (singular alternative available); NB Hindi हम can be singular in eastern varieties: code via the codebook, not the flag", "research plan §5.1"),
 ("F11", "direct_death_reference", "P-HI-60 P-EN-60", "NOT_HERE", "N", "names_direct", "control flag: denominator for the indirect share", "new"),
 ("F12", "names_emotion", "(lexicon rows with pos = noun and FEEL_BAD)", "(form flag, outside K)", "N", "", "used by H4 naming vs narrating", "recommendation N1 (NAME-EMOTION moved out of the vector)"),
]
with open(OUT / "flag_components.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["flag_id", "flag_name", "entry_ids", "components", "grammar_forced", "sub_flag", "eligibility_rule_N2", "source"])
    w.writerows(FLAGS)

KIN_HI = ["माँ","मम्मी","माता","माताजी","अम्मा","अम्मी","पापा","पिता","पिताजी","बाबूजी","बाबा","अब्बू","अब्बा","दादी","दादा","दादाजी","नानी","नाना","नानाजी",
          "भाई","भैया","भाईसाहब","बहन","दीदी","बेटा","बेटी","पति","पत्नी","चाचा","चाची","मामा","मामी","बुआ","मौसी","ताऊ","ताई","दोस्त","सहेली"]
KIN_EN = ["mother","mom","mum","mummy","ma","maa","amma","ammi","father","dad","daddy","papa","appa","abbu","grandmother","grandma","dadi","nani","grandfather","grandpa","dada","nana",
          "brother","bhai","bhaiya","sister","didi","son","daughter","husband","wife","uncle","aunt","aunty","chacha","chachi","mama","mami","bua","mausi","friend","best friend"]

def yq(s): return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
lines = ["# constructions.yaml — construction flags for P8 (regex with explicit Devanagari boundary classes; never \\b)",
         "# Text is NFC-normalised before matching; precomposed nukta letters decompose, so patterns write the nukta as optional \\u093C.",
         "# Every pattern here is copied from lexicon.csv so that the two never drift; lexicon.csv is canonical.",
         "version: 0.2", "status: proposed", "boundary_left: " + yq(r"(?<![ऀ-ॣ०-९ॱ-ॿ‌‍A-Za-z0-9_'])"),
         "boundary_right: " + yq(r"(?![ऀ-ॣ०-९ॱ-ॿ‌‍A-Za-z0-9_'])"), "", "flags:"]
for fid, name, ids, comps, gf, sub, elig, src in FLAGS:
    lines += [f"  - id: {fid}", f"    name: {name}", f"    components: [{', '.join(c.strip() for c in comps.split(';')) if not comps.startswith('(') else ''}]",
              f"    grammar_forced: {yq(gf)}", f"    sub_flag: {yq(sub)}", f"    eligibility_rule: {yq(elig)}", f"    source: {yq(src)}", "    patterns: []" if not any(e in by and by[e]["pattern"] for e in ids.split()) and fid != "F9" else "    patterns:"]
    for eid in ids.split():
        if eid in by and by[eid]["pattern"]:
            lines.append(f"      - entry_id: {eid}")
            lines.append(f"        lang: {by[eid]['lang']}")
            lines.append(f"        regex: {yq(by[eid]['pattern'])}")
    if fid == "F9":
        lines.append("      - entry_id: KIN-HI"); lines.append("        lang: hi")
        lines.append("        regex: " + yq(r"(?<![ऀ-ॣ०-९ॱ-ॿ‌‍A-Za-z0-9_'])(?:" + "|".join(KIN_HI) + r")(?:जी)?(?![ऀ-ॣ०-९ॱ-ॿ‌‍])"))
        lines.append("      - entry_id: KIN-EN"); lines.append("        lang: en")
        lines.append("        regex: " + yq(r"(?<![A-Za-z'])(?:" + "|".join(k.replace(" ", r"\s+") for k in KIN_EN) + r")(?:s|'s)?(?![A-Za-z])"))
    lines.append("")
lines += ["matcher_rules:",
  "  - id: R1", "    rule: \"A clause vector is the elementwise OR of matched entry vectors and flag vectors (Plan v3 N1 step 3).\"",
  "  - id: R2", "    rule: \"Components tagged (grammar) on a construction (HAPPEN_TO from F1, KIN from F2) are written to a separate grammar_forced vector and are not counted as chosen orientation evidence.\"",
  "  - id: R3", "    rule: \"Negation flips duty: सेवा / देखभाल / care with a negated opportunity (अवसर नहीं, नहीं कर पाया, never got to, couldn't) scores DUTY_UNDONE instead of DUTY_DONE; 'never got to say goodbye' scores DUTY_UNDONE.\"",
  "  - id: R4", "    rule: \"Exclusions for prime-form polysemy: pronoun + लोग (हम लोग, आप लोग) is not PEOPLE; 'के पास' possessive is not NEAR; deontic चाहिए is not WANT; N + करना conjunct verbs are not DO; शायद ही is not MAYBE.\"",
  "  - id: R5", "    rule: \"Bare 'passed', bare 'gone' and मरना in hyperbole (शर्म से मर गई) are matched but routed to human review (review_queue = Y) before counting.\"",
  "  - id: R6", "    rule: \"names_emotion (F12) is set when the clause matches a lexicon row with pos beginning 'noun' and FEEL_BAD in its vector; it is a form flag outside the K vector.\"",
  "  - id: R7", "    rule: \"The indirect_death_reference share = clauses matching F3/F4/F5/F16-type euphemisms over (those + F11 direct forms), per language.\"",
  "  - id: R8", "    rule: \"Honorific plural (F2): the pattern matches pronoun forms only; singular reference must be confirmed from the Stanza parse (P7) or by the coder before KIN + respect is scored.\"",
]

BL, BR = r"(?<![ऀ-ॣ०-९ॱ-ॿ‌‍A-Za-z0-9_'])", r"(?![ऀ-ॣ०-९ॱ-ॿ‌‍A-Za-z0-9_'])"
DAT_PRON = ["मुझे", "मुझको", "हमें", "हमको", "उन्हें", "उनको", "उसे", "उसको", "आपको", "तुम्हें", "तुमको", "तुझे", "तुझको",
            "इन्हें", "इनको", "इसे", "इसको"]
DAT_VERB = ["हुआ", "हुई", "हुए", "होता", "होती", "लगता", "लगती", "लगा", "लगी", "आता", "आती", "आते", "आया", "आई", "आयी",
            "रहा", "रही", "रहे"]
GA_PL = r"ग(?:ए|ये|ईं|यीं)"
SHANTI = r"शा(?:ं|ँ|न्)ति"
STAGE4 = [
 ("S4-01", "dative_regex", "F1", "hi",
  BL + "(?:" + "|".join(DAT_PRON) + ")" + BR + r"[^।\n]*?" + BL + "(?:" + "|".join(DAT_VERB) + ")" + BR,
  "finite_dative",
  "dative pronoun followed later in the clause by an experiencer verb form; the form must be a clause head or its "
  "aux/cop/compound and must not directly follow a -ते/-कर/-ए verb (देखते हुए is a converb, not a predicate)"),
 ("S4-03", "motion_euphemism", "F3", "hi",
  BL + r"(?:(?<!ता\s)(?<!ते\s)(?<!ती\s)चल[ेी]\s+" + GA_PL + r"|गुज़?र\s+" + GA_PL + r"|छोड़?\s+" + GA_PL + ")" + BR,
  "no_destination",
  "honorific-plural motion verbs: चले गए / चली गईं / गुज़र गए / छोड़ गए (+ गये/गयीं spellings); not after a "
  "-ता/-ते/-ती participle (बदलती चली गईं = aspectual 'kept changing'); चले/चली गए with a destination "
  "(बाज़ार चले गए, घर को, बाहर) is literal motion and is not counted"),
 ("S4-04", "closing_formula", "F6", "hi",
  BL + r"(?:आत्मा\s+को\s+" + SHANTI + r"|(?:ॐ|ओम्?)\s*" + SHANTI + r"|श्रद्धा(?:ं|ँ)जलि|नमन)" + BR,
  "", "आत्मा को शांति / ॐ शांति / श्रद्धांजलि / नमन"),
 ("S4-05", "motion_euphemism", "F3", "en",
  BL + r"(?i:pass(?:ed|es|ing)\s+away|pass(?:ed|es|ing)\s+on(?!\s+(?:the|a|an|his|her|my|our|their|this|that|it|to|these|those)(?![A-Za-z]))"
  r"|left\s+us(?!\s+(?:a|an|the|some|any|no|his|her|my|our|their|with|alone)(?![A-Za-z])))" + BR,
  "", "passed away / passed on (not + object) / left us (not + object or 'alone')"),
 ("S4-05b", "motion_euphemism", "F3", "en",
  BL + r"(?i:(?:is|was|are|were|be|been|[A-Za-z]+['’]s)\s+gone|gone\s+(?:too\s+soon|forever))" + BR,
  "animate_subject", "is gone / gone too soon|forever, only with a person subject (not 'the pain is gone')"),
 ("S4-06", "no_more", "F5", "en",
  BL + r"(?i:(?:is|was|are|were)\s+no\s+more)(?!\s+(?:than|[A-Za-z]+ing)(?![A-Za-z]))" + BR,
  "", "is/was no more (English counterpart of नहीं रहे); not 'no more than' or 'no more + -ing noun'"),
 ("S4-07", "closing_formula", "F6", "en",
  BL + r"(?:(?i:rest\s+in\s+peace|may\s+(?:her|his|their|your)\s+soul)|RIP|R\.I\.P\.?)" + BR,
  "", "rest in peace / RIP (upper case only) / may her|his soul"),
]
DATIVE_PARSE = {
 "pronouns": DAT_PRON,
 "deprels": ["iobj", "obl", "nsubj"],
 "feel_verb_stems": ["लग", "खल", "सता", "भा", "अखर", "चुभ", "सूझ"],
 "light_verbs": ["हो", "आ", "रह", "पड", "मिल"],
 "feel_words": ["दुख", "दुःख", "गम", "अफसोस", "याद", "गुस्सा", "क्रोध", "डर", "भय", "चिंता", "फिक्र", "तकलीफ", "पीडा",
                "दर्द", "खुशी", "शर्म", "सदमा", "हैरानी", "आश्चर्य", "बुरा", "अच्छा", "रोना", "रुलाई", "हँसी", "हंसी", "नींद",
                "चैन", "परेशानी", "एहसास", "अहसास", "महसूस", "कमी", "प्यार", "मोह", "पछतावा", "ग्लानि", "बेचैनी", "घबराहट",
                "उदासी", "अकेलापन", "सुकून", "तसल्ली", "संतोष", "धक्का", "झटका", "पसंद", "दुखी", "उदास"],
 "body_state_words": ["कैंसर", "बीमारी", "बुखार", "चोट", "दौरा", "अटैक", "लकवा", "संक्रमण", "कोरोना", "कोविड", "टीबी",
                      "मधुमेह", "डायबिटीज", "निमोनिया", "पीलिया", "खांसी", "खाँसी", "जुकाम", "सर्दी", "बेहोशी", "थकान"],
}
FILTERS = {
 "finite_dative": {"pronouns": DAT_PRON, "verbs": DAT_VERB, "aux_deprels": ["aux", "aux:pass", "cop", "compound"],
                   "participle_endings": ["ते", "कर", "ए"]},
 "no_destination": {"motion_stems": ["चले", "चली"],
                    "destination_case_markers": ["को", "में", "तक"],
                    "destination_adverbs": ["बाहर", "अंदर", "भीतर", "वापस", "घर"],
                    "bare_noun_max_distance": ["2"],
                    "otherworld_nouns": ["दुनिया", "संसार", "लोक", "परलोक", "धाम", "स्वर्ग", "जहान", "बैकुंठ"],
                    "time_nouns": ["साल", "सालों", "वर्ष", "वर्षों", "बरस", "बरसों", "दिन", "दिनों", "महीने", "महीना",
                                   "महीनों", "हफ्ते", "हफ्तों", "सप्ताह", "सप्ताहों", "सुबह", "शाम", "रात", "रातों",
                                   "दोपहर", "समय", "वक्त", "बार", "आज", "कल", "घंटे", "घंटों", "पल", "क्षण"]},
 "animate_subject": {"pronouns": ["he", "she", "they", "you", "i", "we"], "kin": KIN_EN},
}
lines += ["", "# Stage 4 clause flags (src/analysis/flags.py), added 2026-10-09. They extend F1/F3/F5/F6 without",
          "# changing them; matched on clause_text, then checked against the Stanza parse when `filter` is set",
          "# (parameters in stage4_filters). Columns not defined for a language are left empty (n/a).",
          "# Honorific reference to the deceased (F2) is not a Stage 4 flag: it is computed in the referent stage",
          "# from verb agreement, because a pronoun-list regex cannot tell honorific from plural reference.",
          "stage4_flags:"]
for sid, col, ext, lang, rx, flt, note in STAGE4:
    lines += [f"  - id: {sid}", f"    column: {col}", f"    extends: {ext}", f"    lang: {lang}",
              f"    regex: {yq(rx)}", f"    filter: {yq(flt)}", f"    note: {yq(note)}"]
lines += ["", "stage4_filters:"]
for name, params in FILTERS.items():
    lines.append(f"  {name}:")
    for k, v in params.items():
        lines.append(f"    {k}: [{', '.join(yq(x) for x in v)}]")
lines += ["", "# dative_parse (hi): a dative pronoun in the clause whose dependency relation is one of `deprels` (Stanza's",
          "# Hindi model labels dative experiencers nsubj) and whose head is a psych predicate: a verb whose form starts",
          "# with a feel_verb_stem, a feel_word itself, or a light verb with a feel_word or body_state_word dependent.",
          "# Nukta is ignored.",
          "stage4_dative_parse:"]
for k, v in DATIVE_PARSE.items():
    lines.append(f"  {k}: [{', '.join(yq(x) for x in v)}]")
lines += ["", "stage4_placeholders: [grammar_forced, dative_alternative_available]  # null until the eligibility detector"]
(OUT / "constructions.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

CHANGELOG = """# CHANGELOG — lexicon v0.1 → v0.2 (2026-09-26)

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
"""
(OUT / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")

README = """# lexicon/ — Bilingual grief lexicon v0.2 (Plan v3 layout)

| File | What | Canonical for |
|---|---|---|
| `lexicon.csv` | 205 entries (96 hi, 109 en) in Plan v3 L2 column order + `component_vector`, `lang`, `status`; constructions carry `pattern` | L2, L4 matcher |
| `primes.csv` | 65 primes, proposed Hindi exponents, allolexes, polysemy, two canonical-context test sentences, confidence, v0.1 exponent for comparison | L3 |
| `components.csv` | K = 24 components in prime language with examples, status, carrier counts and carriers | L6, N1 |
| `entry_vectors.csv` | entry × component binary matrix + `names_emotion` form flag | L6, N1 |
| `flag_components.csv` | construction flags → components, grammar_forced, sub-flags, N2 eligibility rule | N1 step 2, P8b |
| `constructions.yaml` | the same flags with their regexes (copied from lexicon.csv), kin lexicons, matcher rules R1–R8 | P8 |
| `molecules.csv` | every semantic molecule used, where, and why; tolerated non-prime words with reasons | L2 rule |
| `CHANGELOG.md` | every v0.1 entry touched and why; component changes | — |
| `src/` | the Python sources that regenerate every CSV (`python src/build_v02.py`), plus the checker (`--check`) | reproducibility |
| `scripts/` | embedding protocol (4 scripts + helper) and the component classifier; real models named in each header, not downloaded here | Recommendation Part 2 |
| `docs/` | draft document (prime table narrative, protocol, classifier spec, validation checklist) and the v0.1 file | — |

Status: everything `proposed`. Nothing here is a result; `corpus_freq_*` are blank until ground_entries.py is run on the corpus and the numbers are copied in by hand with the corpus version.

Checks the build enforces: prime-only explications (molecules marked [m]); 2–8 lines; every tag traceable to a line (R ⇐ RITUAL_WORDS; F ⇐ KIN/BOND; C ⇐ WITH_OTHERS/EVERYONE/HONOUR; FEEL_BAD ⇐ a feel line; AVOID_DIE ⇐ the die line; ABOVE ⇐ an above line); no two entries in a language share an explication; counterpart ids exist and overlap is symmetric; every pattern compiles, uses no `\\b`, and matches its own example.
"""
(OUT / "README.md").write_text(README, encoding="utf-8")
print("support files written")
