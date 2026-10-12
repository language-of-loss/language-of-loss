import math

import pytest

import translation_bias as T


def test_native_only_from_molecules():
    lex = [dict(entry_id="L-HI-01", lang="hi"), dict(entry_id="L-HI-02", lang="hi"), dict(entry_id="L-EN-01", lang="en")]
    mol = [dict(molecule="shoulders", used_in="L-HI-01", why_unavoidable=""),
           dict(molecule="body", used_in="L-HI-02 L-EN-01", why_unavoidable="")]
    nat = T.native_only_entries(mol, lex)
    assert nat == {"L-HI-01"}
    assert T.item_class(["L-HI-01", "L-HI-02"], nat) == "native_only"
    assert T.item_class(["L-HI-02"], nat) == "translatable" and T.item_class([], nat) == "unmatched"


def test_native_only_strict_ignores_tolerated_molecules():
    lex = [dict(entry_id="L-HI-01", lang="hi"), dict(entry_id="L-HI-03", lang="hi"), dict(entry_id="L-EN-01", lang="en")]
    mol = [dict(molecule="shoulders", used_in="L-HI-01", why_unavoidable=""),
           dict(molecule="(tolerated) respect", used_in="L-HI-03", why_unavoidable="verbatim gloss")]
    assert T.native_only_entries(mol, lex) == {"L-HI-01"}
    assert T.native_only_entries(mol, lex, include_tolerated=True) == {"L-HI-01", "L-HI-03"}


def test_native_only_on_the_real_molecules_file():
    import csv
    lex = list(csv.DictReader(open(T.ROOT / "lexicon" / "lexicon.csv", encoding="utf-8")))
    mol = list(csv.DictReader(open(T.ROOT / "lexicon" / "molecules.csv", encoding="utf-8")))
    strict, tol = T.native_only_entries(mol, lex), T.native_only_entries(mol, lex, include_tolerated=True)
    assert strict < tol and {"L-HI-12", "L-HI-19", "L-HI-23"} <= tol - strict


def test_nrc_loader_keeps_emotion_words_only(tmp_path):
    p = tmp_path / "Hindi-NRC-EmoLex.txt"
    cols = ["English Word", "anger", "anticipation", "disgust", "fear", "joy", "negative", "positive", "sadness",
            "surprise", "trust", "Hindi Word"]
    rows = [["grief", 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, "दुःख"], ["table", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "मेज़"],
            ["good", 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, "अच्छा"], ["abacus", 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, "abacus"]]
    p.write_text("\t".join(cols) + "\n" + "\n".join("\t".join(map(str, r)) for r in rows) + "\n", encoding="utf-8")
    nrc = T.load_nrc(p)
    assert set(nrc) == {"दुःख"} and nrc["दुःख"] == {"negative", "sadness"}
    assert T.load_nrc(tmp_path / "missing.txt") is None


def test_hsl_loader_absent_and_present(tmp_path):
    assert T.load_hsl(tmp_path / "none") is None
    d = tmp_path / "hsl"
    d.mkdir()
    (d / "a.txt").write_text("उदास\tADJ\tneg\nमेज\tNOUN\tneutral\n", encoding="utf-8")
    assert T.load_hsl(d) == {"उदास": "neg"}


def test_phrase_detector_words_and_phrases():
    det = T.phrase_detector({"दुख", "दिल टूट"})
    assert det("मुझे बहुत दुख हुआ।") and det("मेरा दिल टूट गया") and not det("दुखी नहीं")


def test_paired_bootstrap_recalls_and_gaps():
    items = ([dict(cls="native_only", ref=True, detected=dict(lexicon=True, wn=i < 1)) for i in range(4)]
             + [dict(cls="translatable", ref=True, detected=dict(lexicon=True, wn=i < 3)) for i in range(4)]
             + [dict(cls="unmatched", ref=False, detected=dict(lexicon=False, wn=True))])
    rows = {(r["resource"], r["quantity"]): r for r in T.paired_recall_bootstrap(items, ["lexicon", "wn"], B=200)}
    assert rows[("wn", "recall_native_only")]["estimate"] == 0.25
    assert rows[("wn", "recall_translatable")]["estimate"] == 0.75
    assert math.isclose(rows[("wn", "gap_translatable_minus_native")]["estimate"], 0.5)
    assert math.isclose(rows[("wn", "gap_minus_lexicon_gap")]["estimate"], 0.5)
    assert rows[("lexicon", "recall_native_only")]["estimate"] == 1.0
    r = rows[("wn", "gap_translatable_minus_native")]
    assert r["lo"] <= r["estimate"] <= r["hi"]


def test_cli_requires_gold_or_dry_run():
    with pytest.raises(SystemExit):
        T.main([])


def test_item_class_and_reference_come_from_stage5_matches():
    it = T.item_record("c#1", ["L-HI-02"], {"lexicon": False}, {"L-HI-01"}, {"L-HI-01"})
    assert (it["cls"], it["ref"], it["detected"]["lexicon"]) == ("translatable", True, False)
    it = T.item_record("c#2", [], {"lexicon": True}, set(), set())
    assert (it["cls"], it["ref"]) == ("unmatched", False)
    assert T.item_record("c#3", [], {}, set(), set(), gold={"c#3": True})["ref"] is True


def test_gold_mode_keeps_hindi_clauses_only():
    clauses = [dict(clause_id="h#1", lang="hi"), dict(clause_id="e#1", lang="en")]
    cf = {"h#1": {"L-HI-01": "1", "L-EN-01": "0"}, "e#1": {"L-HI-01": "0", "L-EN-01": "1"}}
    got = T.gold_items({"h#1": True, "e#1": True, "x#9": False}, clauses, cf)
    assert [(c["clause_id"], m) for c, m in got] == [("h#1", ["L-HI-01"])]


def test_lexicon_scoring_without_stanza():
    lex = T.LM.load_lexicon(T.ROOT / "lexicon" / "lexicon.csv")
    s = T.LexScorer(lex).score("पापा हमें छोड़कर चले गए", "hi")
    assert s["entries"] and all(e.startswith(("L-HI", "P-HI")) for e in s["entries"])


import csv
import json
from argparse import Namespace
from pathlib import Path


def toks(*pairs):
    return [{T.LM.norm_word(f, "hi"), T.LM.norm_word(lm, "hi")} for f, lm in pairs]


def test_term_list_matches_like_the_lemma_channel():
    tl = T.TermList({"दुख", "दिल टूटना", "शोक़"})
    assert tl.n_terms == 3
    assert tl.hits(toks(("मुझे", "मैं"), ("दुख", "दुख")))
    assert tl.hits(toks(("दिल", "दिल"), ("टूट", "टूटना")))
    assert not tl.hits(toks(("दिल", "दिल"), ("बहुत", "बहुत"), ("टूट", "टूटना")))
    assert tl.hits(toks(("शोक", "शोक")))
    assert not tl.hits(toks(("दुखी", "दुखी")))


def test_iwn_reader_and_wordnet_route(tmp_path):
    p = tmp_path / "all.hindi"
    p.write_text("1\tशोक,ग़म,मातम\tदुख की भावना:\"...\"\tnoun\n2\tदुख,कष्ट\tपीड़ा\tnoun\nbad line\n", encoding="utf-8")
    iwn = T.load_iwn(p)
    assert iwn["lemmas"]["1"] == ["शोक", "गम", "मातम"] and iwn["by_lemma"]["कष्ट"] == {"2"}
    assert T.wordnet_route(["शोक।", "अनजान"], iwn) == {"शोक", "गम", "मातम", "अनजान"}
    assert T.load_iwn(tmp_path / "missing") is None


def test_bridge_translates_only_missing_headwords(tmp_path):
    calls = []

    def fake(ts):
        calls.append(list(ts))
        return [f"हिं {t}" for t in ts]
    cache = tmp_path / "b.json"
    assert T.bridge(["grief", "loss"], cache, fake) == {"grief": "हिं grief", "loss": "हिं loss"}
    assert T.bridge(["grief", "loss", "mourning"], cache, fake)["mourning"] == "हिं mourning"
    assert calls == [["grief", "loss"], ["mourning"]]


def test_entry_classes_give_the_molecules():
    lex = [dict(entry_id="L-HI-01", lang="hi", headword_deva="क", pos="noun"),
           dict(entry_id="L-HI-03", lang="hi", headword_deva="ख", pos="verb"),
           dict(entry_id="L-EN-01", lang="en", headword_deva="", pos="noun")]
    mol = [dict(molecule="shoulders", used_in="L-HI-01", why_unavoidable=""),
           dict(molecule="(tolerated) respect", used_in="L-HI-03", why_unavoidable="")]
    rows = {r["entry_id"]: r for r in T.entry_classes(lex, mol)}
    assert set(rows) == {"L-HI-01", "L-HI-03"}
    assert (rows["L-HI-01"]["entry_class"], rows["L-HI-01"]["native_molecules"]) == ("native_only", "shoulders")
    assert (rows["L-HI-03"]["entry_class"], rows["L-HI-03"]["entry_class_tolerated"]) == ("translatable", "native_only")
    assert rows["L-HI-03"]["tolerated_molecules"] == "respect"
    assert T.entry_class_counts(rows.values()) == dict(strict_native_only=1, strict_translatable=1,
                                                       tolerated_native_only=2, tolerated_translatable=0)


def test_entry_classes_on_the_frozen_lexicon():
    T.frozen_lexicon_ok()
    lex = list(csv.DictReader(open(T.ROOT / "lexicon" / "lexicon.csv", encoding="utf-8")))
    mol = list(csv.DictReader(open(T.ROOT / "lexicon" / "molecules.csv", encoding="utf-8")))
    rows = T.entry_classes(lex, mol)
    assert len(rows) == sum(r["lang"] == "hi" for r in lex)
    assert {r["entry_id"] for r in rows if r["entry_class"] == "native_only"} == T.native_only_entries(mol, lex)
    assert all(r["native_molecules"] for r in rows if r["entry_class"] == "native_only")


def _score_fixture(tmp_path):
    proc = tmp_path / "proc"
    short = proc / "shortform"
    short.mkdir(parents=True)
    tok_cols = ["clause_id", "token_index", "token", "lemma", "upos", "feats", "head", "deprel"]

    def write(dirp, clauses, tokens):
        with open(dirp / "clauses.jsonl", "w", encoding="utf-8") as fh:
            for c in clauses:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
        with open(dirp / "tokens.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(tok_cols)
            for cid, i, f, lm in tokens:
                w.writerow([cid, i, f, lm, "NOUN", "", 0, "root"])
    write(proc, [dict(record_id="blogs:a", clause_id="blogs:a#0001", lang="hi", clause_text="मुझे बहुत दुख है"),
                 dict(record_id="blogs:a", clause_id="blogs:a#0002", lang="hi", clause_text="मातम छा गया"),
                 dict(record_id="blogs:e", clause_id="blogs:e#0001", lang="en", clause_text="grief")],
          [("blogs:a#0001", 1, "मुझे", "मैं"), ("blogs:a#0001", 2, "बहुत", "बहुत"), ("blogs:a#0001", 3, "दुख", "दुख"),
           ("blogs:a#0002", 1, "मातम", "मातम"), ("blogs:a#0002", 2, "छा", "छाना"), ("blogs:e#0001", 1, "grief", "grief")])
    sc = dict(lang="hi", parse_lang="hi", register="short", source="ytcv_nonenglish")
    write(short, [dict(sc, record_id="yt:r", clause_id="yt:r#0001", clause_text="बहुत दुखी", translit=True),
                  dict(sc, record_id="yt:d", clause_id="yt:d#0001", clause_text="दुख", translit=False),
                  dict(sc, record_id="yt:e", clause_id="yt:e#0001", clause_text="sad", translit=True, lang="en")],
          [("yt:r#0001", 1, "बहुत", "बहुत"), ("yt:r#0001", 2, "दुखी", "दुख"), ("yt:d#0001", 1, "दुख", "दुख")])
    nrc = tmp_path / "nrc.txt"
    nrc.write_text("English Word\tsadness\tnegative\tHindi Word\nsorrow\t1\t1\tदुख\n", encoding="utf-8")
    iwn = tmp_path / "all.hindi"
    iwn.write_text("1\tशोक,मातम\tx\tnoun\n", encoding="utf-8")
    return Namespace(clauses=str(proc / "clauses.jsonl"), shortform=str(short), channels=str(tmp_path / "ch"),
                     results=str(tmp_path / "res"), nrc=str(nrc), hsl=str(tmp_path / "no_hsl"), iwn=str(iwn),
                     force=False, agreement=str(tmp_path / "agreement.csv"), gold=str(tmp_path / "gold.csv"),
                     B=50, seed=1, dry_run=False)


def test_score_mode_scores_every_hindi_clause_and_caches(tmp_path):
    args = _score_fixture(tmp_path)
    calls = []

    def fake(ts):
        calls.append(len(ts))
        return ["शोक" if t == "grief" else "अज्ञात" for t in ts]
    m = T.run_score(args, translate=fake)
    rows = {r["clause_id"]: r for r in csv.DictReader(open(Path(args.channels) / "a1_scores.csv", encoding="utf-8"))}
    assert set(rows) == {"blogs:a#0001", "blogs:a#0002", "yt:r#0001"}
    assert m["n_clauses"] == {"long": 2, "short_romanised": 1} and m["unavailable"] == ["hsl"]
    assert rows["yt:r#0001"]["register"] == "short_romanised" and rows["yt:r#0001"]["translit"] == "1"
    assert rows["yt:r#0001"]["det_nrc_hi"] == "1"
    assert (rows["blogs:a#0002"]["det_wordnet"], rows["blogs:a#0002"]["det_nrc_hi"]) == ("1", "0")
    assert "मुझे" not in (Path(args.channels) / "a1_scores.csv").read_text(encoding="utf-8")
    summary = list(csv.DictReader(open(Path(args.results) / "a1_scoring_summary.csv", encoding="utf-8")))
    assert {r["resource"] for r in summary} == {"lexicon", "nrc_hi", "wordnet", "hsl"}
    assert (Path(args.results) / "a1_entry_classes.csv").exists() and m["cached"] is False
    again = T.run_score(args, translate=fake)
    assert again["cached"] is True and len(calls) == 1


def test_gold_recall_is_refused_until_agreement_exists(tmp_path):
    args = _score_fixture(tmp_path)
    T.run_score(args, translate=lambda ts: ["शोक"] * len(ts))
    Path(args.gold).write_text("clause_id,emotional\nblogs:a#0001,1\nblogs:a#0002,1\nyt:r#0001,0\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="refused"):
        T.run_gold(args)
    Path(args.agreement).write_text("field,n_both_coded,alpha_nominal\norientation,0,\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="refused"):
        T.run_gold(args)
    Path(args.agreement).write_text("field,n_both_coded,alpha_nominal\norientation,40,0.71\n", encoding="utf-8")
    out = T.run_gold(args)
    assert out["n_items"] == 3
    rec = list(csv.DictReader(open(Path(args.results) / "a1_resource_recall.csv", encoding="utf-8")))
    assert {r["resource"] for r in rec} == {"lexicon", "nrc_hi", "wordnet"}


def test_gold_cli_refuses_without_agreement(tmp_path):
    with pytest.raises(SystemExit, match="refused"):
        T.main(["--gold", str(tmp_path / "g.csv"), "--agreement", str(tmp_path / "none.csv")])


def test_no_network_route_in_the_script():
    src = Path(T.__file__).read_text(encoding="utf-8")
    for banned in ("api_client", "requests", "urllib", "httpx", "pyiwn", "googletrans", "deep_translator"):
        assert f"import {banned}" not in src and f"from {banned}" not in src
    assert "local_files_only=True" in src and T.NLLB["revision"]
