import csv
import math
import sys
from pathlib import Path

import numpy as np

import entropy as E

FIX = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIX))
import make_moves_synthetic as MK


def test_hand_cases():
    assert E.entropy_rate(["a", "b"] * 10) == 0.0
    assert math.isclose(E.entropy_rate(["a", "a", "b", "b", "a"]), 1.0)
    seq = ["a", "a", "b", "a", "b", "b"]
    h = -(1 / 5 * math.log2(1 / 3) + 2 / 5 * math.log2(2 / 3) + 2 * (1 / 5 * math.log2(1 / 2)))
    assert math.isclose(E.entropy_rate(seq), h)


def test_batched_counts_match_single():
    rng = np.random.default_rng(0)
    batch = rng.integers(0, 4, size=(5, 30))
    c = E.transition_counts(batch, 4)
    for i in range(5):
        assert math.isclose(E.entropy_rate_from_counts(c[i]), E.entropy_rate(list(batch[i]), 4))


def test_permutation_null_separates_ordered_from_random():
    rng = np.random.default_rng(1)
    ordered = E.per_text(E.MOVES * 4, 2000, 500, rng)
    assert ordered["entropy_rate"] == 0.0 and ordered["p_perm"] < 0.001 and ordered["excess"] > 1
    rand = E.per_text([str(x) for x in np.random.default_rng(2).integers(0, 3, 300)], 2000, 500, rng)
    assert rand["p_perm"] > 0.05 and rand["lo"] <= rand["entropy_rate"] <= rand["hi"]


def test_fixture_is_reproducible():
    with open(FIX / "moves_synthetic.csv", encoding="utf-8", newline="") as fh:
        got = [dict(r, position=int(r["position"])) for r in csv.DictReader(fh)]
    assert got == MK.rows()


def test_end_to_end_on_fixture(tmp_path):
    out = tmp_path / "ent.csv"
    E.main(["--in", str(FIX / "moves_synthetic.csv"), "--out", str(out), "--perm", "2000", "--B", "500"])
    rows = list(csv.DictReader(open(out)))
    assert len(rows) == 16
    hi = [r for r in rows if r["lang"] == "hi"]
    assert all(float(r["p_perm"]) < 0.01 for r in hi)
    lang = {(r["lang"], r["quantity"]): r for r in csv.DictReader(open(tmp_path / "ent_by_lang.csv"))}
    d = lang[("hi-en", "entropy_rate")]
    assert float(d["hi"]) < 0


def test_tied_positions_keep_file_order(tmp_path):
    f = tmp_path / "moves.csv"
    f.write_text("text,lang,pos,move\nt1,hi,1,regret\nt1,hi,1,announce\nt1,hi,2,memory\n", encoding="utf-8")
    seqs, _ = E.load_sequences(f, "text", "lang", "pos", "move")
    assert seqs["t1"] == ["regret", "announce", "memory"]
