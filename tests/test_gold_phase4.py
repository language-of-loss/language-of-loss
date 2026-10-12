import csv
import json
import math
from collections import Counter
from pathlib import Path

import pytest

import agreement as AG
import core as C
import corrected_rates as CR
import gold as G
import mcnemar as MC
import predictions as P

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "annotation"
OK_AGREEMENT = "field,n_both_coded,alpha_nominal\norientation,40,0.72\n"


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write(path, rows, fields=None):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def test_assert_blind_rejects_machine_columns(tmp_path):
    ok = write(tmp_path / "ok.csv", [dict.fromkeys(G.SHEET_COLUMNS, "")])
    assert G.assert_blind(ok, G.SHEET_COLUMNS) == G.SHEET_COLUMNS
    bad = write(tmp_path / "bad.csv", [dict.fromkeys(G.SHEET_COLUMNS + ["lexicon_hit"], "")])
    with pytest.raises(ValueError, match="lexicon_hit"):
        G.assert_blind(bad, G.SHEET_COLUMNS + ["lexicon_hit"])


@pytest.mark.skipif(not (ANN / "gold_key_v1.csv").exists(), reason="data/annotation is local")
def test_real_gold_set_is_blind_capped_dev_only_and_disjoint():
    from codebook_examples import example_ids
    key = read(ANN / "gold_key_v1.csv")
    manifest = json.loads((ANN / "gold_manifest_v1.json").read_text())
    for coder in ("coder1", "coder2"):
        G.assert_blind(ANN / f"gold_sheet_v1_{coder}.csv", G.SHEET_COLUMNS)
        comps = G.components_list(ROOT / "lexicon")
        G.assert_blind(ANN / f"gold_components_v1_{coder}.csv", G.SHEET_TEXT + comps + ["notes"])
    s1, s2 = read(ANN / "gold_sheet_v1_coder1.csv"), read(ANN / "gold_sheet_v1_coder2.csv")
    text = lambda rows: [{k: r[k] for k in G.SHEET_TEXT} for r in rows]
    assert text(s1) == text(s2) and len(s1) == len(key)
    master = read(ANN / "gold_sheet_v1.csv")
    assert text(master) == text(s1) and not any(r[f] for r in master for f in G.CODEBOOK)
    assert all(G.split_of(k["record_id"]) == "dev" for k in key)
    for lang in ("hi", "en"):
        rep = manifest["per_language"][lang]
        per_text = Counter(k["record_id"] for k in key if k["lang"] == lang)
        assert max(per_text.values()) <= int(manifest["max_text_share"] * rep["target"])
        assert sum(per_text.values()) == rep["target"] - rep["shortfall"]
        assert sum(int(k["in_component_subset"]) for k in key if k["lang"] == lang) == rep["component_subset"]
    pilot = read(ANN / "gold_pilot_key.csv")
    assert not ({k["clause_id"] for k in key} & ({p["clause_id"] for p in pilot} | set(example_ids())))
    assert manifest["draw_status"] in ("dry_run", "final") and len(manifest["input_sha256"]) == 64


@pytest.mark.skipif(not (ANN / "gold_pilot_key.csv").exists(), reason="data/annotation is local")
def test_real_pilot_is_blind_dev_clauses_spread_over_texts():
    pilot = read(ANN / "gold_pilot_key.csv")
    n = Counter(p["lang"] for p in pilot)
    assert n["hi"] == n["en"] and all(G.split_of(p["record_id"]) == "dev" for p in pilot)
    for lang in ("hi", "en"):
        per = Counter(p["record_id"] for p in pilot if p["lang"] == lang)
        assert max(per.values()) - min(per.values()) <= 1
    for r in ("r1", "r2"):
        G.assert_blind(ANN / f"gold_pilot_{r}.csv", G.SHEET_COLUMNS)


def coded_sheet(path, codes):
    rows = [dict(dict.fromkeys(G.SHEET_COLUMNS, ""), gold_id=f"GRF-{i}", lang="hi", orientation=o, process=p)
            for i, (o, p) in enumerate(codes)]
    return write(path, rows, G.SHEET_COLUMNS)


def test_agreement_writes_the_guard_file_that_unlocks_the_tests(tmp_path, monkeypatch):
    a = coded_sheet(tmp_path / "gold_sheet_v1_coder1.csv", [("F", "L"), ("I", "L"), ("C", "Rs"), ("F", "NA")] * 5)
    b = coded_sheet(tmp_path / "gold_sheet_v1_coder2.csv", [("F", "L"), ("I", "Rs"), ("C", "Rs"), ("I", "NA")] * 5)
    out = tmp_path / "results" / "agreement"
    AG.main(["--a", str(a), "--b", str(b), "--out-dir", str(out), "--disagreements", str(tmp_path / "dis.csv")])
    guard = out / C.AGREEMENT.split("/")[-1]
    assert guard.name == "agreement_summary_gold_sheet_v1.csv" and guard.exists()
    assert P.tests_allowed(guard)
    monkeypatch.setattr(C, "ROOT", tmp_path)
    assert C.agreement_ok()[1]()


def test_blank_sheets_write_a_guard_file_that_stays_locked(tmp_path):
    a = coded_sheet(tmp_path / "gold_sheet_v1_coder1.csv", [("", "")] * 4)
    b = coded_sheet(tmp_path / "gold_sheet_v1_coder2.csv", [("", "")] * 4)
    out = tmp_path / "agreement"
    AG.main(["--a", str(a), "--b", str(b), "--out-dir", str(out), "--disagreements", str(tmp_path / "dis.csv")])
    assert not P.tests_allowed(out / "agreement_summary_gold_sheet_v1.csv")


@pytest.mark.skipif(not (ROOT / "data" / "annotation").exists(),
                    reason="needs data/annotation (not in the public release)")
def test_the_real_guard_stays_locked_while_the_sheets_are_uncoded():
    if not C.coded("data/annotation/gold_sheet_v1_coder1.csv"):
        assert not P.tests_allowed(ROOT / C.AGREEMENT)


def cr_inputs(tmp_path, status="gold v1, adjudicated"):
    vt = write(tmp_path / "validation_table.csv", [
        dict(channel="dict", field="orientation", value="F", lang=lg, n_items=100, tp=0, fp=0, fn=0, tn=0, precision="",
             recall="", f1="", measure="dict:orientation=F", sensitivity=s, fpr=f, n_pos=40, n_neg=60, status=status)
        for lg, s, f in (("hi", 0.8, 0.1), ("en", 0.6, 0.05))])
    clauses, dict_rows = [], []
    for lang, rec, n, k in (("hi", "blogs:h1", 10, 4), ("hi", "blogs:h2", 10, 2), ("en", "blogs:e1", 10, 3)):
        for i in range(n):
            cid = f"{rec}#{i + 1:04d}"
            clauses.append(dict(clause_id=cid, record_id=rec, lang=lang, is_finite=True))
            dict_rows.append(dict(clause_id=cid, orientation="F" if i < k else "I", evidence=""))
    cp = tmp_path / "clauses.jsonl"
    cp.write_text("".join(json.dumps(c) + "\n" for c in clauses))
    dp = write(tmp_path / "dict_channel.csv", dict_rows)
    (tmp_path / "agr.csv").write_text(OK_AGREEMENT)
    return ["--validation", str(vt), "--dict", str(dp), "--clauses", str(cp), "--agreement", str(tmp_path / "agr.csv"),
            "--split", "all", "--B", "200", "--out", str(tmp_path / "cr.csv")]


def test_corrected_rates_follow_rogan_gladen(tmp_path):
    CR.main(cr_inputs(tmp_path))
    rows = {r["lang"]: r for r in read(tmp_path / "cr.csv")}
    o_hi = (0.4 + 0.2) / 2
    assert math.isclose(float(rows["hi"]["observed"]), o_hi)
    assert math.isclose(float(rows["hi"]["corrected"]), (o_hi - 0.1) / (0.8 - 0.1), rel_tol=1e-5)
    assert math.isclose(float(rows["en"]["corrected"]), (0.3 - 0.05) / (0.6 - 0.05), rel_tol=1e-5)
    d = read(tmp_path / "cr_hi_minus_en.csv")[0]
    assert d["gap_ok"] == "False"


def test_corrected_rates_refuse_pilot_validation_and_missing_agreement(tmp_path):
    with pytest.raises(SystemExit, match="refusing"):
        CR.main(cr_inputs(tmp_path, status="pilot mechanics, not validation"))
    args = cr_inputs(tmp_path)
    (tmp_path / "agr.csv").write_text("field,n_both_coded,alpha_nominal\norientation,0,\n")
    with pytest.raises(SystemExit, match="agreement"):
        CR.main(args)


def mc_inputs(tmp_path, agreement=OK_AGREEMENT):
    gold = [1, 1, 1, 1, 0, 0, 0, 0, 1, 0]
    tr = [1, 0, 0, 1, 0, 1, 0, 0, 0, 0]
    na = [1, 1, 1, 1, 0, 0, 0, 1, 1, 0]
    g = write(tmp_path / "gold.csv", [dict(clause_id=f"c#{i}", emotional=v) for i, v in enumerate(gold)])
    t = write(tmp_path / "t.csv", [dict(clause_id=f"c#{i}", pred=v) for i, v in enumerate(tr)])
    n = write(tmp_path / "n.csv", [dict(clause_id=f"c#{i}", pred=v) for i, v in enumerate(na)])
    (tmp_path / "agr.csv").write_text(agreement)
    return ["--gold", str(g), "--translated", str(t), "--native", str(n), "--agreement", str(tmp_path / "agr.csv"),
            "--out", str(tmp_path / "mc.csv")]


def test_mcnemar_counts_and_exact_p(tmp_path):
    from scipy.stats import binomtest
    MC.main(mc_inputs(tmp_path))
    q = {r["quantity"]: r["value"] for r in read(tmp_path / "mc.csv")}
    assert (q["discordant_translated_right_native_wrong"], q["discordant_native_right_translated_wrong"]) == ("1", "4")
    assert math.isclose(float(q["mcnemar_exact_p_two_sided"]), binomtest(1, 5, 0.5).pvalue, rel_tol=1e-5)
    assert q["n_clauses"] == "10"


def test_mcnemar_is_guarded(tmp_path):
    with pytest.raises(SystemExit, match="agreement"):
        MC.main(mc_inputs(tmp_path, agreement="field,n_both_coded,alpha_nominal\norientation,0,\n"))
