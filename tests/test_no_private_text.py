import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEVA_RUN = re.compile(r"[ऀ-ॿ]+(?:[\sऀ-ॿ,'’\-]+[ऀ-ॿ]+)*")
SENTENCE_END = re.compile(r"[।.?!\n|]")
MAX_WORDS = 12
OWN_HINDI = {"docs/reader_study/consent.md"}
SHEETS_WITH_PROVENANCE = ["docs/review_master_2026-10.csv", "data/annotation/gold_sheet_v1_coder1.csv",
                          "data/annotation/meta_review.csv", "data/annotation/audit_rating_sheet_r1.csv"]


def tracked_docs():
    out = subprocess.run(["git", "ls-files", "docs"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / f for f in out.split()]


def long_devanagari_sentences(text):
    return [s for m in DEVA_RUN.finditer(text) for s in SENTENCE_END.split(m.group(0)) if len(s.split()) > MAX_WORDS]


def test_detector_catches_a_long_hindi_sentence():
    long = "पापा के जाने के बाद हम सब बहुत दिनों तक घर में चुपचाप बैठे रहे और किसी से कुछ नहीं कहा"
    assert long_devanagari_sentences(long) and not long_devanagari_sentences("मुझे बहुत दुख हुआ। याद आती है।")


def test_no_tracked_doc_carries_corpus_text():
    bad = []
    for f in tracked_docs():
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        header = text.splitlines()[0] if text else ""
        if f.suffix == ".csv" and "clause_text" in [h.strip() for h in header.split(",")]:
            bad.append(f"{f.relative_to(ROOT)}: clause_text column")
        n = len(long_devanagari_sentences(text))
        if n and str(f.relative_to(ROOT)) not in OWN_HINDI:
            bad.append(f"{f.relative_to(ROOT)}: {n} Devanagari sentence(s) > {MAX_WORDS} words")
    assert not bad, bad


def test_reviewed_prefill_sheets_stay_ignored():
    for f in SHEETS_WITH_PROVENANCE:
        assert subprocess.run(["git", "check-ignore", "-q", f], cwd=ROOT).returncode == 0, f
