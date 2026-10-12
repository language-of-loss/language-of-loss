import re
from pathlib import Path

import lexmatch as M

LEX = M.load_lexicon(Path(M.ROOT) / "lexicon" / "lexicon.csv")
ENTRY = {e["entry_id"]: e for e in LEX["entries"]}


def clause(text, lang, cid="t:1#0001"):
    return dict(clause_id=cid, record_id="t:1", lang=lang, clause_text=text, is_finite=True, n_tokens=len(text.split()))


def toks(pairs, lang):
    return [{M.norm_word(f, lang), M.norm_word(l, lang)} for f, l in pairs]


def test_1_surface_match_hindi_construction():
    m = M.match_clause(clause("मुझे उनकी बहुत याद आती है", "hi"), [], LEX, ("surface",))
    assert m.get("L-HI-07") == "surface"


def test_2_english_surface_is_case_insensitive_and_respects_exclusions():
    assert "L-EN-12" in M.match_clause(clause("Passed away last spring", "en"), [], LEX, ("surface",))
    assert "L-EN-12" not in M.match_clause(clause("she passed the salt", "en"), [], LEX, ("surface",))


def test_3_headword_variants_parsing():
    assert M.headword_variants(ENTRY["L-EN-07"]) == [["miss"], ["missed"], ["missing"]]
    assert M.headword_variants(ENTRY["L-HI-C1"]) == []
    assert ["याद", "करना"] in M.headword_variants(ENTRY["L-HI-09"])


def test_4_lemma_channel_multiword_by_lemma():
    t = toks([("उन्होंने", "वह"), ("याद", "याद"), ("किया", "करना")], "hi")
    assert M.lemma_match(M.headword_variants(ENTRY["L-HI-09"]), t)


def test_5_lemma_channel_needs_contiguous_words():
    t = toks([("याद", "याद"), ("बहुत", "बहुत"), ("किया", "करना")], "hi")
    assert not M.lemma_match([["याद", "करना"]], t)


def test_6_devanagari_boundary_no_partial_word():
    assert "L-HI-03" in M.match_clause(clause("विनम्र श्रद्धांजलि", "hi"), [], LEX, ("surface",))
    assert "L-HI-03" not in M.match_clause(clause("श्रद्धांजलिया", "hi"), [], LEX, ("surface",))


def test_7_entry_tags_components_and_member_flag():
    f = M.clause_features(clause("विनम्र श्रद्धांजलि", "hi"), {"L-HI-03": "surface"}, {}, LEX)
    assert f["L-HI-03"] == 1 and f["orient_R"] == 1 and f["func_offer"] == 1
    assert f["comp_RITUAL_WORDS"] == 1 and f["comp_HONOUR"] == 1 and f["flag_F6"] == 1
    assert f["orient_I"] == 0 and f["proc_loss"] == 0


def test_8_grammar_forced_flag_goes_to_gf_column_only():
    f = M.clause_features(clause("मुझे लगा", "hi"), {}, {"dative_parse": "True"}, LEX)
    assert f["flag_F1"] == 1 and f["gf_HAPPEN_TO"] == 1 and f["comp_HAPPEN_TO"] == 0


def test_9_stage4_motion_flag_and_kin_pattern_add_components():
    f = M.clause_features(clause("पापा चले गये", "hi"), {}, {"motion_euphemism": "True"}, LEX)
    assert f["flag_F3"] == 1 and f["comp_NOT_HERE"] == 1 and f["comp_AVOID_DIE"] == 1
    assert f["flag_F9"] == 1 and f["comp_KIN"] == 1


def test_10_text_rates_per_1000_tokens():
    a, b = clause("one two three four", "en", "t:1#1"), clause("five six seven eight nine ten", "en", "t:1#2")
    rows = M.text_rates([a, b], {"t:1#1": {"x": 1}, "t:1#2": {"x": 0}}, ["x"])
    assert rows[0]["n_clauses"] == 2 and rows[0]["n_tokens"] == 10 and rows[0]["x"] == 100.0


def test_no_word_boundary_escape_in_source():
    assert not re.search(r"\\\\b", Path(M.__file__).read_text(encoding="utf-8"))


def test_l_en_16_is_surface_only():
    assert ENTRY["L-EN-16"]["variants"] == []
    bare = M.match_clause(clause("death is final", "en"), toks([("death", "death"), ("is", "be"), ("final", "final")],
                                                               "en"), LEX)
    assert "L-EN-16" not in bare
    poss = M.match_clause(clause("her passing changed us", "en"),
                          toks([("her", "her"), ("passing", "passing"), ("changed", "change"), ("us", "we")], "en"), LEX)
    assert poss.get("L-EN-16") == "surface"
