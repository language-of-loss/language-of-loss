"""Output 2b: Rogan-Gladen corrected rates of the dictionary channel, per category per language (N3, rae.py)."""
import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rae
from gold import split_of
from predictions import tests_allowed

ROOT = Path(__file__).resolve().parents[2]
NOT_VALIDATION = ("pilot", "placeholder", "stand-in", "standin", "mechanics")
COLUMNS = ["measure", "lang", "n_texts", "observed", "observed_lo", "observed_hi", "corrected", "lo", "hi",
           "sensitivity", "fpr", "n_pos", "n_neg", "flags", "status", "split"]
DIFF_COLUMNS = ["measure", "lang", "diff_observed", "diff_corrected", "lo", "hi", "sign_flip", "p_flip", "recall_gap",
                "gap_ok", "status", "split"]


def validation_rows(path):
    out = defaultdict(dict)
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["channel"] != "dict" or r["lang"] not in ("hi", "en"):
                continue
            if any(k in r["status"].lower() for k in NOT_VALIDATION):
                raise SystemExit(f"refusing: {path} row {r['measure']} ({r['lang']}) has status '{r['status']}', not a "
                                 "validation against the adjudicated gold set")
            out[r["measure"]][r["lang"]] = r
    return out


def per_text_counts(dict_path, clauses_path, split):
    finite = {}
    units = defaultdict(lambda: defaultdict(int))
    with open(clauses_path, encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            if c["is_finite"] and (split == "all" or split_of(c["record_id"]) == split):
                finite[c["clause_id"]] = (c["lang"], c["record_id"])
                units[c["lang"]][c["record_id"]] += 1
    hits = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    with open(dict_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["clause_id"] not in finite:
                continue
            lang, rid = finite[r["clause_id"]]
            for field, value in r.items():
                if field not in ("clause_id", "evidence") and value:
                    hits[(field, value)][lang][rid] += 1
    return hits, units


def measure_key(measure):
    field, value = measure.split(":", 1)[1].split("=", 1)
    return field, value


def run(validation, hits, units, split, B=2000, seed=20261009):
    rows, diffs = [], []
    rng = np.random.default_rng(seed)
    for measure in sorted(validation):
        key = measure_key(measure)
        est, reps = {}, {}
        for lang, v in sorted(validation[measure].items()):
            n_pos, n_neg = int(v["n_pos"]), int(v["n_neg"])
            if not n_pos or not n_neg or not v["sensitivity"] or v["fpr"] == "":
                continue
            texts = sorted(units[lang])
            u = np.array([units[lang][t] for t in texts], float)
            h = np.array([hits[key][lang].get(t, 0) for t in texts], float)
            e, rp = rae.estimate(u, h, float(v["sensitivity"]), float(v["fpr"]), n_pos, n_neg, B=B,
                                 rng=rng.integers(1 << 31))
            est[lang], reps[lang] = e, rp
            flags = [k for k in ("out_of_range", "undefined") if e[k]]
            rows.append(dict(measure=measure, lang=lang, n_texts=e["n_texts"], observed=e["o"], observed_lo=e["o_lo"],
                             observed_hi=e["o_hi"], corrected=e["pi"], lo=e["pi_lo"], hi=e["pi_hi"],
                             sensitivity=e["sensitivity"], fpr=e["fpr"], n_pos=n_pos, n_neg=n_neg,
                             flags=" ".join(flags), status=v["status"], split=split))
        if "hi" in est and "en" in est:
            c = rae.compare(est["hi"], est["en"], reps["hi"], reps["en"])
            diffs.append(dict(measure=measure, lang="hi-en", diff_observed=c["diff_observed"],
                              diff_corrected=c["diff_adjusted"], lo=c["diff_lo"], hi=c["diff_hi"],
                              sign_flip=c["sign_flip"], p_flip=c["p_flip"], recall_gap=c["recall_gap"],
                              gap_ok=c["gap_ok"], status=validation[measure]["hi"]["status"], split=split))
    return rows, diffs


def write(path, rows, diffs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = lambda v: round(v, 6) if isinstance(v, float) and math.isfinite(v) else v
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows({k: fmt(v) for k, v in r.items()} for r in rows)
    dpath = path.with_name(path.stem + "_hi_minus_en.csv")
    with open(dpath, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=DIFF_COLUMNS)
        w.writeheader()
        w.writerows({k: fmt(v) for k, v in r.items()} for r in diffs)
    return path, dpath


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--validation", default=str(ROOT / "results/validation_table.csv"))
    ap.add_argument("--dict", default=str(ROOT / "data/processed/dict_channel.csv"))
    ap.add_argument("--clauses", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--agreement", default=str(ROOT / "results/agreement/agreement_summary_gold_sheet_v1.csv"))
    ap.add_argument("--split", default="dev", choices=["dev", "confirmatory", "all"])
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--out", default=str(ROOT / "results/corrected_rates.csv"))
    args = ap.parse_args(argv)
    if not tests_allowed(args.agreement):
        raise SystemExit(f"refusing: {args.agreement} holds no agreement statistics (study protocol: nothing is validated "
                         "before independent human annotation and agreement statistics)")
    validation = validation_rows(args.validation)
    hits, units = per_text_counts(args.dict, args.clauses, args.split)
    rows, diffs = run(validation, hits, units, args.split, args.B, args.seed)
    out, dout = write(args.out, rows, diffs)
    print(f"{len(rows)} measure x language rows -> {out}; {len(diffs)} hi - en rows -> {dout}; "
          f"sign flips: {sum(1 for d in diffs if d['sign_flip'])}")


if __name__ == "__main__":
    main()
