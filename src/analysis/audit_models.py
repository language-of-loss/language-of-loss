"""Stage 12 prep, machine side of the audit: run two off-the-shelf models that claim Hindi coverage over every text."""
import argparse
import csv
import hashlib
import json
import time
import traceback
from pathlib import Path

import numpy as np

ELIGIBLE = "provisionally_eligible"
LANGS = {"devanagari_hindi": "hi", "english": "en"}
MODELS = [
    dict(key="xlm_emo", repo="MilaNLProc/xlm-emo-t", revision="a6ee7c9fad08d60204e7ae437d41d392381496f0",
         files=["config.json", "pytorch_model.bin", "sentencepiece.bpe.model", "tokenizer.json"], window=512),
    dict(key="muril_sent", repo="airzipm/sentiment-analysis-muril-v2",
         revision="5f61690dbad9163df7bb699753e33b734631fa87",
         files=["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json"], window=128),
]


def load_texts(path):
    out = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("eligibility_status") == ELIGIBLE and r.get("lang_provisional") in LANGS:
            out.append((r["record_id"], LANGS[r["lang_provisional"]], r.get("text_clean") or r.get("text_original") or ""))
    return out


def load_passages(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return [(r["passage_id"], r["lang"], r["passage_text"]) for r in csv.DictReader(fh)]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(spec):
    from huggingface_hub import snapshot_download
    local = snapshot_download(spec["repo"], revision=spec["revision"], allow_patterns=spec["files"])
    return local, {f: sha256(Path(local) / f) for f in spec["files"] if (Path(local) / f).exists()}


def device():
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"


def windows(ids, size):
    return [ids[i:i + size] for i in range(0, len(ids), size)] or [[]]


def score_texts(local, spec, texts, dev, batch=16):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(local)
    model = AutoModelForSequenceClassification.from_pretrained(local, use_safetensors=local_has_safetensors(local))
    model.to(dev).eval()
    labels = [model.config.id2label[i] for i in range(model.config.num_labels)]
    body = spec["window"] - 2
    for rid, lang, text in texts:
        ids = tok(text, add_special_tokens=False)["input_ids"]
        wins = windows(ids, body)
        probs, weights = [], []
        for k in range(0, len(wins), batch):
            chunk = [[tok.cls_token_id] + w + [tok.sep_token_id] for w in wins[k:k + batch]]
            enc = tok.pad({"input_ids": chunk}, return_tensors="pt")
            with torch.no_grad():
                logits = model(**{n: t.to(dev) for n, t in enc.items()}).logits
            probs.append(torch.softmax(logits.float(), -1).cpu().numpy())
            weights += [max(len(w), 1) for w in wins[k:k + batch]]
        p = np.vstack(probs)
        w = np.asarray(weights, float)
        mean = (p * w[:, None]).sum(0) / w.sum()
        share = np.bincount(p.argmax(1), minlength=len(labels)) / len(p)
        yield rid, lang, labels, mean, share, len(wins), len(ids)


def model_hash(file_hashes):
    return hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(file_hashes.items())).encode()).hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cached(cache_dir, score_fn=None):
    score_fn = score_fn or score_texts

    def score(local, spec, texts, dev):
        d = Path(cache_dir) / spec["key"] / spec["model_sha256"][:16]
        d.mkdir(parents=True, exist_ok=True)
        todo = [t for t in texts if not (d / f"{text_hash(t[2])}.json").exists()]
        by_id = {t[0]: t for t in todo}
        for rid, lang, labels, mean, share, nw, nt in (score_fn(local, spec, todo, dev) if todo else []):
            (d / f"{text_hash(by_id[rid][2])}.json").write_text(json.dumps(dict(
                labels=labels, mean=[float(x) for x in mean], share=[float(x) for x in share], n_windows=nw,
                n_tokens=nt)), encoding="utf-8")
        score.n_cached, score.n_scored = len(texts) - len(todo), len(todo)
        for rid, lang, text in texts:
            c = json.loads((d / f"{text_hash(text)}.json").read_text(encoding="utf-8"))
            yield rid, lang, c["labels"], np.array(c["mean"]), np.array(c["share"]), c["n_windows"], c["n_tokens"]
    return score


def load_calibration(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return [(r["calibration_id"], "hi", r["passage_text"]) for r in csv.DictReader(fh)]


def run_audit(args, dev, run_fn=None):
    run_fn = run_fn or run_model
    out = Path(args.audit_dir)
    out.mkdir(parents=True, exist_ok=True)
    sets = {"passage": load_passages(args.passages_file), "calibration": load_calibration(args.calibration_file)}
    manifest = dict(run=time.strftime("%Y-%m-%d %H:%M"), device=dev, cache=str(out / "cache"), models=[],
                    inputs={k: dict(path=v, sha256=sha256(v)) for k, v in
                            (("passages", args.passages_file), ("calibration", args.calibration_file))},
                    n=dict((k, len(v)) for k, v in sets.items()))
    rows = {k: [] for k in sets}
    for spec in (m for m in MODELS if m["key"] in args.models.split(",")):
        for unit, texts in sets.items():
            fn = cached(out / "cache")
            entry, model_rows = run_fn(spec, texts, dev, score_fn=fn)
            entry.update(unit=unit, n_cached=getattr(fn, "n_cached", None), n_scored=getattr(fn, "n_scored", None))
            manifest["models"].append(entry)
            idcol = "passage_id" if unit == "passage" else "calibration_id"
            rows[unit] += [{(idcol if k == "record_id" else k): v for k, v in r.items()} for r in model_rows]
            print(f"{spec['key']} {unit}: {entry['status']} ({entry['seconds']} s; cached {entry['n_cached']}, "
                  f"scored {entry['n_scored']})")
    for unit, name in (("passage", "passage_scores.csv"), ("calibration", "calibration_scores.csv")):
        fields = list(dict.fromkeys(k for r in rows[unit] for k in r))
        with open(out / name, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows[unit])
    import torch
    import transformers
    manifest.update(torch=torch.__version__, transformers=transformers.__version__)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    return manifest


def local_has_safetensors(local):
    return (Path(local) / "model.safetensors").exists()


def run_model(spec, texts, dev, fetch_fn=None, score_fn=None):
    fetch_fn, score_fn = fetch_fn or fetch, score_fn or score_texts
    entry = dict(key=spec["key"], repo=spec["repo"], revision=spec["revision"], window=spec["window"])
    t0, model_rows = time.time(), []
    try:
        local, hashes = fetch_fn(spec)
        entry["sha256"] = hashes
        entry["model_sha256"] = model_hash(hashes)
        labels = None
        for rid, lang, labels, mean, share, nw, nt in score_fn(local, dict(spec, model_sha256=entry["model_sha256"]),
                                                              texts, dev):
            row = dict(record_id=rid, lang=lang, model=spec["key"], model_id=spec["repo"],
                       revision=spec["revision"][:12], n_tokens=nt, n_windows=nw,
                       top_label=labels[int(mean.argmax())])
            row.update({f"p_{lab.lower()}": round(float(v), 5) for lab, v in zip(labels, mean)})
            row.update({f"win_share_{lab.lower()}": round(float(v), 4) for lab, v in zip(labels, share)})
            model_rows.append(row)
        entry.update(status="ok", labels=labels, n_scored=len(model_rows))
    except Exception as e:
        entry.update(status="failed", error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-2000:],
                     n_scored_before_failure=len(model_rows))
        print(f"{spec['key']} FAILED: {e}")
        model_rows = []
    entry["seconds"] = round(time.time() - t0, 1)
    return entry, model_rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default="data/clean/blogs_merged.jsonl")
    ap.add_argument("--out", default=None, help="default: data/processed/audit_scores.csv, or "
                                                "audit_passage_scores.csv with --passages")
    ap.add_argument("--passages", default=None, help="score the audit passages (audit_passages.csv) instead of texts")
    ap.add_argument("--models", default="xlm_emo,muril_sent")
    ap.add_argument("--audit", action="store_true",
                    help="output 5: score the rated passages and the BRIGHTER calibration items through the cache "
                         "-> data/processed/audit/{passage_scores,calibration_scores}.csv, manifest.json")
    ap.add_argument("--passages-file", default="data/annotation/audit_passages.csv")
    ap.add_argument("--calibration-file", default="data/annotation/audit_calibration_brighter_r1.csv")
    ap.add_argument("--audit-dir", default="data/processed/audit")
    args = ap.parse_args(argv)
    if args.audit:
        m = run_audit(args, device())
        print(f"wrote {args.audit_dir}/passage_scores.csv, calibration_scores.csv, manifest.json "
              f"({sum(1 for e in m['models'] if e['status'] == 'ok')} of {len(m['models'])} model x unit runs ok)")
        return
    args.out = args.out or ("data/processed/audit_passage_scores.csv" if args.passages else
                            "data/processed/audit_scores.csv")
    texts = load_passages(args.passages) if args.passages else load_texts(args.inp)
    if args.passages:
        args.inp = args.passages
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dev = device()
    manifest = dict(run=time.strftime("%Y-%m-%d %H:%M"), input=args.inp, n_texts=len(texts),
                    n_by_lang={lg: sum(1 for t in texts if t[1] == lg) for lg in ("hi", "en")}, device=dev, models=[])
    rows = []
    import torch
    import transformers
    manifest.update(torch=torch.__version__, transformers=transformers.__version__)
    for spec in (m for m in MODELS if m["key"] in args.models.split(",")):
        entry, model_rows = run_model(spec, texts, dev)
        if args.passages:
            model_rows = [{("passage_id" if k == "record_id" else k): v for k, v in r.items()} for r in model_rows]
        rows += model_rows
        manifest["models"].append(entry)
        print(f"{spec['key']}: {entry['status']} ({entry['seconds']} s)")
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    out.with_name("audit_passage_scores_manifest.json" if args.passages else "audit_models_manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                                                           encoding="utf-8")
    print(f"wrote {out} ({len(rows)} rows) and audit_models_manifest.json")


if __name__ == "__main__":
    main()
