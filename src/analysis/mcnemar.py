"""Output 8b: one MuRIL classifier pair, trained on translated data versus native data, compared on the same held-out"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from predictions import tests_allowed

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "data" / "processed" / "channels"


def read_labels(path, col):
    out = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            v = (r.get(col) or "").strip()
            if v == "":
                continue
            if v not in ("0", "1"):
                raise SystemExit(f"{path}: {r['clause_id']} {col} = {v!r} (0 or 1 expected)")
            out[r["clause_id"]] = int(v)
    return out


def scores(gold, pred):
    tp = sum(1 for k in gold if gold[k] and pred[k])
    fp = sum(1 for k in gold if not gold[k] and pred[k])
    fn = sum(1 for k in gold if gold[k] and not pred[k])
    acc = sum(1 for k in gold if gold[k] == pred[k]) / len(gold)
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
    return acc, f1


def mcnemar(gold, a, b):
    from scipy.stats import binomtest
    ra = {k: gold[k] == a[k] for k in gold}
    rb = {k: gold[k] == b[k] for k in gold}
    n_b = sum(1 for k in gold if ra[k] and not rb[k])
    n_c = sum(1 for k in gold if rb[k] and not ra[k])
    p = binomtest(n_b, n_b + n_c, 0.5).pvalue if n_b + n_c else 1.0
    return n_b, n_c, float(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gold", default=str(ROOT / "data/annotation/a1_gold.csv"))
    ap.add_argument("--translated", default=str(CH / "muril_translated_predictions.csv"))
    ap.add_argument("--native", default=str(CH / "muril_native_predictions.csv"))
    ap.add_argument("--agreement", default=str(ROOT / "results/agreement/agreement_summary_gold_sheet_v1.csv"))
    ap.add_argument("--status", default="held-out native Hindi gold clauses")
    ap.add_argument("--out", default=str(ROOT / "results/mcnemar_muril.csv"))
    args = ap.parse_args(argv)
    if not tests_allowed(args.agreement):
        raise SystemExit(f"refusing: {args.agreement} holds no agreement statistics (study protocol: no hypothesis test "
                         "before independent human annotation and agreement statistics)")
    gold = read_labels(args.gold, "emotional")
    tr, na = read_labels(args.translated, "pred"), read_labels(args.native, "pred")
    keys = sorted(set(gold) & set(tr) & set(na))
    if not keys:
        raise SystemExit("no clause is in the gold file and in both prediction files")
    gold = {k: gold[k] for k in keys}
    acc_t, f1_t = scores(gold, tr)
    acc_n, f1_n = scores(gold, na)
    n_b, n_c, p = mcnemar(gold, tr, na)
    rows = [("n_clauses", len(keys)), ("gold_positive", sum(gold.values())),
            ("accuracy_translated", acc_t), ("f1_translated", f1_t), ("accuracy_native", acc_n), ("f1_native", f1_n),
            ("discordant_translated_right_native_wrong", n_b), ("discordant_native_right_translated_wrong", n_c),
            ("mcnemar_exact_p_two_sided", p)]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["quantity", "value", "status"])
        for q, v in rows:
            w.writerow([q, round(v, 6) if isinstance(v, float) else v, args.status])
    print(f"{len(keys)} clauses; F1 translated {f1_t:.3f}, native {f1_n:.3f}; discordant {n_b} / {n_c}; p {p:.4g}")


if __name__ == "__main__":
    main()
