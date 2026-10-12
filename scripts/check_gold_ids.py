import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    key = list(csv.DictReader(open(ROOT / "data/annotation/gold_key_v1.csv", encoding="utf-8")))
    texts = {}
    with open(ROOT / "data/processed/clauses.jsonl", encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            texts[c["clause_id"]] = c["clause_text"]
    rows = []
    for k in key:
        t = texts.get(k["clause_id"])
        status = "missing" if t is None else (
            "ok" if hashlib.sha1(t.encode("utf-8")).hexdigest() == k["clause_sha1"] else "text_changed")
        rows.append(dict(gold_id=k["gold_id"], clause_id=k["clause_id"], lang=k["lang"], status=status))
    out = ROOT / "results/gold_id_check.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if r["status"] != "ok"]
    print(f"{len(rows)} gold ids: ok {len(rows) - len(bad)}, missing {sum(r['status'] == 'missing' for r in bad)}, "
          f"text_changed {sum(r['status'] == 'text_changed' for r in bad)} -> {out}")
    for r in bad:
        print(f"  {r['gold_id']} {r['clause_id']} {r['status']}")


if __name__ == "__main__":
    main()
