import csv
import re
from pathlib import Path

import pytest

import decompose as D
import meta_prefill as M

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "data" / "processed" / "text_meta.csv"
REVIEW = ROOT / "data" / "annotation" / "meta_review.csv"
CID = re.compile(r"^[a-z_]+:[^#\s]+#\d{4}$")


def cl(*texts, finite=True):
    return [(f"blogs:t#{i + 1:04d}", t, finite) for i, t in enumerate(texts)]


def test_tense_readings():
    assert M.tense([("VERB", "go", {"Tense": "Past", "VerbForm": "Fin"})], "en") == "past"
    assert M.tense([("AUX", "will", {}), ("VERB", "go", {})], "en") == "future"
    assert M.tense([("VERB", "जा", {"Aspect": "Perf"})], "hi") == "past"
    assert M.tense([("VERB", "जा", {"Aspect": "Perf"}), ("AUX", "है", {"Tense": "Pres"})], "hi") == "present"
    assert M.tense([("VERB", "x", {})], "en") is None


def test_genre_by_past_share_with_confidence():
    clauses = cl("a", "b", "c", "d")
    feats = {c: [("VERB", "v", {"Tense": "Past"})] for c, _, _ in clauses[:3]}
    feats[clauses[3][0]] = [("VERB", "v", {"Tense": "Pres"})]
    value, conf, rule, ev = M.genre(clauses, feats, "en")
    assert (value, conf) == ("narrative", "high") and "0.75" in rule and set(ev) <= {c for c, _, _ in clauses}
    feats = {c: [("VERB", "v", {"Tense": "Pres"})] for c, _, _ in clauses}
    assert M.genre(clauses, feats, "en")[:2] == ("reflective", "high")
    assert M.genre(clauses, {}, "en")[:2] == ("reflective", "low")


@pytest.mark.parametrize("texts,expected", [
    (["Hindi is my mother tongue"], "hi"),
    (["at home we spoke English mostly"], "en"),
    (["my first language was Hindi, then English"], "both"),
    (["मेरी मातृभाषा हिंदी है"], "hi"),
    (["Tamil is my mother tongue"], "none"),
    (["she loved the rain"], "none"),
])
def test_home_language_statement(texts, expected):
    value, conf, rule, ev = M.home_language(cl(*texts))
    assert value == expected
    assert conf in M.CONF and (ev == [] if rule.startswith("no home-language statement matched") else ev)


def test_language_remark_points_but_does_not_decide():
    value, conf, rule, ev = M.home_language(cl("I am writing this in English", "it rained"))
    assert (value, conf) == ("none", "low") and "remark" in rule and ev == ["blogs:t#0001"]


@pytest.mark.parametrize("text,lang,expected", [
    ("We moved to Canada in 2010", "en", "yes"), ("I live in Delhi with my wife", "en", "no"),
    ("Papa loved London", "en", "unknown"), ("हम अमेरिका में रहते थे", "hi", "yes"), ("मैं दिल्ली में रहता हूँ", "hi", "no"),
])
def test_diaspora_needs_a_first_person_statement(text, lang, expected):
    assert M.diaspora(cl(text), lang)[0] == expected


def test_script_mix():
    assert M.script_mix("माँ चली गईं", cl("माँ"))[0] == "devanagari"
    assert M.script_mix("Ma left us", cl("Ma"))[0] == "latin"
    assert M.script_mix("माँ left us all alone today", cl("माँ left", "us"))[0] == "mixed"


def texts_fixture():
    pre = {"genre": ("narrative", "high", "r", ["blogs:t#0001"]), "home_language_statement": ("none", "low", "r", []),
           "diaspora": ("unknown", "low", "r", []), "script_mix": ("latin", "high", "r", [])}
    return [dict(record_id="blogs:t", lang="en", split="dev", source_url="https://example.org/t", prefill=pre,
                 word_count=120)]


def test_human_cells_survive_and_override(tmp_path):
    path = tmp_path / "meta_review.csv"
    texts = texts_fixture()
    M.write_review(path, M.review_rows(texts, {}))
    rows = list(csv.DictReader(open(path)))
    assert len(rows) == len(M.FIELDS) and all(r["confirmed_value"] == "" for r in rows)
    for r in rows:
        r.update(confirmed_value={"home_language_statement": "en"}.get(r["field"], r["prefill_value"]), reviewer="A")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=M.REVIEW_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    texts[0]["prefill"]["genre"] = ("reflective", "low", "r", [])
    new = M.review_rows(texts, M.read_review(path))
    g = next(r for r in new if r["field"] == "genre")
    assert g["confirmed_value"] == "narrative" and g["reviewer"] == "A" and g["prefill_changed"] == 1
    cols = M.apply(texts, {(r["record_id"], r["field"]): r for r in new})["blogs:t"]
    assert cols["home_language_statement"] == "en" and cols["home_language_statement_conf"] == "human"
    assert cols["meta_review_status"] == "human_confirmed" and cols["word_count"] == 120


def test_confirmed_value_outside_the_field_is_an_error():
    with pytest.raises(ValueError):
        M.confirmed(dict(record_id="x", field="diaspora", confirmed_value="maybe", reviewer="A"))
    assert M.confirmed(dict(record_id="x", field="diaspora", confirmed_value="yes", reviewer="")) is None


@pytest.mark.skipif(not META.exists() or not REVIEW.exists(), reason="data/processed and data/annotation are local")
def test_text_meta_is_complete():
    rows = list(csv.DictReader(open(META, encoding="utf-8")))
    assert rows
    for r in rows:
        for f, allowed in M.FIELDS.items():
            assert r[f] in allowed, (r["record_id"], f, r[f])
            assert r[f"{f}_conf"] in M.CONF + ("human",), (r["record_id"], f)
        assert int(r["word_count"]) > 0
        assert r["meta_review_status"] in ("prefilled", "partly_confirmed", "human_confirmed")


@pytest.mark.skipif(not META.exists() or not REVIEW.exists(), reason="data/processed and data/annotation are local")
def test_review_sheet_is_complete_and_holds_ids_only():
    meta = {r["record_id"] for r in csv.DictReader(open(META, encoding="utf-8"))}
    rows = list(csv.DictReader(open(REVIEW, encoding="utf-8")))
    head = list(rows[0])
    assert head[:len(M.REVIEW_COLUMNS)] == M.REVIEW_COLUMNS
    assert head[len(M.REVIEW_COLUMNS):] in ([], ["provenance", "corrections"])
    per = {}
    for r in rows:
        per.setdefault(r["record_id"], set()).add(r["field"])
        for cid in r["evidence_clause_ids"].split():
            assert CID.match(cid) and cid.split("#")[0] == r["record_id"], cid
    assert set(per) == meta and all(v == set(M.FIELDS) for v in per.values())


def meta_file(tmp_path, rows):
    p = tmp_path / "text_meta.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "lang", "home_language_statement", "meta_review_status"])
        w.writeheader()
        w.writerows(rows)
    return p


def test_english_home_subset_refuses_prefill_and_empty(tmp_path):
    hi = dict(record_id="blogs:h", lang="hi", home_language_statement="none", meta_review_status="prefilled")
    with pytest.raises(SystemExit, match="no English text"):
        D.english_home_records(meta_file(tmp_path, [hi]))
    pre = dict(record_id="blogs:e", lang="en", home_language_statement="en", meta_review_status="prefilled")
    with pytest.raises(SystemExit, match="unconfirmed"):
        D.english_home_records(meta_file(tmp_path, [hi, pre]))
    ok = dict(pre, meta_review_status="human_confirmed")
    other = dict(record_id="blogs:e2", lang="en", home_language_statement="none", meta_review_status="prefilled")
    assert D.english_home_records(meta_file(tmp_path, [hi, ok, other])) == {"blogs:h", "blogs:e"}


def test_text_counts_respects_the_record_set():
    refs = [dict(clause_id="blogs:h#0001", lang="hi", referent_class="self"),
            dict(clause_id="blogs:e#0001", lang="en", referent_class="self"),
            dict(clause_id="blogs:x#0001", lang="en", referent_class="self")]
    t = D.text_counts(refs, {}, split="all", records={"blogs:h", "blogs:e"})
    assert set(t["en"]) == {"blogs:e"} and set(t["hi"]) == {"blogs:h"}


def test_platform_type_from_domain():
    import text_meta as T
    assert T.platform_type("https://someone.substack.com/p/x") == "self_published"
    assert T.platform_type("https://www.medium.com/@a/b") == "self_published"
    assert T.platform_type("https://scroll.in/article/1") == "news_magazine"
    assert T.platform_type("https://www.samalochan.com/x") == "literary_or_story_platform"
    assert T.platform_type("https://unknown-person.in/x") == "personal_site"
