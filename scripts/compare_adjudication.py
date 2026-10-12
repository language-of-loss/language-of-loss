"""Robustness comparison: every output-2 number on the agreed-only gold set vs the majority-adjudicated gold set."""
import argparse
import csv
import io
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/robustness"
SPECS = {
    "validation_table.csv": (["channel", "field", "value", "lang"], ["precision", "recall", "f1", "fpr"], ["n_pos"]),
    "rule_table_check.csv": (["field", "lang"], ["accuracy", "lo", "hi"], ["n"]),
    "corrected_rates_dev.csv": (["measure", "lang"], ["observed", "corrected", "lo", "hi", "sensitivity", "fpr"],
                                ["n_pos", "n_neg"]),
    "corrected_rates_dev_hi_minus_en.csv": (["measure", "lang"], ["diff_observed", "diff_corrected", "lo", "hi"], []),
    "corrected_rates_confirmatory.csv": (["measure", "lang"],
                                         ["observed", "corrected", "lo", "hi", "sensitivity", "fpr"],
                                         ["n_pos", "n_neg"]),
    "corrected_rates_confirmatory_hi_minus_en.csv": (["measure", "lang"],
                                                     ["diff_observed", "diff_corrected", "lo", "hi"], []),
}


def rows_at(commit, name):
    text = subprocess.run(["git", "show", f"{commit}:results/{name}"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout
    return list(csv.DictReader(io.StringIO(text)))


def rows_now(name):
    with open(ROOT / "results" / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def same(a, b):
    fa, fb = num(a), num(b)
    if fa is None or fb is None:
        return (a or "") == (b or "")
    return abs(fa - fb) < 1e-9 or (fa != fa and fb != fb)


def macro_f1(rows):
    acc = defaultdict(list)
    for r in rows:
        if r["channel"] == "dict" and num(r["n_pos"]) and num(r["f1"]) is not None:
            acc[(r["field"], r["lang"])].append(float(r["f1"]))
    return {k: (sum(v) / len(v), len(v)) for k, v in acc.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--baseline", required=True, help="commit holding the agreed-only results")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    out = []
    for name, (keys, metrics, ncols) in SPECS.items():
        old = {tuple(r[k] for k in keys): r for r in rows_at(a.baseline, name)}
        new = {tuple(r[k] for k in keys): r for r in rows_now(name)}
        for key in list(old) + [k for k in new if k not in old]:
            o, n = old.get(key, {}), new.get(key, {})
            for m in metrics:
                out.append(dict(file=name, key="|".join(key), metric=m, agreed_only=o.get(m, ""),
                                majority=n.get(m, ""),
                                n_agreed=sum(int(num(o.get(c)) or 0) for c in ncols) if o and ncols else "",
                                n_majority=sum(int(num(n.get(c)) or 0) for c in ncols) if n and ncols else "",
                                changed=not same(o.get(m), n.get(m))))
    with open(OUT / "adjudication_output2.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    mo, mn = macro_f1(rows_at(a.baseline, "validation_table.csv")), macro_f1(rows_now("validation_table.csv"))
    mf = [dict(field=f, lang=l, macro_f1_agreed_only=round(mo[(f, l)][0], 4) if (f, l) in mo else "",
               macro_f1_majority=round(mn[(f, l)][0], 4) if (f, l) in mn else "",
               n_values_agreed=mo.get((f, l), ("", ""))[1], n_values_majority=mn.get((f, l), ("", ""))[1])
          for f, l in sorted(set(mo) | set(mn))]
    with open(OUT / "adjudication_macro_f1.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mf[0]))
        w.writeheader()
        w.writerows(mf)
    print(f"{len(out)} output-2 numbers compared ({sum(r['changed'] for r in out)} changed) -> "
          f"{(OUT / 'adjudication_output2.csv').relative_to(ROOT)}; macro-F1 -> adjudication_macro_f1.csv")


if __name__ == "__main__":
    main()
