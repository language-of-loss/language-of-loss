from __future__ import annotations
import csv, json, pathlib, re, unicodedata
from typing import Iterator

DEVA = "ऀ-ॣ०-९ॱ-ॿ‌‍"
WORD = DEVA + "A-Za-z0-9_'"
DEVA_L = f"(?<![{WORD}])"
DEVA_R = f"(?![{WORD}])"
TOKEN_RE = re.compile(f"[{WORD}]+")

LANG_MAP = {"devanagari_hindi": "hi", "romanized_hindi": "hi_roman",
            "mixed_hi_en": "mixed", "english": "en", "uncertain": "unk"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def bounded(pattern: str) -> re.Pattern:
    return re.compile(DEVA_L + "(?:" + pattern + ")" + DEVA_R, re.IGNORECASE)


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(nfc(text))


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[।॥.!?])\s+|\n+", nfc(text))
    return [p.strip() for p in parts if p and p.strip()]


def read_corpus(clean_dir: pathlib.Path, langs=("hi", "en"),
                sources=("blogs", "ytcv", "hinemo9", "reddit_confessions", "york_survey")
                ) -> Iterator[dict]:
    for src in sources:
        p = clean_dir / f"{src}.jsonl"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                lang = LANG_MAP.get(r.get("lang_provisional"), "unk")
                if lang in langs:
                    yield {"record_id": r["record_id"], "source": src,
                           "lang": lang, "text": nfc(r.get("text_clean", ""))}


def read_lexicon(path: pathlib.Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["lang"] = (r.get("lang") or r["entry_id"].split("-")[1]).lower()
        r["headword"] = r.get("headword_deva") or r.get("headword_en") or ""
        r["counterpart_entry_id"] = r.get("counterpart_entry_id") or r.get("counterpart") or ""
        pat = r.get("pattern") or re.escape(r["headword"])
        r["_re"] = re.compile(pat, re.IGNORECASE) if pat.startswith("(?<!") else bounded(pat)
    return rows


def occurrences(entry: dict, corpus: list[dict], window_chars: int = 160
                ) -> list[dict]:
    out = []
    for rec in corpus:
        if rec["lang"] != entry["lang"] and not (
                entry["lang"] == "hi" and rec["lang"] in ("hi_roman", "mixed")):
            continue
        for m in entry["_re"].finditer(rec["text"]):
            a, b = max(0, m.start() - window_chars), min(len(rec["text"]), m.end() + window_chars)
            out.append({"record_id": rec["record_id"], "start": m.start(), "end": m.end(),
                        "match": m.group(0), "context": rec["text"][a:b],
                        "ctx_start": a})
    return out


def write_csv(path: pathlib.Path, rows: list[dict], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
