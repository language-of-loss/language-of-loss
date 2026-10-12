import csv
from pathlib import Path

import pytest

import eligibility as E

HERE = Path(__file__).resolve().parent
with open(HERE / "eligibility_sentences.csv", encoding="utf-8", newline="") as fh:
    ROWS = list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def nlp():
    stanza = pytest.importorskip("stanza")
    try:
        return {lg: stanza.Pipeline(lg, processors=p, download_method=None, verbose=False)
                for lg, p in (("hi", "tokenize,pos,lemma,depparse"), ("en", "tokenize,mwt,pos,lemma,depparse"))}
    except Exception as e:
        pytest.skip(f"Stanza models unavailable: {e}")


def test_sentence_file_covers_the_brief():
    hi = [r["decision"] for r in ROWS if r["lang"] == "hi"]
    assert len(hi) == 29 and {"forced_dative", "chosen_dative", "forced_nominative", "chosen_nominative", "review",
                              "NA"} == set(hi)
    assert sum(r["rule_id"].startswith("HI-N") and r["decision"] != "NA" for r in ROWS) >= 10


@pytest.mark.parametrize("row", ROWS, ids=[f"{r['lang']}-{i + 2}" for i, r in enumerate(ROWS)])
def test_sentences(row, nlp):
    got = E.classify_text(row["sentence"], row["lang"], nlp[row["lang"]])[0]
    assert (got["decision"], got["predicate"], got["rule_id"]) == (row["decision"], row["predicate"], row["rule_id"])


def test_rule_table_is_consistent():
    keys = [k for _, ks, *_ in E.HI_RULES for k in ks]
    assert len(keys) == len(set(keys)), "a Hindi predicate key is in two rules"
    assert all(dec in ("forced", "chosen", "review") for _, _, dec, *_ in E.HI_RULES)
    assert all("़" not in k for k in keys), "keys must be nukta-free"
    for rid, _, dec, *_ in E.HI_RULES:
        assert rid[3] == {"forced": "F", "chosen": "C", "review": "R"}[dec], rid
    inv = E.inventory_rows()
    assert {r["lang"] for r in inv} == {"hi", "en"} and all(r["rule_id"] and r["decision"] for r in inv)


def test_specific_row_beats_bare_verb():
    assert E.HI_PRED["लग"][1] == "forced" and E.HI_PRED["डर+लग"][1] == "chosen"


def test_nominative_table_follows_its_dative_twin():
    assert not set(E.HI_NOM) & set(E.HI_PRED), "a key is both a dative and a nominative predicate"
    assert all("़" not in k for k in E.HI_NOM)
    for k, (rid, twin, dec) in E.HI_NOM.items():
        assert twin is None or twin in E.HI_PRED, (k, twin)
        assert dec == E.nom_decision(twin)
        if dec == "chosen_nominative":
            assert E.HI_PRED[twin][1] == "chosen"
    assert E.HI_NOM["याद+कर"][2] == "forced_nominative"
    assert E.HI_NOM["महसूस+कर"][2] == "review"
    assert "जान" not in E.HI_NOM and E.HI_PRED["पता+हो"][1] == "forced"
    assert "दर्द+कर" not in E.HI_NOM and "तसल्ली+कर" not in E.HI_NOM
    inv = [r for r in E.inventory_rows() if r["site"] == "nominative"]
    assert len(inv) == len(E.HI_NOM)


def test_recovered_subject_from_referents():
    sent = {1: dict(token_index=1, token="बहुत", lemma="बहुत", upos="ADV", feats="", head=2, deprel="advmod"),
            2: dict(token_index=2, token="उदास", lemma="उदास", upos="ADJ", feats="", head=0, deprel="root"),
            3: dict(token_index=3, token="थी", lemma="था", upos="AUX", feats="VerbForm=Fin", head=2, deprel="cop")}
    ref = dict(subject_text="माँ", subject_source="antecedent", referent_class="deceased")
    got = E.classify("hi", [1, 2, 3], sent, ref)[0]
    assert (got["decision"], got["subject_source"], got["site"]) == ("chosen_nominative", "antecedent", "∅→माँ")
    got = E.classify("hi", [1, 2, 3], sent, dict(ref, referent_class="impersonal"))[0]
    assert got["rule_id"] == "HI-NA-NOM-NOSUBJ"


def test_flag_values():
    row = lambda d: dict(site="x", predicate="p", decision=d, rule_id="r")
    assert E.flag_values([row("forced_dative")]) == (True, False)
    assert E.flag_values([row("chosen_dative")]) == (False, True)
    assert E.flag_values([row("forced_dative"), row("chosen_dative")]) == (True, True)
    assert E.flag_values([row("chosen_nominative")]) == (None, None)
    assert E.flag_values([row("forced_nominative")]) == (None, None)
    assert E.flag_values([row("review")]) == (None, None)
    assert E.flag_values([row("NA")]) == (None, None)


def test_english_rule_mirrors_hindi():
    assert E.en_decision("nominative", "devastated") == "chosen_nominative"
    assert E.en_decision("stimulus", "devastate") == "chosen_impersonal"
    assert E.en_decision("nominative", "miss") == "forced_nominative"
    assert E.en_decision("impersonal", "unbearable") == "forced_impersonal"
    assert E.en_decision("review", "move") == "review"
    assert "afraid" not in E.EN_TWIN
    inv = {r["predicate"]: r for r in E.inventory_rows() if r["lang"] == "en"}
    assert inv["devastated"]["twin"] == "EN-T01" and "it devastated me" in inv["devastated"]["alternative"]
    assert inv["miss"]["twin"] == "" and inv["miss"]["alternative"] == "none"


def tok(i, token, lemma, upos, head, deprel, feats=""):
    return dict(token_index=i, token=token, lemma=lemma, upos=upos, feats=feats, head=head, deprel=deprel)


def test_pronoun_written_apart_from_ko_is_a_site():
    sent = {1: tok(1, "सब", "सब", "PRON", 4, "nsubj"), 2: tok(2, "को", "को", "ADP", 1, "case"),
            3: tok(3, "पता", "पता", "NOUN", 4, "compound"), 4: tok(4, "था", "था", "AUX", 0, "root")}
    kids = E.children(sent)
    assert E.hi_site_word(sent[1], kids) == "सब को"


def test_converb_object_is_not_promoted_to_the_main_verb():
    sent = {1: tok(1, "तुम्हें", "तुम", "PRON", 2, "obj"), 2: tok(2, "देखते", "देखना", "VERB", 5, "advcl"),
            3: tok(3, "हुए", "होना", "AUX", 2, "aux"), 4: tok(4, "ही", "ही", "PART", 2, "dep"),
            5: tok(5, "लग", "लगना", "VERB", 0, "root"), 6: tok(6, "रहा", "रहना", "AUX", 5, "aux"),
            7: tok(7, "है", "है", "AUX", 5, "aux")}
    rows = E.classify("hi", list(sent), sent)
    assert [r["decision"] for r in rows] == ["NA"] and rows[0]["rule_id"] == "HI-NA-OBJ"


def test_object_experiencer_verb_with_person_object_is_not_nominative():
    sent = {1: tok(1, "I", "I", "PRON", 2, "nsubj"), 2: tok(2, "comforted", "comfort", "VERB", 0, "root"),
            3: tok(3, "mother", "mother", "NOUN", 2, "obj")}
    row = E.classify("en", list(sent), sent)[0]
    assert row["construction"] == "stimulus" and row["site"] == "mother"


def test_unknown_language_is_an_error():
    with pytest.raises(ValueError):
        E.classify("hi-Latn", [1], {1: tok(1, "dukh", "dukh", "NOUN", 0, "root")})


def test_proximal_demonstrative_is_not_a_nominative_person_subject():
    assert "यह" not in E.HI_NOM_PRONOUNS and "इसने" not in E.HI_NOM_PRONOUNS and "वे" in E.HI_NOM_PRONOUNS


def test_body_part_list_has_no_being():
    assert "being" not in E.EN_BODY and "heart" in E.EN_BODY


def test_fill_flags_leaves_unclassified_rows_alone(tmp_path):
    p = tmp_path / "flags.csv"
    p.write_text("clause_id,lang,grammar_forced,dative_alternative_available\n"
                 "a#1,hi,True,False\nb#1,hi,,\n", encoding="utf-8")
    row = dict(site="मुझे", predicate="दुख+हो", decision="chosen_dative", rule_id="HI-C01")
    E.fill_flags(p, {"b#1": [row]})
    got = {r["clause_id"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}
    assert got["a#1"]["grammar_forced"] == "True"
    assert (got["b#1"]["grammar_forced"], got["b#1"]["dative_alternative_available"]) == ("False", "True")


def test_missing_referents_file_stops_the_run(tmp_path):
    with pytest.raises(SystemExit):
        E.load_recovered(None, str(tmp_path / "clauses.jsonl"))
    assert E.load_recovered("", str(tmp_path / "clauses.jsonl")) == {}


def test_sentence_meta_covers_non_finite_clauses():
    clauses = [dict(clause_id="r#1", record_id="r", sent_index=0, is_finite=True),
               dict(clause_id="r#2", record_id="r", sent_index=0, is_finite=False)]
    assert set(E.sentence_meta(clauses)) == {"r#1", "r#2"}


def test_ergative_check_ignores_glued_punctuation():
    words = [tok(1, "उसने,", "वह", "PRON", 3, "nsubj"), tok(2, "बातें", "बात", "NOUN", 3, "obj"),
             tok(3, "कहीं", "कहना", "VERB", 0, "root", "Number=Plur")]
    for pron in ("उसने,", "उसने"):
        ref = dict(referent_class="deceased", overt_pronoun=pron, pronoun_person="3", pronoun_number="sg",
                   honorific="True")
        rows = E.classify_relational("hi", ref, {}, words, "parent", set())
        assert all(r["rule_id"] != "REL-HON-F" for r in rows), pron


@pytest.mark.parametrize("hi,en,status", E.CROSS_LANG_EQUIVALENTS,
                         ids=[f"{h}~{e}" for h, e, _ in E.CROSS_LANG_EQUIVALENTS])
def test_translation_equivalents_carry_the_same_decision_class(hi, en, status):
    h, e = E.hi_decision_class(hi), E.en_decision_class(en)
    if status == "consistent":
        assert h == e, f"inventory gap: {hi} {h} vs {en} {e}"
    elif status == E.ASYM:
        assert (h, e) == ("chosen", "forced"), f"not the declared asymmetry: {hi} {h} vs {en} {e}"
        assert en not in E.EN_TWIN and E.EN_PRED[en][1] in ("SUBJ", "ADJ"), \
            f"{en} has an experiencer-object frame: the pair is a gap, not asymmetric by construction"
    else:
        pytest.fail(f"unknown status {status!r}")


def test_asymmetric_pairs_have_their_hindi_alternative_documented():
    inv = {(r["lang"], r["predicate"]): r for r in E.inventory_rows()}
    for hi, en, status in E.CROSS_LANG_EQUIVALENTS:
        if status == E.ASYM or hi == "सदमा+लग":
            row = inv[("hi", hi)]
            assert row["alternative"] and "E3" in row["source"] and "chosen pair" in row["rule"], hi
            assert "asymmetric by construction" in inv[("en", en)]["equivalent"] or status != E.ASYM, en


def test_equivalent_pairs_are_real_predicates_and_in_the_inventory():
    for hi, en, _ in E.CROSS_LANG_EQUIVALENTS:
        assert (hi in E.HI_PRED or hi in E.HI_NOM) and en in E.EN_PRED, (hi, en)
    inv = E.inventory_rows()
    listed = {(r["lang"], r["predicate"]) for r in inv if r["equivalent"]}
    assert all(("hi", hi) in listed and ("en", en) in listed for hi, en, _ in E.CROSS_LANG_EQUIVALENTS)
    path = E.Path(__file__).resolve().parents[1] / "data" / "processed" / "predicate_inventory.csv"
    if path.exists() and "equivalent" in open(path, encoding="utf-8").readline():
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        assert {(r["lang"], r["predicate"]) for r in rows if r["equivalent"]} >= listed


def test_feel_with_emotion_complement_is_chosen_in_both_languages():
    assert E.hi_decision_class("बुरा+लग") == E.en_decision_class("feel") == "chosen"


def test_non_emotion_datives_are_na():
    for key in ("मिल", "चाहिए", "INF+पड", "INF+हो", "पता+हो", "समझ+आ", "लग", "सूझ", "आ", "दिख"):
        assert E.hi_decision_class(key) == "NA", key
    for key in ("याद+आ", "नींद+आ", "कमी+खल", "कैंसर+हो", "दुख+हो"):
        assert E.hi_decision_class(key) != "NA", key


def test_english_feel_needs_an_emotion_complement():
    def tok(i, token, lemma, upos, head, deprel):
        return dict(token_index=i, token=token, lemma=lemma, upos=upos, feats="", head=head, deprel=deprel)
    sad = {1: tok(1, "I", "I", "PRON", 2, "nsubj"), 2: tok(2, "felt", "feel", "VERB", 0, "root"),
           3: tok(3, "sad", "sad", "ADJ", 2, "xcomp")}
    that = {1: tok(1, "I", "I", "PRON", 2, "nsubj"), 2: tok(2, "felt", "feel", "VERB", 0, "root"),
            3: tok(3, "right", "right", "ADJ", 5, "xcomp"), 4: tok(4, "she", "she", "PRON", 5, "nsubj"),
            5: tok(5, "was", "be", "AUX", 2, "ccomp")}
    assert E.classify("en", list(sad), sad)[0]["decision"] == "chosen_nominative"
    row = E.classify("en", [1, 2], that)[0]
    assert (row["decision"], row["rule_id"]) == ("NA", "EN-NA-NONEMO")


def test_gap_and_asymmetry_are_told_apart():
    with pytest.raises(AssertionError, match="inventory gap"):
        test_translation_equivalents_carry_the_same_decision_class("रोना+आ", "cry", "consistent")
    with pytest.raises(AssertionError):
        test_translation_equivalents_carry_the_same_decision_class("सदमा+लग", "shocked", E.ASYM)
