import csv
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import figures_v2 as G


def test_kept_reads_only_kept_confirmatory_records(tmp_path):
    p = tmp_path / "subset.csv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", "lang", "split", "kept"])
        w.writerows([["a", "hi", "confirmatory", 1], ["b", "hi", "dev", 1], ["c", "en", "confirmatory", 0]])
    assert G.kept(p) == {"a"}
    q = tmp_path / "no_split.csv"
    q.write_text("record_id,lang,kept\nx,hi,1\ny,en,0\n")
    assert G.kept(q) == {"x"}


def test_pmi_edges_need_both_thresholds():
    o = dict(N=100, n=np.array([20.0, 20.0, 10.0]), pair=np.array([[20, 10, 4], [10, 20, 0], [4, 0, 10]], float))
    pmi, keep = G.pmi_matrix(o)
    assert keep[0, 1] and keep[1, 0]
    assert not keep[0, 2]
    assert not keep[1, 2] and not keep.diagonal().any()
    assert pmi[0, 1] == pytest.approx(np.log2(10 * 100 / 400))


@pytest.mark.skipif(not (ROOT / "data" / "processed" / "eligibility.csv").exists(), reason="private inputs absent")
def test_recomputed_draws_reproduce_the_logged_choice_share():
    est, draws, n = G.choice_draws()
    logged = G.decomposition(ROOT / "results" / "decompose_relational_confirmatory.csv")["choice_share"]
    assert len(draws) == G.B and n == {"hi": 110, "en": 90}
    assert est == pytest.approx(logged["estimate"], abs=5.1e-5)
    assert np.percentile(draws, 2.5) == pytest.approx(logged["lo"], abs=5.1e-5)
    assert np.percentile(draws, 97.5) == pytest.approx(logged["hi"], abs=5.1e-5)
