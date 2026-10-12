#!/usr/bin/env python3
from __future__ import annotations
import argparse, math, pathlib, sys
from collections import Counter
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lexutil import read_corpus, read_lexicon, occurrences, tokens, TOKEN_RE


def unigrams(corpus: list[dict], lang_set: set[str]) -> Counter:
    c: Counter = Counter()
    for r in corpus:
        if r["lang"] in lang_set:
            c.update(t.lower() for t in tokens(r["text"]))
    return c


def window_tokens(text: str, start: int, end: int, w: int) -> list[str]:
    spans = [(m.start(), m.end(), m.group(0).lower()) for m in TOKEN_RE.finditer(text)]
    left = [t for s, e, t in spans if e <= start][-w:]
    right = [t for s, e, t in spans if s >= end][:w]
    return left + right


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicon", required=True); ap.add_argument("--clean-dir", required=True)
    ap.add_argument("--out", default="grounding.md"); ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--min-count", type=int, default=5); ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()

    corpus = list(read_corpus(pathlib.Path(a.clean_dir), langs=("hi", "hi_roman", "mixed", "en")))
    by_id = {r["record_id"]: r for r in corpus}
    bg = {"hi": unigrams(corpus, {"hi", "hi_roman", "mixed"}), "en": unigrams(corpus, {"en"})}
    N = {k: sum(v.values()) for k, v in bg.items()}
    out = ["# Grounding: PMI collocates and top contexts per entry\n",
           "_Corpus evidence beside the explication. Nothing here defines meaning._\n"]
    for e in read_lexicon(pathlib.Path(a.lexicon)):
        occs = occurrences(e, corpus, window_chars=200)
        out.append(f"\n## {e['entry_id']} — {e['headword']}  ({e['lang']}, n_matches = {len(occs)})\n")
        out.append("**Explication (from lexicon):**\n\n```\n" + (e.get("nsm_explication") or "(none yet)") + "\n```\n")
        if not occs:
            out.append("_No corpus matches; entry is unattested in the current corpus._\n"); continue
        win: Counter = Counter(); per_occ = []
        for o in occs:
            text = by_id[o["record_id"]]["text"]
            wt = window_tokens(text, o["start"], o["end"], a.window)
            win.update(wt); per_occ.append((o, wt))
        W, bgc, n = sum(win.values()), bg[e["lang"]], N[e["lang"]]
        pmi = {w: math.log2((c / W) / (bgc[w] / n)) for w, c in win.items()
               if c >= a.min_count and bgc.get(w)}
        top = sorted(pmi.items(), key=lambda kv: -kv[1])[: a.top]
        out.append("**Collocates (±%d, count ≥ %d):** " % (a.window, a.min_count) +
                   (", ".join(f"{w} ({v:.2f}, n={win[w]})" for w, v in top) or "_none reach min_count_") + "\n")
        scored = sorted(per_occ, key=lambda p: -sum(max(pmi.get(t, 0.0), 0.0) for t in p[1]))[:10]
        out.append("**Top contexts (by summed positive PMI of window tokens):**\n")
        for i, (o, _) in enumerate(scored, 1):
            out.append(f"{i}. `{o['record_id']}` …{o['context'].replace(chr(10), ' ')}…")
        out.append("")
    pathlib.Path(a.out).write_text("\n".join(out), encoding="utf-8")
    print(f"grounding for lexicon -> {a.out}")


if __name__ == "__main__":
    main()
