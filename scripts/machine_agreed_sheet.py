"""Adjudicated sheet from two coder sheets: a field keeps its value only where both coders gave the same value."""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "analysis"))
from agreement import canon
from gold import CODEBOOK, SHEET_TEXT

NOT_FIELDS = set(SHEET_TEXT) | {"notes", "coder", "provenance", "corrections"}


def agreed(rows_a, rows_b, fields, note):
    full, kept, out, dis = 0, {f: 0 for f in fields}, [], []
    for r in rows_a:
        o, other, all_agree = dict(r), rows_b[r["gold_id"]], True
        for f in fields:
            x, y = canon(r[f], f), canon(other[f], f)
            if x and x == y:
                o[f] = x
                kept[f] += 1
            else:
                o[f], all_agree = "", False
                dis.append((r["gold_id"], r.get("lang", ""), f, x, y))
        o["notes"] = note
        full += all_agree
        out.append(o)
    return out, full, kept, dis


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--components", action="store_true", help="compare the component columns, not the codebook")
    ap.add_argument("--note", default="agreed-subset of two machine coders (not human)")
    ap.add_argument("--list", default="", help="append the disagreements (ids and codes only) to this Markdown file")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    with open(a.a, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header, rows_a = reader.fieldnames, list(reader)
    with open(a.b, encoding="utf-8", newline="") as fh:
        rows_b = {r["gold_id"]: r for r in csv.DictReader(fh)}
    fields = [c for c in header if c not in NOT_FIELDS] if a.components else list(CODEBOOK)
    out, full, kept, dis = agreed(rows_a, rows_b, fields, a.note)
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(out)
    if a.list:
        lines = [f"\n## {a.title or Path(a.out).name}\n",
                 f"{len(out)} clauses; all fields agreed on {full}; {len(dis)} field disagreements.\n",
                 "| gold_id | lang | field | coder 1 | coder 2 | adjudicated value |", "|---|---|---|---|---|---|"]
        lines += [f"| {g} | {l} | {f} | {x or '(blank)'} | {y or '(blank)'} |  |" for g, l, f, x, y in dis]
        with open(a.list, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    print(f"{len(out)} clauses; all fields agreed: {full}; disagreements {len(dis)}; per field kept: {kept}")


if __name__ == "__main__":
    main()
