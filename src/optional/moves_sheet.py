"""P3 prep -- paragraph units of every long-form text, blind move-coding sheet, codebook example file."""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from entropy import MOVES
from gold import split_of
from preprocess import LANG_MAP

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261010
SHEET = ["unit_id", "text_id", "unit_no", "lang", "prev_unit", "unit_text", "move", "notes"]
KEY = ["unit_id", "text_id", "record_id", "split", "lang", "unit_no", "n_units_in_text", "codebook_example"]
CODES = MOVES + ["other"]
EXAMPLES = [
    ("blogs:blog_ff5322367bcf", 1, "announcement"), ("blogs:blog_56eb08c9fd16", 36, "announcement"),
    ("blogs:cw_2ca5cb44e79d", 1, "announcement"), ("blogs:blog_33be34a730e8", 3, "announcement"),
    ("blogs:blog_8b666dd3f7e4", 2, "circumstances"), ("blogs:cw_8d3d92bb074b", 17, "circumstances"),
    ("blogs:cw_b0f49d0805b5", 16, "circumstances"), ("blogs:blog_4eb9b44dd0f9", 8, "circumstances"),
    ("blogs:cw_f5baf36bd55e", 23, "character"), ("blogs:blog_56eb08c9fd16", 87, "character"),
    ("blogs:cw_b0f49d0805b5", 5, "character"), ("blogs:blog_1d8075d67392", 5, "character"),
    ("blogs:cw_6a2c0609408b", 3, "memory"), ("blogs:cw_8d3d92bb074b", 7, "memory"),
    ("blogs:cw_c8ad3b363b51", 5, "memory"), ("blogs:blog_12cca32b4a59", 7, "memory"),
    ("blogs:blog_dddd37b0b32a", 6, "regret"), ("blogs:cw_95e0259c53b1", 2, "regret"),
    ("blogs:cw_2ca5cb44e79d", 5, "regret"), ("blogs:blog_0bf67028c93c", 10, "regret"),
    ("blogs:blog_8b666dd3f7e4", 80, "address_dead"), ("blogs:blog_0861b4d96495", 3, "address_dead"),
    ("blogs:blog_0bec8419b0f9", 3, "address_dead"), ("blogs:blog_0bec8419b0f9", 11, "address_dead"),
    ("blogs:blog_5aa741918356", 76, "ritual"), ("blogs:blog_56eb08c9fd16", 124, "ritual"),
    ("blogs:cw_b0f49d0805b5", 30, "ritual"), ("blogs:blog_33be34a730e8", 18, "ritual"),
    ("blogs:cw_6a2c0609408b", 10, "lesson"), ("blogs:cw_f5baf36bd55e", 19, "lesson"),
    ("blogs:blog_0bf67028c93c", 18, "lesson"), ("blogs:blog_33be34a730e8", 27, "lesson"),
    ("blogs:cw_95e0259c53b1", 7, "blessing_closing"), ("blogs:blog_5aa741918356", 80, "blessing_closing"),
    ("blogs:blog_0bec8419b0f9", 40, "blessing_closing"), ("blogs:blog_1d8075d67392", 11, "blessing_closing"),
]


def units(text):
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


def build(records, record_ids, seed):
    rng = random.Random(seed)
    taken = set()

    def new_id(prefix):
        while True:
            x = "%s-%08x" % (prefix, rng.getrandbits(32))
            if x not in taken:
                taken.add(x)
                return x
    order = sorted(record_ids)
    rng.shuffle(order)
    examples = {(r, n): m for r, n, m in EXAMPLES}
    sheet, key = [], []
    for rid in order:
        rec = records[rid]
        lang = LANG_MAP[rec["lang_provisional"]]
        us = units(rec["text_clean"])
        tid = new_id("TX")
        for n, u in enumerate(us, 1):
            uid = new_id("MU")
            sheet.append(dict(unit_id=uid, text_id=tid, unit_no=n, lang=lang, prev_unit=us[n - 2] if n > 1 else "",
                              unit_text=u, move="", notes=""))
            key.append(dict(unit_id=uid, text_id=tid, record_id=rid, split=split_of(rid), lang=lang, unit_no=n,
                            n_units_in_text=len(us), codebook_example=examples.get((rid, n), "")))
    return sheet, key


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def examples_md(sheet, key):
    text = {r["unit_id"]: r["unit_text"] for r in sheet}
    out = ["# Move codebook examples (LOCAL ONLY: third-party text, do not commit)\n",
           "Referenced by unit_id from docs/moves_codebook.md. All from dev-split texts.\n"]
    for move in MOVES:
        out.append(f"## {move}\n")
        for k in key:
            if k["codebook_example"] == move:
                out.append(f"- `{k['unit_id']}` ({k['lang']}): {text[k['unit_id']]}\n")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--records", default=str(ROOT / "data/clean/blogs_merged.jsonl"))
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--out-dir", default=str(ROOT / "data/annotation"))
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args(argv)

    with open(args.inp, encoding="utf-8") as fh:
        ids = {json.loads(line)["record_id"] for line in fh}
    records = {}
    with open(args.records, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["record_id"] in ids:
                records[r["record_id"]] = r
    bad = [(r, n) for r, n, _ in EXAMPLES if split_of(r) != "dev"]
    if bad:
        raise SystemExit(f"codebook examples must come from dev texts: {bad}")
    sheet, key = build(records, ids, args.seed)
    out = Path(args.out_dir)
    for name in ("moves_sheet.csv", "moves_sheet_r1.csv", "moves_sheet_r2.csv"):
        write_csv(out / name, sheet, SHEET)
    write_csv(out / "moves_key.csv", key, KEY)
    (out / "moves_codebook_examples.md").write_text(examples_md(sheet, key), encoding="utf-8")
    for lang in ("hi", "en"):
        ks = [k for k in key if k["lang"] == lang]
        print(f"{lang}: {len({k['text_id'] for k in ks})} texts, {len(ks)} units, "
              f"{sum(k['split'] == 'dev' for k in ks)} in dev texts, examples {sum(bool(k['codebook_example']) for k in ks)}")


if __name__ == "__main__":
    main()
