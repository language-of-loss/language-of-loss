import argparse
import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urljoin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from build_review_master import norm_url
from griefcorpus.collect_blogs import robots_allows
from griefcorpus.http import PoliteClient

CAND = ROOT / "data" / "candidates"
OUT = CAND / "blog_candidates_v14_archive.jsonl"
LOG = CAND / "listing_log_v14.csv"
COUNTS = ROOT / "data" / "interim" / "archive_v14_counts.json"
LISTING = CAND / "archive_v14_listing.json"

WP = "wp"
ONE = "one"
SITEMAP = "sitemap"
SITES = {
    "mediawala.in": dict(lang="hi", mode=SITEMAP, index="https://mediawala.in/sitemap_index.xml",
                         slug=r"in-memory-of-my-(?:father|mother|parents|papa|maa)"),
    "kafaltree.com": dict(lang="hi", mode=WP, post=r"https://kafaltree\.com/[^/\"#?]+/$",
                          archives=["https://kafaltree.com/tag/memoir/", "https://kafaltree.com/tag/memoirs/",
                                    "https://kafaltree.com/tag/death/", "https://kafaltree.com/tag/death-anniversary/",
                                    "https://kafaltree.com/tag/mothers-grief/"]),
    "sahityakunj.net": dict(lang="hi", mode=ONE, post=r"https://sahityakunj\.net/entries/view/[^\"#?]+$",
                            archives=["https://sahityakunj.net/sansmaran/smriti-lekh",
                                      "https://sahityakunj.net/sansmaran/aap-beeti",
                                      "https://sahityakunj.net/sansmaran/aatmkatha"]),
    "samalochan.com": dict(lang="hi", mode=WP, post=r"https://samalochan\.com/[^/\"#?]+/$",
                           archives=["https://samalochan.com/category/literature/memoir/",
                                     "https://samalochan.com/category/literature/self/"]),
    "grehlakshmi.com": dict(lang="hi", mode=None, why="no memoir/संस्मरण/personal-essay category; listings rendered by script"),
    "livewire.thewire.in": dict(lang="en", mode=WP, post=r"https://livewire\.thewire\.in/[a-z0-9-]+/[^/\"#?]+/$",
                                archives=["https://livewire.thewire.in/tag/grief/", "https://livewire.thewire.in/tag/death/",
                                          "https://livewire.thewire.in/tag/loss/"]),
    "scroll.in": dict(lang="en", mode=ONE, post=r"https://scroll\.in/article/\d+/[^\"#?]+$",
                      archives=["https://scroll.in/tag/grief"]),
    "tweakindia.com": dict(lang="en", mode=WP, post=r"https://tweakindia\.com/(?:[a-z0-9-]+/){1,3}[^/\"#?]+/$",
                           archives=["https://tweakindia.com/tag/grief/", "https://tweakindia.com/tag/death-2/",
                                     "https://tweakindia.com/tag/child-loss/", "https://tweakindia.com/tag/first-person-account/"]),
    "womensweb.in": dict(lang="en", mode=None, why="homepage is an API placeholder; sitemap.xml 404; no archive served"),
    "thegoodstoryproject.com": dict(lang="en", mode=WP, post=r"https://thegoodstoryproject\.com/\d{4}/\d{2}/\d{2}/[^/\"#?]+/$",
                                    archives=["https://thegoodstoryproject.com/category/loss-and-grief/",
                                              "https://thegoodstoryproject.com/category/first-person-account/",
                                              "https://thegoodstoryproject.com/category/first-person-accounts/"]),
}
NOT_POST = re.compile(r"/(?:tag|category|author|page|feed|wp-content|wp-json|sansmaran|lekhak|search)/|#|\?")

HI_KIN = ["पापा", "पिता", "पिताजी", "बाबूजी", "बाऊजी", "बापू", "बाबा", "माँ", "मां", "अम्मा", "मम्मी", "माई", "ईजा", "आमा",
          "दादी", "नानी", "दादा", "नाना", "भैया", "भाई", "दीदी", "बहन", "पति", "पत्नी", "बेटा", "बेटी", "बेटे", "चाचा",
          "मामा", "मौसी", "बुआ", "ताऊ", "दोस्त", "मित्र", "सखी"]
HI_DEATH = ["श्राद्ध", "बरसी", "पुण्यतिथि", "श्रद्धांजलि", "अंतिम विदाई", "नहीं रहे", "नहीं रहीं", "नहीं रही", "मृत्यु",
            "निधन", "देहांत", "स्वर्गवास", "स्वर्गीय", "मौत", "शोक", "गुज़र", "गुजर", "चले गए", "चली गई", "स्मृति शेष",
            "स्मृतिशेष", "याद में"]
EN_KIN = r"father|mother|dad|daddy|mum|mom|papa|appa|amma|baba|aai|grand(?:mother|father|ma|pa)|granny|nani|dadi|nana|" \
         r"dada|thatha|paati|brother|sister|husband|wife|son|daughter|uncle|aunt|friend|parents?|child|baby"
EN_DEATH = r"died|dies|death|dying|passed away|passing|loss|lost|losing|grief|griev\w*|mourn\w*|funeral|cremat\w*|" \
           r"last rites|obituary|in memory|remember(?:ing)?|goodbye|farewell|widow\w*|suicide|terminal"
B, E = r"(?<![ऀ-ॿ])", r"(?![ऀ-ॿ])"
SCREEN = {"hi": re.compile(B + "(?:" + "|".join(HI_KIN) + ")" + E + "|" + B + "(?:" + "|".join(HI_DEATH) + ")"),
          "en": re.compile(r"\b(?:" + EN_KIN + "|" + EN_DEATH + r")\b", re.I)}
SLUG_EXTRA = re.compile(r"\b(?:pita|pitaji|maa|babuji|dadi|nani|bhai|shraddhanjali|punyatithi|barsi|smriti)\b", re.I)


def screen(title, lang):
    m = SCREEN[lang].search(title) or SCREEN["en"].search(title) or SLUG_EXTRA.search(title)
    return m.group(0) if m else ""


def text_of(fragment):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def post_links(page, base, pattern):
    rx = re.compile(pattern)

    def collect(chunks):
        found = {}
        for ch in chunks:
            for href, inner in re.findall(r'<a\s[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', ch, re.S):
                u = urljoin(base, html.unescape(href))
                if rx.match(u) and not NOT_POST.search(u.split("://", 1)[1]):
                    t = text_of(inner)
                    if len(t) > len(found.get(u, "")):
                        found[u] = t
        return found
    heads = re.findall(r"<h[1-4][^>]*>.*?</h[1-4]>", page, re.S)
    found = collect(heads)
    return found if found else collect([page])


def walk_archive(client, url, cfg, max_pages, log):
    posts, n = {}, 0
    for p in range(1, max_pages + 1):
        if p == 1:
            page_url = url
        elif cfg["mode"] == WP:
            page_url = url.rstrip("/") + f"/page/{p}/"
        else:
            page_url = url + ("&" if "?" in url else "?") + f"page={p}"
        if not robots_allows(client, page_url):
            log.append(dict(site=cfg["site"], listing=page_url, http_status="robots_disallow", n_posts=0, n_new=0))
            break
        resp, body = client.get(page_url)
        st = resp.status_code if resp is not None else None
        found = post_links((body or b"").decode("utf-8", "replace"), page_url, cfg["post"]) if st == 200 else {}
        new = {u: t for u, t in found.items() if u not in posts}
        log.append(dict(site=cfg["site"], listing=page_url, http_status=st, n_posts=len(found), n_new=len(new)))
        print(f"  {st} {len(found):3d} posts, {len(new):3d} new  {unquote(page_url)}", flush=True)
        if st != 200 or not new:
            break
        n = p
        posts.update(new)
    return posts, n


def walk_sitemap(client, cfg, log):
    resp, body = client.get(cfg["index"])
    maps = [m for m in re.findall(r"<loc>([^<]+)</loc>", (body or b"").decode("utf-8", "replace")) if "post-sitemap" in m]
    log.append(dict(site=cfg["site"], listing=cfg["index"], http_status=resp.status_code if resp else None,
                    n_posts=len(maps), n_new=0))
    posts, total = {}, 0
    for m in maps:
        r, b = client.get(m)
        locs = re.findall(r"<loc>([^<]+)</loc>", (b or b"").decode("utf-8", "replace"))
        total += len(locs)
        hit = {u: unquote(u.rstrip("/").rsplit("/", 1)[-1]).replace("-", " ") for u in locs
               if re.search(cfg["slug"], u, re.I)}
        posts.update(hit)
        log.append(dict(site=cfg["site"], listing=m, http_status=r.status_code if r else None, n_posts=len(locs),
                        n_new=len(hit)))
        print(f"  {r.status_code if r else None} {len(locs):5d} urls, {len(hit):3d} series  {m}", flush=True)
    return posts, len(maps) + 1, total


def known_urls():
    urls = set()
    for l in (ROOT / "data" / "clean" / "blogs_merged.jsonl").open(encoding="utf-8"):
        urls.add(norm_url(json.loads(l)["source_url"]))
    for l in (ROOT / "data" / "raw" / "blogs" / "fetch_log.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        urls |= {norm_url(r["url"]), norm_url(r.get("final_url"))}
    for f in CAND.glob("blog_candidates*.jsonl"):
        if f.name != OUT.name:
            urls |= {norm_url(json.loads(l)["url"]) for l in f.open(encoding="utf-8") if l.strip()}
    return urls - {""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=150)
    ap.add_argument("--rescreen", action="store_true", help="re-run the title screen on the saved listings")
    a = ap.parse_args()
    client = PoliteClient(min_delay_s=3.0)
    known = known_urls()
    log, out, counts = [], [], defaultdict(Counter)
    saved = json.loads(LISTING.read_text(encoding="utf-8")) if a.rescreen else {}
    if a.rescreen:
        log = list(csv.DictReader(LOG.open(encoding="utf-8")))
    for site, cfg in SITES.items():
        cfg = dict(cfg, site=site)
        print(f"== {site}", flush=True)
        if a.rescreen:
            posts, src = saved[site]["posts"], saved[site]["src"]
            counts[site]["archive_pages_walked"] = saved[site]["pages"]
            if cfg["mode"] is None:
                counts[site]["no_archive"] = 1
                continue
        elif cfg["mode"] is None:
            counts[site].update(archive_pages_walked=0)
            log.append(dict(site=site, listing="(none)", http_status="", n_posts=0, n_new=0))
            counts[site]["no_archive"] = 1
            continue
        elif cfg["mode"] == SITEMAP:
            posts, pages, _ = walk_sitemap(client, cfg, log)
            counts[site]["archive_pages_walked"] += pages
            src = {u: "post sitemap (series slug)" for u in posts}
        else:
            posts, src = {}, {}
            for arch in cfg["archives"]:
                found, pages = walk_archive(client, arch, cfg, a.max_pages, log)
                counts[site]["archive_pages_walked"] += max(pages, 1)
                for u, t in found.items():
                    if len(t) > len(posts.get(u, "")):
                        posts[u] = t
                    src.setdefault(u, unquote(arch))
        if not a.rescreen:
            saved[site] = dict(posts=posts, src=src, pages=counts[site]["archive_pages_walked"])
        counts[site]["posts_listed"] = len(posts)
        for u, t in sorted(posts.items()):
            term = screen(t, cfg["lang"])
            if not term:
                continue
            counts[site]["screened"] += 1
            if norm_url(u) in known:
                counts[site]["screened_already_known"] += 1
                continue
            counts[site]["candidates"] += 1
            out.append({"url": u, "site_domain": site, "page_title": t,
                        "language_script": "devanagari_hindi" if cfg["lang"] == "hi" else "english",
                        "type": "unreviewed_archive_v14", "deceased_relation_as_stated": "", "first_person": "unclear",
                        "original_or_translation": "", "approx_length": "", "publication_date_if_visible": "",
                        "notes": f"title screen term: {term}", "query_that_found_it": f"archive:{src[u]}",
                        "query_family": "title_kin_or_death"})
    if not a.rescreen:
        for site, cfg in SITES.items():
            saved.setdefault(site, dict(posts={}, src={}, pages=0))
        LISTING.write_text(json.dumps(saved, ensure_ascii=False, indent=0), encoding="utf-8")
    with OUT.open("w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in out)
    with LOG.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["site", "listing", "http_status", "n_posts", "n_new"])
        w.writeheader()
        w.writerows(log)
    COUNTS.write_text(json.dumps({k: dict(v) for k, v in counts.items()}, indent=1))
    for k, v in counts.items():
        print(k, dict(v))
    print(f"{len(out)} candidates -> {OUT}")


if __name__ == "__main__":
    main()
