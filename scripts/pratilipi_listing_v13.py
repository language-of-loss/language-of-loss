import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.http import PoliteClient

BASE = "https://hindi.pratilipi.com"
GENRES = ["experiences-stories-in-hindi", "life-stories-in-hindi"]
CAND = ROOT / "data" / "candidates"
OUT = CAND / "blog_candidates_v13_pratilipi.jsonl"
LOG = CAND / "listing_log_v13_pratilipi.csv"
KIN = ["पापा", "पिता", "पिताजी", "बाबूजी", "बाऊजी", "बापू", "माँ", "मां", "अम्मा", "मम्मी", "माई", "दादी", "नानी",
       "दादा", "नाना", "भैया", "भाई", "दीदी", "बहन", "पति", "पत्नी", "बेटा", "बेटी"]
DEATH = ["श्राद्ध", "बरसी", "पुण्यतिथि", "श्रद्धांजलि", "अंतिम विदाई", "नहीं रहे", "नहीं रहीं", "नहीं रही", "मृत्यु",
         "निधन", "देहांत", "स्वर्गवास", "मौत"]
B, E = r"(?<![ऀ-ॿ])", r"(?![ऀ-ॿ])"
KIN_RE = re.compile(B + "(?:" + "|".join(KIN) + ")" + E)
DEATH_RE = re.compile("|".join(DEATH))
ITEM = re.compile(r'<a href="(/(?:story|series)/[^"]+)" title="([^"]*)"')


def author_slug(path):
    m = re.search(r"-by-(.+)-[a-z0-9]{12}$", path)
    return m.group(1) if m else None


def known():
    urls = {l.strip().rstrip("/") for l in (CAND / "known_urls_v13.txt").open(encoding="utf-8") if l.strip()}
    authors = {author_slug(u.split("pratilipi.com", 1)[1]) for u in urls if "pratilipi.com/" in u}
    return urls, authors - {None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=25)
    a = ap.parse_args()
    client = PoliteClient(min_delay_s=3.0)
    urls, authors = known()
    out, log = [], []
    for g in GENRES:
        listed = set()
        for p in range(1, a.pages + 1):
            url = f"{BASE}/genres/{g}" + (f"?page={p}" if p > 1 else "")
            resp, body = client.get(url)
            status = resp.status_code if resp is not None else None
            items = ITEM.findall(body.decode("utf-8", "replace")) if status == 200 and body else []
            hits = 0
            if items and set(items) <= listed:
                log.append(dict(listing=url, http_status=status, n_items=len(set(items)), n_kept="repeat_of_earlier_page"))
                print(f"{status} page repeats earlier titles; stop  {url}", flush=True)
                break
            listed |= set(items)
            for path, title in dict(items).items():
                title = html.unescape(title)
                kin, death = KIN_RE.search(title), DEATH_RE.search(title)
                au = author_slug(path)
                if not (kin or death) or BASE + path in urls or au in authors:
                    continue
                authors.add(au)
                hits += 1
                out.append({"url": BASE + path, "site_domain": "hindi.pratilipi.com", "page_title": title,
                            "language_script": "devanagari_hindi", "type": "unreviewed_listing_v13",
                            "deceased_relation_as_stated": kin.group(0) if kin else "", "first_person": "unclear",
                            "original_or_translation": "", "approx_length": "", "publication_date_if_visible": "",
                            "notes": f"public genre listing {g} page {p}; title term: "
                                     + ",".join(x.group(0) for x in (kin, death) if x),
                            "query_that_found_it": f"listing:{g}/{p}", "query_family": "title_kin_or_death"})
            log.append(dict(listing=url, http_status=status, n_items=len(set(items)), n_kept=hits))
            print(f"{status} {len(set(items))} items, {hits} kept  {url}", flush=True)
            if status != 200 or not items:
                break
    with OUT.open("w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in out)
    with LOG.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["listing", "http_status", "n_items", "n_kept"])
        w.writeheader()
        w.writerows(log)
    print(f"{len(out)} candidates -> {OUT}")


if __name__ == "__main__":
    main()
