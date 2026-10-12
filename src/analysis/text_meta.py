"""Text-level covariates for the R models: loss type, split, and matched Hindi/English pairs."""
import argparse
import ast
import csv
import json
import math
import re
from pathlib import Path

from gold import split_of
from meta_prefill import FIELDS, build as build_meta

ROOT = Path(__file__).resolve().parents[2]
ELIGIBLE = "provisionally_eligible"
LANGS = {"devanagari_hindi": "hi", "english": "en"}
LOSS_RULES = [
    ("unstated", r"^\s*$|^\s*(not stated|unknown)|^none$"),
    ("grandparent", r"grand|dadi|daadi|nani|naani|dada|daadu|nana|paati|thatha|आमा|दादी|नानी|बाबा|दादा|नाना"),
    ("parent", r"\bparents?\b|father|mother|\bmom\b|\bdad\b|papa|appa|amma|ammi|\bmaa\b|baji|बीजी|माँ|मां|पिता|पापा"),
    ("spouse", r"wife|husband|spouse|partner"),
    ("child", r"\bson\b|daughter|\bchild\b|baby"),
    ("sibling", r"brother|sister|sibling|bhai|didi"),
    ("other", r"."),
]
LOSS_RX = [(k, re.compile(rx)) for k, rx in LOSS_RULES]
CATEGORY_RULES = [
    ("unknown", LOSS_RULES[0][1]),
    ("parent_in_law", r"in-law|in law|सास|ससुर"),
    ("elder", r"uncle|aunt|mentor|काका|चाचा|ताऊ|मामा|मौसी|बुआ"),
    ("grandparent", LOSS_RULES[1][1]),
    ("parent", LOSS_RULES[2][1]),
    ("sibling", r"brother|sister|sibling|\bbhai\b|didi|भाई|बहन|दीदी"),
    ("spouse", LOSS_RULES[3][1]),
    ("child", LOSS_RULES[4][1]),
    ("teacher", r"teacher|\bguru\b|गुरु|शिक्षक"),
    ("elder", r"elder"),
    ("friend", r"friend|peer|colleague|classmate|batchmate|दोस्त|मित्र|सहेली"),
    ("unknown", r"."),
]
CATEGORY_RX = [(k, re.compile(rx)) for k, rx in CATEGORY_RULES]
HONORIFIC_FORCED = {"parent", "grandparent", "parent_in_law", "teacher", "elder"}
HONORIFIC_CHOSEN = {"sibling", "spouse", "child", "friend"}


def relation_category(relation):
    first = (relation or "").split(";")[0].strip().lower()
    if first in ("none", "nan"):
        first = ""
    return next(k for k, rx in CATEGORY_RX if rx.search(first))


SELF_PUBLISHED_RX = re.compile(r"(blogspot|wordpress|substack|medium)\.com$")
PLATFORM_TYPES = {
    "news_magazine": {"dailyo.in", "freepressjournal.in", "greaterkashmir.com", "grehlakshmi.com", "hindi.webdunia.com",
                      "huffpost.com", "ichowk.in", "janchowk.com", "kashmirlife.net", "kashmirobserver.net",
                      "khaskhabar.com", "livewire.thewire.in", "m.thewire.in", "outlookindia.com", "scroll.in",
                      "thebetterindia.com", "thecitizen.in", "thelogicalindian.com", "thequint.com", "womensweb.in",
                      "tweakindia.com", "bhadas4media.com", "pardafash.in", "mediawala.in"},
    "literary_or_story_platform": {"hindikunj.com", "hindisamay.com", "kafaltree.com", "matrubharti.com",
                                   "sahityakunj.net", "sahityapedia.com", "samalochan.com", "rachanakar.org",
                                   "nayidhara.in", "anunad.com", "hindiblog.projectfuel.in", "thegoodstoryproject.com",
                                   "servicespace.org", "bereavemed.com", "thelivelovelaughfoundation.org"},
}


def source_domain(url):
    from urllib.parse import urlparse
    return urlparse(url or "").netloc.lower().removeprefix("www.") or "unknown"


def platform_type(url):
    from urllib.parse import urlparse
    host = urlparse(url or "").netloc.lower().removeprefix("www.")
    if SELF_PUBLISHED_RX.search(host):
        return "self_published"
    return next((k for k, v in PLATFORM_TYPES.items() if host in v), "personal_site")


FATHER_RX = re.compile(r"father|\bdad\b|papa|appa|abbu|abba|pitaji|पिता|पापा|बाबूजी|अब्बू|अब्बा")
ELDER_CATEGORIES = {"grandparent", "parent_in_law", "teacher", "elder"}


def elder_relation(relation):
    cat = relation_category(relation)
    first = (relation or "").split(";")[0].strip().lower()
    return cat in ELDER_CATEGORIES or (cat == "parent" and bool(FATHER_RX.search(first)))


def loss_type(relation):
    first = (relation or "").split(";")[0].strip().lower()
    if first in ("none", "nan"):
        first = ""
    if re.search(r"uncle|aunt|mentor|friend", first):
        return "other"
    return next(k for k, rx in LOSS_RX if rx.search(first))


def parse_field(v, default):
    if isinstance(v, (dict, list)):
        return v
    if v in (None, "", "None"):
        return default
    try:
        return ast.literal_eval(v)
    except (ValueError, SyntaxError):
        return default


def match_pairs(rows):
    n = 0
    sa = [r for r in rows if r["same_author_pair"]]
    by_lang = {lg: [r for r in sa if r["lang"] == lg] for lg in ("hi", "en")}
    for h, e in zip(sorted(by_lang["hi"], key=lambda r: r["record_id"]), sorted(by_lang["en"], key=lambda r: r["record_id"])):
        n += 1
        h["pair_id"] = e["pair_id"] = f"P{n:03d}"
    cells = {}
    for r in rows:
        if not r["pair_id"]:
            cells.setdefault((r["split"], r["loss_type"]), {"hi": [], "en": []})[r["lang"]].append(r)
    for key in sorted(cells):
        hi = sorted(cells[key]["hi"], key=lambda r: r["record_id"])
        en = sorted(cells[key]["en"], key=lambda r: r["record_id"])
        cand = sorted(((abs(math.log(max(h["n_clauses"], 1)) - math.log(max(e["n_clauses"], 1))), h["record_id"],
                        e["record_id"], h, e) for h in hi for e in en), key=lambda t: t[:3])
        for _, _, _, h, e in cand:
            if not h["pair_id"] and not e["pair_id"]:
                n += 1
                h["pair_id"] = e["pair_id"] = f"P{n:03d}"
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--records", default=str(ROOT / "data/clean/blogs_merged.jsonl"))
    ap.add_argument("--features", default=str(ROOT / "data/processed/text_features.csv"))
    ap.add_argument("--out", default=str(ROOT / "data/processed/text_meta.csv"))
    ap.add_argument("--clauses", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--tokens", default=None, help="default: tokens.csv next to --clauses")
    ap.add_argument("--review", default=str(ROOT / "data/annotation/meta_review.csv"))
    args = ap.parse_args(argv)
    n_cl = {r["record_id"]: int(float(r["n_clauses"])) for r in csv.DictReader(open(args.features, encoding="utf-8"))}
    rows, records = [], []
    for line in open(args.records, encoding="utf-8"):
        r = json.loads(line)
        if r.get("eligibility_status") != ELIGIBLE or r.get("lang_provisional") not in LANGS:
            continue
        records.append((r, LANGS[r["lang_provisional"]]))
        rel = str(parse_field(r.get("extra"), {}).get("deceased_relation_as_stated") or "")
        rows.append(dict(record_id=r["record_id"], lang=LANGS[r["lang_provisional"]], split=split_of(r["record_id"]),
                         n_clauses=n_cl.get(r["record_id"], 0), relation_as_stated=rel, loss_type=loss_type(rel),
                         relation_category=relation_category(rel),
                         same_author_pair="same_author_pair" in parse_field(r.get("flags"), []), pair_id="",
                         platform=platform_type(r.get("source_url", "")),
                         source_domain=source_domain(r.get("source_url", ""))))
    match_pairs(rows)
    tokens = args.tokens or str(Path(args.clauses).with_name("tokens.csv"))
    meta, summary = build_meta(records, args.clauses, tokens, args.review, split_of)
    for r in rows:
        r.update(meta[r["record_id"]])
    rows.sort(key=lambda r: r["record_id"])
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"wrote {args.out}: {len(rows)} texts; loss_type {dict(Counter(r['loss_type'] for r in rows))}; "
          f"pairs {len({r['pair_id'] for r in rows if r['pair_id']})}; unpaired {sum(1 for r in rows if not r['pair_id'])}")
    for f in FIELDS:
        print(f"  {f}: {dict(summary[f])}")
    print(f"  meta_review_status: {dict(Counter(r['meta_review_status'] for r in rows))}; review sheet {args.review}")


if __name__ == "__main__":
    main()
