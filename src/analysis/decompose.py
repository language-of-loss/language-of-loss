"""Eligibility-conditioned decomposition of the hi - en gap in experiencer-backgrounding framings (N2/P8b)."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from gold import split_of

ROOT = Path(__file__).resolve().parents[2]
FORCED = {"hi": {"forced_dative"}, "en": {"forced_impersonal"}}
CHOSEN = {"hi": {"chosen_dative"}, "en": {"chosen_impersonal"}}
NOMINATIVE_ALT = {"hi": {"chosen_nominative"}, "en": {"chosen_nominative"}}
LABELS = {
    "dative": dict(forced=FORCED, chosen=CHOSEN, alt=NOMINATIVE_ALT, unit="clause",
                   out="results/optional/decompose_dev.csv"),
    "relational": dict(forced={lg: {"forced_relational"} for lg in ("hi", "en")},
                       chosen={lg: {"chosen_relational"} for lg in ("hi", "en")},
                       alt={lg: {"chosen_individual"} for lg in ("hi", "en")}, unit="site",
                       out="results/decompose_relational_dev.csv"),
}
COUNTS = ("n", "forced", "chosen", "nominative_alt", "review")
COMPONENTS = ("forced_share", "opportunity_share", "choice_share")


def clause_flags(eligibility_rows, marker="dative", unit=None):
    lab = LABELS[marker]
    unit = unit or lab["unit"]
    out = {}
    for r in eligibility_rows:
        if r.get("marker_type", "dative") != marker:
            continue
        d = out.setdefault(r["clause_id"], dict(lang=r["lang"], forced=0, chosen=0, nominative_alt=0, review=0))
        dec, lg = r["decision"], r["lang"]
        hits = dict(forced=dec in lab["forced"].get(lg, ()), chosen=dec in lab["chosen"].get(lg, ()),
                    nominative_alt=dec in lab["alt"].get(lg, ()), review=dec == "review")
        for k, v in hits.items():
            d[k] = d[k] + int(v) if unit == "site" else d[k] | int(v)
    return out


def english_home_records(text_meta_path):
    with open(text_meta_path, encoding="utf-8", newline="") as fh:
        meta = list(csv.DictReader(fh))
    if not meta or "home_language_statement" not in meta[0]:
        raise SystemExit(f"{text_meta_path}: no home_language_statement column (run `make text_meta`)")
    en = [r for r in meta if r["lang"] == "en" and r["home_language_statement"] == "en"]
    unconfirmed = [r["record_id"] for r in en if r.get("meta_review_status") != "human_confirmed"]
    if unconfirmed:
        raise SystemExit(f"refusing --subset english_home: {len(unconfirmed)} English text(s) with a pre-filled, "
                         "unconfirmed home_language_statement (data/annotation/meta_review.csv)")
    if not en:
        raise SystemExit("refusing --subset english_home: no English text has home_language_statement = en in "
                         f"{text_meta_path}; output 4 cannot be estimated on this corpus as specified")
    return {r["record_id"] for r in meta if r["lang"] == "hi"} | {r["record_id"] for r in en}


def text_counts(referent_rows, flags, split="dev", experiencer=None, records=None):
    texts = {"hi": defaultdict(lambda: dict.fromkeys(COUNTS, 0)), "en": defaultdict(lambda: dict.fromkeys(COUNTS, 0))}
    lang_of_record = {cid.split("#")[0]: fl["lang"] for cid, fl in flags.items()}
    for r in referent_rows:
        rid = r["clause_id"].split("#")[0]
        if split != "all" and split_of(rid) != split:
            continue
        if records is not None and rid not in records:
            continue
        if experiencer and r["referent_class"] not in experiencer:
            continue
        fl = flags.get(r["clause_id"])
        if fl is None:
            lang = r.get("lang") or lang_of_record.get(rid)
            if lang not in texts:
                raise ValueError(f"{r['clause_id']}: no eligibility row and no language to place it")
            texts[lang][rid]["n"] += 1
            continue
        c = texts[fl["lang"]][rid]
        c["n"] += 1
        for k in ("forced", "chosen", "nominative_alt", "review"):
            c[k] += int(fl[k])
    return {lang: dict(t) for lang, t in texts.items()}


def rates(n, forced, chosen, nom):
    n, forced, chosen, nom = (np.asarray(x, dtype=float) for x in (n, forced, chosen, nom))
    sites = chosen + nom
    with np.errstate(invalid="ignore", divide="ignore"):
        f = 100 * forced / n
        q = 100 * sites / n
        p = np.where(sites > 0, chosen / sites, np.nan)
        r = 100 * (forced + chosen) / n
    return dict(f=f, q=q, p=p, r=r)


def decompose(hi, en):
    p_bar, q_bar = (hi["p"] + en["p"]) / 2, (hi["q"] + en["q"]) / 2
    out = dict(forced_share=hi["f"] - en["f"], opportunity_share=(hi["q"] - en["q"]) * p_bar,
               choice_share=q_bar * (hi["p"] - en["p"]))
    out["delta"] = hi["r"] - en["r"]
    return out


def matrix(texts):
    keys = sorted(texts)
    return np.array([[texts[k][c] for c in COUNTS] for k in keys], dtype=float).reshape(len(keys), len(COUNTS))


def bootstrap(texts, B=2000, seed=20261009):
    rng = np.random.default_rng(seed)
    m = {lang: matrix(texts[lang]) for lang in ("hi", "en")}
    point = {lang: rates(*m[lang].sum(0)[:4]) for lang in m}
    est = decompose(point["hi"], point["en"])
    reps = {}
    for lang, x in m.items():
        idx = rng.integers(0, len(x), size=(B, len(x)))
        s = x[idx].sum(1)
        reps[lang] = rates(s[:, 0], s[:, 1], s[:, 2], s[:, 3])
    comp = decompose(reps["hi"], reps["en"])
    ok = np.isfinite(comp["opportunity_share"]) & np.isfinite(comp["choice_share"])
    rows = []
    for lang in ("hi", "en"):
        for k in ("r", "f", "q", "p"):
            v = reps[lang][k][np.isfinite(reps[lang][k])]
            rows.append(dict(quantity=f"{k}_{lang}", estimate=float(point[lang][k]),
                             lo=float(np.percentile(v, 2.5)) if len(v) else np.nan,
                             hi=float(np.percentile(v, 97.5)) if len(v) else np.nan))
    for k in ("delta",) + COMPONENTS:
        v = comp[k][np.isfinite(comp[k])]
        rows.append(dict(quantity=k, estimate=float(est[k]), lo=float(np.percentile(v, 2.5)) if len(v) else np.nan,
                         hi=float(np.percentile(v, 97.5)) if len(v) else np.nan))
    info = dict(B=B, replicates_dropped=int((~ok).sum()), seed=seed,
                **{f"n_texts_{l}": len(texts[l]) for l in texts},
                **{f"{c}_{l}": int(m[l][:, i].sum()) for l in m for i, c in enumerate(COUNTS)},
                hi_nominative_alt_detected=bool(m["hi"][:, 3].sum() > 0))
    return rows, info


def drop_largest(texts, B=2000, seed=20261009):
    largest, summary = {}, {}
    for lang in ("hi", "en"):
        n = {rid: c["n"] for rid, c in texts[lang].items()}
        if n:
            rid = max(n, key=lambda r: (n[r], r))
            largest[lang] = rid
            summary[f"largest_{lang}"] = dict(record_id=rid, finite_clauses=n[rid],
                                              share_of_clauses=round(n[rid] / sum(n.values()), 4),
                                              n_texts=len(n))
    variants = [("all", ())] + [(f"drop_largest_{l}", (l,)) for l in ("hi", "en") if l in largest]
    if len(largest) == 2:
        variants.append(("drop_largest_both", ("hi", "en")))
    rows = []
    for name, langs in variants:
        sub = {l: {r: c for r, c in texts[l].items() if not (l in langs and r == largest[l])} for l in ("hi", "en")}
        if not all(sub.values()):
            continue
        vrows, _ = bootstrap(sub, B, seed)
        dropped = "; ".join(f"{l}:{largest[l]}" for l in langs)
        rows += [dict(variant=name, dropped=dropped, **r) for r in vrows]
    return rows, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--eligibility", default=str(ROOT / "data/processed/eligibility.csv"))
    ap.add_argument("--referents", default=str(ROOT / "data/processed/referents.csv"))
    ap.add_argument("--split", default="dev", choices=["dev", "confirmatory", "all"])
    ap.add_argument("--experiencer", default="", help="comma list of referent classes to keep (default all)")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--marker", default="dative", choices=sorted(LABELS))
    ap.add_argument("--unit", default=None, choices=["clause", "site"], help="default: the marker's own unit")
    ap.add_argument("--out", default=None, help="default: the marker's own results/ file")
    ap.add_argument("--subset", default="all", choices=["all", "english_home"])
    ap.add_argument("--text-meta", default=str(ROOT / "data/processed/text_meta.csv"))
    args = ap.parse_args(argv)
    args.unit = args.unit or LABELS[args.marker]["unit"]
    args.out = args.out or str(ROOT / LABELS[args.marker]["out"])

    with open(args.eligibility, encoding="utf-8", newline="") as fh:
        flags = clause_flags(csv.DictReader(fh), args.marker, args.unit)
    with open(args.referents, encoding="utf-8", newline="") as fh:
        texts = text_counts(csv.DictReader(fh), flags, args.split,
                            set(args.experiencer.split(",")) if args.experiencer else None,
                            english_home_records(args.text_meta) if args.subset == "english_home" else None)
    rows, info = bootstrap(texts, args.B, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["quantity", "estimate", "lo", "hi"])
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    info.update(split=args.split, subset=args.subset, experiencer=args.experiencer or "all", marker=args.marker,
                unit=args.unit,
                status="machine-provisional, unreviewed")
    sens, summary = drop_largest(texts, args.B, args.seed)
    sens_path = out.with_name(out.stem + "_drop_largest.csv")
    with open(sens_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["variant", "dropped", "quantity", "estimate", "lo", "hi"])
        w.writeheader()
        for r in sens:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    info.update(drop_largest=summary, drop_largest_file=sens_path.name,
                split_note="dev = hash threshold on record_id (gold.split_of): the dev text set grows with the corpus")
    out.with_suffix(".json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r['quantity']:18} {r['estimate']:9.3f}  [{r['lo']:9.3f}, {r['hi']:9.3f}]")
    print(json.dumps(info))
    for lang in ("hi", "en"):
        lg = summary.get(f"largest_{lang}")
        if lg:
            print(f"largest {lang} text {lg['record_id']}: {100 * lg['share_of_clauses']:.0f}% of {lang} clauses")
    show = [q for q in ("delta",) + COMPONENTS]
    for name in dict.fromkeys(r["variant"] for r in sens):
        vals = {r["quantity"]: r for r in sens if r["variant"] == name}
        print(f"{name:18} " + "  ".join(f"{q} {vals[q]['estimate']:.3f}" for q in show if q in vals))
    if args.marker == "dative" and not info["hi_nominative_alt_detected"]:
        print("WARNING: no Hindi chosen_nominative rows in eligibility.csv -> Hindi p and q (and the choice / "
              "eligibility shares) are not interpretable")


if __name__ == "__main__":
    main()
