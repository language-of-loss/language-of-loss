import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "annotation"
EMOTIONAL = {"L": 1, "Rs": 1, "NA": 0}


def main():
    key = {r["gold_id"]: r for r in csv.DictReader(open(ANN / "gold_key_v1.csv", encoding="utf-8"))}
    rows, skipped = [], 0
    for g in csv.DictReader(open(ANN / "gold_sheet_v1_adjudicated.csv", encoding="utf-8")):
        if g["lang"] != "hi":
            continue
        v = g["process"].strip()
        if v not in EMOTIONAL:
            skipped += 1
            continue
        rows.append(dict(clause_id=key[g["gold_id"]]["clause_id"], emotional=EMOTIONAL[v],
                         provenance=g.get("provenance", ""), corrections=g.get("corrections", "0")))
    with open(ANN / "a1_gold.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["clause_id", "emotional", "provenance", "corrections"])
        w.writeheader()
        w.writerows(rows)
    print(f"a1_gold.csv: {len(rows)} Hindi clauses (emotional {sum(r['emotional'] for r in rows)}, "
          f"not {sum(1 - r['emotional'] for r in rows)}); left out (process not agreed) {skipped}")


if __name__ == "__main__":
    main()
