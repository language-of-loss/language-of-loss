#!/usr/bin/env python3
from __future__ import annotations
import argparse, pathlib, sys
import numpy as np
from gensim.models import KeyedVectors
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lexutil import read_lexicon, tokens, write_csv

COLS = ["entry_id", "lang", "headword", "rank", "candidate", "cosine", "accept", "note"]


def load(path: str, limit: int) -> KeyedVectors:
    return KeyedVectors.load_word2vec_format(path, binary=False, limit=limit)


def entry_vector(kv: KeyedVectors, headword: str) -> tuple[np.ndarray | None, str]:
    toks = tokens(headword)
    hit = [t for t in toks if t in kv.key_to_index]
    if not hit:
        return None, "headword tokens not in vocabulary"
    v = np.mean([kv[t] for t in hit], axis=0)
    note = "" if len(hit) == len(toks) else f"partial: {len(hit)}/{len(toks)} tokens found"
    return v, note


def neighbours(kv: KeyedVectors, vec: np.ndarray, k: int, exclude: set[str]):
    return [(w, s) for w, s in kv.similar_by_vector(vec, topn=k + len(exclude))
            if w not in exclude][:k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicon", required=True); ap.add_argument("--hi-vec", required=True)
    ap.add_argument("--en-vec", required=True); ap.add_argument("--out", default="candidates.csv")
    ap.add_argument("--k", type=int, default=30); ap.add_argument("--limit", type=int, default=500_000)
    a = ap.parse_args()

    lex = read_lexicon(pathlib.Path(a.lexicon))
    spaces = {"hi": load(a.hi_vec, a.limit), "en": load(a.en_vec, a.limit)}
    rows = []
    for e in lex:
        kv = spaces.get(e["lang"])
        if kv is None:
            continue
        forms = [e["headword"]]
        if e["lang"] == "hi":
            forms += [f.strip() for f in (e.get("headword_roman_variants") or "").split(";") if f.strip()]
        seen: set[str] = set(tokens(" ".join(forms)))
        for form in forms:
            vec, note = entry_vector(kv, form)
            if vec is None:
                rows.append({"entry_id": e["entry_id"], "lang": e["lang"], "headword": form,
                             "rank": "", "candidate": "", "cosine": "", "accept": "", "note": note})
                continue
            for i, (w, s) in enumerate(neighbours(kv, vec, a.k, seen), 1):
                rows.append({"entry_id": e["entry_id"], "lang": e["lang"], "headword": form,
                             "rank": i, "candidate": w, "cosine": f"{s:.4f}", "accept": "", "note": note})
            break
    write_csv(pathlib.Path(a.out), rows, COLS)
    print(f"{len(rows)} candidate rows for {len(lex)} entries -> {a.out}")


if __name__ == "__main__":
    main()
