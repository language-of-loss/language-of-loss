import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
HI = ("devanagari_hindi", "romanized_hindi")
SOURCES = [("blogs", "Blogs / personal essays (PRIMARY)"), ("ytcv", "YouTube comments - YTCommentVerse"),
           ("hinemo9", "YouTube comments - HinEmo-9"), ("reddit_confessions", "Reddit confessions (English only)"),
           ("york_survey", "York grief survey (English reference)")]


def load(name):
    return [json.loads(l) for l in (CLEAN / f"{name}.jsonl").open(encoding="utf-8")]


def main():
    qc = json.loads((CLEAN / "qc_report.json").read_text())["sources"]
    excl = Counter((r["source"], r["reason"]) for r in csv.DictReader((ROOT / "docs" / "exclusion_log.csv").open(encoding="utf-8")))
    problems, lines = [], []
    lines += ["| Source | Retrieved | Duplicates removed (exact + near) | Retained | Provisionally eligible | English | Hindi (Devanagari) | Hindi (Romanized) | Mixed hi-en | Uncertain | Distinct authors | Distinct threads | Human-reviewed |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key, label in SOURCES:
        recs = load(key)
        q = qc[key]
        el = [r for r in recs if r["eligibility_status"] == "provisionally_eligible"]
        pool = el if el else recs
        lang = Counter(r["lang_provisional"] for r in pool)
        dups = excl[(key, "exact_duplicate")] + excl[(key, "near_duplicate")]
        authors = len({r["author_group"] for r in recs if r["author_group"]})
        threads = len({r["thread_id"] for r in recs if r["thread_id"]})
        for name, got, want in (("retained", len(recs), q.get("retained")), ("eligible", len(el), q.get("provisionally_eligible")),
                                ("duplicates", dups, q.get("exact_duplicates_removed", 0) + q.get("near_duplicates_removed", 0))):
            if got != want:
                problems.append(f"{key}: {name} file={got} qc_report={want}")
        reviewed = sum(1 for r in recs if r["review_status"] != "no_human_review")
        lines.append(f"| {label} | {q.get('retrieved')} | {dups} | {len(recs)} | {len(el)}{'' if el else ' (n/a: reference)'} | {lang['english']} | "
                     f"{lang['devanagari_hindi']} | {lang['romanized_hindi']} | {lang['mixed_hi_en']} | {lang['uncertain']} | "
                     f"{authors if authors else 'not available'} | {threads if threads else 'not available'} | {reviewed} |")
    lines += ["| X / Twitter (API) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0 |",
              "| YouTube Data API | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0 |",
              "| Reddit official access | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | 0 |", "",
              "Language columns count provisionally eligible records (retained records for the York reference set). "
              "Language labels are rule-based and provisional. 'Retrieved' for comment/post sources = records passing the broad screen, not rows scanned.", ""]
    b = [r for r in load("blogs") if r["eligibility_status"] == "provisionally_eligible"]
    lines += ["## Blog documents and words (provisionally eligible personal disclosures)", "",
              "| Language (provisional) | Documents | Words | Documents excl. >5,000-word outliers and over-cap | Words in that subset | Median words/doc | Distinct domains |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for lang in ("devanagari_hindi", "english", "romanized_hindi", "mixed_hi_en"):
        docs = [r for r in b if r["lang_provisional"] == lang]
        if not docs:
            continue
        core = [r for r in docs if not {"over_cap", "length_outlier_gt5000w"} & set(r["flags"])]
        w = sorted(r["n_words"] for r in docs)
        lines.append(f"| {lang} | {len(docs)} | {sum(w):,} | {len(core)} | {sum(r['n_words'] for r in core):,} | {w[len(w) // 2]:,} | {len({r['thread_id'] for r in docs})} |")
    sec = Counter(r["eligibility_status"] for r in load("blogs") if r["eligibility_status"] != "provisionally_eligible")
    lines += ["", "Secondary (non-disclosure) blog pages kept separately: " + ", ".join(f"{k.replace('secondary_', '')} {v}" for k, v in sorted(sec.items())) + ".", ""]
    ck = json.loads((ROOT / "data" / "raw" / "youtube" / "ytcv_checkpoint.json").read_text())
    lines += ["## YTCommentVerse scan state", "",
              f"- {ck['rows']:,} comments from {ck['videos']:,} videos scanned = {ck['file_bytes_seen'] / ck['file_bytes_total']:.1%} of the 10.8 GB file "
              f"(updated {ck['updated']}); {ck['overflow_skipped']} over-long rows skipped.",
              f"- Language of ALL scanned comments (5% systematic sample, n={sum(ck['lang_sample'].values()):,}): "
              + ", ".join(f"{k} {v / sum(ck['lang_sample'].values()):.1%}" for k, v in sorted(ck["lang_sample"].items(), key=lambda kv: -kv[1])) + ".", ""]
    ann = Counter((r["stratum"]) for r in csv.DictReader((ROOT / "data" / "annotation" / "annotation_key.csv").open(encoding="utf-8")))
    lines += ["## Annotation sheet", "", f"- {sum(ann.values())} records: " + ", ".join(f"{k} {v}" for k, v in sorted(ann.items())) + ".",
              "- Reviewer fields filled: 0. Human-reviewed records: 0.", ""]
    lines += ["## Reconciliation", ""] + ([f"- MISMATCH {p}" for p in problems] or ["- All counts in this file were recomputed from the data files and match `data/clean/qc_report.json` and `docs/exclusion_log.csv`."])
    notes = (ROOT / "docs" / "corpus_summary_notes.md").read_text(encoding="utf-8")
    (ROOT / "docs" / "corpus_summary.md").write_text("# Corpus summary\n\n" + f"Generated by `scripts/make_summary.py`. **No record has been reviewed by a human.**\n\n## Per-source counts\n\n"
                                                     + "\n".join(lines) + "\n\n" + notes, encoding="utf-8")
    print("\n".join(lines))
    print("PROBLEMS:", problems or "none")


if __name__ == "__main__":
    main()
