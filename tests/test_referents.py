import referents as R


def W(i, token, upos, head, deprel, feats="", lemma=None):
    return dict(token_index=i, token=token, lemma=lemma or token, upos=upos, head=head, deprel=deprel, feats=feats)


def run(sentences, lang="hi", relation="", inherit=None):
    clauses, sents, ids = [], {}, {}
    for k, words in enumerate(sentences):
        cid = f"t:1#{k:04d}"
        src = f"t:1#{inherit[k]:04d}" if inherit and k in inherit else None
        clauses.append(dict(clause_id=cid, record_id="t:1", lang=lang, sent_index=k, is_finite=True,
                            clause_text=" ".join(w["token"] for w in words), subject_inherited_from=src))
        sents[("t:1", k)] = {w["token_index"]: w for w in words}
        ids[cid] = [w["token_index"] for w in words]
    return R.classify_text(clauses, sents, ids, R.deceased_terms(relation))


PERF_PL = "Aspect=Perf|Gender=Masc|Number=Sing|Polite=Form|VerbForm=Part"
PERF_SG = "Aspect=Perf|Gender=Masc|Number=Sing|VerbForm=Part"


def test_1_first_person_singular_is_self():
    r = run([[W(1, "मैं", "PRON", 2, "nsubj"), W(2, "रोया", "VERB", 0, "root", PERF_SG)]])[0]
    assert (r["referent_class"], r["overt_pronoun"], r["pronoun_person"], r["pronoun_number"]) == ("self", "मैं", "1", "sg")


def test_2_first_person_plural_is_community_and_not_honorific():
    r = run([[W(1, "हम", "PRON", 2, "nsubj"), W(2, "गए", "VERB", 0, "root", PERF_PL)]])[0]
    assert r["referent_class"] == "community" and r["pronoun_number"] == "pl" and r["honorific"] is False


def test_3_deceased_kin_with_plural_agreement_is_honorific():
    r = run([[W(1, "पापा", "NOUN", 2, "nsubj", "Number=Sing"), W(2, "चले", "VERB", 0, "root"),
              W(3, "गए", "AUX", 2, "aux", PERF_PL)]], relation="father (Papa)")[0]
    assert r["referent_class"] == "deceased" and r["honorific"] is True


def test_4_other_kin_singular_agreement():
    r = run([[W(1, "भाई", "NOUN", 2, "nsubj", "Number=Sing"), W(2, "आया", "VERB", 0, "root", PERF_SG)]],
            relation="mother")[0]
    assert r["referent_class"] == "kin" and r["honorific"] is False


def test_5_god_subject():
    r = run([[W(1, "भगवान", "PROPN", 4, "nsubj"), W(2, "ने", "ADP", 1, "case"), W(3, "बुला", "VERB", 0, "root"),
              W(4, "लिया", "AUX", 3, "aux", PERF_SG)]])[0]
    r2 = run([[W(1, "भगवान", "PROPN", 3, "nsubj"), W(2, "ने", "ADP", 1, "case"), W(3, "बुला", "VERB", 0, "root")]])[0]
    assert r2["referent_class"] == "God" and r["referent_class"] in ("God", "impersonal")


def test_6_english_it_is_impersonal_and_honorific_empty():
    r = run([[W(1, "It", "PRON", 2, "nsubj"), W(2, "rained", "VERB", 0, "root", "Mood=Ind|VerbForm=Fin")]], "en")[0]
    assert r["referent_class"] == "impersonal" and r["honorific"] == ""


def test_7_coordinated_predicate_inherits_subject():
    rows = run([[W(1, "Papa", "PROPN", 2, "nsubj"), W(2, "cried", "VERB", 0, "root", "Mood=Ind|VerbForm=Fin")],
                [W(1, "left", "VERB", 0, "root", "Mood=Ind|VerbForm=Fin")]], "en", relation="father", inherit={1: 0})
    assert [r["referent_class"] for r in rows] == ["deceased", "deceased"]
    assert rows[1]["subject_source"] == "inherited"


def test_8_dropped_first_person_from_agreement():
    r = run([[W(1, "घर", "NOUN", 2, "obl"), W(2, "जा", "VERB", 0, "root"), W(3, "रहा", "AUX", 2, "aux", PERF_SG),
              W(4, "हूँ", "AUX", 2, "aux", "Mood=Ind|Number=Sing|Person=1|Tense=Pres|VerbForm=Fin")]])[0]
    assert r["referent_class"] == "self" and r["subject_source"] == "agreement" and r["overt_pronoun"] == ""


def test_9_plural_pronoun_with_singular_antecedent_is_honorific():
    rows = run([[W(1, "माँ", "NOUN", 2, "nsubj", "Gender=Fem|Number=Sing"),
                 W(2, "बीमार", "ADJ", 0, "root"), W(3, "थीं", "AUX", 2, "cop", "Mood=Ind|Tense=Past|VerbForm=Fin")],
                [W(1, "उन्होंने", "PRON", 3, "nsubj"), W(2, "कुछ", "PRON", 3, "obj"), W(3, "कहा", "VERB", 0, "root", PERF_SG)]],
               relation="mother (Maa)")
    assert rows[0]["referent_class"] == "deceased" and rows[0]["honorific"] is True
    assert rows[1]["referent_class"] == "deceased" and rows[1]["honorific"] is True
    assert (rows[1]["pronoun_person"], rows[1]["pronoun_number"]) == ("3", "pl")


def test_10_ergative_subject_does_not_control_agreement():
    r = run([[W(1, "डाक्टर", "NOUN", 4, "nsubj", "Number=Sing"), W(2, "ने", "ADP", 1, "case"),
              W(3, "रिपोर्टें", "NOUN", 4, "obj", "Number=Plur", "रिपोर्ट"),
              W(4, "देखीं", "VERB", 0, "root", "Aspect=Perf|Gender=Fem|Number=Plur|VerbForm=Part")]])[0]
    assert r["referent_class"] == "other" and r["honorific"] is False


def test_deceased_terms_from_relation_text():
    t = R.deceased_terms("father (Appa)")
    assert {"पापा", "father", "appa"} <= t and "माँ" not in t


def test_deceased_terms_from_review_category_words():
    assert {"माँ", "पापा", "mother", "father"} <= R.deceased_terms("parent")
    assert {"दादी", "नाना", "grandmother", "grandfather"} <= R.deceased_terms("grandparent")
    assert {"भाई", "दीदी"} <= R.deceased_terms("sibling") and {"पति", "wife"} <= R.deceased_terms("spouse")
    assert {"बेटा", "बेटी"} <= R.deceased_terms("child") and "दोस्त" in R.deceased_terms("friend")
    assert R.deceased_terms("parents") == R.deceased_terms("parent")
    assert "माँ" not in R.deceased_terms("grandparent")
    assert "बेटा" not in R.deceased_terms("father (Appa)")


def test_category_word_identifies_the_deceased():
    r = run([[W(1, "माँ", "NOUN", 2, "nsubj"), W(2, "गईं", "VERB", 0, "root", "Number=Plur")]], relation="parent")[0]
    assert r["referent_class"] == "deceased"


def _tree(words):
    from collections import defaultdict
    sent = {i: dict(token_index=i, token=t, lemma=t, upos=u, head=h, deprel=d, feats="") for i, t, u, h, d in words}
    kids = defaultdict(list)
    for w in sent.values():
        kids[w["head"]].append(w)
    return sent, kids


def test_target_object_is_deceased():
    sent, kids = _tree([(1, "I", "PRON", 2, "nsubj"), (2, "lost", "VERB", 0, "root"), (3, "my", "PRON", 4, "nmod:poss"),
                        (4, "husband", "NOUN", 2, "obj")])
    assert R.classify_target(sent[2], kids, "en", {"husband"}, []) == ("deceased", "husband")


def test_target_nmod_of_light_verb_noun():
    sent, kids = _tree([(1, "मुझे", "PRON", 5, "nsubj"), (2, "माँ", "NOUN", 4, "nmod"), (3, "की", "ADP", 2, "case"),
                        (4, "याद", "NOUN", 5, "compound"), (5, "आई", "VERB", 0, "root")])
    assert R.classify_target(sent[5], kids, "hi", set(), [])[0] == "kin"


def test_target_pronoun_uses_antecedent_and_priority():
    sent, kids = _tree([(1, "I", "PRON", 2, "nsubj"), (2, "miss", "VERB", 0, "root"), (3, "him", "PRON", 2, "obj"),
                        (4, "everyday", "NOUN", 2, "obl")])
    hist = [dict(cls="deceased", number="Sing", gender=None, text="papa")]
    assert R.classify_target(sent[2], kids, "en", set(), hist) == ("deceased", "him")
    sent, kids = _tree([(1, "it", "PRON", 2, "nsubj"), (2, "rained", "VERB", 0, "root")])
    assert R.classify_target(sent[2], kids, "en", set(), []) == ("", "")


def test_relational_union_of_three_channels(tmp_path):
    f = tmp_path / "clause_features.csv"
    f.write_text("clause_id,orient_F,orient_C,L-HI-14\na#1,0,0,0\na#2,1,0,1\na#3,0,0,0\na#4,0,0,0\n", encoding="utf-8")
    rows = [dict(clause_id="a#1", referent_class="kin", target_class=""),
            dict(clause_id="a#2", referent_class="self", target_class="impersonal"),
            dict(clause_id="a#3", referent_class="self", target_class="community"),
            dict(clause_id="a#4", referent_class="impersonal", target_class="other")]
    R.relational_columns(rows, f)
    assert [r["relational"] for r in rows] == [True, True, True, False]
    assert (rows[0]["rel_subject"], rows[1]["rel_entry"], rows[2]["rel_target"]) == (True, True, True)


def test_vocative_kin_is_relational_target(tmp_path):
    sent, kids = _tree([(1, "माँ", "NOUN", 4, "vocative"), (2, "तुम", "PRON", 4, "nsubj"), (3, "कहाँ", "ADV", 4, "advmod"),
                        (4, "चली", "VERB", 0, "root")])
    assert R.classify_target(sent[4], kids, "hi", {"माँ"}, []) == ("deceased", "माँ")
    sent, kids = _tree([(1, "Appa", "PROPN", 4, "vocative"), (2, "I", "PRON", 4, "nsubj"), (3, "really", "ADV", 4, "advmod"),
                        (4, "tried", "VERB", 0, "root")])
    assert R.classify_target(sent[4], kids, "en", R.deceased_terms("father (Appa)"), [])[0] == "deceased"
    f = tmp_path / "cf.csv"
    f.write_text("clause_id,orient_F,orient_C,flag_F7\na#1,0,0,1\n", encoding="utf-8")
    rows = R.relational_columns([dict(clause_id="a#1", referent_class="self", target_class="")], f)
    assert rows[0]["rel_target"] and rows[0]["relational"]


def test_grammar_forced_entries_are_not_relational_evidence(tmp_path):
    rel = R.relational_entries(R.Path(__file__).resolve().parents[1] / "lexicon" / "lexicon.csv")
    assert "L-HI-C2" not in rel and "L-HI-12" not in rel and "L-HI-14" in rel
    f = tmp_path / "cf.csv"
    f.write_text("clause_id,orient_F,L-HI-C2,L-HI-14\na#1,1,1,0\na#2,1,0,1\n", encoding="utf-8")
    rows = R.relational_columns([dict(clause_id=c, referent_class="self", target_class="") for c in ("a#1", "a#2")], f)
    assert [r["rel_entry"] for r in rows] == [False, True]


def test_clause_missing_from_features_is_an_error(tmp_path):
    f = tmp_path / "cf.csv"
    f.write_text("clause_id,L-HI-14\na#1,0\n", encoding="utf-8")
    import pytest
    with pytest.raises(SystemExit):
        R.relational_columns([dict(clause_id="a#9", referent_class="self", target_class="")], f)


def test_kin_forms_found_through_lemma_and_honorific_ji():
    w = lambda tok, lem, upos="NOUN": dict(token=tok, lemma=lem, upos=upos, deprel="nsubj", feats="")
    assert R.classify_noun(w("ताऊजी", "ताऊजी"), "hi", set()) == "kin"
    assert R.classify_noun(w("भाइयों", "भाई"), "hi", set()) == "kin"
    assert R.classify_noun(w("brothers", "brother"), "en", set()) == "kin"
    assert R.classify_noun(w("बेटे", "बेटा"), "hi", {"बेटा"}) == "deceased"
    assert R.classify_noun(w("मेज", "मेज"), "hi", set()) == "impersonal"
