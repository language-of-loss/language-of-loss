import csv
import math

import rae
import validate as V
from gold import SHEET_COLUMNS

GOLD = [("G1", "hi", "I"), ("G2", "hi", "I"), ("G3", "hi", "F"), ("G4", "en", "C"), ("G5", "en", "I"),
        ("G6", "en", "NA"), ("G7", "hi", "")]
CHAN_A = {"G1": "I", "G2": "F", "G3": "F", "G4": "C", "G5": "I", "G6": "I", "G7": "R"}
CHAN_B = {"G1": "I", "G2": "I", "G3": "F", "G4": "C", "G5": "I"}
C1 = {"G1": "I", "G2": "I", "G3": "F", "G4": "C", "G5": "I", "G6": "NA"}
C2 = {"G1": "I", "G2": "F", "G3": "F", "G4": "C", "G5": "I", "G6": "NA"}


def sheet(path, values, langs=None):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS, restval="")
        w.writeheader()
        for gid, lang, _ in GOLD:
            if gid in values:
                w.writerow(dict(gold_id=gid, lang=lang, clause_text=f"clause {gid}", orientation=values[gid]))
    return path


def run(tmp_path):
    g = sheet(tmp_path / "gold.csv", {gid: v for gid, _, v in GOLD})
    a, b = sheet(tmp_path / "a.csv", CHAN_A), sheet(tmp_path / "b.csv", CHAN_B)
    c1, c2 = sheet(tmp_path / "c1.csv", C1), sheet(tmp_path / "c2.csv", C2)
    V.main(["--gold", str(g), "--coders", str(c1), str(c2), "--channel", f"A={a}", "--channel", f"B={b}",
            "--status", "synthetic fixture", "--out", str(tmp_path / "t.csv"), "--alpha-out", str(tmp_path / "al.csv"),
            "--md", str(tmp_path / "t3.md")])
    rows = list(csv.DictReader(open(tmp_path / "t.csv")))
    return {(r["channel"], r["field"], r["value"], r["lang"]): r for r in rows}, tmp_path


def test_counts_and_scores_by_hand(tmp_path):
    t, _ = run(tmp_path)
    r = t["A", "orientation", "I", "hi"]
    assert (r["n_items"], r["tp"], r["fn"], r["fp"], r["tn"]) == ("3", "1", "1", "0", "1")
    assert float(r["precision"]) == 1.0 and float(r["recall"]) == 0.5 and math.isclose(float(r["f1"]), 2 / 3, abs_tol=1e-4)
    assert float(r["sensitivity"]) == 0.5 and float(r["fpr"]) == 0.0 and (r["n_pos"], r["n_neg"]) == ("2", "1")
    f = t["A", "orientation", "F", "hi"]
    assert (f["tp"], f["fp"], f["fn"]) == ("1", "1", "0") and float(f["fpr"]) == 0.5
    assert ("A", "orientation", "R", "hi") not in t
    na = t["B", "orientation", "NA", "en"]
    assert (na["tp"], na["fn"], na["fp"]) == ("0", "1", "0") and float(na["f1"]) == 0.0
    assert t["A", "orientation", "I", "all"]["n_items"] == "6"
    assert t["A", "orientation", "I", "hi"]["measure"] == "A:orientation=I"
    assert t["A", "orientation", "I", "hi"]["status"] == "synthetic fixture"


def test_coder_alpha_and_table3(tmp_path):
    _, d = run(tmp_path)
    al = {(r["field"], r["lang"]): r for r in csv.DictReader(open(d / "al.csv"))}
    assert al["orientation", "en"]["alpha_nominal"] == "1.0"
    assert float(al["orientation", "hi"]["alpha_nominal"]) < 1 and al["orientation", "all"]["n_both_coded"] == "6"
    assert al["process", "all"]["alpha_nominal"] == ""
    md = (d / "t3.md").read_text()
    assert "synthetic fixture" in md and "| orientation |" in md and "A hi" in md and "B en" in md


def test_rae_reads_the_table(tmp_path):
    _, d = run(tmp_path)
    v = rae.read_validation(str(d / "t.csv"), "A:orientation=I")
    assert v["hi"]["sensitivity"] == 0.5 and v["hi"]["n_pos"] == 2 and v["hi"]["status"] == "synthetic fixture"
