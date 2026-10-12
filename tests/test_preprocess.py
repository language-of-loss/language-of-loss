import re
from pathlib import Path

import preprocess as P


def W(i, text, upos, head, deprel, feats="", lemma=None, tok=None):
    return dict(id=i, text=text, lemma=lemma or text, upos=upos, feats=feats, head=head, deprel=deprel,
                tok=i - 1 if tok is None else tok, start=0, end=0)


def sent(*words):
    pos, text, last_tok = 0, "", None
    for w in words:
        if w["tok"] == last_tok:
            w["start"], w["end"] = prev["start"], prev["end"]
            continue
        if text:
            text += " "
            pos += 1
        w["start"], w["end"] = pos, pos + len(w["text"])
        text += w["text"]
        pos = w["end"]
        last_tok, prev = w["tok"], w
    return list(words), text


def units_text(words, text, lang):
    clauses = P.segment({"record_id": "t:1"}, lang, [words], text)
    return [c["clause_text"] for c in clauses[0]]


FIN_PAST = "Mood=Ind|Tense=Past|VerbForm=Fin"


def test_prepare_text_strips_identifiers_but_keeps_years():
    t = P.prepare_text("Call +91 98765 43210 or a.b@c.org, see https://x.y/z [URL] in 1947-2020.")
    assert "98765" not in t and "@" not in t and "http" not in t and "[URL]" not in t
    assert "1947-2020" in t


def test_prepare_text_spaces_danda_and_splits_lines():
    assert P.prepare_text("वह चली गई।\nफिर") == "वह चली गई ।\n\nफिर"


def test_prepare_text_nfc_unifies_nukta_spellings():
    assert P.prepare_text("क़") == P.prepare_text("क़") == "क़"


def test_no_word_boundary_regex_in_module():
    src = Path(P.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\\\\b", src)


def test_en_finite_via_aux_and_participle_not_finite():
    words, text = sent(W(1, "she", "PRON", 3, "nsubj"), W(2, "would", "AUX", 3, "aux", "VerbForm=Fin"),
                       W(3, "come", "VERB", 0, "root", "VerbForm=Inf"))
    kids = {3: [words[0], words[1]]}
    assert P.is_finite(words[2], kids[3], "en")
    lost = W(1, "lost", "VERB", 0, "root", "Tense=Past|VerbForm=Part")
    assert not P.is_finite(lost, [], "en")


def test_hi_copula_and_converb():
    maa = W(3, "माँ", "NOUN", 0, "root")
    thi = W(4, "थी", "AUX", 3, "cop", "Mood=Ind|Tense=Past|VerbForm=Fin")
    assert P.is_finite(maa, [thi], "hi")
    khakar = W(2, "खाकर", "VERB", 4, "advcl", "VerbForm=Conv")
    assert not P.is_finite(khakar, [], "hi")


def test_complement_clause_is_its_own_unit():
    words, text = sent(W(1, "I", "PRON", 2, "nsubj"), W(2, "thought", "VERB", 0, "root", FIN_PAST),
                       W(3, "that", "SCONJ", 5, "mark"), W(4, "she", "PRON", 5, "nsubj"),
                       W(5, "left", "VERB", 2, "ccomp", FIN_PAST), W(6, ".", "PUNCT", 2, "punct"))
    assert units_text(words, text, "en") == ["I thought", "that she left"]


def test_np_coordination_is_not_split():
    words, text = sent(W(1, "I", "PRON", 5, "nsubj"), W(2, "and", "CCONJ", 4, "cc"),
                       W(3, "my", "PRON", 4, "nmod:poss"), W(4, "sister", "NOUN", 1, "conj"),
                       W(5, "went", "VERB", 0, "root", FIN_PAST))
    assert units_text(words, text, "en") == ["I and my sister went"]


def test_connective_split_when_finite_verb_on_both_sides():
    words, text = sent(W(1, "मैं", "PRON", 2, "nsubj"), W(2, "रोया", "VERB", 0, "root", FIN_PAST),
                       W(3, "लेकिन", "CCONJ", 5, "cc"), W(4, "वह", "PRON", 5, "nsubj"),
                       W(5, "हँसा", "VERB", 2, "compound", FIN_PAST))
    assert units_text(words, text, "hi") == ["मैं रोया", "लेकिन वह हँसा"]


def test_postposition_par_is_not_a_connective():
    by_id = {w["id"]: w for w in [W(1, "मेज़", "NOUN", 4, "obl"), W(2, "पर", "ADP", 1, "case"),
                                 W(3, "किताब", "NOUN", 4, "obj"), W(4, "रखी", "VERB", 0, "root", FIN_PAST)]}
    assert len(P.connective_split([1, 2, 3, 4], by_id, "hi")) == 1


def test_span_text_keeps_token_order_and_emits_mwt_once():
    text = "we don't know"
    words = [W(1, "we", "PRON", 2, "nsubj", tok=0), W(2, "do", "AUX", 0, "root", "VerbForm=Fin", tok=1),
             W(3, "n't", "PART", 2, "advmod", tok=1), W(4, "know", "VERB", 2, "xcomp", tok=2)]
    for w, (a, b) in zip(words, [(0, 2), (3, 8), (3, 8), (9, 13)]):
        w["start"], w["end"] = a, b
    by_id = {w["id"]: w for w in words}
    assert P.span_text([1, 2, 3, 4], by_id, text) == "we don't know"
    assert P.span_text([1, 4], by_id, text) == "we know"


def test_near_duplicates_reports_identical_texts_only():
    a = " ".join(f"w{i}" for i in range(60))
    b = " ".join(f"v{i}" for i in range(60))
    dups = P.near_duplicates({"x:1": ("en", a), "x:2": ("en", a), "x:3": ("en", b)})
    assert [(d["a"], d["b"]) for d in dups] == [("x:1", "x:2")]


PERF_M = "Aspect=Perf|Gender=Masc|Number=Sing|VerbForm=Part"
PERF_F = "Aspect=Perf|Gender=Fem|Number=Sing|VerbForm=Part"


def clauses_of(words, text, lang):
    return P.segment({"record_id": "t:1"}, lang, [words], text)[0]


def test_strip_edges_removes_punctuation_and_space_only_at_the_ends():
    assert P.strip_edges(", पाला-पोसा, ") == "पाला-पोसा"
    assert P.strip_edges("“ठीक है।” ") == "ठीक है"
    assert P.strip_edges("—…") == ""


def test_participial_description_is_not_finite():
    words, text = sent(W(1, "रामू", "PROPN", 4, "nsubj", "Gender=Masc"), W(2, "थैला", "NOUN", 4, "obj"),
                       W(3, "लिए", "VERB", 6, "acl", PERF_M), W(4, ",", "PUNCT", 3, "punct"),
                       W(5, "पहने", "VERB", 7, "advcl", PERF_M), W(6, "बाज़ार", "NOUN", 7, "obj"),
                       W(7, "निकलते", "VERB", 0, "root", "Aspect=Imp|Gender=Masc|VerbForm=Part"),
                       W(8, "थे", "AUX", 7, "aux", FIN_PAST), W(9, "।", "PUNCT", 7, "punct"))
    words[0]["head"] = 3
    cl = clauses_of(words, text, "hi")
    assert len(cl) == 1 and cl[0]["is_finite"] and cl[0]["head_lemma"] == "निकलते"


def test_hi_pro_drop_root_and_obligation_are_finite():
    lagaa = W(2, "लगा", "VERB", 0, "root", PERF_M)
    assert P.is_finite(lagaa, [W(1, "बुरा", "ADJ", 2, "compound")], "hi")
    jaana = W(2, "जाना", "VERB", 0, "root", "VerbForm=Inf")
    assert P.is_finite(jaana, [W(3, "पड़ा", "AUX", 2, "aux", PERF_M)], "hi")


def test_hi_huaa_participle_and_te_hi_are_not_finite():
    roti = W(2, "रोती", "VERB", 4, "advcl", "Aspect=Imp|Gender=Fem|VerbForm=Part")
    assert not P.is_finite(roti, [W(3, "हुई", "AUX", 2, "aux", PERF_F)], "hi")
    hote = W(2, "होते", "VERB", 5, "advcl", "Aspect=Imp|Gender=Masc|VerbForm=Part")
    assert not P.is_finite(hote, [W(3, "ही", "PART", 2, "dep")], "hi", W(1, "अँधेरा", "NOUN", 2, "nsubj", "Gender=Masc"))


def test_hi_agreement_with_subject_in_advcl():
    subj_f = W(1, "माँ", "NOUN", 2, "nsubj", "Gender=Fem")
    assert P.is_finite(W(2, "आई", "VERB", 5, "advcl", PERF_F), [], "hi", subj_f)
    assert not P.is_finite(W(2, "आया", "VERB", 5, "advcl", PERF_M), [], "hi", subj_f)
    erg = W(1, "उसने", "PRON", 2, "nsubj", "Case=Acc,Erg")
    assert not P.is_finite(W(2, "पहुंचते", "VERB", 5, "advcl", "Aspect=Imp|VerbForm=Part"), [], "hi", erg)


def test_conj_without_subject_points_to_clause_with_subject():
    words, text = sent(W(1, "she", "PRON", 2, "nsubj"), W(2, "cried", "VERB", 0, "root", FIN_PAST),
                       W(3, "and", "CCONJ", 4, "cc"), W(4, "left", "VERB", 2, "conj", FIN_PAST))
    cl = clauses_of(words, text, "en")
    assert [c["clause_text"] for c in cl] == ["she cried", "and left"]
    assert cl[0]["subject_inherited_from"] is None
    assert cl[1]["subject_inherited_from"] == cl[0]["clause_id"]


def test_discontinuous_unit_keeps_order_and_has_span_text():
    words, text = sent(W(1, "Some", "DET", 3, "obj"), W(2, "we", "PRON", 3, "nsubj"),
                       W(3, "realize", "VERB", 0, "root", "Mood=Ind|VerbForm=Fin"), W(4, "some", "DET", 3, "obj"),
                       W(5, "we", "PRON", 6, "nsubj"), W(6, "do", "AUX", 4, "acl:relcl", "VerbForm=Fin"),
                       W(7, ".", "PUNCT", 3, "punct"))
    main, rel = clauses_of(words, text, "en")
    assert main["clause_text"] == "Some we realize some"
    assert main["span_text"] == "Some we realize some we do ."
    assert rel["clause_text"] == "we do"


def test_space_after_fused_stop_all_languages():
    assert P.prepare_text("Mom left.Then rain") == "Mom left. Then rain"


def test_hindi_latin_stop_ends_paragraph_but_not_abbreviations():
    assert P.prepare_text("उपहारों पर.लगे देखने", "hi") == "उपहारों पर .\n\nलगे देखने"
    assert P.prepare_text("स्व. पिताजी और डॉ. शर्मा, आर. के. नारायण", "hi") == "स्व. पिताजी और डॉ. शर्मा, आर. के. नारायण"
    assert P.prepare_text("वह 3.5 किलो", "hi") == "वह 3.5 किलो"


def test_copular_clause_keeps_complement_hung_under_matrix():
    words, text = sent(W(1, "दादी", "NOUN", 4, "nsubj"), W(2, "को", "ADP", 1, "case"),
                       W(3, "चिंता", "NOUN", 4, "nsubj"), W(4, "आ", "VERB", 0, "root"),
                       W(5, "थी", "AUX", 4, "aux", FIN_PAST), W(6, "कि", "SCONJ", 7, "mark"),
                       W(7, "रीना", "PROPN", 4, "ccomp"), W(8, "शिक्षक", "NOUN", 9, "compound"),
                       W(9, "परिवार", "NOUN", 3, "nmod"), W(10, "की", "ADP", 9, "case"),
                       W(11, "है", "AUX", 7, "cop", "Mood=Ind|Tense=Pres|VerbForm=Fin"))
    assert units_text(words, text, "hi") == ["दादी को चिंता आ थी", "कि रीना शिक्षक परिवार की है"]


def test_copular_repair_never_leaves_an_empty_unit():
    words, text = sent(W(1, "वह", "PRON", 2, "nsubj"), W(2, "माँ", "NOUN", 0, "root"),
                       W(3, "बहुत", "ADV", 0, "dep"), W(4, "थी", "AUX", 2, "cop", FIN_PAST))
    words[1]["deprel"], words[2]["head"] = "root", 0
    units = {2: [1, 2, 4], None: [3]}
    by_id = {w["id"]: w for w in words}
    P.repair_copular_complement(units, by_id)
    assert units == {2: [1, 2, 4, 3]}


def test_connective_split_gives_the_head_to_the_piece_that_contains_it(monkeypatch):
    import preprocess as PP
    text = "वह आया और मैं रोया"
    words, pos = [], 0
    spec = [("वह", "वह", "PRON", 2, "nsubj"), ("आया", "आना", "VERB", 5, "advcl"), ("और", "और", "CCONJ", 5, "cc"),
            ("मैं", "मैं", "PRON", 5, "nsubj"), ("रोया", "रोना", "VERB", 0, "root")]
    for i, (t, lem, upos, head, dep) in enumerate(spec, 1):
        start = text.index(t, pos)
        pos = start + len(t)
        words.append(dict(id=i, text=t, lemma=lem, upos=upos, feats="", head=head, deprel=dep,
                          tok=i - 1, start=start, end=pos))
    monkeypatch.setattr(PP, "tree_units", lambda ws, lang: ({5: {1, 2, 3, 4, 5}}, {5}, {5: 1}))
    monkeypatch.setattr(PP, "repair_copular_complement", lambda units, by_id: None)
    monkeypatch.setattr(PP, "attach_stray_punct", lambda units, by_id: None)
    monkeypatch.setattr(PP, "connective_split", lambda ids, by_id, lang: [([1, 2], None), ([3, 4, 5], "और")])
    clauses, _, n_split, _ = PP.segment(dict(record_id="r"), "hi", [words], text)
    assert n_split == 1 and [c["head_lemma"] for c in clauses] == [None, "रोना"]
    assert clauses[0]["subject_inherited_from"] is None and clauses[1]["subject_inherited_from"] == "r#0001"
