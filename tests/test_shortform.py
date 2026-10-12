import csv
from pathlib import Path

import pytest

import shortform as S

HERE = Path(__file__).resolve().parent
with open(HERE / "shortform_sentences.csv", encoding="utf-8", newline="") as fh:
    ROWS = list(csv.DictReader(fh))


def test_sentence_file():
    assert len(ROWS) == 10
    assert {r["label"] for r in ROWS} == {"romanized_hindi", "code_mixed", "english"}


def test_tokenize_kinds():
    toks = S.tokenize("मेरे papa 10:06 nahi h😢")
    assert [(t, k) for t, k, _, _ in toks] == [("मेरे", "deva"), ("papa", "latin"), ("10:06", "num"),
                                                ("nahi", "latin"), ("h", "latin"), ("😢", "other")]


def test_text_label_thresholds():
    tok = lambda kind: ("w", kind, 0, 1)
    tags = lambda seq: [(g, 0.5) for g in seq]
    assert S.text_label([tok("other")] * 5, tags(["x"] * 5))[0] == "unknown"
    assert S.text_label([tok("latin")] * 5, tags(["hi"] * 5))[0] == "romanized_hindi"
    assert S.text_label([tok("deva")] * 5, tags(["hi"] * 5))[0] == "devanagari_hindi"
    assert S.text_label([tok("latin")] * 5, tags(["hi", "hi", "en", "en", "en"]))[0] == "code_mixed"
    assert S.text_label([tok("latin")] * 5, tags(["en"] * 5))[0] == "english"


def test_language_runs_absorb_insertions():
    t = lambda seq: [(g, 0.5) for g in seq]
    assert S.language_runs(t(["hi", "hi", "hi", "en", "hi", "hi", "hi"])) == [("hi", list(range(7)))]
    got = S.language_runs(t(["en", "en", "en", "en", "x", "hi", "hi", "hi", "hi"]))
    assert got == [("en", [0, 1, 2, 3, 4]), ("hi", [5, 6, 7, 8])]
    assert S.language_runs(t(["en", "hi"])) == [("en", [0, 1])]


def test_roman_lexicon_overrides_without_worker(tmp_path):
    x = S.Xlit(tmp_path / "cache.json")
    got = S.rom2deva(["h", "nhi", "me", "ab", "Hai"], x)
    assert got == {"h": "है", "nhi": "नहीं", "me": "में", "ab": "अब", "Hai": "है"}
    assert S.rom2deva(["nhiiii", "Mtlb"], x) == {"nhiiii": "नहीं", "Mtlb": "मतलब"}


def test_informal_variants():
    assert {"key", "ke"} <= S.informal_variants("key") and "bhi" in S.informal_variants("bhee")
    assert "nahi" in S.informal_variants("nahii")


def test_renumber_into_record():
    cl = [dict(clause_id="r~r1#0001", record_id="r~r1", position=1, sent_index=0, subject_inherited_from=None),
          dict(clause_id="r~r1#0002", record_id="r~r1", position=2, sent_index=0,
               subject_inherited_from="r~r1#0001")]
    tk = [["r~r1#0001", 1, "a"], ["r~r1#0002", 2, "b"]]
    S.renumber(cl, tk, "r", 3, 2)
    assert [c["clause_id"] for c in cl] == ["r#0004", "r#0005"] and cl[1]["subject_inherited_from"] == "r#0004"
    assert [c["sent_index"] for c in cl] == [2, 2] and [t[0] for t in tk] == ["r#0004", "r#0005"]


@pytest.fixture(scope="module")
def model():
    m = S.load_langid()
    if m is None:
        pytest.skip("language classifier missing or of an older format (run `shortform.py --retrain`)")
    return m


@pytest.mark.parametrize("row", ROWS, ids=[f"s{i + 1}" for i in range(len(ROWS))])
def test_tags_and_label(row, model):
    toks = S.tokenize(row["sentence"])
    tags = S.tag_tokens(toks, model)
    tag_of = {t[0]: g for t, (g, _) in zip(toks, tags)}
    wrong = [w for w in row["hindi_words"].split() if tag_of.get(w) != "hi"] + \
            [w for w in row["english_words"].split() if tag_of.get(w) != "en"]
    assert not wrong, f"mis-tagged: {wrong}"
    assert S.text_label(toks, tags)[0] == row["label"]


@pytest.fixture(scope="module")
def pipeline(model, tmp_path_factory):
    if not S.XLIT_PY.exists():
        pytest.skip("IndicXlit not set up (make setup-xlit)")
    stanza = pytest.importorskip("stanza")
    import preprocess as P
    try:
        nlps = P.make_pipelines(["hi", "en"])
    except Exception as e:
        pytest.skip(f"Stanza models unavailable: {e}")
    nlps["_version"] = stanza.__version__
    d = tmp_path_factory.mktemp("sf")
    cache = d / "xlit_cache.json"
    if (S.OUT / "xlit_cache.json").exists():
        cache.write_bytes((S.OUT / "xlit_cache.json").read_bytes())
    return model, S.Xlit(cache), nlps, d


@pytest.mark.parametrize("row", [r for r in ROWS if r["deva_expected"]],
                         ids=[f"s{i + 1}" for i, r in enumerate(ROWS) if r["deva_expected"]])
def test_end_to_end_transliteration_and_clause_language(row, pipeline):
    model, xlit, nlps, d = pipeline
    rec = dict(record_id="t:1", source="test", platform="test", text=row["sentence"], lang_hint="", extra={})
    record, clauses, tokens, _ = S.process_record(rec, model, xlit, nlps, d / "stanza_cache")
    assert record["lang_provisional"] == row["label"] and clauses and tokens
    hi_text = " ".join(c["clause_text"] for c in clauses if c["parse_lang"] == "hi")
    assert row["deva_expected"] in hi_text, hi_text
    for c in clauses:
        assert c["register"] == "short" and c["lang"] in ("hi", "en")
        if c["share_hi"] is not None and c["share_hi"] > 0.5:
            assert c["lang"] == "hi"


def test_stale_classifier_format_is_not_used(tmp_path):
    import pickle
    with open(tmp_path / "langid.pkl", "wb") as fh:
        pickle.dump({"clf": None}, fh)
    assert S.load_langid(tmp_path) is None
    assert S.load_langid(tmp_path / "missing") is None
