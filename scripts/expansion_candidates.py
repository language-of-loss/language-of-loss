import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.clean import clean_doc_text
from griefcorpus.textutil import bereavement_screen

V11_FILES = {"blog_candidates_v11_bilingual.jsonl"}
OUT = ROOT / "docs" / "expansion_candidates_2026-10.csv"
LANG2 = {"devanagari_hindi": "hi", "english": "en", "romanized_hindi": "hi-Latn", "mixed_hi_en": "mixed"}


def main():
    merged = [json.loads(l) for l in (ROOT / "data" / "clean" / "blogs_merged.jsonl").open(encoding="utf-8")]
    known_urls = {r["source_url"].rstrip("/") for r in merged}
    known_text = {hashlib.sha1(r["text_clean"][:2000].encode()).hexdigest() for r in merged}
    log = {}
    for l in (ROOT / "data" / "raw" / "blogs" / "fetch_log.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        if r.get("candidate_file") in V11_FILES:
            log[r["doc_id"]] = r
    rows, stats = [], Counter(fetch_attempts=len(log))
    stats.update(f"fetch_{r['status']}" for r in log.values())
    for l in (ROOT / "data" / "interim" / "blogs_extracted.jsonl").open(encoding="utf-8"):
        d = json.loads(l)
        if d["doc_id"] not in log:
            continue
        text, _ = clean_doc_text(d["text"])
        lang = LANG2.get(d["lang_provisional"], d["lang_provisional"])
        scr = bereavement_screen(text)
        checks = []
        if d["n_words"] < 80:
            checks.append("short_lt80w")
        if lang not in ("hi", "en"):
            checks.append(f"lang_{lang}")
        if d["url"].rstrip("/") in known_urls:
            checks.append("url_already_in_corpus")
        if hashlib.sha1(text[:2000].encode()).hexdigest() in known_text:
            checks.append("text_already_in_corpus")
        if not scr["hit"]:
            checks.append("screen_miss")
        passed = not checks
        stats[f"{lang}_passed" if passed else f"{lang}_failed"] += 1
        rows.append(dict(record_id=f"blogs:{d['doc_id']}", lang=lang, source=d["domain"], url=d["url"],
                         n_words=d["n_words"], screen_score=(scr["n_kin"] + scr["n_death"]) if scr["hit"] else 0,
                         screen_side=scr["side"] or "", automatic_checks="pass" if passed else ";".join(checks),
                         found_by=(d.get("candidate") or {}).get("notes", ""), first_300_chars=text[:300].replace("\n", " "),
                         reviewer_eligible="", reviewer_type="", reviewer_note=""))
    rows.sort(key=lambda r: (-r["screen_score"], r["lang"], r["record_id"]))
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["record_id"])
        w.writeheader()
        w.writerows(rows)
    print(dict(stats))
    print(f"{len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
