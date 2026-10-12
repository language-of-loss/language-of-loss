import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
from gold import split_of


def main():
    records = sorted({json.loads(l)["record_id"] for l in open(ROOT / "data/processed/clauses.jsonl", encoding="utf-8")})
    out = ROOT / "data/processed/split.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", "split"])
        w.writerows([r, split_of(r)] for r in records)
    print(f"{len(records)} records -> {out}: {dict(Counter(split_of(r) for r in records))}")


if __name__ == "__main__":
    main()
