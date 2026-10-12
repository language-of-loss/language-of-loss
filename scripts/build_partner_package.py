import csv
import hashlib
import json
import re
import shutil
import statistics
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.textutil import word_count

NAME = "Hindi_English_Grief_Research_Partner_Package_v1"
REL = ROOT / "release" / "v1"
PKG = REL / NAME
SRC_DOCS = ROOT / "release" / "v1_src"
LOCAL_ONLY = REL / "LOCAL_ONLY_not_in_zip_blog_texts_for_reviewers"
BUILD_TS = datetime.now(timezone.utc).isoformat(timespec="seconds")
CUTOFF = "2026-09-19T14:15:20Z"


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def jl(path):
    return [json.loads(l) for l in Path(path).open(encoding="utf-8")]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def put(rel, text):
    p = PKG / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text.replace("{{BUILD_TS}}", BUILD_TS), encoding="utf-8")


def copy(src, rel):
    p = PKG / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, p)


def packaged(r, keep_text=True):
    out = {k: v for k, v in r.items() if k not in ("text_original", "text_clean", "dedup_key")}
    out["sha256_text_original"] = sha(r["text_original"])
    out["sha256_text_clean"] = sha(r["text_clean"])
    if keep_text:
        out["text_clean"] = r["text_clean"]
    return out


def main():
    if PKG.exists():
        shutil.rmtree(PKG)
    if LOCAL_ONLY.exists():
        shutil.rmtree(LOCAL_ONLY)
    PKG.mkdir(parents=True)
    counts = {}

    blogs = jl(ROOT / "data" / "clean" / "blogs.jsonl")
    fetch = {json.loads(l)["doc_id"]: json.loads(l) for l in (ROOT / "data" / "raw" / "blogs" / "fetch_log.jsonl").open(encoding="utf-8")}
    meta = []
    for r in blogs:
        ex = r.get("extra") or {}
        meta.append({"record_id": r["record_id"], "source_record_id": r["source_record_id"], "source_url": r["source_url"],
                     "domain": r["thread_id"], "title": ex.get("title"), "published_at": r["published_at"],
                     "collected_at": r["collected_at"], "author_group": r["author_group"],
                     "lang_provisional": r["lang_provisional"], "n_words": r["n_words"],
                     "message_type_provisional": r["message_type_provisional"], "message_type_source": r["message_type_source"],
                     "eligibility_status": r["eligibility_status"], "flags": ";".join(r["flags"]),
                     "deceased_relation_as_stated": ex.get("deceased_relation_as_stated"),
                     "indian_context_evidence": ex.get("indian_context_evidence"), "searcher_notes": ex.get("searcher_notes"),
                     "retrieval_route": r["retrieval_route"], "sha256_text_clean": sha(r["text_clean"]),
                     "sha256_text_as_extracted": sha(r["text_original"]),
                     "sha256_raw_html": fetch.get(r["source_record_id"], {}).get("sha256"), "review_status": r["review_status"]})
    write_csv(PKG / "data/blogs/blogs_metadata.csv", meta)
    for f in ("hi", "en"):
        copy(ROOT / "data" / "candidates" / f"blog_candidates_{f}.jsonl", f"data/blogs/provenance/blog_candidates_{f}.jsonl")
    copy(ROOT / "data" / "raw" / "blogs" / "fetch_log.jsonl", "data/blogs/provenance/fetch_log.jsonl")
    el = [r for r in blogs if r["eligibility_status"] == "provisionally_eligible"]
    counts["blogs"] = {"retained": len(blogs), "eligible": len(el), "lang_eligible": dict(Counter(r["lang_provisional"] for r in el)),
                       "secondary": dict(Counter(r["eligibility_status"] for r in blogs if r not in el))}

    ytcv, hin = jl(ROOT / "data" / "clean" / "ytcv.jsonl"), jl(ROOT / "data" / "clean" / "hinemo9.jsonl")
    write_jsonl(PKG / "data/youtube/clean/ytcv_clean.jsonl", [packaged(r) for r in ytcv])
    write_jsonl(PKG / "data/youtube/clean/hinemo9_clean.jsonl", [packaged(r) for r in hin])
    raw_hits = jl(ROOT / "data" / "raw" / "youtube" / "ytcv_screen_hits.jsonl")
    write_csv(PKG / "data/youtube/raw_identifiers/ytcv_screen_hit_ids.csv",
              [{"source_record_id": r["source_record_id"], "thread_id_hashed_video": r["thread_id"], "sqlite_rowid": r["sqlite_rowid"],
                "screen_side": r["screen_side"], "sha256_text_as_retrieved": sha(r["text"]), "collected_at": r["collected_at"]} for r in raw_hits])
    raw_h = jl(ROOT / "data" / "raw" / "reused_datasets" / "hinemo9_screen_hits.jsonl")
    write_csv(PKG / "data/youtube/raw_identifiers/hinemo9_screen_hit_ids.csv",
              [{"source_record_id": r["source_record_id"], "dataset_language_label": r["dataset_language_label"],
                "dataset_genre_seed": r["dataset_genre_seed"], "sha256_text_as_retrieved": sha(r["text"])} for r in raw_h])
    ck = json.loads((ROOT / "data" / "raw" / "youtube" / "ytcv_checkpoint.json").read_text())
    snap = {"release": "v1", "snapshot_cutoff_utc": CUTOFF, "source": "YTCommentVerse YT-30M.db, https://zenodo.org/records/15678816",
            "expected_bytes": 10843156480, "expected_md5": "4a28043e3971da028add9b46665b4c50", "bytes_downloaded": 2405419580,
            "download_status": "INCOMPLETE - transfer closed by server (curl error 18) at 2026-09-19T14:12Z; not resumed for this release",
            "bytes_parsed": ck["file_bytes_seen"], "share_of_file_parsed": round(ck["file_bytes_seen"] / 10843156480, 4),
            "comments_parsed": ck["rows"], "videos_seen": ck["videos"], "overlong_rows_skipped": ck["overflow_skipped"],
            "screen_hits_raw": len(raw_hits), "records_after_cleaning": len(ytcv),
            "language_of_all_parsed_comments_5pct_systematic_sample": ck["lang_sample"],
            "method": "complete SQLite table-leaf pages parsed in file order (code/src/griefcorpus/sqlite_leafscan.py); rows spilling to overflow pages skipped",
            "note": "Only complete, successfully parsed pages are represented. The partial .db file is not packaged."}
    put("data/youtube/SNAPSHOT.json", json.dumps(snap, indent=1))
    counts["ytcv"] = {"raw_hits": len(raw_hits), "clean": len(ytcv), "lang": dict(Counter(r["lang_provisional"] for r in ytcv)),
                      "threads": len({r["thread_id"] for r in ytcv}), "authors": len({r["author_group"] for r in ytcv})}
    counts["hinemo9"] = {"raw_hits": len(raw_h), "clean": len(hin), "lang": dict(Counter(r["lang_provisional"] for r in hin))}

    red = jl(ROOT / "data" / "clean" / "reddit_confessions.jsonl")
    write_jsonl(PKG / "data/exploratory/reddit_confessions/clean/reddit_confessions_clean.jsonl", [packaged(r) for r in red])
    raw_r = jl(ROOT / "data" / "raw" / "reddit" / "confessions_screen_hits.jsonl")
    write_csv(PKG / "data/exploratory/reddit_confessions/raw_identifiers/confessions_screen_hit_ids.csv",
              [{"source_record_id": r["source_record_id"], "subreddit": r["subreddit"], "created_utc": r["created_utc"],
                "permalink": r["permalink"], "focus_early": r["focus_early"], "sha256_text_as_retrieved": sha(r["title"] + "\n\n" + r["text"])} for r in raw_r])
    counts["reddit"] = {"raw_hits": len(raw_r), "clean": len(red), "focus_early": sum("focus_early" in r["flags"] for r in red)}
    york = jl(ROOT / "data" / "clean" / "york_survey.jsonl")
    yp = []
    for r in york:
        o = packaged(r)
        o["n_words_answers_only"] = word_count(re.sub(r"\[[AB]\d\d\]", " ", r["text_clean"]))
        yp.append(o)
    write_jsonl(PKG / "data/exploratory/york_survey/clean/york_survey_clean.jsonl", yp)
    copy(ROOT / "data/discovery/samples/url_https_reshare_ukdataservice_ac_uk_856067_/survey.xlsx",
         "data/exploratory/york_survey/raw_source/ExperiencesOfGrief_APhenomenologicalSurvey.xlsx")
    counts["york"] = {"clean": len(york), "median_answers_only_retained": statistics.median(o["n_words_answers_only"] for o in yp)}

    seed = list(csv.DictReader((ROOT / "docs" / "seed_corpus.csv").open(encoding="utf-8")))
    for s in seed:
        is_blog = s["platform_genre"].startswith("blog")
        s["text_packaged"] = "no - third-party copyright; excerpt only" if is_blog else "yes"
        if not is_blog:
            copy(ROOT / s["text_path"], f"data/seed/texts/{s['seed_id']}.txt")
        s["text_path"] = "" if is_blog else f"texts/{s['seed_id']}.txt"
    write_csv(PKG / "data/seed/seed_corpus.csv", seed)
    copy(ROOT / "docs" / "seed_audit.md", "data/seed/seed_audit.md")
    counts["seed"] = dict(Counter(s["language_provisional"] for s in seed))

    sheet = list(csv.DictReader((ROOT / "docs" / "annotation_sheet.csv").open(encoding="utf-8")))
    key = list(csv.DictReader((ROOT / "data" / "annotation" / "annotation_key.csv").open(encoding="utf-8")))
    rec = {r["record_id"]: r for src in (blogs, ytcv, hin, red, york) for r in src}
    LOCAL_ONLY.mkdir(parents=True)
    for s, k in zip(sheet, key):
        assert s["annotation_id"] == k["annotation_id"]
        full = rec[k["record_id"]]["text_clean"]
        k["sha256_text_clean"] = sha(full)
        if k["source"] == "blogs":
            (LOCAL_ONLY / f"{s['annotation_id']}.txt").write_text(full, encoding="utf-8")
            s["text_or_excerpt"] = full[:300] + " [...] [full text not packaged: third-party copyright - see README_TEXT_AVAILABILITY.md]"
            s["full_text_path"] = f"texts/{s['annotation_id']}.txt"
        elif s["full_text_path"]:
            copy(ROOT / "data" / "annotation" / s["full_text_path"], f"annotation/reviewer_pack/{s['full_text_path']}")
    write_csv(PKG / "annotation/reviewer_pack/annotation_sheet_v1.csv", sheet)
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "annotation_sheet_v1"
    ws.append(list(sheet[0]))
    for row in sheet:
        ws.append([openpyxl.cell.cell.ILLEGAL_CHARACTERS_RE.sub("", v) for v in row.values()])
    ws.freeze_panes = "B2"
    wb.save(PKG / "annotation/reviewer_pack/annotation_sheet_v1.xlsx")
    for n in ("REVIEWER_INSTRUCTIONS.md", "CODEBOOK_STATUS.md", "README_TEXT_AVAILABILITY.md"):
        put(f"annotation/reviewer_pack/{n}", (SRC_DOCS / "reviewer" / n).read_text(encoding="utf-8"))
    write_csv(PKG / "annotation/restricted_machine_key/annotation_key_v1.csv", key)
    copy(ROOT / "data/annotation/id_mapping_v1.csv", "annotation/restricted_machine_key/id_mapping_v1.csv")
    copy(ROOT / "data/annotation/released_annotation_ids.csv", "annotation/restricted_machine_key/released_annotation_ids.csv")
    put("annotation/restricted_machine_key/README_DO_NOT_SHARE.md", (SRC_DOCS / "restricted" / "README_DO_NOT_SHARE.md").read_text(encoding="utf-8"))
    (LOCAL_ONLY / "README.txt").write_text(
        "NOT PART OF THE ZIP. Full cleaned texts of the blog rows of annotation_sheet_v1.csv, named by annotation_id.\n"
        "Third-party copyright: share with the research partner only as your institutions' fair-dealing / research-exception\n"
        "guidance allows; if shared, drop these files into annotation/reviewer_pack/texts/. Do not publish.\n", encoding="utf-8")
    lang_q = Counter(k["lang_provisional_machine"] for k in key)
    counts["queue"] = {"rows": len(key), "lang": dict(lang_q), "by_source": {s: dict(Counter(k["lang_provisional_machine"] for k in key if k["source"] == s)) for s in sorted({k["source"] for k in key})}}

    for n in ("corpus_summary.md", "feasibility_report.md", "sampling_protocol.md", "access_and_cost_report.md", "data_dictionary.md",
              "source_register.csv", "source_register.md", "collection_log.csv", "exclusion_log.csv"):
        copy(ROOT / "docs" / n, f"reports/{n}")
    put("reports/ACCESS_NEXT_STEPS.md", (SRC_DOCS / "ACCESS_NEXT_STEPS.md").read_text(encoding="utf-8"))
    copy(ROOT / "PROGRESS.md", "reports/PROGRESS_working_log.md")
    copy(ROOT / "data/clean/qc_report.json", "reports/qc_report.json")
    copy(ROOT / "data/discovery/search_log.csv", "reports/source_discovery/search_log.csv")
    from griefcorpus.clean import EMAIL_RE, PHONE_RE
    cands = []
    for c in jl(ROOT / "data/discovery/candidates.jsonl"):
        for k in ("description", "title"):
            if c.get(k):
                c[k] = PHONE_RE.sub(lambda m: "[PHONE]" if sum(ch.isdigit() for ch in m.group()) >= 10 else m.group(), EMAIL_RE.sub("[EMAIL]", c[k]))
        cands.append(c)
    write_jsonl(PKG / "reports/source_discovery/candidates.jsonl", cands)
    for f in sorted((ROOT / "data/discovery/evidence").glob("*.json")):
        ev = json.loads(f.read_text(encoding="utf-8"))
        for k in ("sample_head", "sample_rows", "readme_head", "page_head", "description"):
            ev.pop(k, None)
        put(f"reports/source_discovery/evidence/{f.name}", json.dumps(ev, ensure_ascii=False, indent=1))
    for f in ("reddit_pilot_review.csv", "ytcv_partial_pilot.json"):
        copy(ROOT / "data/interim" / f, f"reports/pilots/{f}")

    for f in sorted((ROOT / "src/griefcorpus").glob("*.py")):
        copy(f, f"code/src/griefcorpus/{f.name}")
    for f in sorted((ROOT / "scripts").glob("*")):
        if f.is_file():
            copy(f, f"code/scripts/{f.name}")
    for f in ("pipeline.yaml", "shortlist.yaml", "source_decisions.yaml", "youtube_pilot_queries.txt"):
        copy(ROOT / "config" / f, f"code/config/{f}")
    copy(ROOT / "requirements.txt", "code/requirements.txt")
    copy(ROOT / ".env.example", "code/.env.example")
    copy(ROOT / "README.md", "code/README_pipeline.md")
    copy(ROOT / "data/seed/machine_review.json", "code/config/seed_machine_review.json")
    copy(ROOT / "data/seed/seed_blog_selection.json", "code/config/seed_blog_selection.json")

    b, y = counts["blogs"], counts["ytcv"]
    put("data/blogs/README.md", f"""# data/blogs - PRIMARY source (metadata only; texts withheld)

{b['retained']} web pages retained after cleaning: {b['eligible']} typed `personal_disclosure` by the search tool
(machine language labels: {b['lang_eligible']}) and {b['retained'] - b['eligible']} contrast pages ({b['secondary']}).
**No human has confirmed any type.** The one page labelled `romanized_hindi` is a heavily code-mixed page.

**Why there is no text here.** Each page is its author's or publisher's copyright ("all rights reserved" unless the
page says otherwise). The originating machine holds a local analysis copy; this package does not redistribute it.
`blogs_metadata.csv` gives, per page: URL, site, title, publication date, hashed byline group (never a name), machine
language label, word count of the cleaned text, machine-assigned type, flags, and SHA-256 hashes of the cleaned text, the
extracted text and the raw HTML, so that a rebuilt copy can be checked.

**Retrieval:** from the package root run `python code/scripts/rebuild_blog_texts.py` (add `--annotation` to also write
the reviewer-pack text files). It honours robots.txt, waits 3 s between requests to a site, and reports for each page
`match` / `changed` / `unavailable`. Pages change and disappear; a `changed` page must be re-inspected, not assumed equal.

`provenance/`: the two verified candidate lists (every URL was opened before listing; includes the search query that
found it) and the fetch log (HTTP status, byte count, SHA-256; two robots.txt refusals that were respected).
Raw HTML is not packaged. `raw` and `clean` stages describe the same {b['retained']} pages - they are not extra observations.
""")
    put("data/youtube/README.md", f"""# data/youtube - SECONDARY short-form source (open datasets, not the API)

- `clean/ytcv_clean.jsonl` - {y['clean']} comments from YTCommentVerse (CC BY 4.0, Zenodo 10.5281/zenodo.15678816)
  that passed the bereavement keyword screen, after de-duplication. Machine language labels: {y['lang']}.
  {y['threads']} hashed video threads, {y['authors']} hashed commenters.
- `clean/hinemo9_clean.jsonl` - {counts['hinemo9']['clean']} screen hits from HinEmo-9 (CC BY 4.0, Zenodo 10.5281/zenodo.22041925): {counts['hinemo9']['lang']}.
- `raw_identifiers/` - the same records at the *retrieval* stage ({y['raw_hits']} and {counts['hinemo9']['raw_hits']} screen hits before cleaning):
  dataset IDs and SHA-256 of the text as retrieved. **Raw and clean are two stages of the same comments - never add them.**
  Unmasked raw text is not packaged (it can contain @handles and names); re-obtain it from the Zenodo records.
- `SNAPSHOT.json` - cutoff {CUTOFF}; the 10.8 GB download stopped at 22.2% and this release is frozen there.

`text_clean` has URLs, e-mails, @handles, legacy "+Name" prefixes and phone numbers masked; commenter names were never
stored; `author_group` and `thread_id` are hashes. "Provisionally eligible" means only "passed the screen": on the
samples read by machine about half of English hits and about 60% of Hindi-side hits were real first-person
disclosures; the rest include TV-serial plot talk. No video titles, dates or reply links exist in these datasets, so
this set cannot support a matched bilingual-thread comparison. Attribution is required when reusing (CC BY 4.0); the
compilers' licence cannot exceed what YouTube's terms allowed them, so do not re-publish the text.
""")
    put("data/exploratory/README.md", f"""# data/exploratory - NOT part of any Hindi-English comparison

**reddit_confessions/** - {counts['reddit']['clean']} English Reddit posts (r/offmychest, r/trueoffmychest, r/confession,
r/confessions; 2019-03 to 2021-09) that passed the screen, from `SocialGrep/one-million-reddit-confessions` (Hugging
Face, CC BY 4.0 label by the compiler). {counts['reddit']['focus_early']} carry the flag `focus_early` (death mentioned in the title or first 500
characters; 8 of 18 such posts read by machine were primary disclosures, versus 1 of 12 without the flag).
571,163 of the 1,000,000 source posts were removed/deleted/empty and were never retained. No author field, no replies.
`raw_identifiers/` lists the {counts['reddit']['raw_hits']} screen hits before de-duplication (post ID, permalink, timestamp, hash) - the
same posts at an earlier stage. English only: no suitable Hindi material was found in the Reddit sources searched.

**york_survey/** - {counts['york']['clean']} respondents of "Experiences of Grief: A Phenomenological Survey, 2020" (Millar, Ratcliffe,
Richardson, Hughes; UK Data Service ReShare 856067, DOI 10.5255/UKDA-SN-856067, CC BY 4.0; participants consented to
public release). UK, elicited survey answers: for codebook development only. `raw_source/` is the unchanged workbook;
`clean/` is built from the 40 answer columns only - the workbook's `FullQandAs` column repeats every answer and is
never read. Verified median: 639 words per respondent over all 235 respondents (answers only); the cleaned file omits
one respondent with under 20 words (median of `n_words_answers_only` over the retained {counts['york']['clean']}: {counts['york']['median_answers_only_retained']}).
`n_words` additionally counts the `[A01]`-style labels as tokens. See `CHANGELOG.md`.
""")
    put("data/seed/README.md", f"""# data/seed - 15 feasibility examples (machine labels: {counts['seed']})

Machine-reviewed, provisional; excluded from the annotation queue. Texts are packaged for the 9 items from CC BY datasets;
the 6 blog items appear as a 300-character excerpt plus URL only (third-party copyright). `seed_corpus.csv` contains
machine labels, so keep it away from reviewers.
""")
    put("START_HERE.md", (SRC_DOCS / "START_HERE.md").read_text(encoding="utf-8"))
    put("CHANGELOG.md", (SRC_DOCS / "CHANGELOG.md").read_text(encoding="utf-8"))
    put("reports/RELEASE_v1.json", json.dumps({"package": NAME, "release": "v1", "built_utc": BUILD_TS, "data_cutoff_utc": CUTOFF,
                                                "human_reviewed_records": 0, "counts": counts}, ensure_ascii=False, indent=1, default=str))

    files = sorted(p for p in PKG.rglob("*") if p.is_file() and p.name != "MANIFEST.csv" and p.name != ".DS_Store")
    with (PKG / "MANIFEST.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["relative_path", "bytes", "sha256"])
        for p in files:
            w.writerow([p.relative_to(PKG).as_posix(), p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()])
    zpath = REL / f"{NAME}.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(PKG.rglob("*")):
            if p.is_file() and p.name != ".DS_Store":
                z.write(p, (Path(NAME) / p.relative_to(PKG)).as_posix())
    print(json.dumps(counts, ensure_ascii=False, default=str)[:1500])
    print("files:", len(files) + 1, "| zip bytes:", zpath.stat().st_size, "|", zpath)


if __name__ == "__main__":
    main()
