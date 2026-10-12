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
from bilingual_pairs_regrade import meta_for
from griefcorpus.clean import clean_doc_text
from griefcorpus.http import PoliteClient
from rank_screen import score

CAND = ROOT / "data" / "candidates"
ROUTES = {"blog_candidates_v11_bilingual.jsonl": "v1.1_bilingual_hunt",
          "blog_candidates_v12_hi_webzines.jsonl": "v1.2_hi_webzines",
          "blog_candidates_v12_hi_blogs.jsonl": "v1.2_hi_personal_blogs",
          "blog_candidates_v12_en.jsonl": "v1.2_en_essays",
          "blog_candidates_v12_same_author.jsonl": "same_author_dev",
          "blog_candidates_v12_name_search.jsonl": "v1.2_name_search"}
WEBZINES = {"mediawala.in", "grehlakshmi.com", "samalochan.com", "sahityakunj.net", "hindi.webdunia.com",
            "hindikunj.com", "kafaltree.com", "anunad.com", "matrubharti.com", "pratilipi.com"}
LANG2 = {"devanagari_hindi": "hi", "english": "en", "romanized_hindi": "hi-Latn", "mixed_hi_en": "mixed"}
OUT = ROOT / "docs" / "expansion_candidates_v12.csv"
PAIRS = ROOT / "docs" / "bilingual_pairs_candidates.csv"
TOP_N = 100


def ranked_rows():
    merged = [json.loads(l) for l in (ROOT / "data" / "clean" / "blogs_merged.jsonl").open(encoding="utf-8")]
    known = {r["source_url"].rstrip("/") for r in merged}
    log = {}
    for l in (ROOT / "data" / "raw" / "blogs" / "fetch_log.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        if r.get("candidate_file") in ROUTES:
            log[r["doc_id"]] = r
    rows, stats = [], Counter()
    stats.update(f"fetch_{ROUTES[r['candidate_file']]}_{r['status']}" for r in log.values())
    seen = set()
    for l in (ROOT / "data" / "interim" / "blogs_extracted.jsonl").open(encoding="utf-8"):
        d = json.loads(l)
        if d["doc_id"] not in log or d["doc_id"] in seen:
            continue
        seen.add(d["doc_id"])
        route = ROUTES[log[d["doc_id"]]["candidate_file"]]
        text, _ = clean_doc_text(d["text"])
        lang = LANG2.get(d["lang_provisional"], d["lang_provisional"])
        checks = [c for c, bad in (("short_lt80w", d["n_words"] < 80), (f"lang_{lang}", lang not in ("hi", "en")),
                                   ("already_in_corpus", d["url"].rstrip("/") in known)) if bad]
        s = score(text, lang) if lang in ("hi", "en") else dict(score=0, first_person=0, kin=0, death_near_kin=0, past=0)
        rows.append(dict(record_id=f"blogs:{d['doc_id']}", lang=lang, route=route, source=d["domain"], url=d["url"],
                         n_words=d["n_words"], rank_score=s["score"], first_person=s["first_person"], kin=s["kin"],
                         death_near_kin=s["death_near_kin"], past=s["past"],
                         automatic_checks="pass" if not checks else ";".join(checks),
                         flags="over_cap" if route == "same_author_dev" else "",
                         first_300_chars=text[:300].replace("\n", " "),
                         reviewer_eligible="", reviewer_type="", reviewer_note=""))
        stats[f"{lang}_{route}_{'pass' if not checks else 'fail'}"] += 1
    per_dom = defaultdict(list)
    for r in rows:
        if r["route"] == "v1.2_hi_webzines" and r["automatic_checks"] == "pass":
            per_dom[r["source"].replace("www.", "")].append(r)
    for dom, rs in per_dom.items():
        for r in sorted(rs, key=lambda x: -x["rank_score"])[3:]:
            r["automatic_checks"] = "over_domain_cap"
            stats["webzine_over_domain_cap"] += 1
    return rows, stats


def add_name_pairs(client):
    path = CAND / "name_search_v12_pairs.jsonl"
    if not path.exists():
        return Counter()
    found = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    rows = list(csv.DictReader(open(PAIRS, encoding="utf-8")))
    fields = list(rows[0].keys()) if rows else []
    have = {(r["url_a"], r["url_b"]) for r in rows}
    merged = {json.loads(l)["source_url"].rstrip("/"): json.loads(l) for l in
              (ROOT / "data" / "clean" / "blogs_merged.jsonl").open(encoding="utf-8")}
    stats = Counter()
    for p in found:
        a_is_corpus = p["corpus_lang"] == "hi"
        url_hi, url_en = (p["corpus_url"], p["found_url"]) if a_is_corpus else (p["found_url"], p["corpus_url"])
        if (url_hi, url_en) in have:
            continue
        (b1, _), (b2, _) = meta_for(p["corpus_url"], client), meta_for(p["found_url"], client)
        match = ("same" if b1 == b2 or b1 in b2 or b2 in b1 else "different") if b1 and b2 else "unknown"
        conf = "unlikely" if match == "different" and p["confidence"] != "high" else p["confidence"]
        rec = merged.get(p["corpus_url"].rstrip("/"))
        row = {k: "" for k in fields}
        row.update(confidence=conf, byline_match=match, same_slug="False", site=urlparse(url_hi).netloc,
                   record_a=rec["record_id"] if rec and a_is_corpus else "(new)", lang_a="hi", url_a=url_hi,
                   status_a=rec["eligibility_status"] if rec and a_is_corpus else "not in corpus",
                   record_b=rec["record_id"] if rec and not a_is_corpus else "(new)", lang_b="en", url_b=url_en,
                   status_b=rec["eligibility_status"] if rec and not a_is_corpus else "not in corpus",
                   basis=f"v1.2 same-name search: {p['evidence']}"[:300], confidence_initial=p["confidence"])
        rows.append(row)
        stats[conf] += 1
    order = {"high": 0, "medium": 1, "low": 2, "unlikely": 3}
    rows.sort(key=lambda r: (order.get(r["confidence"], 9), r["site"], r["url_a"], r["url_b"]))
    with open(PAIRS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return stats


def main():
    rows, stats = ranked_rows()
    keep = []
    for lang in ("hi", "en"):
        ok = [r for r in rows if r["lang"] == lang and r["automatic_checks"] == "pass"]
        ok.sort(key=lambda r: (-r["rank_score"], r["record_id"]))
        keep += ok[:TOP_N]
        stats[f"{lang}_passing_total"] = len(ok)
        stats[f"{lang}_score_ge_3"] = sum(1 for r in ok if r["rank_score"] >= 3)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(keep[0].keys()))
        w.writeheader()
        w.writerows(keep)
    stats.update({f"pairs_added_{k}": v for k, v in add_name_pairs(PoliteClient(min_delay_s=3.0)).items()})
    (ROOT / "data" / "interim" / "expansion_v12_counts.json").write_text(json.dumps(dict(stats), indent=1))
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"{len(keep)} rows -> {OUT}")


if __name__ == "__main__":
    main()
