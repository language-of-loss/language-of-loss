"""Discourse-move sequence entropy rate per text, with a permutation null and bootstrap intervals."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MOVES = ["announcement", "circumstances", "character", "memory", "regret", "address_dead", "ritual", "lesson",
         "blessing_closing"]


def entropy_rate_from_counts(c):
    c = np.asarray(c, dtype=float)
    n = c.sum(axis=(-2, -1), keepdims=True)
    row = c.sum(axis=-1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(c > 0, c / n * np.log2(c / row), 0.0)
    return -term.sum(axis=(-2, -1))


def transition_counts(codes, k):
    codes = np.asarray(codes)
    pair = codes[..., :-1] * k + codes[..., 1:]
    flat = pair.reshape(-1, pair.shape[-1])
    off = np.arange(flat.shape[0])[:, None] * k * k
    counts = np.bincount((flat + off).ravel(), minlength=flat.shape[0] * k * k)
    return counts.reshape(*pair.shape[:-1], k, k)


def entropy_rate(seq, k=None):
    codes, k = encode(seq, k)
    return float(entropy_rate_from_counts(transition_counts(codes, k)))


def encode(seq, k=None):
    if len(seq) and not isinstance(seq[0], (int, np.integer)):
        labels = {m: i for i, m in enumerate(sorted(set(seq)))}
        seq = [labels[m] for m in seq]
    codes = np.asarray(seq, dtype=np.int64)
    return codes, int(k or (codes.max() + 1 if len(codes) else 1))


def permutation_null(seq, n_perm, rng):
    codes, k = encode(seq)
    out = []
    for start in range(0, n_perm, 2000):
        m = min(2000, n_perm - start)
        perm = rng.permuted(np.tile(codes, (m, 1)), axis=1)
        out.append(entropy_rate_from_counts(transition_counts(perm, k)))
    return np.concatenate(out)


def bootstrap_transitions(seq, B, rng):
    codes, k = encode(seq)
    pairs = codes[:-1] * k + codes[1:]
    idx = rng.integers(0, len(pairs), size=(B, len(pairs)))
    s = pairs[idx]
    off = np.arange(B)[:, None] * k * k
    c = np.bincount((s + off).ravel(), minlength=B * k * k).reshape(B, k, k)
    return entropy_rate_from_counts(c)


def per_text(seq, n_perm, B, rng):
    h = entropy_rate(seq)
    null = permutation_null(seq, n_perm, rng)
    boot = bootstrap_transitions(seq, B, rng)
    return dict(n_moves=len(seq), n_move_types=len(set(seq)), entropy_rate=h, null_mean=float(null.mean()),
                excess=float(null.mean() - h), p_perm=float((1 + (null <= h + 1e-12).sum()) / (1 + n_perm)),
                lo=float(np.percentile(boot, 2.5)), hi=float(np.percentile(boot, 97.5)))


def by_language(rows, B, rng):
    vals = {lang: np.array([[r["entropy_rate"], r["excess"]] for r in rows if r["lang"] == lang])
            for lang in sorted({r["lang"] for r in rows})}
    reps, out = {}, []
    for lang, v in vals.items():
        idx = rng.integers(0, len(v), size=(B, len(v)))
        reps[lang] = v[idx].mean(1)
        for j, name in enumerate(("entropy_rate", "excess")):
            out.append(dict(lang=lang, quantity=name, n_texts=len(v), estimate=float(v[:, j].mean()),
                            lo=float(np.percentile(reps[lang][:, j], 2.5)),
                            hi=float(np.percentile(reps[lang][:, j], 97.5))))
    if {"hi", "en"} <= set(vals):
        for j, name in enumerate(("entropy_rate", "excess")):
            d = reps["hi"][:, j] - reps["en"][:, j]
            out.append(dict(lang="hi-en", quantity=name, n_texts=len(vals["hi"]) + len(vals["en"]),
                            estimate=float(vals["hi"][:, j].mean() - vals["en"][:, j].mean()),
                            lo=float(np.percentile(d, 2.5)), hi=float(np.percentile(d, 97.5))))
    return out


def load_sequences(path, text_col, lang_col, pos_col, move_col):
    seqs, langs = defaultdict(list), {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if not r[move_col].strip():
                continue
            seqs[r[text_col]].append((float(r[pos_col]), len(seqs[r[text_col]]), r[move_col].strip()))
            langs[r[text_col]] = r[lang_col]
    return {t: [m for _, _, m in sorted(v)] for t, v in seqs.items()}, langs


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default=str(ROOT / "tests/optional/fixtures/moves_synthetic.csv"))
    ap.add_argument("--out", default=str(ROOT / "results/optional/entropy_moves_synthetic.csv"))
    ap.add_argument("--text-col", default="text_id")
    ap.add_argument("--lang-col", default="lang")
    ap.add_argument("--pos-col", default="position")
    ap.add_argument("--move-col", default="move")
    ap.add_argument("--perm", type=int, default=10000)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--min-moves", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20261009)
    args = ap.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    seqs, langs = load_sequences(args.inp, args.text_col, args.lang_col, args.pos_col, args.move_col)
    rows, skipped = [], 0
    for t in sorted(seqs):
        if len(seqs[t]) < args.min_moves:
            skipped += 1
            continue
        rows.append(dict(text_id=t, lang=langs[t], **per_text(seqs[t], args.perm, args.B, rng)))
    out = Path(args.out)
    write_csv(out, rows)
    lang_rows = by_language(rows, args.B, rng)
    write_csv(out.with_name(out.stem + "_by_lang.csv"), lang_rows)
    for r in lang_rows:
        print(f"{r['lang']:6} {r['quantity']:13} n={r['n_texts']:3} {r['estimate']:.3f} [{r['lo']:.3f}, {r['hi']:.3f}]")
    print(f"{len(rows)} texts, {skipped} skipped (< {args.min_moves} moves)")


if __name__ == "__main__":
    main()
