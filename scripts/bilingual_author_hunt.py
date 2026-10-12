import csv
import hashlib
import html as htmlmod
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import trafilatura
from griefcorpus.collect_blogs import robots_allows, HTML
from griefcorpus.http import PoliteClient, now_iso
from griefcorpus.textutil import bereavement_screen, detect_language, word_count

MERGED = ROOT / "data" / "clean" / "blogs_merged.jsonl"
OUT_PAIRS = ROOT / "docs" / "bilingual_pairs_candidates.csv"
OUT_CANDS = ROOT / "data" / "candidates" / "blog_candidates_v11_bilingual.jsonl"
COLLECTION_LOG = ROOT / "docs" / "collection_log.csv"
MAX_POSTS = 500
TAG = re.compile(r"<[^>]+>")
LANG2 = {"devanagari_hindi": "hi", "english": "en", "romanized_hindi": "hi-Latn", "mixed_hi_en": "mixed"}


def plain(html_text):
    return re.sub(r"\s+", " ", htmlmod.unescape(TAG.sub(" ", html_text or ""))).strip()


def byline(doc_id):
    p = HTML / f"{doc_id}.html"
    if not p.exists():
        return ""
    meta = trafilatura.extract_metadata(p.read_text(encoding="utf-8", errors="replace"))
    return ((meta.author if meta else None) or "").strip().lower()


def platform(url):
    u = urlparse(url)
    host = u.netloc.lower()
    if host.endswith(".blogspot.com") or ".blogspot." in host:
        return "blogger", f"https://{host}"
    if host.endswith(".wordpress.com"):
        return "wpcom", host
    if host.endswith(".substack.com"):
        return "substack", f"https://{host}"
    if host == "medium.com" and u.path.startswith("/@"):
        return "medium", "https://medium.com/feed/" + u.path.split("/")[1]
    if host.endswith(".medium.com"):
        return "medium", f"https://{host}/feed"
    return "wpjson", f"https://{host}"


def list_posts(client, kind, base):
    posts = []
    if kind == "blogger":
        for start in range(1, MAX_POSTS, 150):
            url = f"{base}/feeds/posts/default?alt=json&max-results=150&start-index={start}"
            if not robots_allows(client, url):
                break
            data, status = client.get_json(url)
            entries = ((data or {}).get("feed") or {}).get("entry") or []
            for e in entries:
                link = next((l["href"] for l in e.get("link", []) if l.get("rel") == "alternate"), None)
                author = ((e.get("author") or [{}])[0].get("name") or {}).get("$t", "")
                posts.append((link, e.get("title", {}).get("$t", ""), plain((e.get("content") or e.get("summary") or {}).get("$t")),
                              author.lower()))
            if len(entries) < 150:
                break
    elif kind == "wpcom":
        for page in range(1, MAX_POSTS // 100 + 1):
            url = f"https://public-api.wordpress.com/rest/v1.1/sites/{base}/posts/?number=100&page={page}&fields=URL,title,content,author"
            data, status = client.get_json(url)
            items = (data or {}).get("posts") or []
            posts += [(p["URL"], plain(p.get("title")), plain(p.get("content")), (p.get("author") or {}).get("name", "").lower())
                      for p in items]
            if len(items) < 100:
                break
    elif kind == "wpjson":
        for page in range(1, MAX_POSTS // 100 + 1):
            url = f"{base}/wp-json/wp/v2/posts?per_page=100&page={page}&_fields=link,title,content,author"
            if not robots_allows(client, url):
                break
            data, status = client.get_json(url)
            if not isinstance(data, list):
                break
            posts += [(p.get("link"), plain((p.get("title") or {}).get("rendered")),
                       plain((p.get("content") or {}).get("rendered")), f"wpid:{p.get('author')}") for p in data]
            if len(data) < 100:
                break
    elif kind == "substack":
        for offset in range(0, MAX_POSTS, 50):
            url = f"{base}/api/v1/archive?sort=new&limit=50&offset={offset}"
            if not robots_allows(client, url):
                break
            data, status = client.get_json(url)
            if not isinstance(data, list) or not data:
                break
            posts += [(p.get("canonical_url"), p.get("title") or "", " ".join(filter(None, [p.get("title"), p.get("subtitle"),
                       p.get("description"), p.get("truncated_body_text")])), "") for p in data]
            if len(data) < 50:
                break
    elif kind == "medium":
        if robots_allows(client, base):
            resp, body = client.get(base)
            if resp is not None and resp.status_code == 200 and body:
                try:
                    root = ET.fromstring(body)
                    ns = {"content": "http://purl.org/rss/1.0/modules/content/", "dc": "http://purl.org/dc/elements/1.1/"}
                    for it in root.iter("item"):
                        posts.append((it.findtext("link"), it.findtext("title") or "",
                                      plain(it.findtext("content:encoded", namespaces=ns)),
                                      (it.findtext("dc:creator", namespaces=ns) or "").lower()))
                except ET.ParseError:
                    pass
    return [p for p in posts if p[0]]


def main():
    recs = [json.loads(l) for l in MERGED.open(encoding="utf-8")]
    known = {r["source_url"].rstrip("/") for r in recs}
    pairs = []
    by_ag, by_dom = defaultdict(list), defaultdict(list)
    for r in recs:
        if r["author_group"]:
            by_ag[r["author_group"]].append(r)
        by_dom[urlparse(r["source_url"]).netloc.lower().replace("www.", "")].append(r)
    seen_pair = set()
    for key, group, conf, basis in [(k, g, "high", "same author_group (same site + same byline)") for k, g in by_ag.items()] + \
                                   [(k, g, "medium", "same site, both languages; byline not compared") for k, g in by_dom.items()]:
        for a in group:
            for b in group:
                la, lb = LANG2.get(a["lang_provisional"]), LANG2.get(b["lang_provisional"])
                if la == "hi" and lb == "en" and (a["record_id"], b["record_id"]) not in seen_pair:
                    seen_pair.add((a["record_id"], b["record_id"]))
                    pairs.append(dict(confidence=conf, basis=basis, record_a=a["record_id"], lang_a="hi", url_a=a["source_url"],
                                      status_a=a["eligibility_status"], record_b=b["record_id"], lang_b="en",
                                      url_b=b["source_url"], status_b=b["eligibility_status"],
                                      screen_b="", flags=";".join(sorted(set(a["flags"] or []) | set(b["flags"] or [])))))
    client = PoliteClient(min_delay_s=3.0, timeout_s=40, max_retries=2)
    multi = {d for d, g in by_dom.items() if len({r["author_group"] for r in g if r["author_group"]}) > 1}
    sites = defaultdict(list)
    for r in recs:
        if LANG2.get(r["lang_provisional"]) not in ("hi", "en"):
            continue
        dom = urlparse(r["source_url"]).netloc.lower().replace("www.", "")
        kind, base = platform(r["source_url"])
        if dom in multi and kind != "medium":
            continue
        sites[(kind, base)].append(r)
    new_cands, stats = {}, defaultdict(int)
    for (kind, base), rs in sites.items():
        posts = list_posts(client, kind, base)
        stats[f"listed_{kind}"] += 1
        stats["posts_listed"] += len(posts)
        print(f"{kind:9s} {base[:60]:60s} {len(posts):4d} posts", flush=True)
        bylines = {byline(r["record_id"].split(":")[1]) for r in rs} - {""}
        for url, title, text, author in posts:
            if not url or url.rstrip("/") in known:
                continue
            lang, _ = detect_language(text)
            l2 = LANG2.get(lang)
            if l2 not in ("hi", "en"):
                continue
            scr = bereavement_screen(text)
            if not scr["hit"]:
                continue
            if bylines and author and not author.startswith("wpid:") and author not in bylines:
                stats["dropped_other_author"] += 1
                continue
            for r in rs:
                lr = LANG2.get(r["lang_provisional"])
                if lr == l2:
                    stats["same_language_grief_posts_same_author"] += 1
                    continue
                hi_r, en_r = (r, None) if lr == "hi" else (None, r)
                conf = "medium" if kind in ("blogger", "wpcom", "substack", "medium") else "low"
                basis = f"same site ({kind} listing), other-language post passing the bereavement screen"
                if kind == "substack":
                    basis += "; screened on title/subtitle/excerpt only"
                pairs.append(dict(confidence=conf, basis=basis,
                                  record_a=hi_r["record_id"] if hi_r else "(new)", lang_a="hi",
                                  url_a=hi_r["source_url"] if hi_r else url, status_a=hi_r["eligibility_status"] if hi_r else "not fetched",
                                  record_b=en_r["record_id"] if en_r else "(new)", lang_b="en",
                                  url_b=en_r["source_url"] if en_r else url, status_b=en_r["eligibility_status"] if en_r else "not fetched",
                                  screen_b=f"{scr['side']} kin={scr['n_kin']} death={scr['n_death']}", flags=""))
                new_cands[url] = dict(url=url, site_domain=urlparse(url).netloc, page_title=title[:200],
                                      language_script=lang, type="unreviewed_bilingual_hunt_candidate",
                                      deceased_relation_as_stated="", first_person="", original_or_translation="",
                                      approx_length=word_count(text), publication_date_if_visible="",
                                      notes=f"v1.1 bilingual hunt; same site as {r['record_id']}",
                                      query_that_found_it=f"{kind} listing of {base}")
                stats["pair_candidates_online"] += 1
    with open(OUT_PAIRS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pairs[0].keys()) + ["reviewer_confirmed", "reviewer_note"])
        w.writeheader()
        order = {"high": 0, "medium": 1, "low": 2}
        for p in sorted(pairs, key=lambda p: (order[p["confidence"]], p["record_a"])):
            w.writerow({**p, "reviewer_confirmed": "", "reviewer_note": ""})
    with open(OUT_CANDS, "w", encoding="utf-8") as fh:
        for c in new_cands.values():
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    note = (f"v1.1 bilingual-author hunt: {len(sites)} own sites listed ({dict((k, v) for k, v in stats.items() if k.startswith('listed_'))}), "
            f"{stats['posts_listed']} posts listed, {stats['pair_candidates_online']} other-language screen hits, "
            f"{stats['dropped_other_author']} dropped (other author), {stats['same_language_grief_posts_same_author']} same-language grief posts not kept (author cap); "
            f"{len(pairs)} pair candidates in docs/bilingual_pairs_candidates.csv; nothing added to corpus")
    with open(COLLECTION_LOG, "a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow([now_iso(), "bilingual_author_hunt", "own-site listings (Blogger/WordPress/Substack/Medium)",
                                 "v1.1-1", stats["posts_listed"], len(new_cands), 0, str(OUT_CANDS.relative_to(ROOT)), note])
    print(note)


if __name__ == "__main__":
    main()
