"""Score the held-out native Hindi gold clauses with the saved MuRIL checkpoints (no training)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import train_muril_pair as P

ROOT = Path(__file__).resolve().parents[2]
MODELS = {"translated": "muril_translated", "native": "muril_native_provisional"}


def predict(model_dir, rows, device="cpu"):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(device).eval()
    out = {}
    with torch.no_grad():
        for i in range(0, len(rows), P.CONFIG["batch"]):
            chunk = rows[i:i + P.CONFIG["batch"]]
            enc = tok([r["text"] for r in chunk], return_tensors="pt", padding=True, truncation=True,
                      max_length=P.CONFIG["max_len"])
            pred = model(**{k: v.to(device) for k, v in enc.items()}).logits.argmax(-1).tolist()
            out.update({r["id"]: int(p) for r, p in zip(chunk, pred)})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gold", default=str(ROOT / "data/annotation/a1_gold.csv"))
    ap.add_argument("--clauses", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--models-dir", default=str(ROOT / "data/processed/models"))
    ap.add_argument("--channels", default=str(P.CH))
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args(argv)
    rows = P.load_gold(a.gold, a.clauses)
    paths = P.output_paths(False, a.channels)
    for name, sub in MODELS.items():
        preds = predict(Path(a.models_dir) / sub, rows, a.device)
        P.write_predictions(paths[name], preds)
        print(f"{name}: {len(preds)} gold clauses scored, positive {sum(preds.values())} -> {paths[name]}")


if __name__ == "__main__":
    main()
