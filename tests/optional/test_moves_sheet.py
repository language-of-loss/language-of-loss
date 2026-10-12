import json

from test_human_sheets import corpus, read

import moves_sheet as MS


def test_moves_sheet_blind_ordered_and_round_trip(corpus, monkeypatch):
    tmp, recs = corpus
    monkeypatch.setattr(MS, "split_of", lambda r: "dev" if r.endswith(("1", "2")) else "confirmatory")
    monkeypatch.setattr(MS, "EXAMPLES", [("blogs:t2", 2, "memory")])
    out = tmp / "ann"
    MS.main(["--records", str(tmp / "recs.jsonl"), "--in", str(tmp / "clauses.jsonl"), "--out-dir", str(out)])
    sheet, key = read(out / "moves_sheet.csv"), read(out / "moves_key.csv")
    assert read(out / "moves_sheet_r1.csv") == read(out / "moves_sheet_r2.csv") == sheet
    assert list(sheet[0]) == MS.SHEET and len(sheet) == len(key) == 2 * 2 + 2 * 3
    seen = json.dumps(sheet, ensure_ascii=False)
    for r in recs:
        assert r["record_id"] not in seen and r["source_url"] not in seen
    assert "confirmatory" not in seen
    by_uid = {k["unit_id"]: k for k in key}
    rebuilt = {}
    for row in sheet:
        k = by_uid[row["unit_id"]]
        assert (k["text_id"], k["unit_no"], k["lang"]) == (row["text_id"], row["unit_no"], row["lang"])
        rebuilt.setdefault(k["record_id"], []).append((int(row["unit_no"]), row["unit_text"], row["prev_unit"]))
    for r in recs:
        units = sorted(rebuilt[r["record_id"]])
        assert [u for _, u, _ in units] == MS.units(r["text_clean"])
        assert [p for _, _, p in units] == [""] + [u for _, u, _ in units[:-1]]
    ex = [k for k in key if k["codebook_example"]]
    assert [(k["record_id"], k["unit_no"], k["codebook_example"]) for k in ex] == [("blogs:t2", "2", "memory")]
    assert "Second line here." in (out / "moves_codebook_examples.md").read_text()


def test_codebook_examples_are_dev_only_two_per_move_per_language():
    from collections import Counter
    from gold import split_of
    assert all(split_of(r) == "dev" for r, _, _ in MS.EXAMPLES)
    langs = {r: ("hi" if r in HI_RECORDS else "en") for r, _, _ in MS.EXAMPLES}
    c = Counter((m, langs[r]) for r, _, m in MS.EXAMPLES)
    assert set(m for m, _ in c) == set(MS.MOVES) and set(c.values()) == {2}


HI_RECORDS = {"blogs:blog_ff5322367bcf", "blogs:blog_56eb08c9fd16", "blogs:blog_8b666dd3f7e4", "blogs:cw_8d3d92bb074b",
              "blogs:cw_f5baf36bd55e", "blogs:cw_6a2c0609408b", "blogs:blog_dddd37b0b32a", "blogs:cw_95e0259c53b1",
              "blogs:blog_0861b4d96495", "blogs:blog_5aa741918356"}
