import make_all as M


def test_file_stats_and_compare(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    (tmp_path / "a.csv").write_text("h1,h2\n1,2\n3,4\n\n", encoding="utf-8")
    (tmp_path / "b.jsonl").write_text('{"x": 1}\n{"x": 2}\n', encoding="utf-8")
    a, b = M.file_stats("a.csv"), M.file_stats("b.jsonl")
    assert a["rows"] == 2 and b["rows"] == 2 and len(a["sha256"]) == 64
    assert M.file_stats("missing.csv") is None
    assert M.compare(a, a) == "same" and M.compare(None, a) == "new" and M.compare(a, None) == "missing"
    (tmp_path / "a.csv").write_text("h1,h2\n1,2\n3,5\n", encoding="utf-8")
    assert M.compare(a, M.file_stats("a.csv")) == "changed"


def test_order_and_last_writer():
    assert M.STEP_NAMES == ["preprocess", "flags", "lexmatch", "referents", "eligibility", "decompose_relational",
                            "text_meta"]
    assert M.LAST_WRITER["data/processed/flags.csv"] == "eligibility"
    assert M.LAST_WRITER["data/processed/text_features.csv"] == "referents"


def test_snapshot_records_each_file_once(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "ROOT", tmp_path)
    records, failed = M.run(M.STEPS, snapshot=True)
    listed = [o for r in records for o in r["outputs"]]
    assert failed is None and len(listed) == len(set(listed)) == len(M.LAST_WRITER)


def test_summary_without_a_run(tmp_path, capsys):
    assert M.summary(tmp_path / "repro_check.md", tmp_path / "manifest.json") == 1
    assert "no run recorded" in capsys.readouterr().out
