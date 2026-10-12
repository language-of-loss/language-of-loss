"""Output 5 prep (A2 audit): rating passages, two blind interleaved intensity sheets, the BRIGHTER-Hindi calibration"""
import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from gold import split_of
from preprocess import LANG_MAP, prepare_text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.textutil import word_count

SEED = 20261010
LO, HI = 80, 200
EXCLUDE_ENTRIES = ("L-HI-C2",)
EXCLUDE_FLAGS = ("flag_F2",)
ROMANISED = ("romanized_hindi", "code_mixed")
BRIGHTER = ROOT / "data/external/brighter/hin/dev-00000-of-00001.parquet"
BRIGHTER_REV = "brighter-dataset/BRIGHTER-emotion-categories@419566ac8f46f951b51584be36c13e5363008144"
MASTER = ["passage_id", "record_id", "lang", "register", "split", "source_url", "passage_sha256", "window", "words",
          "score", "density", "notes", "passage_text"]
SHEET = ["rating_id", "lang", "passage_text", "intensity_1to7", "notes"]
KEY = ["rating_id", "passage_id", "record_id", "lang", "register", "split", "source_url", "passage_sha256", "order_r1",
       "order_r2"]
CAL_SHEET = ["calibration_id", "passage_text", "intensity_1to7", "notes"]
CAL_KEY = ["calibration_id", "brighter_id", "sadness", "emotions", "order_r1", "order_r2", "source"]


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def windows(words, scores, lo=LO, hi=HI):
    out = []
    for i in range(len(words)):
        w = s = 0
        for j in range(i, len(words)):
            w += words[j]
            s += scores[j]
            if w > hi:
                break
            if w >= lo and s > 0:
                out.append((s / w, s, -i, i, j))
    return sorted(out, reverse=True)


def best_window(words, scores, lo=LO, hi=HI):
    w = windows(words, scores, lo, hi)
    return (w[0][3], w[0][4], "") if w else None


def round_robin(cands, n):
    taken, used = [], defaultdict(set)
    pools = {t: list(c) for t, c in cands.items()}
    while len(taken) < n:
        progress = False
        order = sorted((t for t in pools if pools[t]), key=lambda t: (-pools[t][0][0], t))
        for t in order:
            while pools[t] and set(range(pools[t][0][3], pools[t][0][4] + 1)) & used[t]:
                pools[t].pop(0)
            if not pools[t] or len(taken) >= n:
                continue
            d, s, _, i, j = pools[t].pop(0)
            used[t] |= set(range(i, j + 1))
            taken.append((t, i, j, d, s))
            progress = True
        if not progress:
            break
    return taken


def load_scores(features_path, exclude=EXCLUDE_ENTRIES + EXCLUDE_FLAGS):
    out = {}
    with open(features_path, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        head = next(reader)
        cols = [i for i, h in enumerate(head)
                if ((h[:2] in ("L-", "P-")) or re.fullmatch(r"flag_F\d+", h)) and h not in exclude]
        for row in reader:
            out[row[0]] = sum(int(row[i] or 0) for i in cols)
    return out


def load_components(features_path):
    out = {}
    with open(features_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        comps = [c for c in reader.fieldnames if c.startswith("comp_")]
        for r in reader:
            if r.get("is_finite") in ("1", "True"):
                out[r["clause_id"]] = {c: int(r[c] or 0) for c in comps}
    return out, comps


def sentences(rec, lang, cache_dir):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", rec["record_id"])
    cached = json.loads((Path(cache_dir) / lang / f"{safe}.json").read_text(encoding="utf-8"))
    text = prepare_text(rec["text_clean"], lang)
    out = []
    for s in cached["sentences"]:
        a, b = min(w["start"] for w in s), max(w["end"] for w in s)
        out.append((text[a:b], sum(w["upos"] != "PUNCT" for w in s)))
    return out


def dataset_locator(r):
    m = re.search(r"10\.\d{4,}/[^\s,;]+", r.get("source_dataset") or "")
    return f"https://doi.org/{m.group(0)}#{r.get('source_record_id', '')}" if m else ""


def shortform_urls(root=ROOT):
    urls = {}
    for f in ("data/clean/ytcv.jsonl", "data/clean/hinemo9.jsonl"):
        p = Path(root) / f
        if p.exists():
            for line in open(p, encoding="utf-8"):
                r = json.loads(line)
                urls[r["record_id"]] = r.get("source_url") or dataset_locator(r)
    p = Path(root) / "docs/reddit_india_bereavement_sample.csv"
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf-8", newline="")):
            link = r.get("permalink", "")
            urls[r["record_id"]] = ("https://www.reddit.com" + link) if link.startswith("/") else link
            urls.setdefault("reddit_confessions:" + r["record_id"].split(":")[-1], urls[r["record_id"]])
    return urls


def long_form(records, clauses, scores, cache_dir, n, split="dev"):
    sent_score, sent_clauses = defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(list))
    for c in clauses:
        sent_score[c["record_id"]][c["sent_index"]] += scores.get(c["clause_id"], 0)
        sent_clauses[c["record_id"]][c["sent_index"]].append(c["clause_id"])
    rows, report = [], {}
    for lang in ("hi", "en"):
        cands, sents_of = {}, {}
        for rid in sorted(sent_score):
            rec = records.get(rid)
            if rec is None or LANG_MAP.get(rec["lang_provisional"]) != lang or (split != "all" and split_of(rid) != split):
                continue
            sents = sentences(rec, lang, cache_dir)
            sents_of[rid] = sents
            cands[rid] = windows([w for _, w in sents], [sent_score[rid].get(i, 0) for i in range(len(sents))])
        picked = round_robin(cands, n)
        for rid, i, j, d, s in picked:
            text = " ".join(t for t, _ in sents_of[rid][i:j + 1])
            rows.append(dict(record_id=rid, lang=lang, register="long", split=split_of(rid),
                             source_url=records[rid].get("source_url", ""), passage_sha256=sha(text),
                             window=f"{i}-{j}", words=sum(w for _, w in sents_of[rid][i:j + 1]), score=s,
                             density=round(d, 4), notes="", passage_text=text,
                             _clauses=[cid for k in range(i, j + 1) for cid in sent_clauses[rid].get(k, [])]))
        per_text = defaultdict(int)
        for rid, *_ in picked:
            per_text[rid] += 1
        report[lang] = dict(target=n, taken=len(picked), shortfall=n - len(picked), texts=len(cands),
                            texts_used=len(per_text), max_per_text=max(per_text.values(), default=0),
                            windows_available=sum(len(v) for v in cands.values()))
    return rows, report


def cut(text, hi=HI):
    parts = re.split(r"(?<=[.!?।])\s+", text.strip())
    out = []
    for p in parts:
        if out and word_count(" ".join(out + [p])) > hi:
            break
        out.append(p)
    return " ".join(out)


def short_form(sf_records, urls, n, split="dev"):
    rows = []
    pool = sorted((r for r in sf_records if r.get("lang_provisional") in ROMANISED
                   and (split == "all" or split_of(r["record_id"]) == split)), key=lambda r: r["record_id"])
    for r in pool[:n]:
        text = r["text_clean"].strip()
        wc = word_count(text)
        note = ""
        if wc > HI:
            text, note = cut(text), f"cut to the first sentences up to {HI} words (post has {wc})"
            wc = word_count(text)
        elif wc < LO:
            note = f"whole post under {LO} words"
        rows.append(dict(record_id=r["record_id"], lang="hi", register="short_romanised", split=split_of(r["record_id"]),
                         source_url=urls.get(r["record_id"], ""), passage_sha256=sha(text), window="post", words=wc,
                         score="", density="", notes=note, passage_text=text, _clauses=[]))
    return rows, dict(target=n, taken=len(rows), shortfall=n - len(rows), pool=len(pool))


def blind(rows, seed):
    rng = random.Random(seed)
    ids = set()

    def new(prefix):
        while True:
            x = "%s-%08x" % (prefix, rng.getrandbits(32))
            if x not in ids:
                ids.add(x)
                return x
    for r in rows:
        r["passage_id"], r["rating_id"] = new("AP"), new("AR")
    orders = []
    for _ in range(2):
        o = list(rows)
        rng.shuffle(o)
        orders.append(o)
    pos = [{r["rating_id"]: k for k, r in enumerate(o, 1)} for o in orders]
    sheets = [[dict(rating_id=r["rating_id"], lang=r["lang"], passage_text=r["passage_text"], intensity_1to7="",
                    notes="") for r in o] for o in orders]
    key = [dict(rating_id=r["rating_id"], passage_id=r["passage_id"], record_id=r["record_id"], lang=r["lang"],
                register=r["register"], split=r["split"], source_url=r["source_url"],
                passage_sha256=r["passage_sha256"], order_r1=pos[0][r["rating_id"]], order_r2=pos[1][r["rating_id"]])
           for r in rows]
    return rows, sheets[0], sheets[1], key


def calibration(path, n, seed):
    if not Path(path).exists():
        return None
    import pandas as pd
    df = pd.read_parquet(path)
    rng = random.Random(seed)
    pos = sorted(df.index[df["sadness"] == 1].tolist())
    neg = sorted(df.index[df["sadness"] == 0].tolist())
    pick = rng.sample(pos, min(n // 2, len(pos))) + rng.sample(neg, min(n - n // 2, len(neg)))
    rng.shuffle(pick)
    items = [dict(calibration_id="CB-%08x" % rng.getrandbits(32), row=df.loc[i]) for i in pick]
    orders = [list(items), list(items)]
    for o in orders:
        rng.shuffle(o)
    pos_of = [{it["calibration_id"]: k for k, it in enumerate(o, 1)} for o in orders]
    sheets = [[dict(calibration_id=it["calibration_id"], passage_text=it["row"]["text"], intensity_1to7="", notes="")
               for it in o] for o in orders]
    key = [dict(calibration_id=it["calibration_id"], brighter_id=it["row"]["id"], sadness=int(it["row"]["sadness"]),
                emotions=" ".join(str(e) for e in (it["row"]["emotions"] if it["row"]["emotions"] is not None else [])),
                order_r1=pos_of[0][it["calibration_id"]], order_r2=pos_of[1][it["calibration_id"]],
                source=BRIGHTER_REV) for it in items]
    return sheets[0], sheets[1], key


def components(rows, comp, comps):
    out = []
    for r in rows:
        cl = [comp[c] for c in r["_clauses"] if c in comp]
        n = len(cl)
        out.append(dict(passage_id=r["passage_id"], lang=r["lang"], register=r["register"], n_clauses=n,
                        **{c: round(sum(x[c] for x in cl) / n, 4) if n else "" for c in comps}))
    return out


def write_csv(path, rows, columns):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def file_sha(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--records", default=str(ROOT / "data/clean/blogs_merged.jsonl"))
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--features", default=str(ROOT / "data/processed/clause_features.csv"))
    ap.add_argument("--shortform", default=str(ROOT / "data/processed/shortform/records.jsonl"))
    ap.add_argument("--brighter", default=str(BRIGHTER))
    ap.add_argument("--out-dir", default=str(ROOT / "data/annotation"))
    ap.add_argument("--processed-out", default=str(ROOT / "data/processed"))
    ap.add_argument("--split", default="all", choices=["dev", "all"],
                    help="short-form subset only (decision 2026-10-10: confirmatory short-form posts allowed); the "
                         "long-form passages always come from the dev split")
    ap.add_argument("--n-long", type=int, default=150)
    ap.add_argument("--n-short", type=int, default=100)
    ap.add_argument("--n-calibration", type=int, default=40)
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)

    records = {}
    with open(args.records, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            records[r["record_id"]] = r
    with open(args.inp, encoding="utf-8") as fh:
        clauses = [json.loads(line) for line in fh]
    rows, report = long_form(records, clauses, load_scores(args.features), Path(args.inp).parent / "stanza_cache",
                             args.n_long, "dev")
    sf = []
    if Path(args.shortform).exists():
        sf = [json.loads(l) for l in open(args.shortform, encoding="utf-8")]
    srows, report["short_romanised"] = short_form(sf, shortform_urls(), args.n_short, args.split)
    master, r1, r2, key = blind(rows + srows, args.seed)
    out, proc = Path(args.out_dir), Path(args.processed_out)
    rated = [n for n in ("audit_rating_sheet_r1.csv", "audit_rating_sheet_r2.csv") if (out / n).exists()
             and any((r.get("intensity_1to7") or "").strip() for r in csv.DictReader(open(out / n, encoding="utf-8")))]
    if rated:
        raise SystemExit(f"refusing: {rated} already hold ratings; a redraw would overwrite them (archive them first)")
    write_csv(out / "audit_passages.csv", master, MASTER)
    write_csv(out / "audit_rating_sheet_r1.csv", r1, SHEET)
    write_csv(out / "audit_rating_sheet_r2.csv", r2, SHEET)
    write_csv(out / "audit_key.csv", key, KEY)
    comp, comps = load_components(args.features)
    write_csv(proc / "audit_passage_components.csv", components(master, comp, comps),
              ["passage_id", "lang", "register", "n_clauses"] + comps)
    cal = calibration(args.brighter, args.n_calibration, args.seed + 1)
    if cal:
        write_csv(out / "audit_calibration_brighter_r1.csv", cal[0], CAL_SHEET)
        write_csv(out / "audit_calibration_brighter_r2.csv", cal[1], CAL_SHEET)
        write_csv(out / "audit_calibration_key.csv", cal[2], CAL_KEY)
    report["calibration"] = dict(target=args.n_calibration, taken=len(cal[2]) if cal else 0,
                                 sadness=sum(k["sadness"] for k in cal[2]) if cal else 0,
                                 source=BRIGHTER_REV if cal else f"missing: {args.brighter}")
    manifest = dict(seed=args.seed, split=args.split, bounds=[LO, HI], excluded=list(EXCLUDE_ENTRIES + EXCLUDE_FLAGS),
                    report=report, inputs={k: file_sha(v) for k, v in dict(records=args.records, clauses=args.inp,
                                                                         features=args.features,
                                                                         shortform=args.shortform,
                                                                         brighter=args.brighter).items()})
    (proc / "audit_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    for k, r in report.items():
        if r.get("shortfall"):
            print(f"WARNING {k}: {r['shortfall']} short of {r['target']} (bounds and split not relaxed)")


if __name__ == "__main__":
    main()
