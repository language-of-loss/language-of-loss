"""Output 8b inputs: one MuRIL classifier pair of identical configuration, trained on translated versus native data,"""
import argparse
import csv
import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "data" / "processed" / "channels"
MURIL = dict(repo="google/muril-base-cased", revision="afd9f36c7923d54e97903922ff1b260d091d202f",
             licence="Apache-2.0")
NLLB = dict(repo="facebook/nllb-200-distilled-600M", revision="f8d333a098d19b4fd9a8b18f94170487ad3f821d",
            licence="CC-BY-NC-4.0")
CONFIG = dict(max_len=128, lr=2e-5, weight_decay=0.01, warmup=0.1, batch=16, epochs=3)
SMOKE_N, SMOKE_EPOCHS, SMOKE_EVAL = 200, 1, 100
GOEMO_GRIEF, GOEMO_SADNESS = 16, 25
OUTPUTS = {"translated": "muril_translated_predictions.csv", "native": "muril_native_predictions.csv"}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def goemotions_label(labels):
    ids = [int(x) for x in labels.split(",")] if isinstance(labels, str) else [int(x) for x in labels]
    return int(GOEMO_GRIEF in ids or GOEMO_SADNESS in ids)


def load_goemotions(directory):
    d = Path(directory)
    rows = []
    for p in sorted(d.glob("*.tsv")):
        with open(p, encoding="utf-8", newline="") as fh:
            for r in csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE):
                if len(r) >= 3:
                    rows.append(dict(id=r[2], text=r[0], label=goemotions_label(r[1])))
    if not rows:
        import pandas as pd
        for p in sorted(d.glob("*.parquet")):
            for r in pd.read_parquet(p).to_dict("records"):
                rows.append(dict(id=str(r["id"]), text=r["text"], label=goemotions_label(list(r["labels"]))))
    if not rows:
        raise SystemExit(f"{d}: no GoEmotions files (train/dev/test.tsv or *.parquet). Download the open release "
                         "(github.com/google-research/google-research/tree/master/goemotions, or the Hugging Face "
                         "dataset google-research-datasets/go_emotions, config simplified) into that directory")
    return rows


def read_translation_cache(path):
    out = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["en_sha256"]] = r["hi"]
    return out


def translate_pool(rows, cache_path, translator=None):
    cache = read_translation_cache(cache_path)
    todo = [r for r in rows if sha(r["text"]) not in cache]
    if todo:
        translator = translator or NllbTranslator()
        hi = translator([r["text"] for r in todo])
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "a", encoding="utf-8") as fh:
            for r, h in zip(todo, hi):
                cache[sha(r["text"])] = h
                fh.write(json.dumps(dict(id=r["id"], en_sha256=sha(r["text"]), hi=h), ensure_ascii=False) + "\n")
    out = [dict(r, text=cache[sha(r["text"])], text_en_sha256=sha(r["text"])) for r in rows]
    return out, len(rows) - len(todo), len(todo)


class NllbTranslator:

    def __init__(self, device="cpu"):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        self.torch, self.device = torch, device
        self.tok = AutoTokenizer.from_pretrained(NLLB["repo"], revision=NLLB["revision"], src_lang="eng_Latn")
        self.model = AutoModelForSeq2SeqLM.from_pretrained(NLLB["repo"], revision=NLLB["revision"]).to(device).eval()

    def __call__(self, texts, batch=16, beams=4):
        bos = self.tok.convert_tokens_to_ids("hin_Deva")
        out = []
        for i in range(0, len(texts), batch):
            enc = self.tok(texts[i:i + batch], return_tensors="pt", padding=True, truncation=True,
                           max_length=256).to(self.device)
            with self.torch.no_grad():
                gen = self.model.generate(**enc, forced_bos_token_id=bos, num_beams=beams, max_new_tokens=192)
            out += self.tok.batch_decode(gen, skip_special_tokens=True)
        return out


def load_brighter(directory, splits=("train", "dev")):
    import pandas as pd
    rows = []
    for s in splits:
        for r in pd.read_parquet(Path(directory) / f"{s}-00000-of-00001.parquet").to_dict("records"):
            rows.append(dict(id=r["id"], text=r["text"], label=int(r["sadness"]), split=s))
    return rows


def load_gold(gold_path, clauses_path):
    labels = {}
    with open(gold_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            v = (r.get("emotional") or "").strip()
            if v in ("0", "1"):
                labels[r["clause_id"]] = int(v)
    rows = []
    with open(clauses_path, encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            if c["clause_id"] in labels and c.get("lang") == "hi":
                rows.append(dict(id=c["clause_id"], text=c["clause_text"], label=labels[c["clause_id"]],
                                 group=c["record_id"]))
    return rows


def grouped_folds(rows, k, seed):
    groups = {}
    for r in rows:
        groups.setdefault(r["group"], []).append(r["id"])
    order = sorted(groups)
    random.Random(seed).shuffle(order)
    order.sort(key=lambda g: -len(groups[g]))
    sizes, fold_of = [0] * k, {}
    for g in order:
        f = min(range(k), key=lambda i: (sizes[i], i))
        sizes[f] += len(groups[g])
        for cid in groups[g]:
            fold_of[cid] = f
    return fold_of


def matched_sample(pool, n, pos_share, seed):
    rng = random.Random(seed)
    pos = [r for r in pool if r["label"] == 1]
    neg = [r for r in pool if r["label"] == 0]
    n = min(n, len(pool))
    want_pos = min(round(n * pos_share), len(pos))
    want_neg = n - want_pos
    if want_neg > len(neg):
        want_neg = len(neg)
        want_pos = n - want_neg
    out = rng.sample(pos, want_pos) + rng.sample(neg, want_neg)
    rng.shuffle(out)
    return out


def equal_size_pair(native, translated, seed):
    share = sum(r["label"] for r in native) / len(native) if native else 0.0
    t_pos = sum(r["label"] for r in translated)
    t_neg = len(translated) - t_pos
    n = min(len(native), int(t_pos / share) if share else len(translated),
            int(t_neg / (1 - share)) if share < 1 else len(translated))
    nat = native if n == len(native) else matched_sample(native, n, share, seed)
    share = sum(r["label"] for r in nat) / len(nat) if nat else 0.0
    return nat, matched_sample(translated, n, share, seed + 1)


def scores(gold, pred):
    keys = [k for k in gold if k in pred]
    tp = sum(1 for k in keys if gold[k] and pred[k])
    fp = sum(1 for k in keys if not gold[k] and pred[k])
    fn = sum(1 for k in keys if gold[k] and not pred[k])
    acc = sum(1 for k in keys if gold[k] == pred[k]) / len(keys) if keys else float("nan")
    f1 = 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else float("nan")
    return dict(n=len(keys), accuracy=round(acc, 4), f1=round(f1, 4))


def pick_device(name):
    import torch
    if name != "auto":
        return name
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def train_predict(train_rows, eval_rows, cfg, seed, device, model_spec=MURIL):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    random.seed(seed)
    torch.manual_seed(seed)
    kw = dict(revision=model_spec["revision"]) if model_spec.get("revision") else {}
    tok = AutoTokenizer.from_pretrained(model_spec["repo"], **kw)
    model = AutoModelForSequenceClassification.from_pretrained(model_spec["repo"], num_labels=2, **kw).to(device)

    def batches(rows, shuffle, rng=None):
        idx = list(range(len(rows)))
        if shuffle:
            rng.shuffle(idx)
        for i in range(0, len(idx), cfg["batch"]):
            chunk = [rows[j] for j in idx[i:i + cfg["batch"]]]
            enc = tok([r["text"] for r in chunk], return_tensors="pt", padding=True, truncation=True,
                      max_length=cfg["max_len"])
            yield chunk, {k: v.to(device) for k, v in enc.items()}

    steps = cfg["epochs"] * -(-len(train_rows) // cfg["batch"])
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    sched = get_linear_schedule_with_warmup(opt, int(cfg["warmup"] * steps), steps)
    rng = random.Random(seed)
    model.train()
    for _ in range(cfg["epochs"]):
        for chunk, enc in batches(train_rows, True, rng):
            y = torch.tensor([r["label"] for r in chunk], device=device)
            loss = model(**enc, labels=y).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
    model.eval()
    out = {}
    with torch.no_grad():
        for chunk, enc in batches(eval_rows, False):
            pred = model(**enc).logits.argmax(-1).tolist()
            out.update({r["id"]: int(p) for r, p in zip(chunk, pred)})
    del model
    return out


def write_predictions(path, preds):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["clause_id", "pred"])
        for k in sorted(preds):
            w.writerow([k, preds[k]])


def output_paths(smoke, channels=CH):
    if smoke:
        return {m: Path(channels) / "smoke" / f.replace(".csv", "_smoke.csv") for m, f in OUTPUTS.items()}
    return {m: Path(channels) / f for m, f in OUTPUTS.items()}


def run(args, train_fn=train_predict, translator=None):
    models = ("translated", "native") if args.only == "both" else (args.only,)
    cfg = dict(CONFIG)
    if args.smoke:
        cfg["epochs"] = SMOKE_EPOCHS
    device = pick_device(args.device)
    model_spec = dict(MURIL) if not args.model else dict(repo=args.model, revision=None)

    brighter = load_brighter(args.brighter)
    have_gold = Path(args.gold).exists()
    if not have_gold and not args.smoke:
        raise SystemExit(f"{args.gold} not found: the real run predicts held-out native Hindi gold clauses "
                         "(not in the public release). Use --smoke for a dry run on BRIGHTER only")

    translated = []
    tr_info = {}
    if "translated" in models:
        go = load_goemotions(args.goemotions)
        if args.smoke:
            go = random.Random(args.seed).sample(go, min(len(go), 4 * SMOKE_N))
        translated, n_cached, n_new = translate_pool(go, args.translation_cache, translator)
        tr_info = dict(pool=len(translated), positives=sum(r["label"] for r in translated), cached=n_cached,
                       translated_now=n_new, cache=str(args.translation_cache))

    if have_gold:
        gold = load_gold(args.gold, args.clauses)
        if not gold:
            raise SystemExit(f"{args.gold}: no Hindi gold clause with emotional 0/1 found in {args.clauses}")
        fold_of = grouped_folds(gold, args.folds, args.seed)
        n_folds = args.folds
        bright_train = brighter
        design = f"grouped {args.folds}-fold over native Hindi gold (record_id)"
    else:
        gold = [dict(r, group=r["id"]) for r in brighter if r["split"] == "dev"][:SMOKE_EVAL]
        fold_of = {r["id"]: 0 for r in gold}
        n_folds = 1
        bright_train = [r for r in brighter if r["split"] == "train"]
        design = f"smoke without gold: BRIGHTER train -> {len(gold)} held-out BRIGHTER dev sentences"

    preds = {m: {} for m in models}
    folds = []
    t0 = time.time()
    for k in range(n_folds):
        held = [r for r in gold if fold_of[r["id"]] == k]
        native = bright_train + ([r for r in gold if fold_of[r["id"]] != k] if have_gold else [])
        if args.smoke:
            native = matched_sample(native, SMOKE_N, sum(r["label"] for r in native) / len(native), args.seed + k)
        if translated:
            nat_train, tr_train = equal_size_pair(native, translated, args.seed + 100 * k)
        else:
            nat_train, tr_train = native, []
        info = dict(fold=k, held_out=len(held), held_out_positive=sum(r["label"] for r in held))
        for m, rows in (("translated", tr_train), ("native", nat_train)):
            if m not in models:
                continue
            p = train_fn(rows, held, cfg, args.seed + k, device, model_spec)
            preds[m].update(p)
            info[m] = dict(n_train=len(rows), positive_share=round(sum(r["label"] for r in rows) / len(rows), 4),
                           **scores({r["id"]: r["label"] for r in held}, p))
        folds.append(info)
        print(f"fold {k}: " + ", ".join(f"{m} n={info[m]['n_train']} acc={info[m]['accuracy']}" for m in models))

    paths = output_paths(args.smoke, args.channels)
    for m in models:
        write_predictions(paths[m], preds[m])
    truth = {r["id"]: r["label"] for r in gold}
    status = ("DRY RUN (--smoke: 200 examples, 1 epoch; pipeline check, not a result)" if args.smoke
              else "held-out native Hindi gold predictions; machine output, provisional")
    manifest = dict(status=status, run=time.strftime("%Y-%m-%d %H:%M"), seconds=round(time.time() - t0),
                    device=device, model=model_spec, config=cfg, seed=args.seed, design=design,
                    gold=str(args.gold) if have_gold else None, gold_sha256=file_sha(args.gold) if have_gold else None,
                    brighter_files={s: file_sha(Path(args.brighter) / f"{s}-00000-of-00001.parquet")
                                    for s in ("train", "dev")},
                    translated_pool=tr_info or None, folds=folds,
                    overall={m: scores(truth, preds[m]) for m in models},
                    outputs={m: str(paths[m]) for m in models})
    out = Path(args.manifest or (ROOT / "results" / ("muril_pair_smoke_manifest.json" if args.smoke
                                                      else "muril_pair_manifest.json")))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{status}\n-> " + ", ".join(str(paths[m]) for m in models) + f"; manifest {out}")
    return manifest


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gold", default=str(ROOT / "data/annotation/a1_gold.csv"))
    ap.add_argument("--clauses", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--brighter", default=str(ROOT / "data/external/brighter/hin"))
    ap.add_argument("--goemotions", default=str(ROOT / "data/external/goemotions"))
    ap.add_argument("--translation-cache", default=str(ROOT / "data/external/goemotions_hi/translations.jsonl"))
    ap.add_argument("--channels", default=str(CH))
    ap.add_argument("--manifest", default="")
    ap.add_argument("--only", default="both", choices=["both", "translated", "native"])
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--device", default="auto", help="auto (cuda > mps > cpu), cpu, cuda, mps")
    ap.add_argument("--model", default="", help="override the pinned MuRIL (tests only)")
    ap.add_argument("--smoke", action="store_true", help="dry run: 200 examples, 1 epoch")
    args = ap.parse_args(argv)
    if "data/annotation" in Path(args.channels).resolve().as_posix():
        raise SystemExit("machine predictions never go to data/annotation/")
    run(args)


if __name__ == "__main__":
    sys.exit(main())
