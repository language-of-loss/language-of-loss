"""Optional (not on the core path): the A1 parts that are not output 8 of `make core`."""
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from translation_bias import (LM, NRC_PATH, ROOT, load_hsl, load_nrc, norm, parser, phrase_detector,
                              prepare, recall_rows, score_items, sha256, write_csv, words_of)

OUT = ROOT / "results" / "optional"
MODELS = dict(
    nllb=dict(repo="facebook/nllb-200-distilled-600M", revision="f8d333a098d19b4fd9a8b18f94170487ad3f821d",
              licence="CC-BY-NC-4.0"),
    opus_hi_en=dict(repo="Helsinki-NLP/opus-mt-hi-en", revision="a7d96a16729f812578bd55e7366147beda625d86",
                    licence="Apache-2.0"),
    opus_en_hi=dict(repo="Helsinki-NLP/opus-mt-en-hi", revision="75d7f7c9232b2891c7d65fe4ef635616c72be867",
                    licence="Apache-2.0"),
    minilm=dict(repo="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                revision="e8f8c211226b894fcb81acc59f3b34ba3efd5f42", licence="Apache-2.0"))


def english_headwords(lexicon_rows):
    out = set()
    for r in lexicon_rows:
        if r["lang"] != "en":
            continue
        for v in r["headword_en"].split("/"):
            v = re.sub(r"\([^)]*\)", " ", v).strip().lower()
            if v and not LM.PLACEHOLDER.search(v) and len(v.split()) <= 3:
                out.add(v)
    return sorted(out)


def wordnet_expansion(hindi_words, iwn=None):
    if iwn is None:
        from pyiwn import IndoWordNet, Language
        iwn = IndoWordNet(lang=Language.HINDI)
    out = set()
    for w in hindi_words:
        try:
            syns = iwn.synsets(w)
        except Exception:
            syns = []
        for s in syns:
            out |= {norm(l.replace("_", " ")) for l in s.lemma_names()}
        out.add(norm(w))
    return {x for x in out if x}

def construction_features(text, spec=None):
    import flags as F
    spec = spec or F.load_spec()
    return {name: bool(rx.search(text)) for name, rx, _ in spec["regex"]["hi"]} | {
        "dative_pronoun": any(norm(w) in {norm(p) for p in spec["dative"]["pronouns"]} for w in words_of(text))}

def component_recall(items, B=2000, seed=20261010):
    comps = sorted({c for it in items for c in it["native"] | it["mt"]})
    rng = np.random.default_rng(seed)
    rows = []
    for c in comps:
        ref = np.array([c in it["native"] for it in items])
        hit = np.array([c in it["mt"] for it in items])
        n = int(ref.sum())
        est = float(hit[ref].mean()) if n else math.nan
        reps = []
        for _ in range(B if n else 0):
            idx = rng.integers(0, len(items), len(items))
            r, h = ref[idx], hit[idx]
            if r.sum():
                reps.append(h[r].mean())
        rows.append(dict(component=c, reference_items=n, mt_recall=est,
                         lo=float(np.percentile(reps, 2.5)) if reps else math.nan,
                         hi=float(np.percentile(reps, 97.5)) if reps else math.nan,
                         mt_only_items=int((hit & ~ref).sum()), n_items=len(items)))
    return rows


def stripped_table(originals, roundtrips):
    feats = sorted({f for s in originals + roundtrips for f in s})
    rows = []
    for f in feats:
        o = np.array([f in s for s in originals])
        r = np.array([f in s for s in roundtrips])
        n = int(o.sum())
        rows.append(dict(feature=f, original=n, kept=int((o & r).sum()), stripped=int((o & ~r).sum()),
                         added=int((~o & r).sum()), strip_rate=float((o & ~r).sum() / n) if n else math.nan))
    return rows


def topic_agreement(a, b):
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    return dict(ari=float(adjusted_rand_score(a, b)), nmi=float(normalized_mutual_info_score(a, b)),
                n_docs=len(a), topics_native=len(set(a)), topics_translated=len(set(b)),
                outliers_native=int(sum(x == -1 for x in a)), outliers_translated=int(sum(x == -1 for x in b)))

class Translator:

    def __init__(self, key):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        self.torch, self.key, spec = torch, key, MODELS[key]
        kw = dict(revision=spec["revision"])
        self.nllb = key == "nllb"
        self.tok = AutoTokenizer.from_pretrained(spec["repo"], **kw)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(spec["repo"], **kw).eval()

    def __call__(self, texts, src="hi", tgt="en", batch=8, beams=4):
        codes = {"hi": "hin_Deva", "en": "eng_Latn"}
        out = []
        for i in range(0, len(texts), batch):
            chunk = texts[i:i + batch]
            kw = {}
            if self.nllb:
                self.tok.src_lang = codes[src]
                kw["forced_bos_token_id"] = self.tok.convert_tokens_to_ids(codes[tgt])
            enc = self.tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=256)
            with self.torch.no_grad():
                gen = self.model.generate(**enc, num_beams=beams, max_new_tokens=192, **kw)
            out += self.tok.batch_decode(gen, skip_special_tokens=True)
        return out


def model_manifest(keys):
    from huggingface_hub.constants import HF_HUB_CACHE
    out = {}
    for k in keys:
        spec = MODELS[k]
        local = Path(HF_HUB_CACHE) / f"models--{spec['repo'].replace('/', '--')}" / "snapshots" / spec["revision"]
        files = {p.name: dict(bytes=p.stat().st_size, sha256=sha256(p)) for p in sorted(local.rglob("*"))
                 if p.is_file() and p.suffix in (".bin", ".safetensors", ".model", ".spm")}
        out[k] = dict(spec, files=files, total_bytes=sum(f["bytes"] for f in files.values()))
    return out


def run_topics(native_docs, translated_docs, seed=20261010):
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sentence_transformers import SentenceTransformer
    from umap import UMAP
    emb = SentenceTransformer(MODELS["minilm"]["repo"], revision=MODELS["minilm"]["revision"])
    assign = []
    for docs in (native_docs, translated_docs):
        n = len(docs)
        model = BERTopic(embedding_model=emb, umap_model=UMAP(n_neighbors=min(15, max(2, n // 5)), n_components=5,
                                                             min_dist=0.0, metric="cosine", random_state=seed),
                         hdbscan_model=HDBSCAN(min_cluster_size=max(3, n // 15), prediction_data=True),
                         min_topic_size=max(3, n // 15), calculate_probabilities=False, verbose=False)
        topics, _ = model.fit_transform(docs)
        assign.append(list(topics))
    return dict(**topic_agreement(*assign), embedding=MODELS["minilm"]["repo"],
                note="documents = the sampled clauses in the dry run; texts on the gold run")


def run(args):
    out_res, out_priv = Path(args.results), Path(args.private)
    out_priv.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    prep = prepare(args)
    texts, status = prep["texts"], prep["status"]
    nllb = Translator("nllb")
    hi_en = nllb(texts, "hi", "en")
    nrc, hsl = load_nrc(), load_hsl()
    heads = english_headwords(prep["lexicon_rows"])
    wn_words = wordnet_expansion(nllb(heads, "en", "hi"))
    detectors = {"wordnet": phrase_detector(wn_words)}
    if nrc is not None:
        detectors["nrc_hi"] = phrase_detector(set(nrc))
    if hsl is not None:
        detectors["hsl"] = phrase_detector(set(hsl))
    items, native_scores = score_items(prep, detectors)
    write_csv(out_res / "a1_resource_recall_wordnet.csv",
              recall_rows(items, ["lexicon"] + sorted(detectors), args.B, args.seed), status)
    scorer = prep["scorer"]
    mt_scores = [scorer.score(t, "en") for t in hi_en]
    comp_items = [dict(native=n["comps"], mt=m["comps"]) for n, m in zip(native_scores, mt_scores)]
    write_csv(out_res / "a1_component_recall.csv", component_recall(comp_items, args.B, args.seed), status)
    opus_he, opus_eh = Translator("opus_hi_en"), Translator("opus_en_hi")
    rt = {"nllb": nllb(hi_en, "en", "hi"), "opus": opus_eh(opus_he(texts))}

    def featureset(text, s):
        return ({f"entry:{e}" for e in s["entries"]} | {f"comp:{c}" for c in s["comps"]}
                | {f"construction:{k}" for k, v in construction_features(text).items() if v})
    orig = [featureset(t, s) for t, s in zip(texts, native_scores)]
    rt_rows = []
    for system, outs in rt.items():
        back = [featureset(t, scorer.score(t, "hi")) for t in outs]
        rt_rows += [dict(system=system, **r) for r in stripped_table(orig, back)]
    write_csv(out_res / "a1_roundtrip_stripped.csv", rt_rows, status)
    write_csv(out_res / "a1_topic_agreement.csv", [run_topics(texts, hi_en, args.seed)], status)
    with open(out_priv / "translations.jsonl", "w", encoding="utf-8") as fh:
        for (c, _), en, rn, ro in zip(prep["picked"], hi_en, rt["nllb"], rt["opus"]):
            fh.write(json.dumps(dict(clause_id=c["clause_id"], hi=c["clause_text"], nllb_en=en, nllb_rt=rn,
                                     opus_rt=ro), ensure_ascii=False) + "\n")
    manifest = dict(status=status, run=time.strftime("%Y-%m-%d %H:%M"), seconds=round(time.time() - t0),
                    n_items=len(items), resources=dict(nrc_hi=dict(entries=len(nrc or {}),
                                                                   sha256=sha256(NRC_PATH) if NRC_PATH.exists() else None),
                                                       hsl="unavailable" if hsl is None else len(hsl),
                                                       wordnet=dict(english_headwords=len(heads),
                                                                    hindi_words=len(wn_words))),
                    models=model_manifest(["nllb", "opus_hi_en", "opus_en_hi", "minilm"]))
    (out_priv / "manifest_optional.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                                     encoding="utf-8")
    return manifest


def main(argv=None):
    ap = parser(__doc__)
    ap.set_defaults(results=str(OUT))
    args = ap.parse_args(argv)
    if not args.dry_run and not args.gold:
        ap.error("--gold is required unless --dry-run (no human annotation exists yet)")
    m = run(args)
    print(json.dumps({k: m[k] for k in ("status", "seconds", "n_items")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
