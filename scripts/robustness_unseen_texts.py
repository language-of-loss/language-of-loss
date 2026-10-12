"""Robustness check, no new data: Run 2 and the relational decomposition on the confirmatory texts that were never"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from robustness_original_protocol import LANG, filtered_copy, read_csv

PROC = ROOT / "data" / "processed"
OUT = ROOT / "results" / "robustness"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scratch", default=None, help="scratch root (default: a new temporary directory)")
    args = ap.parse_args(argv)
    split = {r["record_id"]: r["split"] for r in read_csv(PROC / "split.csv")}
    added = {r["record_id"] for r in read_csv(ROOT / "docs" / "review_master_2026-10.csv") if r["decision"] == "yes"}
    with open(ROOT / "data" / "clean" / "blogs_merged.jsonl", encoding="utf-8") as fh:
        lang = {r["record_id"]: LANG.get(r["lang_provisional"], r["lang_provisional"])
                for r in map(json.loads, fh)}
    rows = [dict(record_id=rid, lang=lang.get(rid, ""), split=s, kept=int(rid in added))
            for rid, s in sorted(split.items()) if s == "confirmatory"]
    keep = {r["record_id"] for r in rows if r["kept"]}
    counts = {lg: dict(confirmatory=sum(r["lang"] == lg for r in rows), kept=sum(r["lang"] == lg and r["kept"]
                                                                                  for r in rows))
              for lg in ("hi", "en")}
    print(json.dumps(counts))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "unseen_texts_subset.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    scratch = Path(args.scratch or tempfile.mkdtemp(prefix="robust_unseen_"))
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
    shutil.copy(scratch / "results" / "h1_glmm_run2.csv", OUT / "h1_glmm_run2_unseen_texts.csv")

    filtered_copy(PROC / "eligibility.csv", scratch / "eligibility_kept.csv", keep)
    filtered_copy(PROC / "referents.csv", scratch / "referents_kept.csv", keep)
    dec = OUT / "decompose_relational_unseen_texts.csv"
    subprocess.run([sys.executable, str(ROOT / "src" / "analysis" / "decompose.py"), "--marker", "relational",
                    "--split", "confirmatory", "--B", "2000", "--eligibility", str(scratch / "eligibility_kept.csv"),
                    "--referents", str(scratch / "referents_kept.csv"), "--out", str(dec)], check=True, cwd=ROOT)

    summary = dict(status="robustness: texts unseen during instrument development (reviewed machine-prefilled labels)",
                   counts=counts, run2_hindi=[r for r in read_csv(OUT / "h1_glmm_run2_unseen_texts.csv")
                                              if r.get("term") == "hindi"],
                   decomposition=read_csv(dec), scratch=str(scratch))
    (OUT / "unseen_texts_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
