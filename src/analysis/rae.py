"""Recall-adjusted estimator (N3): correct an observed matcher rate for its sensitivity and false-positive rate."""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

RECALL_GAP_MAX = 0.10


def rogan_gladen(o, s, phi):
    o, s, phi = np.asarray(o, float), np.asarray(s, float), np.asarray(phi, float)
    den = s - phi
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, (o - phi) / np.where(den > 0, den, 1.0), np.nan)


def observed_rate(units, hits, weight="text"):
    units, hits = np.asarray(units, float), np.asarray(hits, float)
    if weight == "unit":
        return hits.sum(axis=-1) / units.sum(axis=-1)
    if weight != "text":
        raise ValueError(f"weight must be 'text' or 'unit', not {weight!r}")
    with np.errstate(divide="ignore", invalid="ignore"):
        rates = np.where(units > 0, hits / np.where(units > 0, units, 1.0), np.nan)
    return np.nanmean(rates, axis=-1)


def bootstrap(units, hits, s, phi, n_pos, n_neg, B=2000, weight="text", rng=None):
    rng = np.random.default_rng(rng)
    units, hits = np.asarray(units, float), np.asarray(hits, float)
    idx = rng.integers(0, len(units), size=(B, len(units)))
    o_b = observed_rate(units[idx], hits[idx], weight)
    s_b = rng.binomial(int(n_pos), s, size=B) / n_pos if n_pos > 0 else np.full(B, s)
    phi_b = rng.binomial(int(n_neg), phi, size=B) / n_neg if n_neg > 0 else np.full(B, phi)
    return dict(o=o_b, s=s_b, phi=phi_b, pi=rogan_gladen(o_b, s_b, phi_b))


def percentile_interval(x, level=0.95):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if not len(x):
        return float("nan"), float("nan")
    a = (1 - level) / 2
    return float(np.quantile(x, a)), float(np.quantile(x, 1 - a))


def estimate(units, hits, s, phi, n_pos, n_neg, B=2000, weight="text", level=0.95, rng=None):
    o = float(observed_rate(units, hits, weight))
    pi = float(rogan_gladen(o, s, phi))
    reps = bootstrap(units, hits, s, phi, n_pos, n_neg, B, weight, rng)
    lo, hi = percentile_interval(reps["pi"], level)
    o_lo, o_hi = percentile_interval(reps["o"], level)
    return dict(n_texts=len(units), o=o, o_lo=o_lo, o_hi=o_hi, sensitivity=s, fpr=phi, n_pos=n_pos, n_neg=n_neg,
                pi=pi, pi_clipped=float(np.clip(pi, 0, 1)) if np.isfinite(pi) else float("nan"), pi_lo=lo, pi_hi=hi,
                out_of_range=bool(np.isfinite(pi) and not 0 <= pi <= 1), undefined=not np.isfinite(pi),
                n_undefined_reps=int(np.sum(~np.isfinite(reps["pi"]))), B=B, level=level, weight=weight), reps


def compare(a, b, reps_a, reps_b, level=0.95):
    d_obs = a["o"] - b["o"]
    d_adj = a["pi"] - b["pi"]
    diff = reps_a["pi"] - reps_b["pi"]
    lo, hi = percentile_interval(diff, level)
    ok = np.isfinite(diff)
    p_flip = float(np.mean(np.sign(diff[ok]) == -np.sign(d_obs))) if ok.any() and d_obs != 0 else float("nan")
    return dict(diff_observed=d_obs, diff_adjusted=d_adj, diff_lo=lo, diff_hi=hi,
                sign_flip=bool(np.sign(d_adj) == -np.sign(d_obs) and d_obs != 0), p_flip=p_flip,
                recall_gap=abs(a["sensitivity"] - b["sensitivity"]),
                gap_ok=abs(a["sensitivity"] - b["sensitivity"]) <= RECALL_GAP_MAX)


def read_validation(path, measure):
    out = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["measure"] != measure:
                continue
            out[r["lang"]] = dict(sensitivity=float(r["sensitivity"]), fpr=float(r["fpr"]), n_pos=int(r["n_pos"]),
                                  n_neg=int(r["n_neg"]), status=r.get("status", "") or "unspecified")
    if not out:
        sys.exit(f"no rows for measure {measure!r} in {path}")
    return out


def read_texts(path, id_col, lang_col, units_col, hits_col):
    by = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            u, h = by.setdefault(r[lang_col], ([], []))
            u.append(float(r[units_col] or 0))
            h.append(float(r[hits_col] or 0))
    return {lg: (np.array(u), np.array(h)) for lg, (u, h) in by.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--texts", required=True)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--measure", required=True)
    ap.add_argument("--id-col", default="text_id")
    ap.add_argument("--lang-col", default="lang")
    ap.add_argument("--units-col", default="n_units")
    ap.add_argument("--hits-col", default="n_hits")
    ap.add_argument("--weight", choices=("text", "unit"), default="text")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--level", type=float, default=0.95)
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--compare", default="hi,en", help="a,b: report a - b ('' = no comparison)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    val = read_validation(args.validation, args.measure)
    texts = read_texts(args.texts, args.id_col, args.lang_col, args.units_col, args.hits_col)
    rng = np.random.default_rng(args.seed)
    rows, reps = [], {}
    for lg in sorted(set(val) & set(texts)):
        v = val[lg]
        est, reps[lg] = estimate(*texts[lg], v["sensitivity"], v["fpr"], v["n_pos"], v["n_neg"], args.B, args.weight,
                                 args.level, rng)
        rows.append(dict(measure=args.measure, lang=lg, validation_status=v["status"], **est))
    if args.compare:
        a, b = args.compare.split(",")
        if a in reps and b in reps:
            ra, rb = (next(r for r in rows if r["lang"] == x) for x in (a, b))
            rows.append(dict(measure=args.measure, lang=f"{a}-{b}",
                             validation_status="+".join(sorted({ra["validation_status"], rb["validation_status"]})),
                             **compare(ra, rb, reps[a], reps[b], args.level)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
