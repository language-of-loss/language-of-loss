import csv
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
_spec = importlib.util.spec_from_file_location("optional_figures",
                                               Path(__file__).resolve().parents[2] / "src" / "optional" / "figures.py")
FG = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FG)

COMPS = ["KIN", "FEEL_BAD", "HAPPEN_TO"]
CATS = ["emotion_verb", "emotion_adjective", "emotion_noun", "agentive_self"]


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def decomposition(scale):
    q = dict(delta=(2.0, 1.0, 3.0), forced_share=(2.5, 1.5, 3.5), opportunity_share=(-1.0, -2.0, 0.0),
             choice_share=(0.5, -0.5, 1.5))
    return [dict(quantity=k, estimate=scale * v[0], lo=scale * v[1], hi=scale * v[2]) for k, v in q.items()]


@pytest.fixture()
def dirs(tmp_path):
    proc, res = tmp_path / "processed", tmp_path / "results"
    refs, elig = [], []
    for lang in ("hi", "en"):
        for t in range(3):
            for k in range(8):
                cid = f"blogs:{lang}{t}#{k + 1:04d}"
                refs.append(dict(clause_id=cid, referent_class=FG.CLASSES[(k + t) % len(FG.CLASSES)],
                                 relational=int((k + t) % 3 == 0)))
                elig.append(dict(clause_id=cid, lang=lang, marker_type="relational",
                                 decision="forced_relational" if lang == "hi" and k == 0 else "chosen_individual"))
    write(proc / "referents.csv", refs)
    write(proc / "eligibility.csv", elig)
    write(res / "decompose_all.csv", decomposition(1))
    write(res / "decompose_relational_all.csv", decomposition(3))
    write(res / "p1_choice.csv", [
        dict(quantity="dative_choice_rate", estimate=0.2, lo=0.1, hi=0.3, k=4, n=20, eligibility_sha256="ab" * 32),
        dict(quantity="forced_baseline_dative_share", estimate=0.9, lo=0.8, hi=0.95, k=45, n=50,
             eligibility_sha256="ab" * 32)])
    write(res / "p1_pos_logodds.csv", [dict(category=c, delta=0.5 - i, sd=0.2, z=(0.5 - i) / 0.2, count_hi=5,
                                            count_en=7, note="") if c != "emotion_noun" else
                                       dict(category=c, delta="", sd="", z="", count_hi=5, count_en=0,
                                            note="n/a: en = 0 by construction") for i, c in enumerate(CATS)])
    write(res / "p2_component_profile.csv", [dict(lang=lg, component=c, clauses=10 + i, profile_share=(10 + i) / 36)
                                             for lg in ("hi", "en") for i, c in enumerate(COMPS)])
    write(res / "p2_component_logodds.csv", [dict(component=c, delta=i - 1, sd=0.3, z=(i - 1) / 0.3)
                                             for i, c in enumerate(COMPS)])
    write(res / "p2_residue.csv", [dict(lang=lg, residue=r, count=3, denominator=40)
                                   for lg in ("hi", "en") for r in ("grammar_forced_component_clauses",
                                                                    "matched_clauses_without_component",
                                                                    "emotion_sites_in_unmatched_clauses")])
    write(res / "p2_jsd.csv", [dict(quantity="jsd_component_profiles_base2", estimate=0.1, lo=0.05, hi=0.2)])
    return tmp_path, proc, res


EXPECTED = ["fig1_relational_share.png", "fig1b_referent_density.png", "fig2_decomposition.png",
            "fig3_dative_choice.png", "fig4_components.png", "captions.md"]


def test_every_figure_and_captions_are_written(dirs):
    tmp_path, proc, res = dirs
    out = tmp_path / "figs"
    FG.main(["--processed", str(proc), "--results", str(res), "--out-dir", str(out), "--split", "all", "--B", "100"])
    for name in EXPECTED:
        p = out / name
        assert p.exists() and p.stat().st_size > 0, name
        if name.endswith(".png"):
            assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", name
    cap = (out / "captions.md").read_text(encoding="utf-8")
    assert FG.STAMP in cap and "relational" in cap and "JSD 0.100 [0.050, 0.200]" in cap
    assert "emotion noun: n/a" in cap
    for name in EXPECTED[:-1]:
        assert f"## {name}" in cap


def test_fig2_without_relational_file_has_one_panel(dirs):
    tmp_path, proc, res = dirs
    (res / "decompose_relational_all.csv").unlink()
    out = tmp_path / "figs"
    FG.main(["--processed", str(proc), "--results", str(res), "--out-dir", str(out), "--split", "all", "--B", "50"])
    cap = (out / "captions.md").read_text(encoding="utf-8")
    assert (out / "fig2_decomposition.png").exists() and "Panels: dative." in cap


def test_stripped_share_drops_forced_relational_clauses(dirs):
    _, proc, _ = dirs
    c = FG.relational_counts(FG.read_csv(proc / "referents.csv"), FG.read_csv(proc / "eligibility.csv"), "all")
    t = c["hi"]["blogs:hi0"]
    assert (t["n"], t["n_s"]) == (8, 7) and c["en"]["blogs:en0"]["n_s"] == 8


def test_wilson_interval():
    lo, hi = FG.wilson(5, 10)
    assert 0.23 < lo < 0.24 and 0.76 < hi < 0.77


def test_results_from_another_split_are_refused(dirs):
    tmp_path, proc, res = dirs
    rows = list(csv.DictReader(open(res / "p1_choice.csv", encoding="utf-8")))
    write(res / "p1_choice.csv", [dict(r, split="dev") for r in rows])
    with pytest.raises(SystemExit, match="split"):
        FG.main(["--processed", str(proc), "--results", str(res), "--out-dir", str(tmp_path / "f"), "--split", "all",
                 "--B", "20"])
