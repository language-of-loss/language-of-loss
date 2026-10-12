import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import trafilatura
from griefcorpus.collect_blogs import HTML, doc_id, robots_allows
from griefcorpus.http import PoliteClient
from griefcorpus.textutil import bereavement_screen

PAIRS = ROOT / "docs" / "bilingual_pairs_candidates.csv"
OUTLETS = {"tweakindia.com", "indianculturalforum.in"}
KIN_SLUG = ("father", "mother", "papa", "dad", "mom", "maa", "amma", "appa", "pita", "mata", "nani", "dadi", "baba")
_client = None


def norm_name(s):
    return " ".join(unicodedata.normalize("NFC", s or "").lower().split())


def meta_for(url, client):
    p = HTML / f"{doc_id(url)}.html"
    if p.exists():
        html = p.read_text(encoding="utf-8", errors="replace")
    else:
        if not robots_allows(client, url):
            return "", ""
        resp, body = client.get(url)
        if resp is None or resp.status_code != 200 or not body:
            return "", ""
        html = body.decode(resp.encoding or "utf-8", errors="replace")
    meta = trafilatura.extract_metadata(html)
    text = trafilatura.extract(html, favor_precision=True) or ""
    return norm_name(meta.author if meta else ""), text


def main():
    client = PoliteClient(min_delay_s=3.0, timeout_s=40, max_retries=2)
    rows = list(csv.DictReader(open(PAIRS, encoding="utf-8")))
    cache = {}
    for r in rows:
        for side in ("a", "b"):
            u = r[f"url_{side}"]
            if u not in cache:
                cache[u] = meta_for(u, client)
        (ba, ta), (bb, tb) = cache[r["url_a"]], cache[r["url_b"]]
        sa, sb = bereavement_screen(ta), bereavement_screen(tb)
        site = urlparse(r["url_a"]).netloc.lower().replace("www.", "")
        if ba and bb:
            match = "same" if ba == bb or ba in bb or bb in ba else "different"
        else:
            match = "unknown"
        slug = lambda u: re.sub(r"-\d+$", "", urlparse(u).path.rstrip("/").split("/")[-1].lower())
        same_slug = slug(r["url_a"]) == slug(r["url_b"])
        kin_both = any(k in slug(r["url_a"]) for k in KIN_SLUG) and any(k in slug(r["url_b"]) for k in KIN_SLUG)
        known_pair = "same_author_pair" in (r.get("flags") or "")
        if known_pair:
            conf = "high"
        elif match == "different" or not (sa["hit"] and sb["hit"]):
            conf = "unlikely"
        elif same_slug or (match == "same" and site not in OUTLETS and kin_both):
            conf = "high"
        elif match == "same" and site not in OUTLETS:
            conf = "medium"
        else:
            conf = "low"
        if site in OUTLETS and match == "same":
            match = "house byline"
        r.update(confidence_initial=r.get("confidence_initial") or r["confidence"], confidence=conf, byline_match=match,
                 same_slug=same_slug,
                 screen_a=f"{sa['side']} kin={sa['n_kin']} death={sa['n_death']}" if sa["hit"] else "miss",
                 screen_b=f"{sb['side']} kin={sb['n_kin']} death={sb['n_death']}" if sb["hit"] else "miss",
                 site=urlparse(r["url_a"]).netloc)
    order = {"high": 0, "medium": 1, "low": 2, "unlikely": 3}
    rows.sort(key=lambda r: (order[r["confidence"]], r["site"], r["url_a"], r["url_b"]))
    fields = ["confidence", "byline_match", "same_slug", "site", "record_a", "lang_a", "url_a", "status_a", "screen_a",
              "record_b", "lang_b", "url_b", "status_b", "screen_b", "basis", "confidence_initial", "flags",
              "reviewer_confirmed", "reviewer_note"]
    with open(PAIRS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter(r["confidence"] for r in rows), Counter(r["byline_match"] for r in rows))


if __name__ == "__main__":
    main()
