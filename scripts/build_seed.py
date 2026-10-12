import csv
import io
import json
import random
import re
import sys
import warnings
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")
from griefcorpus.http import now_iso
from griefcorpus.textutil import bereavement_screen, dedup_key, detect_language, normalize_for_analysis, word_count

SEED = 20260919
TEXTS = ROOT / "data" / "seed" / "texts"
SAMPLES = ROOT / "data" / "discovery" / "samples"

MACHINE_REVIEW = json.loads((ROOT / "data" / "seed" / "machine_review.json").read_text(encoding="utf-8")) \
    if (ROOT / "data" / "seed" / "machine_review.json").exists() else {}
SEED_BLOGS = json.loads((ROOT / "data" / "seed" / "seed_blog_selection.json").read_text(encoding="utf-8")) \
    if (ROOT / "data" / "seed" / "seed_blog_selection.json").exists() else []

FIELDS = ["seed_id", "platform_genre", "source_dataset", "source_url", "source_record_id", "retrieval_route",
          "collected_at", "publication_date", "language_provisional", "language_machine_reviewed", "n_words",
          "message_type_machine_reviewed", "eligibility_machine_reviewed", "deceased_relation_as_stated",
          "context_available", "population_evidence", "reuse_terms", "text_retained", "text_path", "text_excerpt",
          "dedup_key", "review_status", "machine_note"]


def york_items():
    import openpyxl
    ws = openpyxl.load_workbook(str(SAMPLES / "url_https_reshare_ukdataservice_ac_uk_856067_" / "survey.xlsx"), read_only=True)["Sheet 1 - Bereavement"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h) for h in rows[0]]
    qcols = [i for i, h in enumerate(hdr) if re.match(r"[AB]\d\d\.", h)]
    resp = [r for r in rows[1:] if r[0] is not None]
    random.seed(SEED)
    for r in random.sample(resp, 3):
        text = "\n\n".join(f"[{hdr[i].split('.')[0]}] {r[i].strip()}" for i in qcols if isinstance(r[i], str) and r[i].strip())
        yield dict(key=f"york_{r[0]}", platform_genre="survey_open_text (elicited; not online)",
                   source_dataset="UKDA ReShare 856067, Experiences of Grief survey (CC BY 4.0)",
                   source_url="https://reshare.ukdataservice.ac.uk/856067/", source_record_id=f"Respondent {r[0]}",
                   retrieval_route="open download of xlsx; fixed-seed random draw of 3 from 235 respondents",
                   publication_date="2020-06/2021-02 (collection window)", deceased=str(r[5]),
                   context=f"40 question prompts; age band, gender, nationality, past/present grief fields; nationality field = {r[3]}",
                   population=f"self-reported nationality: {r[3]}", reuse="CC BY 4.0; participants consented to public release",
                   retain=True, text=text)


def hinemo_items():
    z = zipfile.ZipFile(str(SAMPLES / "zenodo_22041925" / "hinemo9.zip"))
    name = next(n for n in z.namelist() if n.endswith("data/full.jsonl"))
    recs = [json.loads(l) for l in io.TextIOWrapper(z.open(name), encoding="utf-8")]
    hits = [r for r in recs if bereavement_screen(r["text"])["hit"]]
    random.seed(SEED)
    for variety, k in (("Hindi", 2), ("Hinglish", 2), ("English", 2)):
        pool = [r for r in hits if r["language_label"] == variety]
        random.shuffle(pool)
        for r in pool[:k]:
            yield dict(key=f"hinemo_{r['id']}", platform_genre="youtube_comment (reused dataset)",
                       source_dataset="HinEmo-9 v1.0.1, Zenodo 10.5281/zenodo.22041925",
                       source_url="https://zenodo.org/records/22041925", source_record_id=r["id"],
                       retrieval_route=f"open download; broad bereavement screen over 30,436 comments (13 hits); dataset variety label={variety}; genre seed={r['genre']}",
                       publication_date="", deceased="", context="none: no video ID, thread, date or author in release; names masked as [NAME]/[USER]",
                       population="unknown", reuse="CC BY 4.0 on curation/annotations; underlying comment text belongs to commenters (YouTube ToS)",
                       retain=True, text=r["text"])


def blog_items():
    ext = {}
    p = ROOT / "data" / "interim" / "blogs_extracted.jsonl"
    if p.exists():
        for line in p.open(encoding="utf-8"):
            d = json.loads(line)
            ext[d["url"]] = d
    for url in SEED_BLOGS:
        d = ext[url]
        yield dict(key=d["doc_id"], platform_genre="blog_or_longform_web", source_dataset="", source_url=url,
                   source_record_id=d["doc_id"], retrieval_route="web search -> URL verified by opening -> collect_blogs.py (robots.txt honoured) -> trafilatura main-body extraction",
                   publication_date=d.get("publication_date") or "", deceased=(d.get("candidate") or {}).get("deceased_relation_as_stated", ""),
                   context=f"full article body; title; domain={d['domain']}; author grouped as {d.get('author_group')}",
                   population=(d.get("candidate") or {}).get("indian_context_evidence", "unknown") or "unknown",
                   reuse="all rights reserved by author/site unless stated; local research copy only, not redistributable; excerpt <= 300 chars in CSV",
                   retain=True, text=d["text"], collected_at=d["collected_at"])


def main():
    TEXTS.mkdir(parents=True, exist_ok=True)
    rows, n = [], 0
    for item in list(york_items()) + list(hinemo_items()) + list(blog_items()):
        n += 1
        sid = f"seed_{n:02d}"
        text = normalize_for_analysis(item["text"])
        (TEXTS / f"{sid}.txt").write_text(text, encoding="utf-8")
        lang, _ = detect_language(text)
        rv = MACHINE_REVIEW.get(item["key"], {})
        rows.append({
            "seed_id": sid, "platform_genre": item["platform_genre"], "source_dataset": item["source_dataset"],
            "source_url": item["source_url"], "source_record_id": item["source_record_id"],
            "retrieval_route": item["retrieval_route"], "collected_at": item.get("collected_at") or now_iso(),
            "publication_date": item["publication_date"], "language_provisional": lang,
            "language_machine_reviewed": rv.get("language", ""), "n_words": word_count(text),
            "message_type_machine_reviewed": rv.get("message_type", ""), "eligibility_machine_reviewed": rv.get("eligibility", ""),
            "deceased_relation_as_stated": rv.get("deceased", item["deceased"]), "context_available": item["context"],
            "population_evidence": item["population"], "reuse_terms": item["reuse"], "text_retained": item["retain"],
            "text_path": f"data/seed/texts/{sid}.txt",
            "text_excerpt": text[:300].replace("\n", " ") if len(text) > 300 else text.replace("\n", " "),
            "dedup_key": dedup_key(text), "review_status": "machine_reviewed_provisional; human_review=none",
            "machine_note": rv.get("note", "")})
    with (ROOT / "docs" / "seed_corpus.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "seed rows written; unreviewed keys:", [r["seed_id"] for r in rows if not r["message_type_machine_reviewed"]])
    for r in rows:
        print(r["seed_id"], r["source_record_id"], r["language_provisional"], r["n_words"], sep=" | ")


if __name__ == "__main__":
    main()
