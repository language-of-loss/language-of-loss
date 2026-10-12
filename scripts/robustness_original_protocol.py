"""Robustness check, no new data: Run 2 and the relational decomposition on the confirmatory texts that satisfy the"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from build_review_master import BYLINE_UNRELIABLE_DOMAINS, domain_covariate

PROC = ROOT / "data" / "processed"
OUT = ROOT / "results" / "robustness"
DOMAIN_CAP, AUTHOR_CAP = 3, 1
LANG = {"devanagari_hindi": "hi", "english": "en"}


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def subset(merged, split, master):
    recs = [r for r in merged if r["record_id"] in split]
    pre = [r for r in recs if "review" not in (r.get("extra") or {})]
    rev = sorted((r for r in recs if "review" in (r.get("extra") or {})),
                 key=lambda r: (-float(master[r["record_id"]]["rank_score"] or 0), r["record_id"]))
    per_dom, per_auth, rows = Counter(), Counter(), []
    for r in pre + rev:
        extra = r.get("extra") or {}
        dom = extra.get("domain_covariate") or domain_covariate(r["thread_id"])
        au = None if dom in BYLINE_UNRELIABLE_DOMAINS else r.get("author_group")
        flags = set(r.get("flags") or [])
        reasons = []
        if "over_cap" in flags:
            reasons.append("over_cap_flag")
        else:
            per_dom[dom] += 1
            if per_dom[dom] > DOMAIN_CAP:
                reasons.append("domain_cap_3")
            if au:
                per_auth[au] += 1
                if per_auth[au] > AUTHOR_CAP:
                    reasons.append("author_cap_1")
        if "length_outlier_gt5000w" in flags:
            reasons.append("length_outlier_gt5000w")
        rows.append(dict(record_id=r["record_id"], lang=LANG.get(r["lang_provisional"], r["lang_provisional"]),
                         domain=dom, split=split[r["record_id"]], kept=int(not reasons), reason=";".join(reasons)))
    return rows


def filtered_copy(src, dst, keep):
    with open(src, encoding="utf-8", newline="") as fi, open(dst, "w", encoding="utf-8", newline="") as fo:
        rd = csv.DictReader(fi)
        w = csv.DictWriter(fo, fieldnames=rd.fieldnames)
        w.writeheader()
        w.writerows(r for r in rd if r["clause_id"].split("#")[0] in keep)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scratch", default=None, help="scratch root (default: a new temporary directory)")
    args = ap.parse_args(argv)
    split = {r["record_id"]: r["split"] for r in read_csv(PROC / "split.csv")}
    master = {r["record_id"]: r for r in read_csv(ROOT / "docs" / "review_master_2026-10.csv")}
    with open(ROOT / "data" / "clean" / "blogs_merged.jsonl", encoding="utf-8") as fh:
        merged = [json.loads(line) for line in fh]
    rows = subset(merged, split, master)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "original_protocol_subset.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    keep = {r["record_id"] for r in rows if r["kept"] and r["split"] == "confirmatory"}
    conf = [r for r in rows if r["split"] == "confirmatory"]
    counts = {lang: dict(confirmatory=sum(r["lang"] == lang for r in conf),
                         kept=sum(r["lang"] == lang and r["kept"] for r in conf),
                         dropped_by=dict(Counter(x for r in conf if r["lang"] == lang and not r["kept"]
                                                 for x in r["reason"].split(";"))))
              for lang in ("hi", "en")}
    print(json.dumps(counts, indent=1))

    scratch = Path(args.scratch or tempfile.mkdtemp(prefix="robust_op_"))
    sp = scratch / "data" / "processed"
    sp.mkdir(parents=True, exist_ok=True)
    (scratch / "results" / "agreement").mkdir(parents=True, exist_ok=True)
    for f in ("text_features.csv", "clause_features.csv", "text_meta.csv", "eligibility.csv", "referents.csv"):
        if not (sp / f).exists():
            os.symlink(PROC / f, sp / f)
    shutil.copy(ROOT / "results" / "agreement" / "agreement_summary_gold_sheet_v1.csv",
                scratch / "results" / "agreement" / "agreement_summary_gold_sheet_v1.csv")
    with open(sp / "split.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", "split"])
        w.writerows([rid, "confirmatory" if rid in keep else ("excluded" if s == "confirmatory" else s)]
                    for rid, s in sorted(split.items()))
    subprocess.run(["Rscript", str(ROOT / "R" / "h1_glmm.R"), "--run", "--split", "confirmatory", "--root",
                    str(scratch)], check=True, cwd=ROOT)
    shutil.copy(scratch / "results" / "h1_glmm_run2.csv", OUT / "h1_glmm_run2_original_protocol.csv")

    filtered_copy(PROC / "eligibility.csv", scratch / "eligibility_kept.csv", keep)
    filtered_copy(PROC / "referents.csv", scratch / "referents_kept.csv", keep)
    dec = OUT / "decompose_relational_original_protocol.csv"
    subprocess.run([sys.executable, str(ROOT / "src" / "analysis" / "decompose.py"), "--marker", "relational",
                    "--split", "confirmatory", "--B", "2000", "--eligibility", str(scratch / "eligibility_kept.csv"),
                    "--referents", str(scratch / "referents_kept.csv"), "--out", str(dec)], check=True, cwd=ROOT)

    run2 = read_csv(OUT / "h1_glmm_run2_original_protocol.csv")
    decomp = read_csv(dec)
    summary = dict(status="robustness: original protocol subset (reviewed machine-prefilled labels)",
                   counts=counts, run2_hindi=[r for r in run2 if r.get("term") == "hindi"],
                   decomposition=decomp, scratch=str(scratch))
    (OUT / "original_protocol_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n",
                                                          encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
