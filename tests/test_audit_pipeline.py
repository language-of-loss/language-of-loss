import csv
import random
import shutil
import subprocess
from pathlib import Path

import pytest

import audit_match as M
import audit_passages as AP

ROOT = Path(__file__).resolve().parents[1]


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def synthetic(tmp, n=40, seed=1):
    rng = random.Random(seed)
    key, s1, s2, meta = [], [], [], []
    for lang in ("hi", "en"):
        for i in range(n):
            rid, rec = f"AR-{lang}{i:03d}", f"blogs:{lang}{i % 8}"
            key.append(dict(rating_id=rid, passage_id=f"AP-{lang}{i:03d}", record_id=rec, lang=lang, register="long",
                            split="dev", source_url="", passage_sha256="", order_r1=0, order_r2=0))
            base = rng.randint(2, 6)
            s1.append(dict(rating_id=rid, lang=lang, passage_text="(synthetic)", intensity_1to7=base, notes=""))
            s2.append(dict(rating_id=rid, lang=lang, passage_text="(synthetic)",
                           intensity_1to7=min(7, max(1, base + rng.choice([-2, -1, 0, 0, 1]))), notes=""))
    for lang in ("hi", "en"):
        for k in range(8):
            meta.append(dict(record_id=f"blogs:{lang}{k}", lang=lang, loss_type="parent" if k < 5 else "spouse"))
    ann, proc = tmp / "data/annotation", tmp / "data/processed"
    return dict(r1=write(ann / "r1.csv", s1), r2=write(ann / "r2.csv", s2), key=write(ann / "key.csv", key),
                meta=write(proc / "text_meta.csv", meta), proc=proc, res=tmp / "results")


def run_match(tmp, d):
    M.main(["--r1", str(d["r1"]), "--r2", str(d["r2"]), "--key", str(d["key"]), "--text-meta", str(d["meta"]),
            "--cal-key", str(tmp / "none.csv"), "--processed", str(d["proc"]), "--results", str(d["res"])])
    return read(d["proc"] / "audit_pairs.csv"), read(d["proc"] / "audit_ratings.csv")


def test_pairs_are_one_to_one_within_relationship_and_tolerance(tmp_path):
    d = synthetic(tmp_path)
    pairs, rated = run_match(tmp_path, d)
    loss = {r["passage_id"]: r["loss_type"] for r in rated}
    seen = [p[k] for p in pairs for k in ("passage_id_hi", "passage_id_en")]
    assert pairs and len(seen) == len(set(seen))
    for p in pairs:
        assert abs(float(p["rating_hi"]) - float(p["rating_en"])) <= M.TOLERANCE
        assert loss[p["passage_id_hi"]] == loss[p["passage_id_en"]] == p["loss_type"]
    agr = {r["lang"]: r for r in read(d["res"] / "audit_rating_agreement.csv")}
    assert set(agr) == {"hi", "en", "all"} and int(agr["all"]["n_both_rated"]) == 80


def test_agreed_flag_needs_both_passages_within_one_point(tmp_path):
    d = synthetic(tmp_path)
    pairs, rated = run_match(tmp_path, d)
    ok = {r["passage_id"]: abs(int(r["r1"]) - int(r["r2"])) <= M.AGREE_WITHIN for r in rated}
    for p in pairs:
        assert p["agreed"] == str(int(ok[p["passage_id_hi"]] and ok[p["passage_id_en"]]))


def test_unfilled_sheets_refuse_and_bad_values_fail(tmp_path):
    d = synthetic(tmp_path)
    rows = read(d["r1"])
    for r in rows:
        r["intensity_1to7"] = ""
    write(d["r1"], rows)
    with pytest.raises(SystemExit, match="not filled"):
        run_match(tmp_path, d)
    rows[0]["intensity_1to7"] = "8"
    write(d["r1"], rows)
    with pytest.raises(SystemExit, match="1-7"):
        run_match(tmp_path, d)


def test_round_robin_spreads_over_texts_without_overlap():
    cands = {"a": AP.windows([50, 50, 50, 50, 50, 50], [5, 5, 0, 5, 5, 5]),
             "b": AP.windows([90, 90], [1, 0])}
    got = AP.round_robin(cands, 10)
    texts = [t for t, *_ in got]
    assert texts.count("b") == 1 and texts.count("a") >= 2
    used = {}
    for t, i, j, *_ in got:
        span = set(range(i, j + 1))
        assert not span & used.get(t, set())
        used.setdefault(t, set()).update(span)
    assert all(d > 0 for *_, d, s in got)


def test_honorific_columns_do_not_score(tmp_path):
    f = tmp_path / "cf.csv"
    write(f, [{"clause_id": "c#1", "L-HI-01": 1, "L-HI-C2": 1, "flag_F1": 1, "flag_F2": 1}])
    assert AP.load_scores(f) == {"c#1": 2}


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed")
def test_r_audit_model_runs_on_synthetic_ratings(tmp_path):
    d = synthetic(tmp_path, n=60, seed=3)
    pairs, rated = run_match(tmp_path, d)
    rng = random.Random(7)
    rating = {r["passage_id"]: float(r["mean_rating"]) for r in rated}
    scores, chat, comps = [], [], []
    for pid, y in rating.items():
        hindi = pid.startswith("AP-hi")
        c1 = rng.random()
        under = (-0.15 - 0.2 * c1) if hindi else 0.0
        for model, col in (("xlm_emo", "p_sadness"), ("muril_sent", "p_negative")):
            scores.append(dict(passage_id=pid, model=model, **{col: round(0.1 * y + under + rng.gauss(0, 0.05), 4)},
                               **{("p_negative" if col == "p_sadness" else "p_sadness"): 0.1}))
        for cue in ("none", "india"):
            chat.append(dict(passage_id=pid, system="llm-test", cue=cue, sample=0,
                             rating=max(1, min(7, round(y + (2 * under if cue == "none" else under) * 5
                                                        + rng.gauss(0, 0.3))))))
        comps.append(dict(passage_id=pid, lang="hi" if hindi else "en", register="long", n_clauses=10,
                          comp_KIN=round(c1, 3), comp_FEEL_BAD=round(rng.random(), 3),
                          comp_NOT_HERE=round(rng.random(), 3)))
    write(d["proc"] / "audit" / "passage_scores.csv", scores)
    write(d["proc"] / "audit_passage_components.csv", comps)
    write(d["res"] / "audit_chat_scores.csv", chat)
    (d["res"] / "agreement").mkdir(parents=True, exist_ok=True)
    (d["res"] / "agreement" / "agreement_summary_gold_sheet_v1.csv").write_text(
        "field,n_both_coded,alpha_nominal\norientation,40,0.7\n")
    r = subprocess.run(["Rscript", str(ROOT / "R" / "audit.R"), "--run", "--root", str(tmp_path)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    lm = read(d["res"] / "audit_lmer.csv")
    terms = {(x["system"], x["pairs"], x["term"]) for x in lm}
    assert ("llm-test", "all", "hindi:cue") in terms and ("xlm_emo", "all", "hindi") in terms
    assert not any(t == "hindi:cue" for s, _, t in terms if s == "xlm_emo")
    assert any(p == "agreed" for _, p, _ in terms)
    hindi = {(x["system"], x["pairs"]): float(x["estimate"]) for x in lm if x["term"] == "hindi"}
    assert hindi[("xlm_emo", "all")] < 0
    stab = read(d["res"] / "audit_stability.csv")
    assert {"system", "component", "selection_freq", "stable"} <= set(stab[0])


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed")
def test_r_audit_model_refuses_without_agreement(tmp_path):
    r = subprocess.run(["Rscript", str(ROOT / "R" / "audit.R"), "--run", "--root", str(tmp_path)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode != 0 and "refusing to fit" in r.stderr
