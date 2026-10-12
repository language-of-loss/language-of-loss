import csv
import math

import agreement as A
from gold import SHEET_COLUMNS

ROWS = [
    ("GRF-1", "I", "I", "self", "self"),
    ("GRF-2", "I", "F", "kin", "kin"),
    ("GRF-3", "F", "F", "deceased", "deceased"),
    ("GRF-4", "F", "f", "God", ""),
]


def sheet(path, coder):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS, restval="")
        w.writeheader()
        for gid, o1, o2, e1, e2 in ROWS:
            w.writerow(dict(gold_id=gid, lang="hi", clause_text=f"clause {gid}",
                            orientation=o1 if coder == 1 else o2, experiencer=e1 if coder == 1 else e2))
    return path


def test_alpha_matches_hand_computation():
    assert math.isclose(A.alpha_nominal([("a", "a"), ("a", "b"), ("b", "b"), ("b", "b")]), 8 / 15, abs_tol=1e-9)
    assert A.alpha_nominal([("a", "a"), ("b", "b")]) == 1.0
    assert math.isnan(A.alpha_nominal([("a", "a"), ("a", "a")]))


def test_canon_is_case_insensitive_and_keeps_unknowns():
    assert A.canon(" f ", "orientation") == "F"
    assert A.canon("god", "experiencer") == "God"
    assert A.canon("X", "orientation") == "X"


def test_toy_pair_end_to_end(tmp_path):
    a, b = sheet(tmp_path / "c1.csv", 1), sheet(tmp_path / "c2.csv", 2)
    dis = tmp_path / "dis.csv"
    A.main(["--a", str(a), "--b", str(b), "--out-dir", str(tmp_path / "out"), "--disagreements", str(dis)])
    summ = {r["field"]: r for r in csv.DictReader(open(tmp_path / "out" / "agreement_summary_c1.csv"))}
    assert set(summ) == set(A.CODEBOOK)
    o = summ["orientation"]
    assert (o["n_both_coded"], o["n_agree"], o["pct_agree"]) == ("4", "3", "75.0")
    assert math.isclose(float(o["alpha_nominal"]), 8 / 15, abs_tol=1e-3)
    e = summ["experiencer"]
    assert (e["n_both_coded"], e["alpha_nominal"]) == ("3", "1.0")
    assert summ["target"]["alpha_nominal"] == ""
    conf = [r for r in csv.DictReader(open(tmp_path / "out" / "confusion_c1.csv")) if r["field"] == "orientation"]
    assert {(r["coder1"], r["coder2"]): int(r["n"]) for r in conf} == {("I", "I"): 1, ("I", "F"): 1, ("F", "F"): 2}
    flagged = {(r["gold_id"], r["field"]) for r in csv.DictReader(open(dis))}
    assert flagged == {("GRF-2", "orientation"), ("GRF-4", "experiencer")}


def test_sheet_label_keeps_codebook_and_components_apart():
    assert A.sheet_label("data/annotation/gold_sheet_v1_coder1.csv") == "gold_sheet_v1"
    assert A.sheet_label("gold_components_v1_coder1.csv") == "gold_components_v1"
    assert A.sheet_label("gold_pilot_r1.csv") == "gold_pilot"


def test_duplicate_gold_id_is_an_error(tmp_path):
    p = tmp_path / "dup.csv"
    p.write_text("gold_id,lang,orientation\nGRF-1,hi,F\nGRF-1,hi,I\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError, match="duplicate gold_id"):
        A.read_sheet(p)


def test_provenance_is_carried_into_the_summary_and_never_compared(tmp_path):
    import csv as _csv
    import agreement as A
    prov = "machine pre-filled (test), reviewed"
    for name, val in (("s_coder1.csv", "I"), ("s_coder2.csv", "F")):
        with open(tmp_path / name, "w", encoding="utf-8", newline="") as fh:
            w = _csv.writer(fh)
            w.writerow(["gold_id", "lang", "clause_text", "orientation", "notes", "provenance", "corrections"])
            w.writerow(["G1", "hi", "x", val, "", prov, "0"])
            w.writerow(["G2", "hi", "y", "I", "", prov, "0"])
    A.main(["--a", str(tmp_path / "s_coder1.csv"), "--b", str(tmp_path / "s_coder2.csv"), "--out-dir", str(tmp_path),
            "--disagreements", str(tmp_path / "d.csv")])
    rows = list(_csv.DictReader(open(tmp_path / "agreement_summary_s.csv", encoding="utf-8")))
    assert [r["field"] for r in rows] == ["orientation"] and rows[0]["provenance"] == prov
