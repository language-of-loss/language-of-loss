"""Install the reviewed machine-prefilled sheets as the gold standard."""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/processed/channels/machine_annotation_20261011"
CORRECTIONS = ROOT / "docs/annotation_corrections.csv"
PROVENANCE = ("machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator "
              "without change unless a correction is logged")
ANN = ROOT / "data/annotation"
TARGETS = {
    "gold_pilot_r1.csv": ANN / "gold_pilot_r1.csv", "gold_pilot_r2.csv": ANN / "gold_pilot_r2.csv",
    "gold_sheet_v1_coder1.csv": ANN / "gold_sheet_v1_coder1.csv",
    "gold_sheet_v1_coder2.csv": ANN / "gold_sheet_v1_coder2.csv",
    "gold_components_v1_coder1.csv": ANN / "gold_components_v1_coder1.csv",
    "gold_components_v1_coder2.csv": ANN / "gold_components_v1_coder2.csv",
    "audit_rating_sheet_r1.csv": ANN / "audit_rating_sheet_r1.csv",
    "audit_rating_sheet_r2.csv": ANN / "audit_rating_sheet_r2.csv",
    "audit_calibration_brighter_r1.csv": ANN / "audit_calibration_brighter_r1.csv",
    "audit_calibration_brighter_r2.csv": ANN / "audit_calibration_brighter_r2.csv",
    "meta_review.csv": ANN / "meta_review.csv",
    "review_master_2026-10.csv": ROOT / "docs/review_master_2026-10.csv",
}
FILL = {"meta_review.csv": ["confirmed_value"], "review_master_2026-10.csv": ["decision"]}
DECISION = {"include": "yes", "exclude": "no"}


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        return r.fieldnames, list(r)


def row_id(header, row, name):
    if name == "meta_review.csv":
        return f"{row['record_id']}|{row['field']}"
    return row[header[0]]


def already_human(name, target):
    if not target.exists():
        return False
    header, rows = read(target)
    if "provenance" in header:
        return any(r["provenance"] != PROVENANCE for r in rows)
    cols = FILL.get(name) or [c for c in header if c not in {"gold_id", "lang", "context_before", "clause_text",
                                                             "span_text", "context_after", "notes", "rating_id",
                                                             "calibration_id", "passage_text"}]
    return any((r.get(c) or "").strip() for r in rows for c in cols)


def load_corrections():
    if not CORRECTIONS.exists():
        return defaultdict(list)
    out = defaultdict(list)
    for c in read(CORRECTIONS)[1]:
        out[(c["file"], c["row_id"])].append(c)
    return out


def install(name, target, corrections, dry):
    header, rows = read(SRC / name)
    n_corr = 0
    for r in rows:
        rid = row_id(header, r, name)
        cs = corrections.get((name, rid), [])
        for c in cs:
            if r[c["field"]] != c["old"]:
                raise SystemExit(f"{name} {rid} {c['field']}: correction expects {c['old']!r}, sheet has "
                                 f"{r[c['field']]!r}")
            r[c["field"]] = c["new"]
        if name == "review_master_2026-10.csv":
            r["decision"] = DECISION.get(r["decision"].strip(), r["decision"])
        r["provenance"], r["corrections"] = PROVENANCE, len(cs)
        n_corr += len(cs)
    if not dry:
        with open(target, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=header + ["provenance", "corrections"])
            w.writeheader()
            w.writerows(rows)
    return len(rows), n_corr


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    blocked = [n for n, t in TARGETS.items() if already_human(n, t)]
    if blocked:
        raise SystemExit(f"refusing: these targets already hold filled cells of another origin: {blocked}")
    corrections = load_corrections()
    total = Counter()
    for name, target in TARGETS.items():
        n, c = install(name, target, corrections, a.dry_run)
        total["rows"] += n
        total["corrections"] += c
        print(f"{name:36s} -> {target.relative_to(ROOT)}  rows={n} corrections={c}")
    print(f"{'(dry run) ' if a.dry_run else ''}installed {len(TARGETS)} sheets, {total['rows']} rows, "
          f"{total['corrections']} logged corrections")


if __name__ == "__main__":
    sys.exit(main())
