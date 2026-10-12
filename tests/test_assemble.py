import csv
import re
import shutil
from pathlib import Path

import pytest

import assemble as A

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
pytestmark = pytest.mark.skipif(not (RESULTS / "decompose_relational_dev.csv").exists(), reason="needs dev outputs")
POST_GUARD = {"audit_lmer.csv", "audit_stability.csv"}
NAMES = ["Output1_agreement", "Output2_validation", "Output3_hypothesis", "Output4_rival_check", "Output5_audit",
         "Output6_dative_choice", "Output7_jsd", "Output8_translation", "Output9_collocation"]


def run(tmp_path, agreement=False, extra=None):
    res = tmp_path / "results"
    res.mkdir()
    for p in list(RESULTS.glob("*.csv")) + list(RESULTS.glob("*.json")):
        if not agreement and (p.name in POST_GUARD or p.name.startswith(("h1_glmm_", "decompose_relational_confirmatory", "corrected_rates_confirmatory"))):
            continue
        shutil.copy(p, res)
    for name, text in (extra or {}).items():
        (res / name).write_text(text, encoding="utf-8")
    if agreement:
        (res / "agreement").mkdir()
        (res / "agreement" / A.AGREEMENT_FILE).write_text(
            "field,n_units,n_both_coded,n_agree,pct_agree,alpha_nominal,n_out_of_codebook\n"
            "orientation,600,40,30,75.0,0.7,0\n")
    A.main(["--results", str(res), "--figures", str(ROOT / "figures"), "--figures-out", str(tmp_path / "final")])
    return res, tmp_path / "final"


def q(name, quantity, lang=None):
    for r in csv.DictReader(open(RESULTS / name, encoding="utf-8")):
        if r.get("quantity") == quantity and (lang is None or r.get("lang") == lang):
            return float(r["estimate"])


@pytest.mark.skipif(not (ROOT / "figures" / "colloc_hi.png").exists(),
                    reason="needs the collocation figures (not in the public release)")
def test_exactly_nine_output_tables_and_two_figures(tmp_path):
    res, final = run(tmp_path)
    assert sorted(p.stem for p in (res / "tables").iterdir()) == NAMES
    assert sorted(p.name for p in final.iterdir()) == sorted(A.FIGURES.values())
    t3 = (res / "tables" / "Output3_hypothesis.md").read_text()
    for sym in ("r_L", "f_L", "q_L", "p_L", "| forced |", "| opportunity |", "| choice |"):
        assert sym in t3
    assert "Pending" in t3
    t4 = (res / "tables" / "Output4_rival_check.md").read_text()
    assert "not estimable from text-internal evidence" in t4 and "Pending" in t4
    assert "Pending" in (res / "tables" / "Output5_audit.md").read_text()


def test_headline_lists_outputs_one_to_nine_and_nothing_else(tmp_path):
    res, _ = run(tmp_path)
    text = (res / "HEADLINE.md").read_text()
    items = re.findall(r"^(\d)\. \*\*", text, flags=re.M)
    assert items == [str(k) for k in range(1, 10)]
    for gone in ("P2-", "P1-3", "residue", "naming share", "WordNet", "round trip", "BERTopic", "entropy"):
        assert gone not in text, gone


def test_paper_symbols_come_straight_from_decompose(tmp_path):
    res, _ = run(tmp_path)
    t3 = (res / "tables" / "Output3_hypothesis.md").read_text()
    assert f"{q('decompose_relational_dev.csv', 'choice_share'):.2f}" in t3


def test_every_number_in_headline_is_labelled_dev_smoke(tmp_path):
    res, _ = run(tmp_path)
    text = (res / "HEADLINE.md").read_text()
    for line in text.split("## Outputs", 1)[1].splitlines():
        for m in re.finditer(r"(?<![\w.])[−+-]?\d+\.\d+(?: \[[^\]]+\])?", line):
            if not line[m.start() - 1:m.start()] == "[" and not re.match(r"[,\]]", line[m.end():m.end() + 1]):
                assert line[m.end():].startswith(" (dev smoke)"), (m.group(), line[:80])


def test_headline_sentence_is_sign_neutral(tmp_path):
    res, _ = run(tmp_path)
    text = (res / "HEADLINE.md").read_text()
    opp = q("decompose_relational_dev.csv", "opportunity_share")
    assert ("offers fewer unforced" in text) == (opp < 0) and ("offers more unforced" in text) == (opp > 0)
    assert "the greater number of choice sites" not in text


def test_describe_follows_sign_and_hedges_ci():
    lab = lambda e, lo=None, hi=None, digits=2, pct=False, signed=False: f"{e:+.1f}"
    pos, neg = "more", "fewer"
    assert A.describe(dict(estimate="2", lo="1", hi="3"), pos, neg, lab).endswith("meaning more")
    assert A.describe(dict(estimate="-2", lo="-3", hi="-1"), pos, neg, lab).endswith("meaning fewer")
    assert "sign is not established" in A.describe(dict(estimate="1", lo="-1", hi="3"), pos, neg, lab)


def test_directions_follow_the_csv_signs(tmp_path):
    res, _ = run(tmp_path)
    text = (res / "HEADLINE.md").read_text()
    contradicted = text.split("## Pre-registered directions that the current numbers contradict", 1)[1].split("##")[0]
    p1 = q("p1_choice.csv", "dative_choice_rate") - q("p1_choice.csv", "forced_baseline_dative_share")
    assert ("**P1**" in contradicted) == (p1 < 0)
    h2 = q("decompose_relational_dev.csv", "choice_share")
    assert ("**H-2**" in contradicted) == (h2 < 0)
    assert "| A2 | 5 |" in text and "not assessable" in text


def test_label_switches_off_when_agreement_exists(tmp_path):
    res, _ = run(tmp_path, agreement=True)
    assert "(dev smoke)" not in (res / "HEADLINE.md").read_text()
    assert "| orientation | 600 | 40 |" in (res / "tables" / "Output1_agreement.md").read_text()


def test_verdict_rules():
    assert A.verdict("+", None) == "not assessable"
    assert A.verdict("+", dict(estimate=1, lo=0.5, hi=2)) == "as expected"
    assert A.verdict("+", dict(estimate=1, lo=-1, hi=2)) == "as expected, CI includes 0"
    assert A.verdict("-", dict(estimate=1, lo=None, hi=None)) == "DIFFERS"
    assert A.verdict("+", dict(estimate=0, lo=None, hi=None)) == "zero"


def test_odds_ratios_are_exponentiated_and_runs_labelled(tmp_path):
    rows = ("term,estimate,se,stat,df,p,estimator,ci_lo,ci_hi,run,split,subset,n_clauses,n_texts,singular,converged,"
            "odds_ratio,status\nhindi,0.5,0.1,5,,0.001,glmer,0.3,0.7,{run},confirmatory,all,900,60,FALSE,TRUE,1.65,x\n")
    extra = {f"h1_glmm_{r}.csv": rows.format(run=r) for r in A.RUNS}
    res, _ = run(tmp_path, extra=extra)
    t3 = (res / "tables" / "Output3_hypothesis.md").read_text()
    for r in A.RUNS:
        assert A.RUN_LABEL[r] in t3
    assert "1.65 [1.35, 2.01]" in t3


def test_missing_csv_is_pending(tmp_path):
    res = tmp_path / "empty"
    res.mkdir()
    A.main(["--results", str(res), "--figures", str(tmp_path / "nofig"), "--figures-out", str(tmp_path / "final")])
    text = (res / "HEADLINE.md").read_text()
    assert text.count("pending") >= 8
