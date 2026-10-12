import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("apply_adjudication", ROOT / "scripts/apply_adjudication.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


def write(p, rows):
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def read(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def test_majority_apply_and_log(tmp_path, monkeypatch):
    dis = tmp_path / "dis.csv"
    write(dis, [dict(gold_id="G1", lang="hi", field="orientation", coder1="I", coder2="F"),
                dict(gold_id="G2", lang="en", field="orientation", coder1="I", coder2="F"),
                dict(gold_id="G3", lang="en", field="target", coder1="kin", coder2="self")])
    comp = tmp_path / "comp.csv"
    write(comp, [dict(gold_id="G1", lang="hi", field="KIN", coder1="1", coder2="0")])
    third = tmp_path / "third.csv"
    write(third, [dict(sheet="codebook", gold_id="G1", field="orientation", third="F"),
                  dict(sheet="codebook", gold_id="G2", field="orientation", third="I"),
                  dict(sheet="codebook", gold_id="G3", field="target", third="none"),
                  dict(sheet="components", gold_id="G1", field="KIN", third="0")])
    cb, cp = tmp_path / "cb.csv", tmp_path / "cp.csv"
    write(cb, [dict(gold_id=g, orientation="", target="", provenance="old", corrections="0") for g in ("G1", "G2", "G3")])
    write(cp, [dict(gold_id="G1", KIN="", provenance="old", corrections="0")])
    dec, log = tmp_path / "dec.csv", tmp_path / "log.csv"
    monkeypatch.setattr(A, "DISAGREEMENTS", {"codebook": dis, "components": comp})
    monkeypatch.setattr(A, "SHEETS", {"codebook": cb, "components": cp})
    monkeypatch.setattr(A, "DEC", dec)
    monkeypatch.setattr(A, "LOG", log)
    n = A.majority(third, "third coder: m 2026-10-11", dec)
    assert n == {"coder1": 1, "coder2": 2, "unresolved": 1}
    d = {(r["gold_id"], r["field"]): r for r in read(dec)}
    assert d[("G3", "target")]["decision"] == "" and d[("G3", "target")]["source"] == "unresolved_three_way"
    assert d[("G1", "orientation")]["source"] == "majority_with_third_coder"
    for _ in range(2):
        monkeypatch.setattr(sys, "argv", ["x", "--decisions", str(dec), "--provenance", "NEW"])
        A.main()
    rows = read(cb)
    assert [r["orientation"] for r in rows] == ["F", "I", ""] and rows[2]["target"] == ""
    assert {r["provenance"] for r in rows + read(cp)} == {"NEW"} and read(cp)[0]["KIN"] == "0"
    lg = read(log)
    assert len(lg) == 4 and sum(r["source"] == "unresolved_three_way" for r in lg) == 1
    assert "clause_text" not in lg[0] and "note" not in lg[0]
