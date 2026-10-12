import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from gold import split_of

ROOT = Path(__file__).resolve().parents[2]


def feel_site(r):
    return (r["lang"] == "hi" and (r["predicate"] == "लग" or r["predicate"].endswith("+लग"))) or (r["lang"] == "en" and r["predicate"] in ("feel", "seem"))


def main(argv=None):
    proc = ROOT / "data" / "processed"
    n = Counter()
    for r in csv.DictReader(open(proc / "referents.csv", encoding="utf-8", newline="")):
        rid = r["clause_id"].split("#")[0]
        lang = "hi" if any("ऀ" <= ch <= "ॿ" for ch in "") else None
        n[(rid, )] += 1
    lang_of, sites = {}, Counter()
    for r in csv.DictReader(open(proc / "eligibility.csv", encoding="utf-8", newline="")):
        rid = r["clause_id"].split("#")[0]
        lang_of[rid] = r["lang"]
        if r.get("marker_type", "dative") == "dative" and feel_site(r):
            for split in ("dev", "all"):
                if split == "all" or split_of(rid) == split:
                    sites[(r["lang"], split, r["rule_id"], r["decision"])] += 1
    den = Counter()
    for (rid,), k in n.items():
        for split in ("dev", "all"):
            if split == "all" or split_of(rid) == split:
                den[(lang_of.get(rid), split)] += k
    out = ROOT / "results" / "optional" / "feel_rates.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["lang", "split", "rule_id", "decision", "sites", "finite_clauses", "per_100"])
        for (lang, split, rule, dec), k in sorted(sites.items()):
            d = den[(lang, split)]
            w.writerow([lang, split, rule, dec, k, d, round(100 * k / d, 3) if d else ""])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
