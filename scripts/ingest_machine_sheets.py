"""Ingest machine-filled annotation sheets as MACHINE-PROVISIONAL channel files (never as human gold)."""
import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
from gold import CODEBOOK, COMPONENT_VALUES

DEST = ROOT / "data/processed/channels/machine_annotation_20261011"
BLANKS = {
    "gold_pilot_r1.csv": "data/annotation/gold_pilot_r1.csv",
    "gold_pilot_r2.csv": "data/annotation/gold_pilot_r2.csv",
    "gold_sheet_v1_coder1.csv": "data/annotation/gold_sheet_v1_coder1.csv",
    "gold_sheet_v1_coder2.csv": "data/annotation/gold_sheet_v1_coder2.csv",
    "gold_components_v1_coder1.csv": "data/annotation/gold_components_v1_coder1.csv",
    "gold_components_v1_coder2.csv": "data/annotation/gold_components_v1_coder2.csv",
    "audit_rating_sheet_r1.csv": "data/annotation/audit_rating_sheet_r1.csv",
    "audit_rating_sheet_r2.csv": "data/annotation/audit_rating_sheet_r2.csv",
    "audit_calibration_brighter_r1.csv": "data/annotation/audit_calibration_brighter_r1.csv",
    "audit_calibration_brighter_r2.csv": "data/annotation/audit_calibration_brighter_r2.csv",
    "meta_review.csv": "data/annotation/meta_review.csv",
    "review_master_2026-10.csv": "docs/review_master_2026-10.csv",
}
FILL = {
    "gold": list(CODEBOOK),
    "components": None,
    "rating": ["intensity_1to7"],
    "meta": ["confirmed_value", "reviewer"],
    "review": ["decision", "relation", "reason", "reviewer"],
}
META_VALUES = {"genre": {"narrative", "reflective"}, "home_language_statement": {"en", "hi", "both", "none"},
               "diaspora": {"yes", "no", "unknown"}, "script_mix": {"devanagari", "latin", "mixed"}}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        return r.fieldnames, list(r)


def kind(name):
    if name.startswith("gold_components"):
        return "components"
    if name.startswith("gold_"):
        return "gold"
    if name.startswith("audit_"):
        return "rating"
    return "meta" if name.startswith("meta") else "review"


def check(name, blank_path, filled_path):
    problems, blanks_left = [], []
    bh, brows = read(blank_path)
    fh, frows = read(filled_path)
    if bh != fh:
        return [f"header differs: blank {bh} vs filled {fh}"], [], len(frows)
    idc = bh[0]
    if [r[idc] for r in brows] != [r[idc] for r in frows]:
        b, f = [r[idc] for r in brows], [r[idc] for r in frows]
        problems.append(f"row ids differ: missing {sorted(set(b) - set(f))[:10]}, extra {sorted(set(f) - set(b))[:10]}, "
                        f"order same={b == f}")
        return problems, [], len(frows)
    k = kind(name)
    comp_cols = [c for c in bh if c in COMPONENT_NAMES]
    fill = comp_cols if k == "components" else FILL[k]
    for b, f in zip(brows, frows):
        for c in bh:
            if b[c] != "" and b[c] != f[c]:
                problems.append(f"{f[idc]}: pre-filled cell {c} changed")
        for c in fill:
            v = f[c].strip()
            if v == "":
                blanks_left.append(f"{f[idc]}:{c}")
                continue
            if k == "gold" and v not in CODEBOOK[c]:
                problems.append(f"{f[idc]}: {c}={v!r} not in codebook")
            if k == "components" and v not in COMPONENT_VALUES:
                problems.append(f"{f[idc]}: {c}={v!r} not 0/1")
            if k == "rating" and v not in {str(i) for i in range(1, 8)}:
                problems.append(f"{f[idc]}: intensity {v!r} not 1-7")
            if k == "meta" and c == "confirmed_value" and v not in META_VALUES.get(f["field"], {v}):
                problems.append(f"{f[idc]}/{f['field']}: {v!r} not allowed")
            if k == "review" and c == "decision" and v not in {"include", "exclude"}:
                problems.append(f"{f[idc]}: decision {v!r}")
    return problems, blanks_left, len(frows)


COMPONENT_NAMES = set()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True)
    ap.add_argument("--dest", default=str(DEST))
    ap.add_argument("--manifest", default=str(ROOT / "results/machine_pilot/ingest_manifest.json"))
    a = ap.parse_args()
    comp_header, _ = read(ROOT / BLANKS["gold_components_v1_coder1.csv"])
    COMPONENT_NAMES.update(c for c in comp_header[6:] if c != "notes")
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    out = {"status": "MACHINE-PROVISIONAL: machine-filled sheets (machine annotator1/annotator2), not human annotation",
           "source_dir": str(Path(a.src)), "files": {}}
    for name, blank in BLANKS.items():
        src = Path(a.src) / name
        entry = {"blank": blank, "blank_sha256": sha(ROOT / blank)}
        if not src.exists():
            entry["status"] = "missing in source"
        else:
            problems, left, n = check(name, ROOT / blank, src)
            entry.update(rows=n, sha256=sha(src), problems=problems, blank_cells_left=len(left),
                         blank_cells_left_ids=left[:40])
            if problems and any(p.startswith(("header", "row ids")) for p in problems):
                entry["status"] = "skipped: structure differs"
            else:
                shutil.copy2(src, dest / name)
                entry["status"] = "copied" + (" with value problems" if problems else "")
        out["files"][name] = entry
        print(f"{name:38s} {entry['status']:30s} rows={entry.get('rows')} problems={len(entry.get('problems', []))} "
              f"blanks_left={entry.get('blank_cells_left')}")
    Path(a.manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(a.manifest).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
