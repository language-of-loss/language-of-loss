#!/usr/bin/env python3
from __future__ import annotations
import argparse, pathlib, sys
import numpy as np
from sentence_transformers import SentenceTransformer
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lexutil import read_lexicon, write_csv

COLS = ["hi_entry_id", "hi_headword", "en_entry_id", "en_headword", "counterpart_source",
        "overlap", "cosine", "silently_translatable"]


def texts(entries: list[dict], use_examples: bool, ex_col: str) -> list[str]:
    return [e["headword"] + (f" . {e.get(ex_col, '')}" if use_examples and e.get(ex_col) else "")
            for e in entries]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicon", required=True); ap.add_argument("--out", default="alignment.csv")
    ap.add_argument("--threshold", type=float, default=0.6); ap.add_argument("--use-examples", action="store_true")
    a = ap.parse_args()

    lex = read_lexicon(pathlib.Path(a.lexicon))
    hi = [e for e in lex if e["lang"] == "hi"]; en = [e for e in lex if e["lang"] == "en"]
    if not hi or not en:
        sys.exit("need both Hindi and English entries")
    model = SentenceTransformer("sentence-transformers/LaBSE")
    H = model.encode(texts(hi, a.use_examples, "example_hi"), normalize_embeddings=True)
    E = model.encode(texts(en, a.use_examples, "example_en"), normalize_embeddings=True)
    S = H @ E.T
    en_index = {e["entry_id"]: i for i, e in enumerate(en)}

    rows = []
    for i, e in enumerate(hi):
        cp = (e.get("counterpart_entry_id") or "").strip()
        if cp and cp.lower() != "none" and cp in en_index:
            j, src = en_index[cp], "lexicon"
        else:
            j, src = int(np.argmax(S[i])), "nearest"
        cos = float(S[i, j]); overlap = (e.get("overlap") or "").strip().lower()
        rows.append({"hi_entry_id": e["entry_id"], "hi_headword": e["headword"],
                     "en_entry_id": en[j]["entry_id"], "en_headword": en[j]["headword"],
                     "counterpart_source": src, "overlap": overlap, "cosine": f"{cos:.4f}",
                     "silently_translatable": "Y" if overlap == "none" and cos > a.threshold else ""})
    write_csv(pathlib.Path(a.out), rows, COLS)

    none_rows = [r for r in rows if r["overlap"] == "none"]
    for t in (0.5, a.threshold, 0.7):
        k = sum(float(r["cosine"]) > t for r in none_rows)
        print(f"overlap=none entries: {len(none_rows)}; flagged at cosine > {t:.2f}: {k}")
    print(f"{len(rows)} rows -> {a.out}")


if __name__ == "__main__":
    main()
