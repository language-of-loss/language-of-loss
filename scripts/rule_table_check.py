"""Eligibility rule table vs hand-coded grammar_forced / dative_alternative_available (accuracy, threshold 0.80)."""
import argparse
import csv
import math

FIELDS = ["grammar_forced", "dative_alternative_available"]


def wilson(k, n, z=1.96):
    if not n:
        return "", ""
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 4), round(c + h, 4)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold", required=True)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--threshold", type=float, default=0.80)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.gold, encoding="utf-8", newline="") as fh:
        gold = list(csv.DictReader(fh))
    with open(a.rules, encoding="utf-8", newline="") as fh:
        rules = {r["gold_id"]: r for r in csv.DictReader(fh)}
    rows = []
    for f in FIELDS:
        for lang in ("hi", "en", "all"):
            items = [(g[f].strip(), rules[g["gold_id"]][f].strip()) for g in gold
                     if lang in ("all", g["lang"]) and g[f].strip()]
            n, k = len(items), sum(1 for x, y in items if x == y)
            lo, hi = wilson(k, n)
            acc = round(k / n, 4) if n else ""
            rows.append(dict(field=f, lang=lang, n=n, n_agree=k, accuracy=acc, lo=lo, hi=hi, threshold=a.threshold,
                             result=("pass" if n and k / n >= a.threshold else "fail" if n else "no items"),
                             status=a.status))
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['field']:30s} {r['lang']:3s} n={r['n']:3d} acc={r['accuracy']} [{r['lo']}, {r['hi']}] {r['result']}")


if __name__ == "__main__":
    main()
