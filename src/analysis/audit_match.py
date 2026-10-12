"""Output 5: from the two investigators' intensity ratings to matched Hindi-English pairs (draft v4 §3.6 A2)."""
import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ANN, PROC = ROOT / "data" / "annotation", ROOT / "data" / "processed"
TOLERANCE = 0.5
AGREE_WITHIN = 1


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def ratings(sheet, col="intensity_1to7", id_col="rating_id"):
    out = {}
    for r in read(sheet):
        v = (r.get(col) or "").strip()
        if not v:
            continue
        if v not in {str(k) for k in range(1, 8)}:
            raise SystemExit(f"{sheet}: {r[id_col]} {col} = {v!r} (a whole number 1-7 expected)")
        out[r[id_col]] = int(v)
    return out


def alpha(pairs, level):
    import krippendorff
    if len(pairs) < 2 or len({x for p in pairs for x in p}) < 2:
        return float("nan")
    data = np.array([[a for a, _ in pairs], [b for _, b in pairs]], float)
    return float(krippendorff.alpha(reliability_data=data, level_of_measurement=level))


def rated_passages(r1, r2, key, loss):
    rows = []
    for k in key:
        a, b = r1.get(k["rating_id"]), r2.get(k["rating_id"])
        if a is None or b is None:
            continue
        rows.append(dict(passage_id=k["passage_id"], lang=k["lang"], register=k["register"],
                         loss_type=loss.get(k["record_id"], "unknown"), r1=a, r2=b, mean_rating=(a + b) / 2,
                         agreed=int(abs(a - b) <= AGREE_WITHIN)))
    return rows


def reader_passages(readers, key, loss):
    by_id = {k["passage_id"]: k for k in key}
    rows = []
    for r in readers:
        k = by_id.get(r["passage_id"])
        if k is None:
            raise SystemExit(f"reader rating for {r['passage_id']}, which is not in the audit key")
        if not (r.get("mean_rating") or "").strip():
            continue
        rows.append(dict(passage_id=k["passage_id"], lang=k["lang"], register=k["register"],
                         loss_type=loss.get(k["record_id"], "unknown"), r1="", r2="",
                         mean_rating=float(r["mean_rating"]), n_raters=int(r["n_raters"]), agreed=int(r["agreed"])))
    return rows


def match(rows, tol=TOLERANCE):
    cells = defaultdict(lambda: {"hi": [], "en": []})
    for r in rows:
        if r["register"] == "long":
            cells[r["loss_type"]][r["lang"]].append(r)
    pairs, n = [], 0
    for lt in sorted(cells):
        cand = sorted((abs(h["mean_rating"] - e["mean_rating"]), h["passage_id"], e["passage_id"], h, e)
                      for h in cells[lt]["hi"] for e in cells[lt]["en"]
                      if abs(h["mean_rating"] - e["mean_rating"]) <= tol + 1e-9)
        used = set()
        for d, _, _, h, e in cand:
            if h["passage_id"] in used or e["passage_id"] in used:
                continue
            used |= {h["passage_id"], e["passage_id"]}
            n += 1
            pairs.append(dict(pair_id=f"AQ{n:03d}", passage_id_hi=h["passage_id"], passage_id_en=e["passage_id"],
                              rating_hi=h["mean_rating"], rating_en=e["mean_rating"], diff=round(d, 3), loss_type=lt,
                              agreed=int(h["agreed"] and e["agreed"])))
    matched = {p[k] for p in pairs for k in ("passage_id_hi", "passage_id_en")}
    unmatched = Counter(r["lang"] for r in rows if r["register"] == "long" and r["passage_id"] not in matched)
    return pairs, dict(unmatched)


def agreement_rows(rows):
    out = []
    for lang in ("hi", "en", "all"):
        rr = [r for r in rows if lang == "all" or r["lang"] == lang]
        pr = [(r["r1"], r["r2"]) for r in rr]
        out.append(dict(lang=lang, n_both_rated=len(rr), alpha_ordinal=alpha(pr, "ordinal"),
                        alpha_interval=alpha(pr, "interval"),
                        share_within_1=sum(r["agreed"] for r in rr) / len(rr) if rr else float("nan")))
    return out


def calibration_rows(c1, c2, key):
    out = []
    for name, r in (("r1", c1), ("r2", c2)):
        sad = [r[k["calibration_id"]] for k in key if k["calibration_id"] in r and k["sadness"] == "1"]
        non = [r[k["calibration_id"]] for k in key if k["calibration_id"] in r and k["sadness"] == "0"]
        m1, m0 = (float(np.mean(sad)) if sad else float("nan")), (float(np.mean(non)) if non else float("nan"))
        out.append(dict(rater=name, n_sadness=len(sad), mean_sadness=m1, n_other=len(non), mean_other=m0,
                        difference=m1 - m0))
    return out


def write(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows({k: (round(v, 4) if isinstance(v, float) and math.isfinite(v) else v) for k, v in r.items()}
                    for r in rows)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--r1", default=str(ANN / "audit_rating_sheet_r1.csv"))
    ap.add_argument("--r2", default=str(ANN / "audit_rating_sheet_r2.csv"))
    ap.add_argument("--key", default=str(ANN / "audit_key.csv"))
    ap.add_argument("--text-meta", default=str(PROC / "text_meta.csv"))
    ap.add_argument("--cal-r1", default=str(ANN / "audit_calibration_brighter_r1.csv"))
    ap.add_argument("--cal-r2", default=str(ANN / "audit_calibration_brighter_r2.csv"))
    ap.add_argument("--cal-key", default=str(ANN / "audit_calibration_key.csv"))
    ap.add_argument("--processed", default=str(PROC))
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--tolerance", type=float, default=TOLERANCE)
    ap.add_argument("--readers", default="", help="reader_ingest.py output: readers' mean intensity replaces r1/r2")
    args = ap.parse_args(argv)
    loss = {r["record_id"]: r["loss_type"] for r in read(args.text_meta)} if Path(args.text_meta).exists() else {}
    proc, res = Path(args.processed), Path(args.results)
    if args.readers:
        rows = reader_passages(read(args.readers), read(args.key), loss)
        if not rows:
            raise SystemExit(f"{args.readers}: no reader ratings")
        pairs, unmatched = match(rows, args.tolerance)
        write(proc / "audit_ratings.csv", rows)
        write(proc / "audit_pairs.csv", pairs, ["pair_id", "passage_id_hi", "passage_id_en", "rating_hi", "rating_en",
                                                "diff", "loss_type", "agreed"])
        print(f"reader-rated passages: {len(rows)}; pairs: {len(pairs)} (agreed {sum(p['agreed'] for p in pairs)}); "
              f"unmatched long-form passages: {unmatched}")
        return
    r1, r2 = ratings(args.r1), ratings(args.r2)
    if not r1 or not r2:
        raise SystemExit("the rating sheets are not filled yet (intensity_1to7 empty): nothing to match")
    rows = rated_passages(r1, r2, read(args.key), loss)
    pairs, unmatched = match(rows, args.tolerance)
    write(proc / "audit_ratings.csv", rows)
    write(proc / "audit_pairs.csv", pairs, ["pair_id", "passage_id_hi", "passage_id_en", "rating_hi", "rating_en",
                                            "diff", "loss_type", "agreed"])
    write(res / "audit_rating_agreement.csv", agreement_rows(rows))
    if Path(args.cal_key).exists() and Path(args.cal_r1).exists() and Path(args.cal_r2).exists():
        c1 = ratings(args.cal_r1, id_col="calibration_id")
        c2 = ratings(args.cal_r2, id_col="calibration_id")
        if c1 and c2:
            write(res / "audit_calibration.csv", calibration_rows(c1, c2, read(args.cal_key)))
    print(f"rated by both: {len(rows)}; pairs: {len(pairs)} (agreed {sum(p['agreed'] for p in pairs)}); "
          f"unmatched long-form passages: {unmatched}")


if __name__ == "__main__":
    main()
