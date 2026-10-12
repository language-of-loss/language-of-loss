"""Stage 10 -- PMI collocation maps around lexicon entries (development split only)."""
import argparse
import csv
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from sklearn.manifold import MDS

from gold import split_of
from lexmatch import load_lexicon, norm_word

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "fonts"
DEVANAGARI_FONTS = ["Noto Sans Devanagari", "Kohinoor Devanagari", "Devanagari Sangam MN", "DejaVu Sans"]
DROP_UPOS = {"PUNCT", "ADP", "AUX", "CCONJ", "DET", "NUM", "PART", "PRON", "PROPN", "SCONJ", "SYM", "X"}
STOPWORDS = {
    "hi": set("""और या लेकिन पर परन्तु किन्तु कि तो भी ही न नहीं ना मत जो जब तब तक से में को का की के ने पे
              यह वह ये वे इस उस इन उन इसे उसे इसका उसका इसकी उसकी यहाँ वहाँ यहां वहां अब फिर कभी सब कुछ कोई
              होना है हैं था थी थे हो हुआ हुई हुए रहा रही रहे गया गई गए गयी गये कर करके किया की लिए लिये
              एक बहुत बात साथ बाद तरह क्या क्यों कैसे कहाँ कहां वाला वाली वाले अपना अपनी अपने""".split()),
    "en": set("""a an the and or but if then so as of at by for from in into on onto to with without about
              over under up down out off than too very just also not no nor only own same such that this these
              those there here when where why how what which who whom whose be am is are was were been being
              have has had having do does did doing will would shall should can could may might must i me my
              mine we us our you your he him his she her it its they them their one all any both each few more
              most other some s t ll d m re ve get got go going went""".split()),
}


def register_fonts():
    from matplotlib import font_manager
    known = {f.fname for f in font_manager.fontManager.ttflist}
    for p in sorted(FONT_DIR.glob("*.ttf")):
        if str(p) not in known:
            font_manager.fontManager.addfont(str(p))


def font_family():
    from matplotlib import font_manager
    register_fonts()
    names = {f.name for f in font_manager.fontManager.ttflist}
    return [f for f in DEVANAGARI_FONTS if f in names] or ["DejaVu Sans"]


def norm_lemma(w, lang):
    return unicodedata.normalize("NFC", norm_word(w, lang))


def load_dev(clauses_path):
    clauses = {}
    with open(clauses_path, encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            if split_of(c["record_id"]) == "dev":
                clauses[c["clause_id"]] = c
    return clauses


def load_words(tokens_path, clauses):
    words = defaultdict(list)
    with open(tokens_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            c = clauses.get(r["clause_id"])
            if c is None or r["upos"] == "PUNCT":
                continue
            words[r["clause_id"]].append(dict(i=int(r["token_index"]), form=r["token"], lemma=r["lemma"],
                                              upos=r["upos"], lang=c["lang"]))
    for ws in words.values():
        ws.sort(key=lambda w: w["i"])
    return words


def char_spans(text, words):
    spans, cur = [], 0
    for w in words:
        k = text.find(w["form"], cur)
        if k < 0:
            spans.append(None)
            continue
        spans.append((k, k + len(w["form"])))
        cur = k + len(w["form"])
    return spans


def anchors(entry, clause, words):
    found = []
    spans = None
    for m in entry["rx"].finditer(clause["clause_text"]):
        spans = spans or char_spans(clause["clause_text"], words)
        idx = {k for k, s in enumerate(spans) if s and s[0] < m.end() and m.start() < s[1]}
        if idx:
            found.append(idx)
    lang = clause["lang"]
    keys = [{norm_word(w["form"], lang), norm_word(w["lemma"], lang)} for w in words]
    for variant in entry["variants"]:
        n = len(variant)
        for i in range(len(words) - n + 1):
            if all(variant[k] in keys[i + k] for k in range(n)):
                idx = set(range(i, i + n))
                if not any(idx & f for f in found):
                    found.append(idx)
    return found


def is_content(w):
    lem = norm_lemma(w["lemma"] or w["form"], w["lang"])
    return (w["upos"] not in DROP_UPOS and lem not in STOPWORDS[w["lang"]] and len(lem) > 1
            and any(ch.isalpha() for ch in lem))


def cooccurrences(clauses, words, lex, window):
    sentences = defaultdict(list)
    for cid, c in clauses.items():
        sentences[(c["record_id"], c["sent_index"])].append(cid)
    stats = {lang: dict(N=0, freq=Counter(), entries={}) for lang in ("hi", "en")}
    entries = {lang: [e for e in lex["entries"] if e["lang"] == lang] for lang in ("hi", "en")}
    for (rid, _), cids in sentences.items():
        lang = clauses[cids[0]]["lang"]
        stream = sorted(((w["i"], cid, k) for cid in cids for k, w in enumerate(words.get(cid, []))))
        pos = {(cid, k): p for p, (_, cid, k) in enumerate(stream)}
        counted = set()
        flat = [words[cid][k] for _, cid, k in stream]
        st = stats[lang]
        st["N"] += len(flat)
        for w in flat:
            if is_content(w):
                st["freq"][norm_lemma(w["lemma"] or w["form"], lang)] += 1
        found = defaultdict(list)
        for cid in cids:
            ws = words.get(cid, [])
            for e in entries[lang]:
                occ = anchors(e, clauses[cid], ws)
                if occ:
                    found[e["entry_id"]].append((cid, occ))
        for eid, per_clause in found.items():
            own = {pos[(cid, k)] for cid, occ in per_clause for idx in occ for k in idx}
            es = st["entries"].setdefault(eid, dict(clauses=0, occ=0, pairs=Counter(), texts=defaultdict(set)))
            for cid, occ in per_clause:
                es["clauses"] += 1
                for idx in occ:
                    es["occ"] += 1
                    ps = sorted(pos[(cid, k)] for k in idx)
                    lo, hi = max(0, ps[0] - window), min(len(flat), ps[-1] + window + 1)
                    seen = set()
                    for p in range(lo, hi):
                        if p in own or (eid, p) in counted or not is_content(flat[p]):
                            continue
                        counted.add((eid, p))
                        lem = norm_lemma(flat[p]["lemma"] or flat[p]["form"], lang)
                        if lem not in seen:
                            seen.add(lem)
                            es["pairs"][lem] += 1
                            es["texts"][lem].add(rid)
    return stats


def pmi_table(stats, lex, min_matches, min_count, window):
    rows = []
    head = {e["entry_id"]: headword(e) for e in lex["entries"]}
    for lang, st in stats.items():
        for eid, es in sorted(st["entries"].items()):
            if es["clauses"] < min_matches:
                continue
            for lem, c in es["pairs"].items():
                if c < min_count:
                    continue
                pmi = math.log2(c * st["N"] / (es["occ"] * st["freq"][lem] * 2 * window))
                rows.append(dict(lang=lang, entry_id=eid, headword=head[eid], entry_clauses=es["clauses"],
                                 entry_occurrences=es["occ"], collocate=lem, cooc=c, collocate_freq=st["freq"][lem],
                                 pmi=round(pmi, 3), n_texts=len(es["texts"][lem])))
    return rows


def headword(e):
    hw = e["headword_deva"] if e["lang"] == "hi" else e["headword_en"]
    return re.sub(r"\s*\([^)]*\)", "", hw.split("/")[0]).strip()


def covered(lemma, lang, lex):
    for e in lex["entries"]:
        if e["lang"] != lang:
            continue
        if e["rx"].search(lemma) or any(lemma in v for v in e["variants"]):
            return True
    return False


def candidates(rows, lex, min_pmi, min_texts):
    by = defaultdict(list)
    for r in rows:
        if r["pmi"] >= min_pmi and r["n_texts"] >= min_texts:
            by[(r["lang"], r["collocate"])].append(r)
    out = []
    for (lang, lem), rs in by.items():
        if covered(lem, lang, lex):
            continue
        best = max(rs, key=lambda r: r["pmi"])
        out.append(dict(lang=lang, candidate=lem, best_pmi=best["pmi"], best_anchor=best["entry_id"],
                        best_anchor_headword=best["headword"], cooc_with_best=best["cooc"],
                        candidate_freq=best["collocate_freq"], n_anchor_entries=len(rs),
                        anchor_entries=" ".join(sorted(r["entry_id"] for r in rs)),
                        max_texts=max(r["n_texts"] for r in rs), status="proposed (unreviewed)"))
    out.sort(key=lambda r: (r["lang"], -r["n_anchor_entries"], -r["best_pmi"]))
    return out


def build_graph(rows, lang, top):
    g = nx.Graph()
    by = defaultdict(list)
    for r in rows:
        if r["lang"] == lang and r["pmi"] > 0:
            by[r["entry_id"]].append(r)
    for eid, rs in by.items():
        g.add_node(eid, kind="entry", label=rs[0]["headword"])
        for r in sorted(rs, key=lambda r: -r["pmi"])[:top]:
            node = "w:" + r["collocate"]
            if node not in g:
                g.add_node(node, kind="collocate", label=r["collocate"])
            g.add_edge(eid, node, pmi=r["pmi"], length=1 / r["pmi"])
    return g


def mds_layout(g, seed=0):
    nodes = list(g)
    if len(nodes) < 3:
        return {n: (float(i), 0.0) for i, n in enumerate(nodes)}
    d = dict(nx.all_pairs_dijkstra_path_length(g, weight="length"))
    m = np.full((len(nodes), len(nodes)), np.inf)
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            m[i, j] = d[a].get(b, np.inf)
    finite = m[np.isfinite(m)].max()
    m[~np.isfinite(m)] = 1.2 * finite
    xy = MDS(n_components=2, metric="precomputed", init="classical_mds", random_state=seed,
             n_init=1).fit_transform(m)
    return {n: tuple(p) for n, p in zip(nodes, xy)}


def spread(xy, dmin, iters=200):
    xy = xy.copy()
    for _ in range(iters):
        d = xy[:, None, :] - xy[None, :, :]
        r = np.sqrt((d ** 2).sum(-1))
        np.fill_diagonal(r, np.inf)
        close = r < dmin
        if not close.any():
            break
        push = np.where(close, (dmin - r) / np.maximum(r, 1e-9) / 2, 0)[..., None] * d
        xy += push.sum(1) * 0.5
    return xy


def packed_layout(g, seed=0, gap=None, aspect=1.5):
    med = float(np.median([d["length"] for _, _, d in g.edges(data=True)])) if g.number_of_edges() else 1.0
    gap = 2.2 * med if gap is None else gap
    boxes = []
    for nodes in sorted(nx.connected_components(g), key=lambda c: (-len(c), sorted(c)[0])):
        h = g.subgraph(nodes)
        order = sorted(h)
        if len(order) == 2:
            xy = np.array([[0.0, 0.0], [h.edges[order[0], order[1]]["length"], 0.0]])
        else:
            p = mds_layout(h, seed)
            xy = np.array([p[n] for n in order], dtype=float)
            xy -= xy.mean(0)
            if len(order) > 2:
                _, _, vt = np.linalg.svd(xy, full_matrices=False)
                vt *= np.where(vt[:, 0:1] < 0, -1, 1)
                xy = xy @ vt.T
        xy = spread(xy, 0.6 * med)
        xy -= xy.min(0)
        boxes.append((order, xy, xy.max(0)))
    width = max(max(b[2][0] for b in boxes),
                math.sqrt(sum((w + gap) * (hh + gap) for _, _, (w, hh) in boxes) * aspect))
    pos, x, y, row_h = {}, 0.0, 0.0, 0.0
    for order, xy, (w, hh) in sorted(boxes, key=lambda b: -b[2][1]):
        if x > 0 and x + w > width:
            x, y, row_h = 0.0, y - row_h - gap, 0.0
        for n, (a, b) in zip(order, xy):
            pos[n] = (x + a, y - (hh - b))
        x += w + gap
        row_h = max(row_h, hh)
    return pos


def node_freq(rows, lang):
    f = {}
    for r in rows:
        if r["lang"] == lang:
            f[r["entry_id"]] = int(r["entry_occurrences"])
            f["w:" + r["collocate"]] = int(r["collocate_freq"])
    return f


def draw_network(ax, g, pos, freq, lang, fmax, pmax):
    from adjustText import adjust_text
    import figures as F
    for a, b, d in g.edges(data=True):
        (x0, y0), (x1, y1) = pos[a], pos[b]
        ax.plot([x0, x1], [y0, y1], color=F.GREY, lw=edge_width(d["pmi"], pmax), alpha=0.55, zorder=1,
                solid_capstyle="round")
    family = font_family()[:1] + F.font_list() if lang == "hi" else None
    texts, px, py = [], [], []
    for n, d in sorted(g.nodes(data=True)):
        x, y = pos[n]
        entry = d["kind"] == "entry"
        ax.scatter(x, y, s=node_area(freq.get(n, 1), fmax), color=F.VERMILLION if entry else F.GREY,
                   edgecolor="white", linewidth=0.5, zorder=3 if entry else 2)
        texts.append(ax.text(x, y, d["label"], fontsize=7.5 if entry else 6, fontweight="bold" if entry else "normal",
                             color=F.VERMILLION if entry else F.MUTED, zorder=4, family=family,
                             ha="center", va="center"))
        px.append(x), py.append(y)
    ax.set_xticks([]), ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    xs, ys = np.array(px), np.array(py)
    padx, pady = 0.08 * (np.ptp(xs) or 1), 0.08 * (np.ptp(ys) or 1)
    ax.set_xlim(xs.min() - padx, xs.max() + padx)
    ax.set_ylim(ys.min() - pady, ys.max() + pady)
    ax.set_aspect("equal", adjustable="box")
    adjust_text(texts, x=xs, y=ys, ax=ax, expand=(1.2, 1.4), ensure_inside_axes=True, iter_lim=2000,
                arrowprops=dict(arrowstyle="-", color=F.RULE, lw=0.4))


def node_area(f, fmax, lo=6.0, hi=90.0):
    return lo + (hi - lo) * math.sqrt(f / fmax)


def edge_width(pmi, pmax):
    return 0.3 + 1.6 * pmi / pmax


def network_legend(ax, fmax, pmax):
    import figures as F
    from matplotlib.lines import Line2D
    sizes = [v for v in (10, 100, 1000) if v <= fmax] or [fmax]
    h = [Line2D([], [], marker="o", ls="none", color=F.VERMILLION, mec="white", ms=6, label="lexicon entry"),
         Line2D([], [], marker="o", ls="none", color=F.GREY, mec="white", ms=6, label="collocate (lemma)")]
    h += [Line2D([], [], marker="o", ls="none", color=F.GREY, mec="white", ms=math.sqrt(node_area(v, fmax)),
                 label=f"frequency {v:,}") for v in sizes]
    h += [Line2D([], [], color=F.GREY, lw=edge_width(v, pmax), label=f"PMI {v:g}") for v in (3, 6) if v <= pmax]
    ax.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=len(h), handletextpad=0.3,
              columnspacing=1.0, borderaxespad=0.0)


def extent(pos):
    xy = np.array(list(pos.values()))
    return max(np.ptp(xy[:, 0]), 1e-9), max(np.ptp(xy[:, 1]), 1e-9)


def plot_networks(graphs, rows, final_dir, legacy_dir=None):
    import figures as F
    F.setup_style()
    font_family()
    width = 7.2
    lay = {lang: packed_layout(g) for lang, g in graphs.items()}
    freq = {lang: node_freq(rows, lang) for lang in graphs}
    fmax = max(max(f.values()) for f in freq.values())
    pmax = max(d["pmi"] for g in graphs.values() for _, _, d in g.edges(data=True))
    paths = []
    ratio = {lang: extent(p)[1] / extent(p)[0] for lang, p in lay.items()}
    heights = {lang: min(max(width * r, 2.6), 4.6) for lang, r in ratio.items()}
    for lang, g in graphs.items():
        fig, ax = plt.subplots(figsize=(width, min(max(width * ratio[lang], 2.6), 8.0)))
        draw_network(ax, g, lay[lang], freq[lang], lang, fmax, pmax)
        network_legend(ax, fmax, pmax)
        stem = f"Figure2_collocation_{lang}"
        if legacy_dir:
            Path(legacy_dir).mkdir(parents=True, exist_ok=True)
            fig.savefig(Path(legacy_dir) / f"colloc_{lang}.png", format="png", metadata={"Software": None})
        paths += F.save(fig, Path(final_dir), stem, "")
    langs = [lang for lang in ("hi", "en") if lang in graphs]
    fig, axes = plt.subplots(len(langs), 1, figsize=(width, sum(heights[lang] for lang in langs) + 0.3),
                             gridspec_kw=dict(height_ratios=[heights[lang] for lang in langs], hspace=0.08),
                             squeeze=False)
    for k, (lang, ax) in enumerate(zip(langs, axes[:, 0])):
        draw_network(ax, graphs[lang], lay[lang], freq[lang], lang, fmax, pmax)
        ax.text(0.0, 1.0, f"({'ab'[k]}) {'Hindi' if lang == 'hi' else 'English'}", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=10, fontweight="bold", color=F.INK)
    network_legend(axes[-1, 0], fmax, pmax)
    paths += F.save(fig, Path(final_dir), "Figure2_collocation", "")
    return paths


def write_caption(key, text, path=None):
    path = Path(path or ROOT / "figures" / "captions.md")
    begin, end = f"<!-- {key}:begin -->", f"<!-- {key}:end -->"
    old = path.read_text(encoding="utf-8") if path.exists() else (
        "# Figure captions (publication figures)\n\nEach block is written by the script that draws the figure; "
        "regenerate, do not edit by hand.\n")
    block = f"{begin}\n{text.strip()}\n{end}"
    if begin in old and end in old:
        new = old[:old.index(begin)] + block + old[old.index(end) + len(end):]
    else:
        new = old.rstrip("\n") + "\n\n" + block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return path


def collocation_caption(graphs, n_texts, args):
    parts = []
    for k, lang in enumerate(("hi", "en")):
        g = graphs.get(lang)
        if g is None:
            continue
        n_e = sum(1 for _, d in g.nodes(data=True) if d["kind"] == "entry")
        parts.append(f"({'ab'[k]}) {'Hindi' if lang == 'hi' else 'English'}: {n_e} lexicon entries, "
                     f"{g.number_of_nodes() - n_e} collocates, {nx.number_connected_components(g)} connected "
                     f"components" + (f", {n_texts[lang]} development texts" if n_texts else ""))
    return ("## Figure 2. Collocation networks of lexicon entries\n\n"
            "Files: `figures/final/Figure2_collocation.{pdf,png}` (panels a, b), "
            "`figures/final/Figure2_collocation_{hi,en}.{pdf,png}`. Script: `src/analysis/collocation.py`.\n\n"
            f"Lexicon entries (bold, vermillion) and their top {args.top} collocates by PMI (grey) in a "
            f"±{args.window}-word window within the sentence, development set only (the 30% development split; "
            "the confirmatory texts are not used). " + "; ".join(parts) + ". "
            f"Entries need ≥ {args.min_matches} matched clauses and pairs ≥ {args.min_count} co-occurrences; "
            "PMI = log2(c(e,w) N / (c(e) c(w) 2·window)). Marker area grows with the square root of frequency "
            "(entries: anchor occurrences; collocates: lemma frequency in the development texts); edge width grows "
            "with PMI. Each connected component is laid out separately by metric MDS (classical start) of "
            "shortest-path distances with edge length 1/PMI, turned to its principal axis, nodes closer than 0.6 × the "
            "median edge length pushed apart (cosmetic), and the components packed; distances between components "
            "carry no meaning. Labels are moved apart by adjustText, with a thin leader line "
            "where a label left its node. Collocates are lemmas; proper nouns are excluded. Exploratory instrument "
            "description (output 9), not a test; matches are machine-provisional and unreviewed. "
            "Source: `results/collocation_pmi.csv`.")


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def draw_only(args):
    with open(args.pmi_out, encoding="utf-8", newline="") as fh:
        rows = [dict(r, pmi=float(r["pmi"])) for r in csv.DictReader(fh)]
    graphs = {lang: g for lang in ("hi", "en") if (g := build_graph(rows, lang, args.top)).number_of_nodes()}
    for p in plot_networks(graphs, rows, args.final_dir, args.fig_dir):
        print(p)
    n_texts = None
    if Path(args.inp).exists():
        dev = load_dev(args.inp)
        n_texts = {lang: len({c["record_id"] for c in dev.values() if c["lang"] == lang}) for lang in ("hi", "en")}
    write_caption("Figure2", collocation_caption(graphs, n_texts, args), args.captions)
    for lang, g in graphs.items():
        print(f"{lang}: graph {g.number_of_nodes()} nodes / {g.number_of_edges()} edges, "
              f"{nx.number_connected_components(g)} components (from {args.pmi_out})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.csv"))
    ap.add_argument("--fig-dir", default=str(ROOT / "figures"), help="colloc_{hi,en}.png (assemble.py input)")
    ap.add_argument("--final-dir", default=str(ROOT / "figures/final"), help="Figure2_collocation*.{pdf,png}")
    ap.add_argument("--captions", default=str(ROOT / "figures/captions.md"))
    ap.add_argument("--pmi-out", default=str(ROOT / "results/collocation_pmi.csv"))
    ap.add_argument("--candidates-out", default=str(ROOT / "docs/collocation_candidates.csv"))
    ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--min-matches", type=int, default=10)
    ap.add_argument("--min-count", type=int, default=3)
    ap.add_argument("--top", type=int, default=6, help="collocates per entry drawn in the graph")
    ap.add_argument("--min-pmi", type=float, default=3.0, help="candidate list threshold")
    ap.add_argument("--min-texts", type=int, default=2, help="candidate must co-occur in this many texts")
    ap.add_argument("--draw-only", action="store_true",
                    help="redraw the figures from the existing --pmi-out CSV; compute and write nothing else")
    args = ap.parse_args(argv)
    if args.draw_only:
        return draw_only(args)

    lex = load_lexicon(args.lexicon)
    clauses = load_dev(args.inp)
    words = load_words(Path(args.inp).parent / "tokens.csv", clauses)
    stats = cooccurrences(clauses, words, lex, args.window)
    rows = pmi_table(stats, lex, args.min_matches, args.min_count, args.window)
    write_csv(Path(args.pmi_out), rows, list(rows[0]) if rows else ["lang"])
    cands = candidates(rows, lex, args.min_pmi, args.min_texts)
    write_csv(Path(args.candidates_out), cands, list(cands[0]) if cands else ["lang", "candidate"])
    graphs, n_texts = {}, {}
    for lang in ("hi", "en"):
        n_texts[lang] = len({c["record_id"] for c in clauses.values() if c["lang"] == lang})
        g = build_graph(rows, lang, args.top)
        if g.number_of_nodes():
            graphs[lang] = g
        st = stats[lang]
        mapped = sum(1 for es in st["entries"].values() if es["clauses"] >= args.min_matches)
        print(f"{lang}: dev texts {n_texts[lang]}, words {st['N']}, entries matched {len(st['entries'])}, "
              f">= {args.min_matches} clauses {mapped}, pairs kept {sum(r['lang'] == lang for r in rows)}, "
              f"graph {g.number_of_nodes()} nodes / {g.number_of_edges()} edges, "
              f"candidates {sum(c['lang'] == lang for c in cands)}")
    if graphs:
        for p in plot_networks(graphs, rows, args.final_dir, args.fig_dir):
            print(p)
        write_caption("Figure2", collocation_caption(graphs, n_texts, args), args.captions)


if __name__ == "__main__":
    main()
