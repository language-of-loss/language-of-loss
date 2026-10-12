import csv
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import apply_review as AR
import build_review_master as BRM

LOCAL = [ROOT / "docs" / "review_master_2026-10.csv", ROOT / "data" / "clean" / "blogs_merged.jsonl",
         ROOT / "data" / "interim" / "blogs_extracted.jsonl"]


def row(rid, decision, reviewer=""):
    return {"review_id": rid, "decision": decision, "reviewer": reviewer}


def test_blank_decision_refuses():
    errs = AR.validate([row("RV-1", "yes", "a"), row("RV-2", " ")])
    assert any("blank decision" in e and "RV-2" in e for e in errs)


def test_invalid_value_and_missing_reviewer_refuse():
    errs = AR.validate([row("RV-1", "accept", "a"), row("RV-2", "yes")])
    assert any("not yes/no/maybe" in e for e in errs) and any("without reviewer" in e for e in errs)


def test_filled_sheet_passes():
    assert AR.validate([row("RV-1", "Yes", "a"), row("RV-2", "no"), row("RV-3", "maybe")]) == []


def test_url_normalisation_and_domain_folding():
    assert BRM.norm_url("http://www.Example.com/a/") == BRM.norm_url("https://example.com/a")
    assert BRM.domain_covariate("m.sahityakunj.net") == "sahityakunj.net"
    assert BRM.domain_covariate("hindi.pratilipi.com") == "pratilipi.com"
    assert BRM.review_id("https://www.x.in/p/") == BRM.review_id("http://x.in/p")


@pytest.mark.skipif(not all(p.exists() for p in LOCAL), reason="needs local (git-ignored) corpus and review files")
def test_accepted_rows_enter_corpus_with_provenance(tmp_path, monkeypatch):
    rows = list(csv.DictReader(open(LOCAL[0], encoding="utf-8")))
    for i, r in enumerate(rows):
        r["decision"], r["reviewer"] = ("yes", "tester") if i < 2 else ("no", "")
    merged, ledger, report = tmp_path / "merged.jsonl", tmp_path / "ledger.jsonl", tmp_path / "report.md"
    with open(LOCAL[1], encoding="utf-8") as src, open(merged, "w", encoding="utf-8") as dst:
        dst.writelines(l for l in src if json.loads(l)["review_status"] != AR.REVIEW_STATUS)
    report.write_text("# base\n")
    monkeypatch.setattr(AR, "MERGED", merged)
    monkeypatch.setattr(AR, "LEDGER", ledger)
    monkeypatch.setattr(AR, "REPORT", report)
    monkeypatch.setattr(AR.subprocess, "run", lambda *a, **k: None)
    recs, stats = AR.update_ledger(rows, "2026-10-10", dry_run=False)
    AR.rebuild(recs, stats, dry_run=False)
    out = [json.loads(l) for l in merged.open(encoding="utf-8")]
    added = [r for r in out if r["review_status"] == AR.REVIEW_STATUS]
    base_n = sum(1 for l in LOCAL[1].open(encoding="utf-8") if json.loads(l)["review_status"] != AR.REVIEW_STATUS)
    assert len(added) == 2 and len(out) == base_n + 2
    rv = added[0]["extra"]["review"]
    assert rv["reviewer"] == "tester" and rv["review_date"] == "2026-10-10" and rv["pass"] in ("v1.1", "v1.2", "v1.3", "v1.4")
    assert added[0]["text_clean"] and added[0]["dedup_key"] and "domain_covariate" in added[0]["extra"]
    assert "Review additions" in report.read_text()
    rows[0]["decision"] = "no"
    recs, _ = AR.update_ledger(rows, "2026-10-11", dry_run=False)
    assert len(recs) == 1
