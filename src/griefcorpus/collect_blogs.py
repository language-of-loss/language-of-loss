import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

import trafilatura

from .http import PoliteClient, ROOT, USER_AGENT, now_iso
from .textutil import detect_language, word_count

RAW = ROOT / "data" / "raw" / "blogs"
HTML = RAW / "html"
FETCH_LOG = RAW / "fetch_log.jsonl"
EXTRACTED = ROOT / "data" / "interim" / "blogs_extracted.jsonl"
AUTHOR_SALT = "grief-hi-en-corpus/author/v1"
_robots = {}


def doc_id(url):
    return "blog_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def robots_allows(client, url):
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots:
        rp = robotparser.RobotFileParser()
        resp, body = client.get(base + "/robots.txt")
        if resp is not None and resp.status_code == 200 and body:
            rp.parse(body.decode("utf-8", errors="replace").splitlines())
            _robots[base] = rp
        elif resp is not None and resp.status_code in (401, 403):
            _robots[base] = False
        else:
            _robots[base] = None
    rp = _robots[base]
    if rp is None:
        return True
    if rp is False:
        return False
    return rp.can_fetch(USER_AGENT, url)


def load_seen():
    seen = {}
    if FETCH_LOG.exists():
        for line in FETCH_LOG.open(encoding="utf-8"):
            r = json.loads(line)
            seen[r["url"]] = r
    return seen


def run(candidate_files, limit=None):
    HTML.mkdir(parents=True, exist_ok=True)
    EXTRACTED.parent.mkdir(parents=True, exist_ok=True)
    client = PoliteClient(min_delay_s=3.0, timeout_s=40, max_retries=2)
    seen = load_seen()
    cands = []
    for f in candidate_files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                c["_candidate_file"] = Path(f).name
                cands.append(c)
    done = 0
    for c in cands:
        url = c["url"].strip()
        if url in seen:
            continue
        if limit and done >= limit:
            break
        done += 1
        rec = {"url": url, "doc_id": doc_id(url), "fetched_at": now_iso(), "candidate_file": c["_candidate_file"]}
        try:
            if not robots_allows(client, url):
                rec.update(status="robots_disallow")
            else:
                resp, body = client.get(url)
                rec["http_status"] = resp.status_code if resp is not None else None
                if resp is None or resp.status_code != 200 or not body:
                    rec.update(status="fetch_failed")
                else:
                    (HTML / f"{rec['doc_id']}.html").write_bytes(body)
                    rec.update(status="fetched", bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                               final_url=resp.url)
                    html = body.decode(resp.encoding or "utf-8", errors="replace") if resp.encoding else body.decode("utf-8", errors="replace")
                    text = trafilatura.extract(html, include_comments=False, include_tables=False,
                                               favor_precision=True, deduplicate=True) or ""
                    meta = trafilatura.extract_metadata(html)
                    author = (meta.author if meta else None) or ""
                    lang, det = detect_language(text)
                    out = {"doc_id": rec["doc_id"], "url": url, "domain": urlparse(url).netloc.lower().replace("www.", ""),
                           "title": (meta.title if meta else None), "publication_date": (meta.date if meta else None),
                           "author_group": ("au_" + hashlib.sha1((AUTHOR_SALT + urlparse(url).netloc + author.lower()).encode()).hexdigest()[:10]) if author else None,
                           "collected_at": rec["fetched_at"], "text": text, "n_words": word_count(text),
                           "lang_provisional": lang, "lang_details": det,
                           "candidate": {k: v for k, v in c.items() if not k.startswith("_") and k != "url"}}
                    rec["n_words_extracted"] = out["n_words"]
                    if out["n_words"] < 80:
                        rec["status"] = "fetched_but_extraction_short"
                    with EXTRACTED.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(out, ensure_ascii=False) + "\n")
        except Exception as exc:
            rec.update(status="error", error=repr(exc)[:300])
        with FETCH_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{rec['status']}] {rec.get('http_status','')} {rec.get('n_words_extracted','')}w {url[:100]}", flush=True)
    print(f"processed {done} new URLs; {len(seen)} were already in the log")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    sys.exit(run(a.files, a.limit))
