#!/usr/bin/env python3
from __future__ import annotations
import argparse, pathlib, sys
import numpy as np, torch
from sklearn.cluster import HDBSCAN, AgglomerativeClustering
from transformers import AutoModel, AutoTokenizer
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lexutil import read_corpus, read_lexicon, occurrences, write_csv

MODEL = "google/muril-base-cased"
N_LAST = 4
COLS = ["entry_id", "headword", "cluster", "n_in_cluster", "example_rank",
        "record_id", "context", "sense_label", "keep"]


def embed_spans(tok, model, occs: list[dict]) -> np.ndarray:
    vecs = []
    for o in occs:
        enc = tok(o["context"], return_tensors="pt", truncation=True, max_length=256,
                  return_offsets_mapping=True)
        offsets = enc.pop("offset_mapping")[0]
        with torch.no_grad():
            hs = model(**enc, output_hidden_states=True).hidden_states
        h = torch.stack([x[0] for x in hs[-N_LAST:]]).mean(0)
        s, e = o["start"] - o["ctx_start"], o["end"] - o["ctx_start"]
        idx = [i for i, (a, b) in enumerate(offsets.tolist()) if b > s and a < e and b > a]
        v = h[idx].mean(0) if idx else h.mean(0)
        vecs.append((v / v.norm()).numpy())
    return np.vstack(vecs)


def cluster(X: np.ndarray) -> np.ndarray:
    if len(X) >= 10:
        lab = HDBSCAN(min_cluster_size=5, metric="euclidean").fit_predict(X)
        if (lab >= 0).sum() >= 5:
            return lab
    return AgglomerativeClustering(n_clusters=None, distance_threshold=0.35,
                                   metric="cosine", linkage="average").fit_predict(X)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicon", required=True); ap.add_argument("--clean-dir", required=True)
    ap.add_argument("--out", default="senses.csv"); ap.add_argument("--max-occ", type=int, default=400)
    ap.add_argument("--examples", type=int, default=5); ap.add_argument("--model", default=MODEL)
    a = ap.parse_args()

    corpus = list(read_corpus(pathlib.Path(a.clean_dir), langs=("hi", "hi_roman", "mixed", "en")))
    tok, model = AutoTokenizer.from_pretrained(a.model), AutoModel.from_pretrained(a.model).eval()
    rows, rng = [], np.random.default_rng(20260926)
    for e in read_lexicon(pathlib.Path(a.lexicon)):
        occs = occurrences(e, corpus)
        if len(occs) > a.max_occ:
            occs = [occs[i] for i in sorted(rng.choice(len(occs), a.max_occ, replace=False))]
        if len(occs) < 2:
            print(f"[{e['entry_id']}] {len(occs)} occurrence(s); nothing to cluster"); continue
        labels = cluster(embed_spans(tok, model, occs))
        print(f"\n=== {e['entry_id']} {e['headword']}  n={len(occs)}  clusters={len(set(labels) - {-1})}")
        for c in sorted(set(labels)):
            members = [o for o, l in zip(occs, labels) if l == c]
            name = "noise" if c == -1 else f"c{c}"
            print(f"--- {name} (n={len(members)})")
            for k, o in enumerate(members[: a.examples], 1):
                s0, e0 = o["start"] - o["ctx_start"], o["end"] - o["ctx_start"]
                ctx = (o["context"][:s0] + "⟦" + o["context"][s0:e0] + "⟧" + o["context"][e0:]).replace("\n", " ")
                print(f"  {k}. …{ctx}…")
                rows.append({"entry_id": e["entry_id"], "headword": e["headword"], "cluster": name,
                             "n_in_cluster": len(members), "example_rank": k,
                             "record_id": o["record_id"], "context": ctx, "sense_label": "", "keep": ""})
    write_csv(pathlib.Path(a.out), rows, COLS)
    print(f"\n{len(rows)} example rows -> {a.out}")


if __name__ == "__main__":
    main()
