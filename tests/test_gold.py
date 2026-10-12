import csv
import json

import pytest

import gold as G


def corpus(n_texts=60, per_text=40):
    out = []
    for lang in ("hi", "en"):
        for t in range(n_texts):
            rid = f"toy:{lang}{t:03d}"
            for p in range(1, per_text + 1):
                out.append(dict(record_id=rid, lang=lang, clause_id=f"{rid}#{p:04d}", position=p,
                                clause_text=f"{lang} text {t} clause {p}", span_text=f"{lang} {t} span {p}.",
                                is_finite=p % 2 == 1))
    return out


def run(tmp_path, clauses, *extra):
    src = tmp_path / "clauses.jsonl"
    src.write_text("".join(json.dumps(c) + "\n" for c in clauses), encoding="utf-8")
    G.main(["--in", str(src), "--features", str(tmp_path / "none.csv"), "--released-ids", str(tmp_path / "none.csv"),
            "--split-out", str(tmp_path / "split.csv"), "--out-dir", str(tmp_path / "ann"), *extra])
    return tmp_path / "ann"


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_split_is_deterministic_and_near_30_percent():
    ids = [f"toy:{i}" for i in range(4000)]
    assert [G.split_of(r) for r in ids] == [G.split_of(r) for r in ids]
    assert 0.27 < sum(G.split_of(r) == "dev" for r in ids) / len(ids) < 0.33


def test_water_fill_is_even_and_capped():
    import random
    alloc = G.water_fill({"a": 2, "b": 100, "c": 100, "d": 100}, 30, 15, random.Random(1))
    assert alloc["a"] == 2 and sum(alloc.values()) == 30 and max(alloc.values()) <= 15
    short = G.water_fill({"a": 100, "b": 100}, 300, 15, random.Random(1))
    assert short == {"a": 15, "b": 15}


def test_draw_uses_dev_only_finite_only_and_respects_cap(tmp_path):
    ann = run(tmp_path, corpus(), "--dry-run")
    key = read(ann / "gold_key_v1.csv")
    split = {r["record_id"]: r["split"] for r in read(tmp_path / "split.csv")}
    assert all(split[k["record_id"]] == "dev" for k in key)
    assert all(int(k["position"]) % 2 == 1 for k in key)
    for lang in ("hi", "en"):
        per_text = {}
        for k in key:
            if k["lang"] == lang:
                per_text[k["record_id"]] = per_text.get(k["record_id"], 0) + 1
        assert max(per_text.values()) <= 15


def test_sheets_are_blind_with_context_and_identical_copies(tmp_path):
    ann = run(tmp_path, corpus(), "--dry-run")
    sheet = read(ann / "gold_sheet_v1.csv")
    assert list(sheet[0]) == G.SHEET_COLUMNS
    assert not any("toy:" in v for r in sheet for v in r.values())
    assert all(r[f] == "" for r in sheet for f in G.CODEBOOK)
    assert (ann / "gold_sheet_v1_coder1.csv").read_text() == (ann / "gold_sheet_v1_coder2.csv").read_text()
    key = {k["gold_id"]: k for k in read(ann / "gold_key_v1.csv")}
    r = sheet[0]
    p = int(key[r["gold_id"]]["position"])
    assert r["context_before"].endswith(f"span {p - 1}.") and r["context_after"].endswith(f"span {p + 1}.")
    comp = read(ann / "gold_components_v1_coder1.csv")
    assert len(comp) == 100
    assert len(read(ann / "gold_shortform_placeholder_v1.csv")) == 400
    assert len({r["gold_id"] for r in sheet}) == len(sheet)


def test_final_draw_is_locked(tmp_path):
    run(tmp_path, corpus())
    with pytest.raises(SystemExit):
        run(tmp_path, corpus(), "--dry-run")


def test_pilot_is_dev_only_one_per_text_and_excludes_gold_and_examples(tmp_path, monkeypatch):
    import codebook_examples
    clauses = corpus()
    dev_finite = [c for c in clauses if G.split_of(c["record_id"]) == "dev" and c["is_finite"]]
    banned_example = dev_finite[0]["clause_id"]
    monkeypatch.setattr(codebook_examples, "EXAMPLES", [("orientation", "I", "hi", banned_example, "test")])
    ann = run(tmp_path, clauses, "--dry-run")
    main_ids = {k["clause_id"] for k in read(ann / "gold_key_v1.csv")}
    run(tmp_path, clauses, "--pilot")
    key = read(ann / "gold_pilot_key.csv")
    split = {r["record_id"]: r["split"] for r in read(tmp_path / "split.csv")}
    assert len(key) == 40 and {k["lang"] for k in key} == {"hi", "en"}
    assert all(split[k["record_id"]] == "dev" for k in key)
    assert not any(G.split_of(k["record_id"]) == "confirmatory" for k in key)
    for lang in ("hi", "en"):
        texts = [k["record_id"] for k in key if k["lang"] == lang]
        assert len(texts) == len(set(texts)) == 20
    ids = {k["clause_id"] for k in key}
    assert not ids & main_ids and banned_example not in ids
    r1, r2 = read(ann / "gold_pilot_r1.csv"), read(ann / "gold_pilot_r2.csv")
    assert r1 == r2 and list(r1[0]) == G.SHEET_COLUMNS
    assert not any("toy:" in v for r in r1 for v in r.values())
    by_gid = {k["gold_id"]: k for k in key}
    text = {c["clause_id"]: c["clause_text"] for c in clauses}
    assert all(text[by_gid[r["gold_id"]]["clause_id"]] == r["clause_text"] for r in r1)


def test_pilot_never_reaches_confirmatory_even_when_dev_is_small(tmp_path):
    ann = run(tmp_path, corpus(n_texts=12), "--pilot")
    key = read(ann / "gold_pilot_key.csv")
    assert key and all(G.split_of(k["record_id"]) == "dev" for k in key)


def test_pilot_clauses_are_excluded_from_the_main_draw(tmp_path):
    key = tmp_path / "gold_pilot_key.csv"
    key.write_text("gold_id,clause_id,record_id,lang\nGRF-aaaa,r:1#0001,r:1,hi\nGRF-bbbb,r:2#0003,r:2,en\n",
                   encoding="utf-8")
    clauses, ids = G.pilot_exclusions(key)
    assert clauses == {"r:1#0001", "r:2#0003"} and ids == {"GRF-aaaa", "GRF-bbbb"}
    assert G.pilot_exclusions(tmp_path / "none.csv") == (set(), set())
    import inspect
    assert "pilot_exclusions(out / \"gold_pilot_key.csv\")" in inspect.getsource(G.main)


def test_replace_final_only_while_every_sheet_is_blank(tmp_path):
    clauses = corpus()
    ann = run(tmp_path, clauses)
    with pytest.raises(SystemExit, match="final draw"):
        run(tmp_path, clauses)
    run(tmp_path, clauses, "--replace-final")
    assert any(p.name.startswith("gold_manifest_v1.replaced-") for p in ann.iterdir())
    sheet = ann / "gold_sheet_v1_coder2.csv"
    rows = read(sheet)
    rows[0]["orientation"] = "F"
    with open(sheet, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(SystemExit, match="coding has begun"):
        run(tmp_path, clauses, "--replace-final")
