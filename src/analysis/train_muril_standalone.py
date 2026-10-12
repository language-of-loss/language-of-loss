"""Train the MuRIL pair's two models once on their full training pools and save the checkpoints (no gold, no"""
import argparse
import csv
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_muril_pair as P

ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = ROOT / "data" / "processed" / "models"
STATUS = {"translated": "model 1, trained on the full matched GoEmotions-MT pool; not evaluated (no gold yet); the "
                        "registered McNemar run retrains it per gold fold",
          "native_provisional": "PROVISIONAL model 2: BRIGHTER-Hindi sadness only, without the native gold the "
                                "registered model 2 adds; to be retrained once the gold set exists; not evaluated"}


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pools(args):
    native = P.load_brighter(args.brighter)
    share = sum(r["label"] for r in native) / len(native)
    english = P.load_goemotions(args.goemotions)
    sample = P.matched_sample(english, len(native), share, args.seed)
    t0 = time.time()
    translated, n_cached, n_new = P.translate_pool(sample, args.translation_cache) if args.only != "native_provisional" \
        else (sample, 0, 0)
    info = dict(n_cached=n_cached, n_translated=n_new, seconds=round(time.time() - t0, 1),
                pool_english=len(english), pool_english_positive=sum(r["label"] for r in english))
    return native, translated, info


def fit(rows, cfg, seed, device, out_dir, model_spec=P.MURIL):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup
    random.seed(seed)
    torch.manual_seed(seed)
    kw = dict(revision=model_spec["revision"]) if model_spec.get("revision") else {}
    tok = AutoTokenizer.from_pretrained(model_spec["repo"], **kw)
    model = AutoModelForSequenceClassification.from_pretrained(model_spec["repo"], num_labels=2, **kw).to(device)
    steps = cfg["epochs"] * -(-len(rows) // cfg["batch"])
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    sched = get_linear_schedule_with_warmup(opt, int(cfg["warmup"] * steps), steps)
    rng = random.Random(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log, step, t0, epoch_loss = [], 0, time.time(), []
    model.train()
    for epoch in range(cfg["epochs"]):
        idx = list(range(len(rows)))
        rng.shuffle(idx)
        losses = []
        for i in range(0, len(idx), cfg["batch"]):
            chunk = [rows[j] for j in idx[i:i + cfg["batch"]]]
            enc = tok([r["text"] for r in chunk], return_tensors="pt", padding=True, truncation=True,
                      max_length=cfg["max_len"]).to(device)
            loss = model(**enc, labels=torch.tensor([r["label"] for r in chunk], device=device)).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            step += 1
            losses.append(float(loss))
            log.append(dict(step=step, epoch=epoch + 1, loss=round(float(loss), 5), lr=sched.get_last_lr()[0],
                            seconds=round(time.time() - t0, 1)))
            if step % 25 == 0:
                print(f"  {out_dir.name}: step {step}/{steps} epoch {epoch + 1} loss {sum(losses[-25:]) / 25:.4f} "
                      f"({time.time() - t0:.0f} s)", flush=True)
        epoch_loss.append(round(sum(losses) / len(losses), 5))
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    with open(out_dir / "training_log.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(log[0]))
        w.writeheader()
        w.writerows(log)
    with open(out_dir / "train_ids.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "label"])
        w.writerows([r["id"], r["label"]] for r in rows)
    weights = next((p for p in out_dir.iterdir() if p.suffix in (".safetensors", ".bin")), None)
    return dict(steps=steps, seconds=round(time.time() - t0, 1), mean_loss_per_epoch=epoch_loss,
                checkpoint=str(out_dir.relative_to(ROOT)) if out_dir.is_relative_to(ROOT) else str(out_dir),
                weights_sha256=file_sha(weights) if weights else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brighter", default=str(ROOT / "data/external/brighter/hin"))
    ap.add_argument("--goemotions", default=str(ROOT / "data/external/goemotions"))
    ap.add_argument("--translation-cache", default=str(ROOT / "data/external/goemotions_hi/translations.jsonl"))
    ap.add_argument("--only", default="both", choices=["both", "translated", "native_provisional"])
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--models-dir", default=str(MODELS_DIR))
    ap.add_argument("--manifest", default=str(ROOT / "results/muril_standalone_manifest.json"))
    args = ap.parse_args(argv)
    native, translated, tinfo = pools(args)
    import torch
    import transformers
    manifest = dict(run=time.strftime("%Y-%m-%d %H:%M"), device=args.device, seed=args.seed, config=P.CONFIG,
                    muril=P.MURIL, nllb=P.NLLB, torch=torch.__version__, transformers=transformers.__version__,
                    translation=tinfo, inputs=dict(
                        brighter={p.name: file_sha(p) for p in sorted(Path(args.brighter).glob("*.parquet"))},
                        goemotions={p.name: file_sha(p) for p in sorted(Path(args.goemotions).glob("*.parquet"))}),
                    models={})
    for name, rows in (("translated", translated), ("native_provisional", native)):
        if args.only not in ("both", name):
            continue
        print(f"training {name}: {len(rows)} examples, {sum(r['label'] for r in rows)} positive", flush=True)
        res = fit(rows, P.CONFIG, args.seed, args.device, Path(args.models_dir) / f"muril_{name}")
        manifest["models"][name] = dict(n=len(rows), positive=sum(r["label"] for r in rows),
                                        positive_share=round(sum(r["label"] for r in rows) / len(rows), 4),
                                        status=STATUS[name], **res)
        Path(args.manifest).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {x: v[x] for x in ("n", "positive", "seconds", "mean_loss_per_epoch")}
                      for k, v in manifest["models"].items()}, indent=1))


if __name__ == "__main__":
    main()
