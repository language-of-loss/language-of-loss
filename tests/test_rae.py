import csv
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import rae as R

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def toy_texts(rate, n_texts=40, units=100):
    return np.full(n_texts, units), np.full(n_texts, round(rate * units))


def test_rogan_gladen_by_hand():
    assert R.rogan_gladen(0.20, 0.50, 0.05) == pytest.approx(1 / 3)
    assert R.rogan_gladen(0.25, 0.90, 0.05) == pytest.approx(4 / 17)
    assert R.rogan_gladen(0.30, 1.0, 0.0) == pytest.approx(0.30)
    assert R.rogan_gladen(0.03, 0.50, 0.05) == pytest.approx(-0.02 / 0.45)
    assert np.isnan(R.rogan_gladen(0.2, 0.05, 0.05))


def test_observed_rate_weighting():
    units, hits = [10, 90], [1, 45]
    assert R.observed_rate(units, hits, "text") == pytest.approx(0.30)
    assert R.observed_rate(units, hits, "unit") == pytest.approx(0.46)
    assert R.observed_rate([0, 10], [0, 2], "text") == pytest.approx(0.2)


def test_toy_estimates_and_sign_flip():
    hi, reps_hi = R.estimate(*toy_texts(0.20), 0.50, 0.05, 100, 100, B=4000, rng=1)
    en, reps_en = R.estimate(*toy_texts(0.25), 0.90, 0.05, 100, 100, B=4000, rng=2)
    assert hi["o"] == pytest.approx(0.20) and en["o"] == pytest.approx(0.25)
    assert hi["pi"] == pytest.approx(1 / 3) and en["pi"] == pytest.approx(4 / 17)
    assert hi["pi_lo"] < hi["pi"] < hi["pi_hi"] and en["pi_lo"] < en["pi"] < en["pi_hi"]
    assert not hi["out_of_range"] and not hi["undefined"]
    c = R.compare(hi, en, reps_hi, reps_en)
    assert c["diff_observed"] == pytest.approx(-0.05)
    assert c["diff_adjusted"] == pytest.approx(1 / 3 - 4 / 17)
    assert c["sign_flip"] and 0.5 < c["p_flip"] <= 1
    assert c["recall_gap"] == pytest.approx(0.40) and not c["gap_ok"]


def test_no_flip_when_recall_is_equal():
    hi, rh = R.estimate(*toy_texts(0.20), 0.80, 0.05, 100, 100, B=2000, rng=3)
    en, re_ = R.estimate(*toy_texts(0.25), 0.80, 0.05, 100, 100, B=2000, rng=4)
    c = R.compare(hi, en, rh, re_)
    assert not c["sign_flip"] and c["gap_ok"] and c["diff_adjusted"] < 0


def test_text_bootstrap_adds_width():
    units = np.full(30, 50)
    hits = np.random.default_rng(0).integers(0, 25, size=30)
    est, _ = R.estimate(units, hits, 1.0, 0.0, 0, 0, B=2000, rng=5)
    assert est["pi"] == pytest.approx(est["o"]) and est["pi_hi"] - est["pi_lo"] > 0.01


def test_out_of_range_flag():
    est, _ = R.estimate(*toy_texts(0.03), 0.50, 0.05, 100, 100, B=500, rng=6)
    assert est["out_of_range"] and est["pi"] < 0 and est["pi_clipped"] == 0


def test_cli_carries_placeholder_status(tmp_path):
    texts = tmp_path / "texts.csv"
    with open(texts, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["text_id", "lang", "n_units", "n_hits"])
        for i in range(20):
            w.writerow([f"h{i}", "hi", 100, 20])
            w.writerow([f"e{i}", "en", 100, 25])
    out = tmp_path / "rae.csv"
    subprocess.run([sys.executable, str(ROOT / "src" / "analysis" / "rae.py"), "--texts", str(texts),
                    "--validation", str(HERE / "rae_validation_placeholder.csv"), "--measure", "toy", "--B", "500",
                    "--out", str(out)], check=True, capture_output=True)
    rows = {r["lang"]: r for r in csv.DictReader(open(out))}
    assert set(rows) == {"en", "hi", "hi-en"}
    assert all(r["validation_status"] == "placeholder" for r in rows.values())
    assert float(rows["hi"]["pi"]) == pytest.approx(1 / 3) and rows["hi-en"]["sign_flip"] == "True"
