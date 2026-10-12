import argparse, csv, datetime, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
from gold import CODEBOOK, COMPONENT_VALUES

SHEETS = {"codebook": ROOT / "data/annotation/gold_sheet_v1_adjudicated.csv",
          "components": ROOT / "data/annotation/gold_components_v1_adjudicated.csv"}
DEC = ROOT / "data/processed/agreement/adjudication_decisions.csv"
LOG = ROOT / "docs/adjudication_log.csv"
DISAGREEMENTS = {"codebook": ROOT / "data/processed/agreement/gold_disagreements_gold_sheet_v1.csv",
                 "components": ROOT / "data/processed/agreement/gold_disagreements_gold_components_v1.csv"}
DEC_COLS = ["sheet", "gold_id", "lang", "field", "coder1", "coder2", "decision", "source", "decided_by", "note"]
LOG_COLS = ["sheet", "gold_id", "lang", "field", "coder1", "coder2", "decision", "source", "decided_by", "date"]


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        return rd.fieldnames, list(rd)


def majority(third_path, decided_by, out=DEC):
    _, third = read(third_path)
    t = {(r["sheet"], r["gold_id"], r["field"]): r for r in third}
    rows, n = [], {"coder1": 0, "coder2": 0, "unresolved": 0}
    for s, p in DISAGREEMENTS.items():
        for d in read(p)[1]:
            r = t.get((s, d["gold_id"], d["field"]))
            if r is None or not r["third"]:
                sys.exit(f"no third code for {s}/{d['gold_id']}/{d['field']}")
            v = r["third"]
            if v in (d["coder1"], d["coder2"]):
                n["coder1" if v == d["coder1"] else "coder2"] += 1
                dec, src = v, "majority_with_third_coder"
            else:
                n["unresolved"] += 1
                dec, src = "", "unresolved_three_way"
            rows.append(dict(sheet=s, gold_id=d["gold_id"], lang=d["lang"], field=d["field"], coder1=d["coder1"],
                             coder2=d["coder2"], decision=dec, source=src, decided_by=decided_by,
                             note=f"third coder: {v}"))
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=DEC_COLS); w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} decisions -> {out}: coder 1 + third {n['coder1']}, coder 2 + third {n['coder2']}, "
          f"unresolved three-way {n['unresolved']}")
    return n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--decisions", default=DEC)
    ap.add_argument("--provenance", help="new text for the provenance column of every row of both sheets")
    ap.add_argument("--majority-from", help="third-coder CSV: write the decisions file by majority and stop")
    ap.add_argument("--decided-by", default="", help="with --majority-from: the decided_by text")
    a = ap.parse_args()
    if a.majority_from:
        if not a.decided_by:
            sys.exit("--decided-by is required with --majority-from")
        majority(a.majority_from, a.decided_by, a.decisions); return
    _, decs = read(a.decisions)
    logged = {(r["sheet"], r["gold_id"], r["field"], r["decision"]) for r in read(LOG)[1]} if LOG.exists() else set()
    unresolved_log = []
    sheets = {s: read(p) for s, p in SHEETS.items()}
    index = {s: {r["gold_id"]: r for r in rows} for s, (_, rows) in sheets.items()}
    applied, undecided, errors, log = 0, 0, [], []
    for d in decs:
        v = (d.get("decision") or "").strip()
        if not v:
            undecided += 1
            if (d.get("source") or "").strip() and (d["sheet"], d["gold_id"], d["field"], "") not in logged:
                unresolved_log.append(dict(sheet=d["sheet"], gold_id=d["gold_id"], lang=d.get("lang", ""),
                                           field=d["field"], coder1=d.get("coder1", ""), coder2=d.get("coder2", ""),
                                           decision="", source=d["source"], decided_by=d.get("decided_by", ""),
                                           date=datetime.date.today().isoformat()))
            continue
        s, gid, f = d["sheet"], d["gold_id"], d["field"]
        allowed = CODEBOOK.get(f) if s == "codebook" else COMPONENT_VALUES
        if s not in index or gid not in index[s] or f not in sheets[s][0]:
            errors.append(f"unknown item {s}/{gid}/{f}"); continue
        canon = next((x for x in allowed if x.lower() == v.lower()), None)
        if canon is None:
            errors.append(f"{gid} {f}: '{v}' is not in the codebook ({', '.join(allowed)})"); continue
        cur = index[s][gid][f].strip()
        if cur and cur != canon:
            errors.append(f"{gid} {f}: sheet already holds '{cur}', decision says '{canon}'"); continue
        index[s][gid][f] = canon; applied += 1
        if (s, gid, f, canon) in logged:
            continue
        log.append(dict(sheet=s, gold_id=gid, lang=d.get("lang", ""), field=f, coder1=d.get("coder1", ""),
                        coder2=d.get("coder2", ""), decision=canon, source=d.get("source", ""),
                        decided_by=d.get("decided_by", ""), date=datetime.date.today().isoformat()))
    if errors:
        print("REFUSED, nothing written:\n  " + "\n  ".join(errors)); sys.exit(1)
    print(f"{applied} decisions valid, {undecided} still undecided; {len(log) + len(unresolved_log)} new log rows.")
    if a.provenance:
        for s, (cols, rows) in sheets.items():
            if "provenance" not in cols:
                print(f"REFUSED: {SHEETS[s].name} has no provenance column"); sys.exit(1)
            for r in rows:
                r["provenance"] = a.provenance
        print(f"provenance -> {a.provenance!r}")
    if a.dry_run:
        print("dry run: nothing written"); return
    for s, (cols, rows) in sheets.items():
        with open(SHEETS[s], "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    new = not LOG.exists()
    with open(LOG, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_COLS); new and w.writeheader(); w.writerows(log + unresolved_log)
    print(f"written: {SHEETS['codebook'].name}, {SHEETS['components'].name}; log {LOG}")


if __name__ == "__main__":
    main()
