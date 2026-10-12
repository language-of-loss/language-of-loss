import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from .http import ROOT, now_iso
from .textutil import dedup_key, detect_language, jaccard, normalize_for_analysis, shingles, word_count, words

RAW, CLEAN, DOCS = ROOT / "data" / "raw", ROOT / "data" / "clean", ROOT / "docs"
HINDI_SIDE = {"devanagari_hindi", "romanized_hindi", "mixed_hi_en"}
KEEP_LANGS = HINDI_SIDE | {"english", "uncertain"}

URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
HANDLE_RE = re.compile(r"(?<!\w)@+[\w.\-]{2,}|^\+[^\W\d_]+(?: [A-Z][^\W\d_]+)?(?= )")
BOILER = re.compile(
    r"^(featured image|image credit|photo credit|share this|posted by|labels?:|filed under|tags?:|related posts?|"
    r"you can (find|follow|reach) (her|him|them|me)|follow (us|me) on|subscribe|leave a (comment|reply)|"
    r"(he|she) (tweets|is on twitter)|.{0,80} is an? .{0,120}(writer|journalist|student|editor|poet|professor|manager)\b.{0,200}$|"
    r"-?\s*https?://\S+$|-+$|you may also like|अधिक जानकारी के लिए|ईमेल|वेबसाइट|disclaimer|अस्वीकरण|यह पोस्ट .{0,40} ब्लॉग पर भी है|लिंक|आप ब्लॉग पर|ψ+|किसी भी योजना, प्रक्रिया|.{0,60}category से संबंधित है)", re.I)

PHONE_RE = re.compile(r"(?<![\w])(?:\+?[\d०-९][\d०-९\s\-]{8,}[\d०-९])(?![\w])")

EXCL = []


def exclude(source, rid, reason, detail=""):
    EXCL.append({"source": source, "source_record_id": rid, "reason": reason, "detail": detail, "logged_at": now_iso()})


def mask(text):
    text = URL_RE.sub("[URL]", text)
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub(lambda m: "[PHONE]" if sum(ch.isdigit() for ch in m.group()) >= 10 else m.group(), text)
    return HANDLE_RE.sub("[HANDLE]", text)


def clean_doc_text(text):
    lines, out = [l for l in normalize_for_analysis(text).split("\n")], []
    for l in lines:
        if not out or l.strip() != out[-1].strip() or not l.strip():
            out.append(l)
    removed = 0
    while out and removed < 14 and (not out[-1].strip() or BOILER.search(out[-1].strip())):
        if out[-1].strip():
            removed += 1
        out.pop()
    return mask("\n".join(out)).strip(), removed


def near_dup_groups(records):
    buckets = defaultdict(list)
    for i, r in enumerate(records):
        toks = [w.lower() for w in words(r["text_clean"])]
        if len(toks) >= 12:
            buckets[("h", " ".join(toks[:8]))].append(i)
            buckets[("t", " ".join(toks[-8:]))].append(i)
    parent = {}
    for idxs in buckets.values():
        if 1 < len(idxs) <= 50:
            sh = {i: shingles(records[i]["text_clean"]) for i in idxs}
            for a in idxs:
                for b in idxs:
                    if a < b and jaccard(sh[a], sh[b]) >= 0.8:
                        parent.setdefault(b, a)
    return parent


def put(qc, **kw):
    for k, v in kw.items():
        qc[k] = v


def finish(source, records, qc):
    seen, kept = {}, []
    for r in records:
        lang, det = detect_language(r["text_clean"])
        r["lang_provisional"], r["n_words"] = lang, word_count(r["text_clean"])
        r["dedup_key"] = dedup_key(r["text_clean"])
        if r["n_words"] < r.pop("_min_words"):
            exclude(source, r["source_record_id"], "empty_or_too_short", f"{r['n_words']} words")
            continue
        if lang not in KEEP_LANGS:
            exclude(source, r["source_record_id"], "other_language", json.dumps(det, ensure_ascii=False)[:160])
            continue
        if r["dedup_key"] in seen:
            exclude(source, r["source_record_id"], "exact_duplicate", f"of {seen[r['dedup_key']]}")
            qc["exact_duplicates_removed"] += 1
            continue
        seen[r["dedup_key"]] = r["record_id"]
        kept.append(r)
    nd = near_dup_groups(kept)
    final = []
    for i, r in enumerate(kept):
        if i in nd:
            exclude(source, r["source_record_id"], "near_duplicate", f"of {kept[nd[i]]['record_id']}")
            qc["near_duplicates_removed"] += 1
            continue
        r["duplicate_group"] = r["record_id"]
        final.append(r)
    CLEAN.mkdir(parents=True, exist_ok=True)
    with (CLEAN / f"{source}.jsonl").open("w", encoding="utf-8") as fh:
        for r in final:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    el = [r for r in final if r["eligibility_status"] == "provisionally_eligible"]
    put(qc, retained=len(final), provisionally_eligible=len(el),
              lang_all=dict(Counter(r["lang_provisional"] for r in final)),
              lang_eligible=dict(Counter(r["lang_provisional"] for r in el)),
              eligibility=dict(Counter(r["eligibility_status"] for r in final)),
              authors_distinct=len({r["author_group"] for r in final if r["author_group"]}),
              authors_missing=sum(1 for r in final if not r["author_group"]),
              threads_distinct=len({r["thread_id"] for r in final if r["thread_id"]}),
              words_by_lang_eligible={k: sum(r["n_words"] for r in el if r["lang_provisional"] == k)
                                     for k in {r["lang_provisional"] for r in el}},
              human_reviewed=0)
    return final


def base(source, rid, **kw):
    r = {"record_id": f"{source}:{rid}", "platform": None, "genre": None, "source_url": None, "source_record_id": rid,
         "source_dataset": None, "collected_at": None, "published_at": None, "thread_id": None, "parent_id": None,
         "author_group": None, "text_original": None, "text_clean": None, "lang_provisional": None, "n_words": None,
         "message_type_provisional": None, "message_type_source": None, "eligibility_status": None,
         "exclusion_reason": None, "retrieval_route": None, "duplicate_group": None, "reuse_notes": None,
         "flags": [], "review_status": "no_human_review", "_min_words": 4}
    r.update(kw)
    return r


def blogs():
    qc = Counter()
    cand = {}
    for f in ("hi", "en"):
        for line in (ROOT / "data" / "candidates" / f"blog_candidates_{f}.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                cand[c["url"].strip()] = dict(c, _list=f)
    ext = {}
    for line in (ROOT / "data" / "interim" / "blogs_extracted.jsonl").open(encoding="utf-8"):
        d = json.loads(line)
        ext[d["url"]] = d
    for line in (RAW / "blogs" / "fetch_log.jsonl").open(encoding="utf-8"):
        f = json.loads(line)
        qc["attempted"] += 1
        if f["status"] in ("robots_disallow", "fetch_failed", "error"):
            qc["failed"] += 1
            exclude("blogs", f["doc_id"], f["status"], f["url"])
    recs = []
    for url, d in ext.items():
        c = cand.get(url)
        if c is None:
            exclude("blogs", d["doc_id"], "dropped_from_final_candidate_list_by_searcher", url)
            continue
        text, removed = clean_doc_text(d["text"])
        typ = c["type"]
        status = "provisionally_eligible" if typ == "personal_disclosure" else f"secondary_{typ}"
        if c.get("original_or_translation") in ("translation",):
            status = "secondary_translation"
        flags = []
        if removed:
            flags.append(f"boilerplate_lines_removed:{removed}")
        if d["n_words"] > 5000:
            flags.append("length_outlier_gt5000w")
        if c.get("original_or_translation") in ("repost", "unclear"):
            flags.append(f"provenance:{c['original_or_translation']}")
        recs.append(base("blogs", d["doc_id"], platform="web", genre="blog_or_personal_essay", source_url=url,
                         collected_at=d["collected_at"], published_at=d.get("publication_date"), thread_id=d["domain"],
                         author_group=d.get("author_group"), text_original=d["text"], text_clean=text,
                         message_type_provisional=typ, message_type_source="search tool after opening page (not human)",
                         eligibility_status=status,
                         retrieval_route=f"web search ({c['_list']} list): {c.get('query_that_found_it', '')}",
                         reuse_notes="copyright of author/site; local analysis copy; do not redistribute text",
                         flags=flags, _min_words=80,
                         extra={"title": d.get("title"), "deceased_relation_as_stated": c.get("deceased_relation_as_stated"),
                                "indian_context_evidence": c.get("indian_context_evidence", "not recorded"),
                                "searcher_notes": c.get("notes")}))
    final = finish("blogs", recs, qc)
    per_dom, per_auth = Counter(), Counter()
    for r in final:
        if r["eligibility_status"] != "provisionally_eligible":
            continue
        per_dom[r["thread_id"]] += 1
        over = per_dom[r["thread_id"]] > 3
        if r["author_group"]:
            per_auth[r["author_group"]] += 1
            over = over or per_auth[r["author_group"]] > 1
        if over:
            r["flags"].append("over_cap")
    with (CLEAN / "blogs.jsonl").open("w", encoding="utf-8") as fh:
        for r in final:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    el = [r for r in final if r["eligibility_status"] == "provisionally_eligible"]
    qc["documents_by_lang_eligible"] = dict(Counter(r["lang_provisional"] for r in el))
    qc["words_by_lang_eligible_excl_outliers"] = {k: sum(r["n_words"] for r in el if r["lang_provisional"] == k and "length_outlier_gt5000w" not in r["flags"])
                                                  for k in {r["lang_provisional"] for r in el}}
    qc["documents_excl_outliers_and_over_cap"] = dict(Counter(r["lang_provisional"] for r in el if not set(r["flags"]) & {"length_outlier_gt5000w", "over_cap"}))
    qc["retrieved"] = len(ext)
    return qc


def ytcv():
    qc = Counter()
    recs = []
    p = RAW / "youtube" / "ytcv_screen_hits.jsonl"
    for line in p.open(encoding="utf-8"):
        d = json.loads(line)
        qc["retrieved"] += 1
        recs.append(base("ytcv", d["source_record_id"], platform="youtube", genre="video_comment (reused dataset)",
                         source_dataset="YTCommentVerse, Zenodo 10.5281/zenodo.15678816", collected_at=d["collected_at"],
                         thread_id=d["thread_id"], author_group=d["author_group"], text_original=d["text"],
                         text_clean=mask(normalize_for_analysis(d["text"])), message_type_provisional="unreviewed_screen_hit",
                         message_type_source="regex screen", eligibility_status="provisionally_eligible",
                         retrieval_route=f"leaf-page scan of YT-30M.db; broad bereavement screen ({d['screen_side']} side)",
                         reuse_notes="CC BY 4.0 compilation; underlying comments belong to commenters; IDs hashed by dataset authors",
                         extra={"video_category": d["video_category"], "votes": d["votes"]}))
    ck = json.loads((RAW / "youtube" / "ytcv_checkpoint.json").read_text())
    final = finish("ytcv", recs, qc)
    put(qc, rows_scanned=ck["rows"], share_of_file_scanned=round(ck["file_bytes_seen"] / ck["file_bytes_total"], 4),
              language_5pct_sample_of_all_scanned_rows=ck["lang_sample"], videos_scanned=ck["videos"])
    return qc


def reddit():
    qc = Counter()
    recs = []
    for line in (RAW / "reddit" / "confessions_screen_hits.jsonl").open(encoding="utf-8"):
        d = json.loads(line)
        qc["retrieved"] += 1
        full = d["title"] + "\n\n" + d["text"]
        recs.append(base("reddit_confessions", d["source_record_id"], platform="reddit", genre=f"post r/{d['subreddit']} (reused dataset)",
                         source_url=d["permalink"], source_dataset="SocialGrep/one-million-reddit-confessions (HF, CC BY 4.0)",
                         collected_at=d["collected_at"], published_at=d["created_utc"], thread_id=d["source_record_id"],
                         text_original=full, text_clean=mask(normalize_for_analysis(full)),
                         message_type_provisional="unreviewed_screen_hit", message_type_source="regex screen",
                         eligibility_status="provisionally_eligible" if d["focus_early"] else "secondary_screen_hit_late_mention",
                         retrieval_route="broad bereavement screen over 1,000,000 posts; focus_early = match within title/first 500 chars",
                         reuse_notes="third-party compilation; Reddit names RFR as the authorised research route; exploratory use only",
                         flags=["focus_early"] if d["focus_early"] else []))
    finish("reddit_confessions", recs, qc)
    return qc


def hinemo_and_york():
    out = {}
    qc = Counter()
    recs = []
    for line in (RAW / "reused_datasets" / "hinemo9_screen_hits.jsonl").open(encoding="utf-8"):
        d = json.loads(line)
        qc["retrieved"] += 1
        recs.append(base("hinemo9", d["source_record_id"], platform="youtube", genre="video_comment (reused dataset)",
                         source_dataset="HinEmo-9 v1.0.1, Zenodo 10.5281/zenodo.22041925", collected_at=d["collected_at"],
                         text_original=d["text"], text_clean=normalize_for_analysis(d["text"]),
                         message_type_provisional="unreviewed_screen_hit", message_type_source="regex screen",
                         eligibility_status="provisionally_eligible", retrieval_route="broad screen over 30,436 comments",
                         reuse_notes="CC BY 4.0 curation; PII pre-masked by dataset authors; no thread/author/date fields exist",
                         extra={"dataset_language_label": d["dataset_language_label"], "dataset_genre_seed": d["dataset_genre_seed"]}))
    finish("hinemo9", recs, qc)
    out["hinemo9"] = qc
    qc2 = Counter()
    recs = []
    for line in (RAW / "reused_datasets" / "york_survey_respondents.jsonl").open(encoding="utf-8"):
        d = json.loads(line)
        qc2["retrieved"] += 1
        recs.append(base("york_survey", d["source_record_id"], platform="survey", genre="open_text_survey_answers (elicited)",
                         source_url="https://reshare.ukdataservice.ac.uk/856067/", source_dataset="UKDA ReShare 856067 (CC BY 4.0)",
                         collected_at=d["collected_at"], published_at="2020-06/2021-02", author_group=d["source_record_id"],
                         text_original=d["text"], text_clean=normalize_for_analysis(d["text"]),
                         message_type_provisional="personal_disclosure_elicited", message_type_source="survey design",
                         eligibility_status="secondary_reference_english_only", retrieval_route="open download; all respondents",
                         reuse_notes="CC BY 4.0; participants consented to public release", _min_words=20,
                         extra={"nationality_self_reported": d["nationality_self_reported"], "person_who_died": d["person_who_died"],
                                "past_or_present": d["past_or_present"]}))
    finish("york_survey", recs, qc2)
    out["york_survey"] = qc2
    return out


def main():
    report = {"built_at": now_iso(), "sources": {}}
    report["sources"]["blogs"] = blogs()
    report["sources"]["ytcv"] = ytcv()
    report["sources"]["reddit_confessions"] = reddit()
    report["sources"].update(hinemo_and_york())
    (CLEAN / "qc_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, default=dict), encoding="utf-8")
    with (DOCS / "exclusion_log.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "source_record_id", "reason", "detail", "logged_at"])
        w.writeheader()
        w.writerows(EXCL)
        w.writerow({"source": "reddit_confessions", "source_record_id": "(aggregate)", "reason": "removed_deleted_or_empty_at_source",
                    "detail": "571,163 of 1,000,000 posts had selftext [removed]/[deleted]/empty and were never retained (deletions honoured); counted, not listed",
                    "logged_at": now_iso()})
    for s, q in report["sources"].items():
        print(s, {k: q[k] for k in ("retrieved", "exact_duplicates_removed", "near_duplicates_removed", "retained", "provisionally_eligible") if k in q},
              q.get("lang_eligible"))
    print("exclusions logged:", len(EXCL) + 1)


if __name__ == "__main__":
    main()
