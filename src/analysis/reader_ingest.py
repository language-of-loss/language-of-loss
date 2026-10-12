"""Reader study responses -> per-passage reader intensity (the human standard for output 5) and reader alpha."""
import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
AGREE_WITHIN = 1
PASSAGE = re.compile(r"^\s*\[B(\d+)-(\d+)\]")
SKIP = re.compile(r"^\s*\[B(\d+)-(\d+) skip\]")
REPLY = re.compile(r"^\s*\[R(\d+)\]")
CONSENT = "I am 18 or older"
STATUS = "reader study (anonymous adult readers)"


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def kripp_interval(matrix):
    import krippendorff
    m = np.array(matrix, dtype=float)
    if m.size == 0 or m.shape[0] < 2:
        return float("nan")
    pairable = (np.sum(~np.isnan(m), axis=0) >= 2)
    vals = m[:, pairable]
    if not pairable.any() or len(np.unique(vals[~np.isnan(vals)])) < 2:
        return float("nan")
    return float(krippendorff.alpha(reliability_data=m, level_of_measurement="interval"))


def parse_file(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    pcols, scols, rcols, consent = {}, {}, {}, None
    for i, h in enumerate(header):
        if (m := SKIP.match(h)):
            scols[(int(m[1]), int(m[2]))] = i
        elif (m := PASSAGE.match(h)):
            pcols[(int(m[1]), int(m[2]))] = i
        elif (m := REPLY.match(h)):
            rcols[int(m[1])] = i
        elif h.strip() == "Consent" or CONSENT in h:
            consent = i
    blocks = {b for b, _ in pcols}
    if len(blocks) != 1:
        raise SystemExit(f"{path}: passage codes span blocks {sorted(blocks)} (one export per form expected)")
    block = blocks.pop()
    passages, replies, dropped = defaultdict(list), defaultdict(list), 0
    for row in rows:
        if not any(c.strip() for c in row):
            continue
        if consent is not None and CONSENT not in row[consent]:
            dropped += 1
            continue
        for (b, pos), i in pcols.items():
            v = row[i].strip() if i < len(row) else ""
            skipped = (b, pos) in scols and scols[(b, pos)] < len(row) and row[scols[(b, pos)]].strip()
            passages[pos].append(float(v) if v and not skipped else float("nan"))
        for ex, i in rcols.items():
            v = row[i].strip() if i < len(row) else ""
            replies[ex].append(float(v) if v else float("nan"))
    n = sum(1 for r in rows if any(c.strip() for c in r))
    return block, passages, replies, n, dropped


def summary(values):
    v = [x for x in values if not math.isnan(x)]
    if not v:
        return dict(n_raters=0, mean_rating="", sd="", min="", max="")
    return dict(n_raters=len(v), mean_rating=round(float(np.mean(v)), 4),
                sd=round(float(np.std(v, ddof=1)), 4) if len(v) > 1 else "", min=min(v), max=max(v))


def write(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def pad(columns):
    units = sorted(columns)
    width = max((len(columns[u]) for u in units), default=0)
    return [[columns[u][r] if r < len(columns[u]) else float("nan") for u in units] for r in range(width)]


def run(responses_dir, assignment, replies_csv, key_csv):
    assign = {(int(r["block"]), int(r["position"])): r for r in read(assignment)}
    exchanges = {int(r["exchange_id"][1:]): r for r in read(replies_csv)} if Path(replies_csv).exists() else {}
    key = {r["passage_id"]: r for r in read(key_csv)} if Path(key_csv).exists() else {}
    files = sorted(Path(responses_dir).glob("*.csv"))
    if not files:
        raise SystemExit(f"no response CSVs in {responses_dir}")
    per_passage, per_reply, alpha_rows, report = {}, defaultdict(list), [], {"files": {}}
    all_cols = {}
    seen_blocks = {}
    for f in files:
        block, passages, replies, n, dropped = parse_file(f)
        if block in seen_blocks:
            raise SystemExit(f"{f} and {seen_blocks[block]} are both block {block}")
        seen_blocks[block] = f.name
        cols = {}
        for pos, v in passages.items():
            if (block, pos) not in assign:
                raise SystemExit(f"{f}: code B{block:02d}-{pos:02d} not in {assignment}")
            a = assign[(block, pos)]
            pid, s = a["passage_id"], summary(v)
            per_passage[pid] = dict(passage_id=pid, lang=a["lang"], register=key.get(pid, {}).get("register", "long"),
                                    block=block, **s, status=STATUS,
                                    agreed=int(s["n_raters"] >= 2 and s["max"] - s["min"] <= AGREE_WITHIN))
            cols[pid] = all_cols[pid] = v
        for ex, v in replies.items():
            per_reply[ex] += v
        alpha_rows.append(dict(scope=f"block {block}", items="passages", n_readers=n - dropped, n_units=len(cols),
                               alpha_interval=round(kripp_interval(pad(cols)), 4)))
        report["files"][f.name] = dict(block=block, rows=n, dropped_no_consent=dropped,
                                       skipped_ratings=sum(math.isnan(x) for v in passages.values() for x in v))
    missing = sorted({b for b, _ in assign} - set(seen_blocks))
    report["blocks_missing"] = missing
    alpha_rows.append(dict(scope="all blocks", items="passages", n_readers=sum(r["n_readers"] for r in alpha_rows),
                           n_units=len(all_cols), alpha_interval=round(kripp_interval(pad(all_cols)), 4)))
    alpha_rows.append(dict(scope="all blocks", items="replies", n_readers=max((len(v) for v in per_reply.values()),
                                                                                default=0),
                           n_units=len(per_reply), alpha_interval=round(kripp_interval(pad(dict(per_reply))), 4)))
    reply_rows = [dict(exchange_id=f"R{ex:02d}", passage_id=exchanges.get(ex, {}).get("passage_id", ""),
                       system=exchanges.get(ex, {}).get("system", ""), **summary(v)) for ex, v in sorted(per_reply.items())]
    return [per_passage[p] for p in sorted(per_passage)], reply_rows, alpha_rows, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--responses", default=str(ROOT / "data/annotation/readers"))
    ap.add_argument("--assignment", default=str(ROOT / "docs/reader_study/block_assignment.csv"))
    ap.add_argument("--replies", default=str(ROOT / "docs/reader_study/replies.csv"))
    ap.add_argument("--key", default=str(ROOT / "data/annotation/audit_key.csv"))
    ap.add_argument("--out", default=str(ROOT / "data/annotation/reader_ratings.csv"))
    ap.add_argument("--reply-out", default=str(ROOT / "data/annotation/reader_reply_ratings.csv"))
    ap.add_argument("--results", default=str(ROOT / "results/reader_study"))
    a = ap.parse_args(argv)
    rows, reply_rows, alpha_rows, report = run(a.responses, a.assignment, a.replies, a.key)
    write(a.out, rows, ["passage_id", "lang", "register", "block", "n_raters", "mean_rating", "sd", "min", "max",
                        "agreed", "status"])
    write(a.reply_out, reply_rows, ["exchange_id", "passage_id", "system", "n_raters", "mean_rating", "sd"])
    res = Path(a.results)
    write(res / "reader_alpha.csv", alpha_rows, ["scope", "items", "n_readers", "n_units", "alpha_interval"])
    (res / "ingest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for r in alpha_rows:
        print(f"{r['scope']:12s} {r['items']:9s} readers={r['n_readers']:3d} units={r['n_units']:3d} "
              f"alpha(interval)={r['alpha_interval']}")
    print(f"{len(rows)} passages -> {a.out}; {len(reply_rows)} reply items -> {a.reply_out}; "
          f"blocks missing: {report['blocks_missing'] or 'none'}")


if __name__ == "__main__":
    main()
