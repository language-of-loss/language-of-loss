import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from datasketch import MinHash, MinHashLSH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from griefcorpus.clean import clean_doc_text
from griefcorpus.textutil import detect_language, jaccard, shingles, word_count
from rank_screen import score

OUT = ROOT / "docs" / "review_master_2026-10.csv"
COUNTS = ROOT / "data" / "interim" / "review_master_counts.json"
PASSES = {"blog_candidates_v11_bilingual.jsonl": ("v1.1", "v1.1_bilingual_hunt"),
          "blog_candidates_v12_hi_webzines.jsonl": ("v1.2", "v1.2_hi_webzines"),
          "blog_candidates_v12_hi_blogs.jsonl": ("v1.2", "v1.2_hi_personal_blogs"),
          "blog_candidates_v12_en.jsonl": ("v1.2", "v1.2_en_essays"),
          "blog_candidates_v12_name_search.jsonl": ("v1.2", "v1.2_name_search"),
          "blog_candidates_v12_same_author.jsonl": ("v1.2", "same_author_dev"),
          "blog_candidates_v13_hi_webzines.jsonl": ("v1.3", "v1.3_hi_webzines"),
          "blog_candidates_v13_hi_blogs.jsonl": ("v1.3", "v1.3_hi_personal_blogs"),
          "blog_candidates_v13_pratilipi.jsonl": ("v1.3", "v1.3_hi_pratilipi_listing"),
          "blog_candidates_v13_en.jsonl": ("v1.3", "v1.3_en_essays"),
          "blog_candidates_v14_archive.jsonl": ("v1.4", "v1.4_archive_listing")}
LANG2 = {"devanagari_hindi": "hi", "english": "en", "romanized_hindi": "hi-Latn", "mixed_hi_en": "mixed"}
KEEP = ("hi", "en", "hi-Latn", "mixed")
DOMAIN_CAP = {"mediawala.in": 8, "kafaltree.com": 5, "grehlakshmi.com": 5, "samalochan.com": 5, "sahityakunj.net": 8,
              "livewire.thewire.in": 5, "scroll.in": 5, "tweakindia.com": 5,
              "thegoodstoryproject.com": 5, "womensweb.in": 5}
DEFAULT_CAP = 3
JACCARD = 0.8
REVIEW_COLS = ("decision", "relation", "reason", "reviewer")
BYLINE_UNRELIABLE = {"v1.2_hi_webzines", "v1.3_hi_webzines", "v1.3_hi_pratilipi_listing"}
BYLINE_UNRELIABLE_DOMAINS = {"mediawala.in", "kafaltree.com", "sahityakunj.net", "samalochan.com", "grehlakshmi.com",
                             "pratilipi.com"}
PASS_GROUP = {"v1.1": 0, "v1.2": 0, "v1.3": 0, "v1.4": 1}
FIELDS = ["review_id", "record_id", "lang", "source_domain", "domain_covariate", "corpus_texts_same_domain", "url",
          "title", "n_words", "rank_score", "pass", "route", "over_cap", "first_300_chars",
          "decision", "relation", "reason", "reviewer"]


def norm_url(u):
    u = re.sub(r"^https?://", "", (u or "").strip()).rstrip("/")
    host, _, path = u.partition("/")
    host = host.lower()
    return (host[4:] if host.startswith("www.") else host) + ("/" + path if path else "")


def domain_covariate(domain):
    d = domain.lower().replace("www.", "")
    d = d[2:] if d.startswith("m.") else d
    return "pratilipi.com" if d.endswith("pratilipi.com") else d


def review_id(url):
    return "RV-" + hashlib.sha256(norm_url(url).encode("utf-8")).hexdigest()[:10]


def minhash(sh):
    m = MinHash(num_perm=128)
    for s in sh:
        m.update(s.encode("utf-8"))
    return m


def load_candidates():
    log = {}
    for l in (ROOT / "data" / "raw" / "blogs" / "fetch_log.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        if r.get("candidate_file") in PASSES and r["doc_id"] not in log:
            log[r["doc_id"]] = r
    out = {}
    for l in (ROOT / "data" / "interim" / "blogs_extracted.jsonl").open(encoding="utf-8"):
        d = json.loads(l)
        if d["doc_id"] not in log or d["doc_id"] in out:
            continue
        f = log[d["doc_id"]]
        text, removed = clean_doc_text(d["text"])
        lang, det = detect_language(text)
        out[d["doc_id"]] = dict(doc=d, fetch=f, text=text, boilerplate_removed=removed, lang_provisional=lang,
                                lang=LANG2.get(lang, lang), n_words=word_count(text),
                                pass_=PASSES[f["candidate_file"]][0], route=PASSES[f["candidate_file"]][1])
    return out


def main():
    stats = Counter()
    corpus = [json.loads(l) for l in (ROOT / "data" / "clean" / "blogs_merged.jsonl").open(encoding="utf-8")]
    corpus_urls = {norm_url(r["source_url"]) for r in corpus}
    corpus_authors = {r["author_group"] for r in corpus if r["author_group"] and
                      r["eligibility_status"] == "provisionally_eligible"}
    corpus_dom = Counter(domain_covariate(r["thread_id"] or "") for r in corpus
                         if r["eligibility_status"] == "provisionally_eligible")
    cands = load_candidates()
    stats["fetched_texts"] = len(cands)
    rows = []
    for doc_id, c in cands.items():
        if c["n_words"] < 80:
            stats["dropped_short_lt80w"] += 1
            continue
        if c["lang"] not in KEEP:
            stats[f"dropped_lang_{c['lang']}"] += 1
            continue
        urls = {norm_url(c["doc"]["url"]), norm_url(c["fetch"].get("final_url"))} - {""}
        if urls & corpus_urls:
            stats["dropped_url_in_corpus"] += 1
            continue
        lang = c["lang"]
        s = score(c["text"], "hi" if lang in ("hi", "mixed") else "en")["score"] if lang != "hi-Latn" else ""
        rows.append(dict(c, doc_id=doc_id, urls=urls, rank=s))
    rows.sort(key=lambda r: (PASS_GROUP[r["pass_"]], -(r["rank"] or 0), r["doc_id"]))
    lsh = MinHashLSH(threshold=JACCARD, num_perm=128)
    corpus_sh = {}
    for r in corpus:
        sh = shingles(r["text_clean"] or "")
        corpus_sh[r["record_id"]] = sh
        lsh.insert(r["record_id"], minhash(sh))
    seen_urls, kept, cand_sh = set(), [], {}
    for r in rows:
        if r["urls"] & seen_urls:
            stats["dropped_url_dup_within_candidates"] += 1
            continue
        sh = shingles(r["text"])
        hits = [k for k in lsh.query(minhash(sh))
                if jaccard(sh, corpus_sh.get(k) or cand_sh.get(k, set())) >= JACCARD]
        if hits:
            stats["dropped_minhash_" + ("corpus" if any(h in corpus_sh for h in hits) else "within_candidates")] += 1
            continue
        key = "cand:" + r["doc_id"]
        cand_sh[key] = sh
        lsh.insert(key, minhash(sh))
        seen_urls |= r["urls"]
        kept.append(r)
    per_dom, authors = Counter(), set(corpus_authors)
    kept.sort(key=lambda r: (-(r["rank"] or 0), r["doc_id"]))
    for r in kept:
        flags = []
        dom = domain_covariate(r["doc"]["domain"])
        r["dom"] = dom
        au = r["doc"].get("author_group")
        if dom in BYLINE_UNRELIABLE_DOMAINS:
            au = None
        if r["route"] == "same_author_dev":
            flags.append("same_author_dev")
        elif r["route"] == "v1.1_bilingual_hunt" or (au and au in authors and r["route"] not in BYLINE_UNRELIABLE):
            flags.append("author_cap")
        else:
            per_dom[dom] += 1
            if per_dom[dom] > DOMAIN_CAP.get(dom, DEFAULT_CAP):
                flags.append("domain_cap")
            if au and r["route"] not in BYLINE_UNRELIABLE:
                authors.add(au)
        r["over_cap"] = ";".join(flags)
    order = {"hi": 0, "en": 1, "mixed": 2, "hi-Latn": 3}
    kept.sort(key=lambda r: (order[r["lang"]], -(r["rank"] or 0), r["doc_id"]))
    out = [dict(review_id=review_id(r["doc"]["url"]), record_id=f"blogs:{r['doc_id']}", lang=r["lang"],
                source_domain=r["doc"]["domain"], domain_covariate=r["dom"],
                corpus_texts_same_domain=corpus_dom.get(r["dom"], 0), url=r["doc"]["url"],
                title=(r["doc"].get("title") or "").replace("\n", " "), n_words=r["n_words"], rank_score=r["rank"],
                pass_=r["pass_"], route=r["route"], over_cap=r["over_cap"],
                first_300_chars=r["text"][:300].replace("\n", " "), decision="", relation="", reason="", reviewer="")
           for r in kept]
    assert len({o["review_id"] for o in out}) == len(out), "review_id collision"
    filled = {}
    if OUT.exists():
        filled = {r["review_id"]: r for r in csv.DictReader(OUT.open(encoding="utf-8"))
                  if any((r.get(k) or "").strip() for k in REVIEW_COLS)}
    lost = sorted(set(filled) - {o["review_id"] for o in out})
    if lost:
        sys.exit(f"REFUSED: filled review rows would disappear: {lost[:10]}")
    for o in out:
        if o["review_id"] in filled:
            o.update({k: filled[o["review_id"]][k] for k in REVIEW_COLS})
    stats["review_rows_carried_over"] = len(filled)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for o in out:
            o["pass"] = o.pop("pass_")
            w.writerow(o)
    eligible = Counter(LANG2.get(r["lang_provisional"], r["lang_provisional"]) for r in corpus
                       if r["eligibility_status"] == "provisionally_eligible")
    eligible_uncapped = Counter(LANG2.get(r["lang_provisional"], r["lang_provisional"]) for r in corpus
                                if r["eligibility_status"] == "provisionally_eligible" and "over_cap" not in r["flags"])
    for o in out:
        stats[f"rows_{o['lang']}"] += 1
        stats[f"rows_{o['lang']}_{o['pass']}"] += 1
        if not o["over_cap"]:
            stats[f"rows_{o['lang']}_not_over_cap"] += 1
            if o["rank_score"] != "" and o["rank_score"] >= 2.5:
                stats[f"rows_{o['lang']}_not_over_cap_ge_2.5"] += 1
        for f in o["over_cap"].split(";") if o["over_cap"] else []:
            stats[f"rows_{o['lang']}_flag_{f}"] += 1
    for lang in ("hi", "en"):
        stats[f"corpus_eligible_{lang}"] = eligible[lang]
        stats[f"corpus_eligible_not_over_cap_{lang}"] = eligible_uncapped[lang]
        stats[f"yes_needed_for_100_{lang}"] = max(100 - eligible[lang], 0)
        stats[f"yes_needed_for_100_not_over_cap_{lang}"] = max(100 - eligible_uncapped[lang], 0)
    stats["rows_total"] = len(out)
    COUNTS.write_text(json.dumps(dict(sorted(stats.items())), indent=1))
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"{len(out)} rows -> {OUT}")


if __name__ == "__main__":
    main()
