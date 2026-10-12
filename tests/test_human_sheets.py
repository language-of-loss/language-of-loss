import csv
import json

import pytest

import audit_passages as A

FILL_HI, FILL_EN = " शब्द" * 44, " word" * 42
HI = f"पहला वाक्य{FILL_HI} है। दूसरा वाक्य{FILL_HI} है।\nतीसरा वाक्य{FILL_HI} है।"
EN = f"First line here{FILL_EN}.\nSecond line here.{FILL_EN}\n\nThird line here{FILL_EN}."


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_best_window_prefers_density_within_bounds():
    words = [50, 40, 40, 50, 300, 60]
    scores = [0, 8, 8, 0, 50, 1]
    assert A.best_window(words, scores) == (1, 2, "")
    assert A.best_window([30, 20], [1, 1]) is None
    assert A.best_window([300, 250], [1, 9]) is None
    assert A.best_window([50, 50], [0, 0]) is None


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "split_of", lambda r: "dev" if r.endswith(("1", "2")) else "confirmatory")
    recs, clauses = [], []
    cache = tmp_path / "stanza_cache"
    for i, (lang, text) in enumerate([("hi", HI), ("en", EN), ("hi", HI), ("en", EN)], 1):
        rid = f"blogs:t{i}"
        recs.append(dict(record_id=rid, lang_provisional="devanagari_hindi" if lang == "hi" else "english",
                         text_clean=text, source_url=f"https://example.org/{i}"))
        prepared = A.prepare_text(text, lang)
        sents, start = [], 0
        for k, line in enumerate(l for l in prepared.split("\n") if l.strip()):
            a = prepared.index(line, start)
            ws, pos = [], a
            for w in line.split():
                p = prepared.index(w, pos)
                ws.append(dict(text=w, upos="NOUN", start=p, end=p + len(w)))
                pos = p + len(w)
            sents.append(ws)
            start = a + len(line)
            clauses.append(dict(record_id=rid, lang=lang, clause_id=f"{rid}#{k + 1:04d}", sent_index=k))
        (cache / lang).mkdir(parents=True, exist_ok=True)
        (cache / lang / f"blogs_t{i}.json").write_text(json.dumps(dict(record_id=rid, sentences=sents)))
    (tmp_path / "recs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
    (tmp_path / "clauses.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in clauses))
    with open(tmp_path / "feat.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["clause_id", "L-HI-01", "L-HI-C2", "flag_F1"])
        for c in clauses:
            w.writerow([c["clause_id"], 1 if c["clause_id"].endswith("2") else 0, 1, 0])
    return tmp_path, recs


def test_audit_sheets_blind_interleaved_and_round_trip(corpus):
    tmp, recs = corpus
    out, proc = tmp / "ann", tmp / "proc"
    A.main(["--records", str(tmp / "recs.jsonl"), "--in", str(tmp / "clauses.jsonl"), "--features",
            str(tmp / "feat.csv"), "--out-dir", str(out), "--processed-out", str(proc), "--shortform",
            str(tmp / "no_shortform.jsonl"), "--brighter", str(tmp / "no_brighter.parquet")])
    master = {r["passage_id"]: r for r in read(out / "audit_passages.csv")}
    key = read(out / "audit_key.csv")
    r1, r2 = read(out / "audit_rating_sheet_r1.csv"), read(out / "audit_rating_sheet_r2.csv")
    assert list(r1[0]) == A.SHEET and len(r1) == len(r2) == len(master) == 2
    assert {m["record_id"] for m in master.values()} == {"blogs:t1", "blogs:t2"}
    seen = json.dumps(r1 + r2, ensure_ascii=False)
    for r in recs:
        assert r["record_id"] not in seen and r["source_url"] not in seen
    assert "confirmatory" not in seen and "AP-" not in seen and "long" not in seen
    assert {r["lang"] for r in r1} == {"hi", "en"}
    for sheet, col in ((r1, "order_r1"), (r2, "order_r2")):
        by_id = {k["rating_id"]: k for k in key}
        for pos, row in enumerate(sheet, 1):
            k = by_id[row["rating_id"]]
            assert int(k[col]) == pos
            m = master[k["passage_id"]]
            assert m["passage_text"] == row["passage_text"] and m["record_id"] == k["record_id"]
            assert k["passage_sha256"] == A.sha(row["passage_text"]) and k["source_url"].startswith("https://")
    assert all(int(m["score"]) == 1 and 80 <= int(m["words"]) <= 200 for m in master.values())
    assert (proc / "audit_passage_components.csv").exists() and (proc / "audit_manifest.json").exists()
    assert not (out / "audit_calibration_key.csv").exists()
