import csv
import re
from pathlib import Path

import pytest

import flags as F

HERE = Path(__file__).resolve().parent
SPEC = F.load_spec()
with open(HERE / "flag_sentences.csv", encoding="utf-8", newline="") as fh:
    ROWS = list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def nlp():
    stanza = pytest.importorskip("stanza")
    try:
        return {lg: stanza.Pipeline(lg, processors=p, download_method=None, verbose=False)
                for lg, p in (("hi", "tokenize,pos,lemma,depparse"), ("en", "tokenize,mwt,pos,lemma,depparse"))}
    except Exception as e:
        pytest.skip(f"Stanza models unavailable: {e}")


def test_sentence_file_is_well_formed():
    assert ROWS, "tests/flag_sentences.csv has no rows"
    known = set(SPEC["columns"])
    for r in ROWS:
        assert r["lang"] in ("hi", "en"), r
        unknown = {f for f in r["expected_flags"].split(";") if f} - known
        assert not unknown, f"unknown flag(s) {unknown} in: {r['sentence']}"


@pytest.mark.parametrize("row", ROWS, ids=[f"{r['lang']}-{i + 2}" for i, r in enumerate(ROWS)])
def test_expected_flags(row, nlp):
    expected = {f for f in row["expected_flags"].split(";") if f} & SPEC["defined"][row["lang"]]
    assert F.flag_text(row["sentence"], row["lang"], nlp[row["lang"]], SPEC) == expected


def test_patterns_have_no_word_boundary_escape():
    text = (Path(F.__file__).resolve().parents[2] / "lexicon" / "constructions.yaml").read_text(encoding="utf-8")
    assert not re.search(r"\\\\b", text)


def test_regex_examples_and_near_misses():
    hit = lambda t, lg: set(F.regex_flags(t, lg, SPEC))
    assert "motion_euphemism" in hit("पापा चले गये", "hi")
    assert "motion_euphemism" not in hit("परंपराएं बदलती चली गईं", "hi")
    assert "no_more" in hit("Amma is no more", "en")
    assert "no_more" not in hit("there was no more lounging", "en")
    assert "closing_formula" not in hit("they rip the paper", "en")
    assert "motion_euphemism" not in hit("she passed on the message", "en")


def _w(i, token, lemma, upos, head, deprel, feats=""):
    return dict(token_index=i, token=token, lemma=lemma, upos=upos, feats=feats, head=head, deprel=deprel)


def _finite(words):
    p = F.load_spec()["filters"]["finite_dative"]
    sentence = {w["token_index"]: w for w in words}
    return F.finite_dative(words, sentence, p)


def test_progressive_aux_after_an_object_pronoun_is_not_a_dative_experiencer():
    words = [_w(1, "मैं", "मैं", "PRON", 3, "nsubj"), _w(2, "उसे", "वह", "PRON", 3, "obj"),
             _w(3, "देख", "देखना", "VERB", 0, "root"), _w(4, "रहा", "रहना", "AUX", 3, "aux"),
             _w(5, "था", "था", "AUX", 3, "aux")]
    assert not _finite(words)


def test_progressive_aux_of_an_experiencer_verb_still_counts():
    words = [_w(1, "मुझे", "मैं", "PRON", 3, "nsubj"), _w(2, "डर", "डर", "NOUN", 3, "compound"),
             _w(3, "लग", "लगना", "VERB", 0, "root"), _w(4, "रहा", "रहना", "AUX", 3, "aux"),
             _w(5, "था", "था", "AUX", 3, "aux")]
    assert _finite(words)


def test_psych_head_needs_the_exact_lemma():
    d = F.load_spec()["dative"]
    assert not F.is_psych_head(_w(1, "भागा", "भागना", "VERB", 0, "root"), [], d)
    assert not F.is_psych_head(_w(1, "लगाया", "लगाना", "VERB", 0, "root"), [], d)
    assert F.is_psych_head(_w(1, "लगा", "लगाना", "VERB", 0, "root"), [], d)
    assert F.is_psych_head(_w(1, "खला", "खलना", "VERB", 0, "root"), [], d)
    inceptive = [_w(2, "करने", "करना", "VERB", 1, "xcomp", "VerbForm=Inf")]
    assert not F.is_psych_head(_w(1, "लगा", "लगाना", "VERB", 0, "root"), inceptive, d)
    assert not F.is_psych_head(_w(1, "आदत", "आदत", "NOUN", 0, "root"), [_w(2, "दुख", "दुख", "NOUN", 1, "nmod")], d)
