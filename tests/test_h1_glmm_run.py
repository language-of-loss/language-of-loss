import csv
import random
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def synthetic_root(tmp, n_texts=24, n_cl=30, effect=1.2, seed=5):
    rng = random.Random(seed)
    tf, cf, meta, split, elig, refs = [], [], [], [], [], []
    for t in range(n_texts):
        lang = "hi" if t % 2 else "en"
        rec = f"blogs:{lang}{t:03d}"
        tf.append(dict(record_id=rec, n_clauses=n_cl))
        meta.append(dict(record_id=rec, lang=lang, split="dev", loss_type="parent" if t % 3 else "spouse",
                         diaspora="unknown", diaspora_conf="human", platform="personal_site",
                         source_domain=f"site{t % 6}.in"))
        split.append(dict(record_id=rec, split="dev"))
        base = rng.gauss(0, 0.3)
        for i in range(n_cl):
            cid = f"{rec}#{i:04d}"
            p = 1 / (1 + 2.718281828 ** -(-1 + base + (effect if lang == "hi" else 0)))
            rel = int(rng.random() < p)
            cf.append(dict(clause_id=cid, record_id=rec, lang=lang, is_finite=1, flag_F6=int(i == 0)))
            refs.append(dict(clause_id=cid, relational=rel, rel_subject=rel, rel_target=0, rel_entry=0,
                             honorific_elder=int(lang == "hi" and i == 1)))
            elig.append(dict(clause_id=cid, marker_type="relational",
                             decision="forced_relational" if (lang == "hi" and i == 2) else "chosen_relational"))
    proc = tmp / "data" / "processed"
    write(proc / "text_features.csv", tf)
    write(proc / "clause_features.csv", cf)
    write(proc / "text_meta.csv", meta)
    write(proc / "split.csv", split)
    write(proc / "eligibility.csv", elig)
    write(proc / "referents.csv", refs)
    (tmp / "results" / "agreement").mkdir(parents=True)
    (tmp / "results" / "agreement" / "agreement_summary_gold_sheet_v1.csv").write_text(
        "field,n_both_coded,alpha_nominal\norientation,40,0.7\n")
    return tmp


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed")
def test_h1_runs_with_domain_intercept_and_permutation(tmp_path):
    root = synthetic_root(tmp_path)
    r = subprocess.run(["Rscript", str(ROOT / "R" / "h1_glmm.R"), "--run", "--split", "dev", "--root", str(root)],
                       capture_output=True, text=True, timeout=600, env={**__import__("os").environ, "H1_PERM_B": "19"})
    assert r.returncode == 0, r.stderr[-2000:]
    for run in ("run1", "run2", "run2b", "rF6"):
        rows = [x for x in read(root / "results" / f"h1_glmm_{run}.csv") if x["term"] == "hindi"]
        est = {x["estimator"]: x for x in rows}
        assert any(e.startswith("glmer (conditional") for e in est)
        assert any(e.startswith("glm + CR2") for e in est)
        assert any("domain random intercept" in e for e in est)
        perm = [x for e, x in est.items() if e.startswith("permutation over texts")]
        assert len(perm) == 1 and "B = 19" in next(e for e in est if e.startswith("permutation"))
        assert float(perm[0]["p"]) == pytest.approx(1 / 20)
        assert float(perm[0]["estimate"]) > 0
    n = {run: int(read(root / "results" / f"h1_glmm_{run}.csv")[0]["n_clauses"]) for run in ("run1", "run2", "run2b")}
    assert n["run1"] > n["run2"] > n["run2b"]
