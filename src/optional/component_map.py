"""Lexicon entries in NSM component space: one MDS map, Hindi and English coloured."""
import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.manifold import MDS

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from collocation import font_family, headword, write_caption

ROOT = Path(__file__).resolve().parents[2]


def load(lexicon_dir):
    with open(Path(lexicon_dir) / "entry_vectors.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    comps = [c for c in rows[0] if c not in ("entry_id", "lang", "names_emotion")]
    with open(Path(lexicon_dir) / "lexicon.csv", encoding="utf-8") as fh:
        heads = {e["entry_id"]: headword(e) for e in csv.DictReader(fh)}
    ids = [r["entry_id"] for r in rows]
    langs = [r["lang"] for r in rows]
    x = np.array([[int(r[c]) for c in comps] for r in rows], dtype=bool)
    return ids, langs, [heads.get(i, i) for i in ids], x, comps


def jaccard(x):
    inter = (x[:, None, :] & x[None, :, :]).sum(-1)
    union = (x[:, None, :] | x[None, :, :]).sum(-1)
    return 1 - np.divide(inter, union, out=np.ones(inter.shape), where=union > 0)


def layout(x, seed=0):
    d = jaccard(x)
    np.fill_diagonal(d, 0)
    xy = MDS(n_components=2, metric="precomputed", init="classical_mds", random_state=seed).fit_transform(d)
    rng = np.random.default_rng(seed)
    return xy + rng.normal(scale=0.012, size=xy.shape)


def counterpart_pairs(lexicon_dir, ids):
    with open(Path(lexicon_dir) / "lexicon.csv", encoding="utf-8") as fh:
        cp = {e["entry_id"]: e["counterpart"] for e in csv.DictReader(fh)}
    at = {e: i for i, e in enumerate(ids)}
    pairs = set()
    for eid, val in cp.items():
        for other in re.split(r"[;,\s|]+", val or ""):
            if eid in at and other in at and eid != other:
                a, b = sorted((at[eid], at[other]))
                pairs.add((a, b))
    return sorted(pairs)


def visible_points(pts, radius):
    keep, cover = np.zeros(len(pts), bool), np.full(len(pts), -1)
    shown = []
    for i, p in enumerate(pts):
        near = [j for j in shown if np.hypot(*(pts[j] - p)) < radius]
        if near:
            cover[i] = min(near, key=lambda j: np.hypot(*(pts[j] - p)))
        else:
            keep[i] = True
            shown.append(i)
    return keep, cover


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lexicon-dir", default=str(ROOT / "lexicon"))
    ap.add_argument("--out-dir", default=str(ROOT / "figures/final"))
    ap.add_argument("--stem", default="Figure1_component_space")
    ap.add_argument("--captions", default=str(ROOT / "figures/captions.md"))
    args = ap.parse_args(argv)
    from adjustText import adjust_text
    from matplotlib.lines import Line2D
    import figures as F

    ids, langs, labels, x, comps = load(args.lexicon_dir)
    xy = layout(x)
    links = counterpart_pairs(args.lexicon_dir, ids)
    F.setup_style()
    deva = font_family()[:1] + F.font_list()
    marker_s = 16.0
    fig, ax = plt.subplots(figsize=(7.2, 6.6))
    ax.set_aspect("equal", adjustable="box")
    pad = 0.06 * np.ptp(xy, axis=0)
    ax.set_xlim(xy[:, 0].min() - pad[0], xy[:, 0].max() + pad[0])
    ax.set_ylim(xy[:, 1].min() - pad[1], xy[:, 1].max() + pad[1])
    ax.set_xticks([]), ax.set_yticks([])
    ax.grid(False)
    for s_ in ax.spines.values():
        s_.set_visible(False)
    fig.canvas.draw()
    disp = ax.transData.transform(xy) * 72 / fig.dpi
    keep, cover = visible_points(disp, radius=0.75 * 2 * math.sqrt(marker_s / math.pi))
    for a, b in links:
        ax.plot(xy[[a, b], 0], xy[[a, b], 1], color=F.RULE, lw=0.35, zorder=1)
    for lang in ("hi", "en"):
        st = F.LANG[lang]
        for vis, z in ((False, 2), (True, 3)):
            k = [i for i, l in enumerate(langs) if l == lang and keep[i] == vis]
            ax.scatter(xy[k, 0], xy[k, 1], s=marker_s, marker=st["marker"], color=st["colour"], edgecolor="white",
                       linewidth=0.4, zorder=z)
    texts = [ax.text(xy[i, 0], xy[i, 1], labels[i], fontsize=5.6, color=F.INK, zorder=4, ha="center", va="center",
                     family=deva if langs[i] == "hi" else None) for i in np.flatnonzero(keep)]
    adjust_text(texts, x=xy[:, 0], y=xy[:, 1], ax=ax, expand=(1.15, 1.35), iter_lim=800,
                arrowprops=dict(arrowstyle="-", color=F.GREY, lw=0.3))
    handles = [Line2D([], [], marker=F.LANG[l]["marker"], ls="none", color=F.LANG[l]["colour"], mec="white", ms=5,
                      label=f"{F.LANG[l]['name']} ({langs.count(l)} entries)") for l in ("hi", "en")]
    handles.append(Line2D([], [], color=F.RULE, lw=0.8, label="Hindi entry – English counterpart"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, borderaxespad=0.0)
    paths = F.save(fig, Path(args.out_dir), args.stem, "")

    hidden = defaultdict(list)
    for i in np.flatnonzero(~keep):
        hidden[int(cover[i])].append(i)
    note = "; ".join(f"at {labels[j]} ({ids[j]}): " + ", ".join(f"{labels[i]} ({ids[i]})" for i in hidden[j])
                     for j in sorted(hidden, key=lambda j: ids[j]))
    n_unique = len({tuple(r) for r in x})
    write_caption("Figure1", (
        "## Figure 1. Lexicon entries in semantic-component space\n\n"
        f"Files: `figures/final/{args.stem}.{{pdf,png}}`. Script: `src/optional/component_map.py`.\n\n"
        f"The {len(ids)} entries of lexicon v0.2 ({langs.count('hi')} Hindi, circles; {langs.count('en')} English, "
        f"squares), each a binary vector over the K = {len(comps)} NSM semantic components "
        "(`lexicon/entry_vectors.csv`; the names_emotion form flag is not a component). Positions: metric MDS "
        "(classical start, random_state 0) of the Jaccard distance between component sets, plus a fixed jitter "
        f"(sd 0.012) so identical sets do not coincide exactly ({n_unique} distinct sets). Axes have no units; only "
        f"distances are meaningful. Grey lines join each Hindi entry to its English counterpart(s) as listed in "
        f"`lexicon/lexicon.csv` ({len(links)} links). The map shows the lexicon's design, not corpus usage; all "
        "entries have status 'proposed'. Labels were moved apart with adjustText (leader lines where moved). "
        f"{int((~keep).sum())} entries are not labelled because their marker lies under another entry's "
        "(centres closer than 0.75 marker diameters; the first entry in entry_vectors.csv order is kept): "
        + (note or "none") + "."), args.captions)
    for p_ in paths:
        print(p_)
    print(f"{len(ids)} entries ({langs.count('hi')} hi / {langs.count('en')} en), {len(comps)} components, "
          f"{n_unique} distinct component sets, {len(links)} counterpart links, {int(keep.sum())} labelled, "
          f"{int((~keep).sum())} hidden")


if __name__ == "__main__":
    main()
