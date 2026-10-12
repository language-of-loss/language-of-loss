#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, pathlib
import numpy as np, pandas as pd, torch
from sklearn.metrics import precision_recall_fscore_support as prfs
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)

LR, BATCH, EPOCHS, FOLDS, SEED, THRESH, MAXLEN = 2e-5, 16, 4, 5, 20260926, 0.5, 128
MODEL = os.environ.get("LEXICON_SMOKE_MODEL", "google/muril-base-cased")


class Clauses(Dataset):
    def __init__(self, tok, texts, Y):
        self.enc = tok(list(texts), truncation=True, max_length=MAXLEN, padding=True, return_tensors="pt")
        self.Y = torch.tensor(np.asarray(Y, dtype=np.float32))
    def __len__(self): return len(self.Y)
    def __getitem__(self, i):
        return {k: v[i] for k, v in self.enc.items()} | {"labels": self.Y[i]}


def train(tok, texts, Y, K, device):
    torch.manual_seed(SEED)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL, num_labels=K, problem_type="multi_label_classification").to(device)
    dl = DataLoader(Clauses(tok, texts, Y), batch_size=BATCH, shuffle=True)
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    steps = EPOCHS * len(dl)
    sch = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    model.train()
    for ep in range(EPOCHS):
        for batch in dl:
            loss = model(**{k: v.to(device) for k, v in batch.items()}).loss
            loss.backward(); opt.step(); sch.step(); opt.zero_grad()
    return model.eval()


@torch.no_grad()
def predict(model, tok, texts, device) -> np.ndarray:
    probs = []
    for i in range(0, len(texts), 64):
        enc = tok(list(texts[i:i + 64]), truncation=True, max_length=MAXLEN, padding=True, return_tensors="pt")
        probs.append(torch.sigmoid(model(**{k: v.to(device) for k, v in enc.items()}).logits).cpu().numpy())
    return (np.vstack(probs) >= THRESH).astype(int) if probs else np.zeros((0, model.config.num_labels), int)


def per_component(Y, P, comps) -> pd.DataFrame:
    p, r, f, s = prfs(Y, P, average=None, zero_division=0)
    return pd.DataFrame({"component": comps, "precision": p, "recall": r, "f1": f, "support": s})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clauses", required=True); ap.add_argument("--gold", required=True)
    ap.add_argument("--components", required=True); ap.add_argument("--out-dir", default="classifier_out")
    a = ap.parse_args(); out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    cdf = pd.read_csv(a.components); cdf = cdf[cdf.get("status", "kept") != "form_flag"]
    comps = [f"c_{c}" for c in cdf[cdf.columns[0]]]; K = len(comps)
    cl, gold = pd.read_csv(a.clauses), pd.read_csv(a.gold)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    cov = cl[cl.matcher_covered == 1].reset_index(drop=True)
    unc = cl[cl.matcher_covered == 0].reset_index(drop=True)

    cv_rows = []
    for k, (tr, va) in enumerate(GroupKFold(FOLDS).split(cov, groups=cov.text_id), 1):
        m = train(tok, cov.text.iloc[tr], cov[comps].values[tr], K, device)
        df = per_component(cov[comps].values[va], predict(m, tok, cov.text.iloc[va].tolist(), device), comps)
        df.insert(0, "fold", k); cv_rows.append(df)
    pd.concat(cv_rows).to_csv(out / "cv_metrics.csv", index=False)

    model = train(tok, cov.text, cov[comps].values, K, device)
    Yg = gold[comps].values
    clf = per_component(Yg, predict(model, tok, gold.text.tolist(), device), comps).add_prefix("clf_")
    gm = gold.merge(cl[["clause_id"] + comps], on="clause_id", how="left", suffixes=("", "_m")).fillna(0)
    mat = per_component(Yg, gm[[c + "_m" for c in comps]].values.astype(int), comps).add_prefix("matcher_")
    ev = pd.concat([clf, mat.drop(columns=["matcher_component"])], axis=1)
    ev["use_classifier"] = ev.clf_f1 >= ev.matcher_f1
    ev.to_csv(out / "gold_eval.csv", index=False)
    macro_ok = bool(ev.clf_f1.mean() >= ev.matcher_f1.mean())

    P = predict(model, tok, unc.text.tolist(), device) * ev.use_classifier.values.astype(int)
    pd.concat([unc[["clause_id", "text_id", "lang", "text"]], pd.DataFrame(P, columns=comps)], axis=1) \
        .to_csv(out / "predictions_uncovered.csv", index=False)
    newly = int((P.sum(1) > 0).sum())
    json.dump({"n_clauses": len(cl), "n_matcher_covered": len(cov), "n_uncovered": len(unc),
               "n_scored_by_classifier_not_matcher": newly,
               "coverage_gain": newly / max(len(cl), 1),
               "classifier_used_overall": macro_ok,
               "components_using_classifier": ev.loc[ev.use_classifier, "clf_component"].tolist()},
              open(out / "coverage.json", "w"), indent=2)
    print(f"macro-F1 clf {ev.clf_f1.mean():.3f} vs matcher {ev.matcher_f1.mean():.3f} -> "
          f"classifier {'USED' if macro_ok else 'NOT USED'}; coverage gain {newly}/{len(cl)}")


if __name__ == "__main__":
    main()
