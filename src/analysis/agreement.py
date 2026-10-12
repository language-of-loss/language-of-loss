"""Stage 6 -- inter-coder agreement between two filled gold sheets (gold.py output)."""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

import krippendorff
import numpy as np

from gold import CODEBOOK, COMPONENT_VALUES, SHEET_TEXT, refuse_annotation_dir

ROOT = Path(__file__).resolve().parents[2]
NOT_FIELDS = set(SHEET_TEXT) | {"notes", "coder", "provenance", "corrections"}


def read_sheet(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ids = [r["gold_id"] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"{path}: duplicate gold_id(s) {dup[:5]} -- a later row would silently replace an earlier one")
    return {r["gold_id"]: r for r in rows}, list(rows[0].keys()) if rows else []


def sheet_label(path):
    stem = Path(path).stem
    return re.sub(r"_(coder1|coder_1|r1|a)$", "", stem)


def allowed(field):
    return CODEBOOK.get(field, COMPONENT_VALUES)


def canon(value, field):
    v = (value or "").strip()
    for a in allowed(field):
        if v.lower() == a.lower():
            return a
    return v


def alpha_nominal(pairs):
    values = sorted({x for p in pairs for x in p if x})
    if len(values) < 2:
        return float("nan")
    code = {v: i for i, v in enumerate(values)}
    data = np.array([[code[a] if a else np.nan for a, _ in pairs],
                     [code[b] if b else np.nan for _, b in pairs]], dtype=float)
    try:
        return float(krippendorff.alpha(reliability_data=data, level_of_measurement="nominal"))
    except ValueError:
        return float("nan")


def compare(sheet_a, sheet_b, fields):
    ids = [g for g in sheet_a if g in sheet_b]
    summary, confusion, disagree = [], [], []
    for f in fields:
        pairs = [(canon(sheet_a[g].get(f), f), canon(sheet_b[g].get(f), f)) for g in ids]
        both = [(a, b) for a, b in pairs if a and b]
        agree = sum(a == b for a, b in both)
        invalid = sum(1 for p in pairs for x in p if x and x not in allowed(f))
        alpha = alpha_nominal(pairs)
        summary.append(dict(field=f, n_units=len(ids), n_both_coded=len(both), n_agree=agree,
                            pct_agree=round(100 * agree / len(both), 1) if both else "",
                            alpha_nominal="" if np.isnan(alpha) else round(alpha, 3),
                            n_out_of_codebook=invalid))
        for (a, b), n in sorted(Counter(pairs).items()):
            confusion.append(dict(field=f, coder1=a or "(blank)", coder2=b or "(blank)", n=n))
        for g, (a, b) in zip(ids, pairs):
            if a != b:
                disagree.append(dict(gold_id=g, lang=sheet_a[g].get("lang", ""), field=f, coder1=a, coder2=b,
                                     clause_text=sheet_a[g].get("clause_text", "")))
    return summary, confusion, disagree


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--a", required=True, help="coder 1 sheet")
    ap.add_argument("--b", required=True, help="coder 2 sheet")
    ap.add_argument("--out-dir", default=str(ROOT / "results/agreement"))
    ap.add_argument("--label", default="", help="output name suffix; default: coder-1 sheet name without _coder1/_r1")
    ap.add_argument("--disagreements", default="",
                    help="default: data/processed/agreement/gold_disagreements_<label>.csv (coder-vs-coder codes "
                         "must not sit beside the blind sheets)")
    args = ap.parse_args(argv)

    sheet_a, cols_a = read_sheet(args.a)
    sheet_b, cols_b = read_sheet(args.b)
    only_a, only_b = set(sheet_a) - set(sheet_b), set(sheet_b) - set(sheet_a)
    if only_a or only_b:
        print(f"WARNING gold_ids in one sheet only: coder1 {len(only_a)}, coder2 {len(only_b)} (skipped)")
    fields = [c for c in cols_a if c in cols_b and c not in NOT_FIELDS]
    summary, confusion, disagree = compare(sheet_a, sheet_b, fields)

    out, label = Path(args.out_dir), args.label or sheet_label(args.a)
    prov = sorted({r.get("provenance", "") for sh in (sheet_a, sheet_b) for r in sh.values()} - {""})
    if prov:
        for s in summary:
            s["provenance"] = " / ".join(prov)
    write_csv(out / f"agreement_summary_{label}.csv", summary, list(summary[0]) if summary else ["field"])
    write_csv(out / f"confusion_{label}.csv", confusion, ["field", "coder1", "coder2", "n"])
    dis = Path(args.disagreements or ROOT / "data/processed/agreement" / f"gold_disagreements_{label}.csv")
    write_csv(Path(refuse_annotation_dir(dis)), disagree,
              ["gold_id", "lang", "field", "coder1", "coder2", "clause_text"])
    for s in summary:
        print(f"{s['field']:30} both={s['n_both_coded']:4} agree={s['pct_agree']!s:>5}% "
              f"alpha={s['alpha_nominal']!s:>6} out_of_codebook={s['n_out_of_codebook']}")
    print(f"{len(disagree)} disagreements -> {dis}")


if __name__ == "__main__":
    main()
