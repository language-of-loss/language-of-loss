import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from bilingual_author_hunt import LANG2, byline, list_posts, platform
from griefcorpus.collect_blogs import AUTHOR_SALT
from griefcorpus.http import PoliteClient, now_iso
from griefcorpus.textutil import bereavement_screen, detect_language
from rank_screen import score

MERGED = ROOT / "data" / "clean" / "blogs_merged.jsonl"
OUT = ROOT / "data" / "candidates" / "same_author_v12.jsonl"
KNOWN = ROOT / "data" / "candidates" / "known_urls_v12.txt"
COLLECTION_LOG = ROOT / "docs" / "collection_log.csv"
DEV_PER_AUTHOR = 3


def author_key(rec):
    if rec["author_group"]:
        return rec["author_group"], "byline"
    dom = urlparse(rec["source_url"]).netloc.lower().replace("www.", "")
    return "site_" + hashlib.sha1((AUTHOR_SALT + dom).encode()).hexdigest()[:10], "site"


def main():
    recs = [json.loads(l) for l in MERGED.open(encoding="utf-8")]
    known = {u.strip().rstrip("/") for u in KNOWN.read_text(encoding="utf-8").splitlines() if u.strip()}
    by_dom = defaultdict(list)
    for r in recs:
        by_dom[urlparse(r["source_url"]).netloc.lower().replace("www.", "")].append(r)
    multi = {d for d, g in by_dom.items() if len({x["author_group"] for x in g if x["author_group"]}) > 1}
    sites = defaultdict(list)
    for r in recs:
        if LANG2.get(r["lang_provisional"]) not in ("hi", "en"):
            continue
        dom = urlparse(r["source_url"]).netloc.lower().replace("www.", "")
        kind, base = platform(r["source_url"])
        if dom in multi and kind != "medium":
            continue
        sites[(kind, base)].append(r)
    client = PoliteClient(min_delay_s=3.0, timeout_s=40, max_retries=2)
    rows, stats = {}, Counter()
    for (kind, base), rs in sites.items():
        posts = list_posts(client, kind, base)
        stats["sites"] += 1
        stats["posts_listed"] += len(posts)
        listed = {u.rstrip("/"): a for u, _, _, a in posts}
        print(f"{kind:9s} {base[:55]:55s} {len(posts):4d}", flush=True)
        for r in rs:
            lr = LANG2.get(r["lang_provisional"])
            own_id = listed.get(r["source_url"].rstrip("/"), "") if kind == "wpjson" else ""
            name = byline(r["record_id"].split(":")[1]) if kind in ("blogger", "wpcom") else ""
            akey, akind = author_key(r)
            for url, title, text, author in posts:
                u = url.rstrip("/")
                if u in known or u in rows:
                    continue
                lang, _ = detect_language(text)
                if LANG2.get(lang) != lr or not bereavement_screen(text)["hit"]:
                    continue
                if kind == "wpjson":
                    if own_id and author != own_id:
                        stats["dropped_other_author"] += 1
                        continue
                    verified = "wp_author_id" if own_id else "author_unverified"
                elif kind in ("blogger", "wpcom"):
                    if name and author and author != name:
                        stats["dropped_other_author"] += 1
                        continue
                    verified = "byline" if name and author else "author_unverified"
                else:
                    verified = f"{kind}_author_feed"
                s = score(text, lr)
                rows[u] = dict(url=url, site_domain=urlparse(url).netloc, page_title=title[:200], lang=lr,
                               author_group=akey, author_key_kind=akind, author_verification=verified,
                               corpus_record=r["record_id"], listing_kind=kind, listing_words=s["n_words"],
                               rank_score=s["score"], rank_parts={k: s[k] for k in ("first_person", "kin", "death_near_kin", "past")},
                               flags=["over_cap"], proposed_split="not_admitted")
    by_author = defaultdict(list)
    for row in rows.values():
        if row["author_verification"] != "author_unverified":
            by_author[row["author_group"]].append(row)
    for group in by_author.values():
        for row in sorted(group, key=lambda x: -x["rank_score"])[:DEV_PER_AUTHOR]:
            row["proposed_split"] = "development"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for row in sorted(rows.values(), key=lambda x: (x["author_group"], -x["rank_score"])):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    c = Counter((r["lang"], r["proposed_split"]) for r in rows.values())
    v = Counter(r["author_verification"] for r in rows.values())
    note = (f"v1.2 same-author re-list: {stats['sites']} own sites, {stats['posts_listed']} posts listed; "
            f"{len(rows)} same-language screen hits by verified/unverified same author ({dict(v)}); "
            f"{stats['dropped_other_author']} dropped as other authors; proposed development (<=3/author): "
            f"hi {c[('hi', 'development')]}, en {c[('en', 'development')]}; all over_cap; nothing added to corpus")
    with open(COLLECTION_LOG, "a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow([now_iso(), "same_author_relist", "own-site listings (Blogger/WordPress/Substack/Medium)",
                                 "v1.2-3", stats["posts_listed"], len(rows), 0, str(OUT.relative_to(ROOT)), note])
    print(note)


if __name__ == "__main__":
    main()
