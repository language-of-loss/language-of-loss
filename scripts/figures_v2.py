"""Ten publication figures G1-G10 -> figures/final/G*.{pdf,png} (300-dpi PNG + vector PDF) and their captions in"""
import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
import collocation as C
import decompose as D
import figures as F
import predictions as P
from gold import DEV_SHARE, components_list
from translation_bias import native_only_entries

PROC = ROOT / "data" / "processed"
RES = ROOT / "results"
ROB = RES / "robustness"
LEX = ROOT / "lexicon"
FIGURES = ["G1_study_design", "G2_sankey", "G3_decomposition_waterfall", "G4_choice_bootstrap_density",
           "G5_robustness_forest", "G6_text_component_clustermap", "G7_lexicon_overlap_heatmap",
           "G8_component_networks", "G9_audit_slopes", "G10_worked_example"]
SEED, B = 20261009, 2000
PMI_MIN, MIN_PAIR = 1.0, 5
NEUTRAL = "#4d4d4d"
STATUS = ("reviewed machine-prefilled labels; features machine-provisional (lexicon matcher, rule-based eligibility)")
SUMMARY = {}


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def kept(path):
    return {r["record_id"] for r in read(path) if r["kept"] == "1" and r.get("split", "confirmatory") == "confirmatory"}


def fmt(v, d=2, sign=False):
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    return s.replace("-", "−")


def rel(p):
    return str(Path(p).relative_to(ROOT))


def caption(key, title, body, sources, status=STATUS):
    files = f"Files: `figures/final/{key}.{{pdf,png}}`. Script: `scripts/figures_v2.py`" + (
        " (drawn by `R/figures_v2.R`)." if key in ("G2_sankey", "G9_audit_slopes") else ".")
    src = "; ".join(f"`{s}`" for s in sources)
    C.write_caption(key, f"## {key}. {title}\n\n{files}\n\n{body} Status: {status}. Source: {src}.")


_CACHE = {}


def clause_features():
    if "cf" not in _CACHE:
        _CACHE["cf"] = read(PROC / "clause_features.csv")
    return _CACHE["cf"]


def text_lang():
    return {r["record_id"]: r["lang"] for r in read(PROC / "text_features.csv")}


def decomposition(path):
    return {r["quantity"]: {k: float(r[k]) for k in ("estimate", "lo", "hi")} for r in read(path)}


def choice_draws(records=None):
    if "flags" not in _CACHE:
        with open(PROC / "eligibility.csv", encoding="utf-8", newline="") as fh:
            _CACHE["flags"] = D.clause_flags(csv.DictReader(fh), "relational")
        _CACHE["refs"] = read(PROC / "referents.csv")
    texts = D.text_counts(_CACHE["refs"], _CACHE["flags"], "confirmatory", None, records)
    rng = np.random.default_rng(SEED)
    m = {lg: D.matrix(texts[lg]) for lg in ("hi", "en")}
    reps = {}
    for lg, x in m.items():
        s = x[rng.integers(0, len(x), size=(B, len(x)))].sum(1)
        reps[lg] = D.rates(s[:, 0], s[:, 1], s[:, 2], s[:, 3])
    point = {lg: D.rates(*m[lg].sum(0)[:4]) for lg in m}
    c = D.decompose(reps["hi"], reps["en"])["choice_share"]
    return float(D.decompose(point["hi"], point["en"])["choice_share"]), c[np.isfinite(c)], \
        {lg: len(texts[lg]) for lg in texts}


SETS = [("main", "main (200 confirmatory texts)", None, RES / "decompose_relational_confirmatory.csv"),
        ("unseen", "texts unseen during development", ROB / "unseen_texts_subset.csv",
         ROB / "decompose_relational_unseen_texts.csv"),
        ("original", "original sampling protocol", ROB / "original_protocol_subset.csv",
         ROB / "decompose_relational_original_protocol.csv")]


def box(ax, x, y, w, h, text, edge=F.MUTED, face="white", lw=0.7, size=7.6, weight="normal", align="center"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=face, ec=edge, lw=lw, zorder=2))
    tx = x if align == "center" else x - w / 2 + 0.12
    ax.text(tx, y, text, ha=align, va="center", fontsize=size, fontweight=weight, color=F.INK, zorder=3,
            linespacing=1.35)


def arrow(ax, a, b, label=None, off=(0, 0)):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=F.MUTED, lw=0.8, shrinkA=0, shrinkB=0,
                                                    mutation_scale=8), zorder=1)
    if label:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], label, ha="center", va="center", fontsize=6.6,
                color=F.MUTED, style="italic", zorder=3)


def g1(out, stamp):
    split = {r["record_id"]: r["split"] for r in read(PROC / "split.csv")}
    lang = text_lang()
    n = Counter((split[r], lang[r]) for r in split)
    tot = Counter(lang[r] for r in split)
    nd, nc = sum(v for (s, _), v in n.items() if s == "dev"), sum(v for (s, _), v in n.items() if s == "confirmatory")
    lex = Counter(r["lang"] for r in read(LEX / "lexicon.csv"))
    k = len(components_list(LEX))
    n_pred = len(read(PROC / "predicate_inventory.csv"))
    fields = len(read(RES / "agreement" / "agreement_summary_gold_sheet_v1.csv"))
    gold = Counter(r["lang"] for r in read(ROOT / "data" / "annotation" / "gold_sheet_v1_adjudicated.csv"))
    a1 = len(read(ROOT / "data" / "annotation" / "a1_gold.csv"))
    pairs = len(read(PROC / "audit_pairs.csv"))
    systems = {r["system"] for r in read(RES / "audit_lmer.csv")}
    n_llm = sum(s.startswith("commercial_llm") for s in systems)
    unseen, orig = kept(ROB / "unseen_texts_subset.csv"), kept(ROB / "original_protocol_subset.csv")
    p1 = read(RES / "p1_choice.csv")
    assert {r["split"] for r in p1} == {"confirmatory"}, "p1_choice.csv is not the confirmatory run"
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(1.15, 7.3)
    ax.axis("off")
    box(ax, 5, 6.85, 4.6, 0.75, f"Corpus: {len(split)} texts (Hindi {tot['hi']}, English {tot['en']})\n"
        "grief blogs and personal essays", edge=F.INK, lw=0.9, weight="bold")
    box(ax, 2.45, 5.45, 4.3, 0.62, f"Development set: {nd} texts\n(Hindi {n[('dev', 'hi')]}, English "
        f"{n[('dev', 'en')]})", face="#f2f2f2", weight="bold")
    box(ax, 7.55, 5.45, 4.3, 0.62, f"Confirmatory set: {nc} texts\n(Hindi {n[('confirmatory', 'hi')]}, English "
        f"{n[('confirmatory', 'en')]})", face="#f2f2f2", weight="bold")
    arrow(ax, (3.6, 6.47), (2.6, 5.78), f"record-id hash < {DEV_SHARE:.2f}", off=(-0.75, 0.05))
    arrow(ax, (6.4, 6.47), (7.4, 5.78), f"hash ≥ {DEV_SHARE:.2f}, held out", off=(0.8, 0.05))
    box(ax, 2.45, 4.0, 4.3, 1.55,
        "Instruments built here, then frozen:\n"
        f"• lexicon v0.2: {lex['hi']} Hindi / {lex['en']} English entries,\n   K = {k} semantic components\n"
        f"• predicate rule table: {n_pred} predicate keys\n"
        f"• codebook: {fields} fields\n"
        f"• gold set: {sum(gold.values())} clauses ({gold['hi']} Hindi / {gold['en']} English)", align="left")
    arrow(ax, (2.45, 5.14), (2.45, 4.78))
    box(ax, 2.45, 1.95, 4.3, 1.3,
        "Audits (development texts)\n"
        f"• Audit 1, translation bias: {a1} Hindi gold\n   clauses; NRC-Hindi, WordNet route, MuRIL pair\n"
        f"• Audit 2, machine reading: {pairs} matched Hindi–\n   English passage pairs; {len(systems)} systems "
        f"({len(systems) - n_llm} open\n   models, {n_llm} commercial LLMs)", align="left")
    arrow(ax, (2.45, 3.22), (2.45, 2.6))
    hy = 4.55
    box(ax, 7.55, hy, 4.3, 0.78, "H1: mixed model (Run 2, fixed in advance) +\nchoice / forced / opportunity "
        "decomposition", edge=F.VERMILLION, lw=1.1, weight="bold")
    box(ax, 7.55, 3.6, 4.3, 0.5, "P1: chosen-dative rate vs forced baseline")
    box(ax, 7.55, 2.95, 4.3, 0.5, f"P2: component-profile JSD, K = {k}")
    box(ax, 7.55, 1.95, 4.3, 1.3,
        "Robustness checks\n"
        f"• texts unseen during development ({len(unseen)} texts)\n"
        f"• original sampling protocol ({len(orig)} texts)\n"
        "• largest text dropped (Hindi, English, both)\n"
        "• majority-adjudicated gold", align="left")
    arrow(ax, (7.55, 5.14), (7.55, hy + 0.39))
    arrow(ax, (4.6, 4.0), (5.4, 4.0), "applied\nunchanged", off=(0, 0.3))
    fig.tight_layout()
    paths = F.save(fig, out, "G1_study_design", stamp)
    caption("G1_study_design", "Study design",
            f"The {len(split)} texts were split by a hash of the record id into a development set ({nd} texts) and a "
            f"held-out confirmatory set ({nc} texts). Every instrument (the NSM lexicon, the predicate rule table, the "
            f"codebook and the {sum(gold.values())}-clause gold set) was built on the development set and frozen "
            "before the confirmatory texts were analysed (registration tag prereg-v1-20261010). The tests fixed in "
            "advance "
            "(H1, P1, P2) and the robustness checks use the confirmatory set; the two audits use development texts "
            "(the gold clauses for Audit 1, matched passages for Audit 2), not the confirmatory set.",
            ["data/processed/split.csv", "lexicon/lexicon.csv", "lexicon/entry_vectors.csv",
             "data/processed/predicate_inventory.csv", "data/annotation/gold_sheet_v1_adjudicated.csv",
             "data/annotation/a1_gold.csv", "data/processed/audit_pairs.csv", "results/robustness/*_subset.csv"])
    return paths


def g3(out, stamp):
    d = decomposition(RES / "decompose_relational_confirmatory.csv")
    steps = [("forced_share", "forced", F.GREY), ("opportunity_share", "opportunity", F.SKY),
             ("choice_share", "choice", F.CHOICE)]
    total = sum(d[k]["estimate"] for k, _, _ in steps)
    assert abs(total - d["delta"]["estimate"]) < 2e-3, "forced + opportunity + choice != Δ"
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    cum = 0.0
    for i, (k, label, colour) in enumerate(steps):
        v = d[k]
        lo, hi = sorted((cum, cum + v["estimate"]))
        ax.add_patch(Rectangle((i - 0.32, lo), 0.64, hi - lo, fc=colour, ec=F.INK if k == "choice_share" else "none",
                               lw=0.9, zorder=2))
        ax.errorbar(i, cum + v["estimate"], yerr=[[v["estimate"] - v["lo"]], [v["hi"] - v["estimate"]]], fmt="none",
                    ecolor=F.INK, elinewidth=0.9, capsize=3, zorder=3)
        neg = v["estimate"] < 0
        ax.text(i, cum + (v["lo"] - 0.35 if neg else v["hi"] + 0.35),
                f"{fmt(v['estimate'], 2, True)}\n[{fmt(v['lo'])}, {fmt(v['hi'])}]", ha="center",
                va="top" if neg else "bottom", fontsize=7, color=F.INK,
                fontweight="bold" if k == "choice_share" else "normal")
        nxt = cum + v["estimate"]
        ax.plot([i + 0.32, i + 0.68], [nxt, nxt], color=F.MUTED, lw=0.6, ls=(0, (2, 2)), zorder=1)
        cum = nxt
    v = d["delta"]
    ax.add_patch(Rectangle((3 - 0.32, 0), 0.64, v["estimate"], fc="white", ec=F.INK, lw=0.9, zorder=2))
    ax.errorbar(3, v["estimate"], yerr=[[v["estimate"] - v["lo"]], [v["hi"] - v["estimate"]]], fmt="none",
                ecolor=F.INK, elinewidth=0.9, capsize=3, zorder=3)
    ax.text(3, v["hi"] + 0.35, f"{fmt(v['estimate'], 2, True)}\n[{fmt(v['lo'])}, {fmt(v['hi'])}]", ha="center",
            va="bottom", fontsize=7)
    F.zero_line(ax, 0, vertical=False)
    ax.set_xticks(range(4), ["+ forced", "+ opportunity", "+ choice", "= Δ (gap)"])
    ax.set_xlim(-0.6, 3.6)
    tops = [d["forced_share"]["hi"], d["delta"]["hi"], cum - d["choice_share"]["estimate"] + d["choice_share"]["hi"]]
    ax.set_ylim(min(0, cum - d["choice_share"]["estimate"] - 3), max(tops) + 2.4)
    ax.set_ylabel("Hindi − English, per 100 finite clauses")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    paths = F.save(fig, out, "G3_decomposition_waterfall", stamp)
    j = json.loads((RES / "decompose_relational_confirmatory.json").read_text())
    caption("G3_decomposition_waterfall", "Decomposition of the Hindi − English gap in relational marking",
            "Waterfall from 0: the forced share, the opportunity share and the choice share add up to the gap Δ = "
            f"r_hi − r_en ({fmt(d['delta']['estimate'], 2, True)} per 100 finite clauses). Each step's error bar is "
            "its own 95% percentile interval from "
            f"{j['B']:,} bootstrap resamples of texts within language (seed {j['seed']}), placed at the step's end; "
            "the choice share (headline statistic) is outlined. Confirmatory set, "
            f"{j['n_texts_hi']} Hindi and {j['n_texts_en']} English texts; values after the deceased-detection fix "
            "(2bd38d6).", ["results/decompose_relational_confirmatory.csv", "results/decompose_relational_confirmatory.json"])
    return paths


def g4(out, stamp):
    from scipy.stats import gaussian_kde
    draws, check = {}, {}
    for key, label, subset, path in SETS:
        est, c, n = choice_draws(kept(subset) if subset else None)
        logged = decomposition(path)["choice_share"]
        got = dict(estimate=est, lo=float(np.percentile(c, 2.5)), hi=float(np.percentile(c, 97.5)))
        diff = max(abs(got[k] - logged[k]) for k in got)
        if diff > 5.1e-5:
            raise SystemExit(f"G4: recomputed draws for {key} do not reproduce {rel(path)} ({got} vs {logged})")
        draws[key] = (label, c, logged, n)
        check[key] = dict(n_texts=n, draws=int(len(c)), logged=logged, recomputed={k: round(v, 4) for k, v in
                                                                                    got.items()},
                          max_abs_diff=round(diff, 6))
    SUMMARY["G4_reproduction"] = dict(seed=SEED, B=B, sets=check)
    fig, ax = plt.subplots(figsize=(5.8, 3.5))
    allv = np.concatenate([v[1] for v in draws.values()])
    grid = np.linspace(min(0, allv.min()) - 1, allv.max() + 1, 600)
    label, c, lg, n = draws["main"]
    dens = gaussian_kde(c)(grid)
    ax.fill_between(grid, dens, color=F.CHOICE, alpha=0.18, lw=0, zorder=1)
    inside = (grid >= lg["lo"]) & (grid <= lg["hi"])
    ax.fill_between(grid[inside], dens[inside], color=F.CHOICE, alpha=0.45, lw=0, zorder=2,
                    label="main: 95% interval")
    ax.plot(grid, dens, color=F.CHOICE, lw=1.3, zorder=3, label=f"main ({n['hi']} + {n['en']} texts)")
    ax.plot([lg["estimate"]] * 2, [0, dens.max()], color=F.CHOICE, lw=0.9, zorder=3)
    ax.annotate(f"{fmt(lg['estimate'], 2, True)} [{fmt(lg['lo'])}, {fmt(lg['hi'])}]",
                xy=(lg["estimate"], dens.max()), xytext=(8, 2), textcoords="offset points", fontsize=7.5,
                fontweight="bold", color=F.INK)
    for key, style, colour in (("unseen", (0, (4, 2)), F.INK), ("original", (0, (1, 1.5)), F.PURPLE)):
        label, c, lgd, n = draws[key]
        ax.plot(grid, gaussian_kde(c)(grid), color=colour, lw=0.8, ls=style, zorder=4,
                label=f"{label} ({n['hi']} + {n['en']}): {fmt(lgd['estimate'], 2, True)} "
                      f"[{fmt(lgd['lo'])}, {fmt(lgd['hi'])}]")
    ax.axvline(0, color=F.MUTED, lw=0.8, zorder=1)
    ax.set_xlabel("choice share, Hindi − English (per 100 finite clauses)")
    ax.set_ylabel("density of bootstrap draws")
    ax.set_ylim(0, 1.55 * dens.max())
    ax.legend(loc="upper left", fontsize=6.6, handlelength=2.4)
    fig.tight_layout()
    paths = F.save(fig, out, "G4_choice_bootstrap_density", stamp)
    caption("G4_choice_bootstrap_density", "Bootstrap distribution of the choice share",
            f"Gaussian kernel density (Scott bandwidth) of the {B:,} bootstrap draws of the choice share (texts "
            f"resampled within language, seed {SEED}) on the confirmatory set, with its 95% percentile interval "
            "shaded and the point estimate marked; thin lines: the same for the texts unseen during instrument "
            "development (dashed) and the original-protocol subset (dotted). The draws are not stored by "
            "decompose.py; they were recomputed with its functions and seed and reproduce the logged estimate and "
            "interval of all three CSVs to their 4 decimals. The vertical line marks 0.",
            [rel(p) for *_, p in SETS] + ["data/processed/eligibility.csv", "data/processed/referents.csv"])
    return paths


def run2_or(path):
    rows = [r for r in read(path) if r["term"] == "hindi"]
    pick = {}
    for r in rows:
        if r["estimator"].startswith("glmer (conditional"):
            pick["glmer"] = r
        elif r["estimator"].startswith("glm + CR2"):
            pick["CR2"] = r
    return {k: dict(estimate=math.exp(float(r["estimate"])), lo=math.exp(float(r["ci_lo"])),
                    hi=math.exp(float(r["ci_hi"])), n_texts=int(r["n_texts"])) for k, r in pick.items()}


def g5(out, stamp):
    ors = [("main", RES / "h1_glmm_run2.csv"), ("unseen texts", ROB / "h1_glmm_run2_unseen_texts.csv"),
           ("original protocol", ROB / "h1_glmm_run2_original_protocol.csv")]
    main_dec = decomposition(RES / "decompose_relational_confirmatory.csv")["choice_share"]
    drop = {r["variant"]: {k: float(r[k]) for k in ("estimate", "lo", "hi")}
            for r in read(RES / "decompose_relational_confirmatory_drop_largest.csv") if r["quantity"] == "choice_share"}
    shares = [("main", main_dec), ("unseen texts", decomposition(SETS[1][3])["choice_share"]),
              ("original protocol", decomposition(SETS[2][3])["choice_share"]),
              ("main, largest Hindi text dropped", drop["drop_largest_hi"]),
              ("main, largest English text dropped", drop["drop_largest_en"]),
              ("main, both dropped", drop["drop_largest_both"])]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw=dict(width_ratios=[1, 1.15], wspace=0.08))
    labels = []
    for i, (name, path) in enumerate(ors):
        r = run2_or(path)
        labels.append(f"{name} ({r['glmer']['n_texts']} texts)")
        for j, (key, lab, colour, marker, filled) in enumerate(F.ESTIMATORS):
            v = r[key]
            y = i + (-0.13 if j == 0 else 0.13)
            a1.errorbar(v["estimate"], y, xerr=[[v["estimate"] - v["lo"]], [v["hi"] - v["estimate"]]], fmt=marker,
                        color=colour, mfc=colour if filled else "white", ms=4.5, elinewidth=0.9, capsize=2,
                        label=lab if i == 0 else None)
            a1.text(v["hi"] * 1.02, y, f"{v['estimate']:.2f} [{v['lo']:.2f}, {v['hi']:.2f}]", va="center",
                    fontsize=6, color=F.INK)
    a1.axvline(1, color=F.MUTED, lw=0.8)
    a1.set_xscale("log")
    ticks = [t for t in F.OR_TICKS if 0.8 <= t <= 3]
    a1.set_xticks(ticks, [f"{t:g}" for t in ticks])
    a1.minorticks_off()
    a1.set_xlim(0.8, 3.2)
    a1.set_yticks(range(len(ors)), labels)
    a1.set_ylim(len(ors) - 0.5, -0.5)
    a1.set_xlabel("Run 2 odds ratio, Hindi (log scale)")
    a1.set_title("(a) Run 2 odds ratio", loc="left")
    a1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=6.5)
    a1.grid(axis="y", visible=False)
    for i, (name, v) in enumerate(shares):
        colour = F.CHOICE if i < 3 else F.MUTED
        a2.errorbar(v["estimate"], i, xerr=[[v["estimate"] - v["lo"]], [v["hi"] - v["estimate"]]], fmt="D",
                    color=colour, mfc=colour if i < 3 else "white", ms=4, elinewidth=0.9, capsize=2)
        a2.text(v["hi"] + 0.3, i, f"{fmt(v['estimate'], 2, True)} [{fmt(v['lo'])}, {fmt(v['hi'])}]", va="center",
                fontsize=6, color=F.INK)
    a2.axvline(0, color=F.MUTED, lw=0.8)
    a2.set_yticks(range(len(shares)), [s[0] for s in shares])
    a2.yaxis.tick_right()
    a2.set_ylim(len(shares) - 0.5, -0.5)
    a2.set_xlim(-1, max(v["hi"] for _, v in shares) + 4.5)
    a2.set_xlabel("choice share, per 100 finite clauses")
    a2.set_title("(b) Choice share", loc="left")
    a2.grid(axis="y", visible=False)
    a2.tick_params(axis="y", length=0)
    paths = F.save(fig, out, "G5_robustness_forest", stamp)
    caption("G5_robustness_forest", "Robustness of the Run 2 odds ratio and the choice share",
            "(a) Odds ratio for Hindi in Run 2 (relational ~ hindi + log clauses + loss type + (1 | text), clauses "
            "with a forced relational site removed): GLMM conditional estimate with Wald 95% CI (filled circles) "
            "and population-averaged GLM with CR2 cluster-robust 95% CI (open squares), for the main confirmatory "
            "set, the confirmatory texts unseen during instrument development, and the original-protocol subset "
            "(≤ 3 texts per domain, 1 per author group, ≤ 5,000 words). Log scale, reference line at 1. (b) Choice "
            "share with 95% bootstrap intervals (2,000 text resamples) for the same three sets and for the main set "
            "without its largest Hindi text, largest English text, or both. Reference line at 0. All values after "
            "the deceased-detection fix (2bd38d6).",
            ["results/h1_glmm_run2.csv", "results/robustness/h1_glmm_run2_{unseen_texts,original_protocol}.csv",
             "results/decompose_relational_confirmatory{,_drop_largest}.csv",
             "results/robustness/decompose_relational_{unseen_texts,original_protocol}.csv"])
    return paths


def text_component_matrix():
    classes = P.entry_classes(read(LEX / "entry_vectors.csv"))
    texts = P.p2_text_counts(clause_features(), classes, "confirmatory")
    comps = components_list(LEX)
    rids = sorted(texts)
    X = np.array([[100 * texts[r]["comp"][c] / texts[r]["n_clauses"] for c in comps] for r in rids])
    return rids, [texts[r]["lang"] for r in rids], comps, X


def dendro(ax, link, orientation):
    from scipy.cluster.hierarchy import dendrogram
    d = dendrogram(link, orientation=orientation, no_labels=True, color_threshold=0, above_threshold_color=F.MUTED,
                   ax=ax)
    ax.axis("off")
    return d["leaves"]


def g6(out, stamp):
    from scipy.cluster.hierarchy import fcluster, linkage
    from sklearn.metrics import adjusted_rand_score
    rids, langs, comps, X = text_component_matrix()
    sd = X.std(0, keepdims=True)
    Z = np.where(sd > 0, (X - X.mean(0, keepdims=True)) / np.where(sd > 0, sd, 1), 0.0)
    rl, cl = linkage(Z, "ward"), linkage(Z.T, "ward")
    top = fcluster(rl, 2, "maxclust")
    ari = adjusted_rand_score(langs, top)
    tab = Counter(zip(top.tolist(), langs))
    SUMMARY["G6"] = dict(n_texts=len(rids), n_hi=langs.count("hi"), n_en=langs.count("en"), n_components=len(comps),
                         standardisation="column z-score (each component across the texts)",
                         zero_variance_columns=int((sd == 0).sum()), linkage="ward (euclidean), rows and columns",
                         top_split_by_language={f"cluster {c}": {lg: tab[(c, lg)] for lg in ("hi", "en")}
                                                for c in (1, 2)}, adjusted_rand_index=round(float(ari), 4))
    fig = plt.figure(figsize=(7.2, 7.6))
    gs = fig.add_gridspec(3, 4, width_ratios=[1.1, 0.18, 6, 0.18], height_ratios=[1.0, 7, 0.0001], wspace=0.02,
                          hspace=0.01)
    ax_top, ax_left = fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[1, 0])
    ax_bar, ax = fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[1, 2])
    cax = fig.add_subplot(gs[1, 3])
    with plt.rc_context({"lines.linewidth": 0.5}):
        cols = dendro(ax_top, cl, "top")
        rows = dendro(ax_left, rl, "left")[::-1]
    lo = max(-3.0, float(Z.min()))
    M = np.clip(Z[np.ix_(rows, cols)], lo, 3)
    im = ax.imshow(M, aspect="auto", cmap="cividis", vmin=lo, vmax=3, interpolation="nearest")
    ax.set_xticks(range(len(cols)), [comps[c] for c in cols], rotation=90, fontsize=6.2)
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    colour = {"hi": F.BLUE, "en": F.ORANGE}
    ax_bar.imshow(np.array([[matplotlib.colors.to_rgb(colour[langs[r]])] for r in rows]), aspect="auto",
                  interpolation="nearest")
    ax_bar.set_xticks([])
    ax_bar.set_yticks([])
    for s in ax_bar.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("hits per 100 finite clauses, column z-score (clipped at 3)", fontsize=7)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6.5)
    from matplotlib.patches import Patch
    ax_top.legend(handles=[Patch(fc=F.BLUE, label=f"Hindi ({langs.count('hi')} texts)"),
                           Patch(fc=F.ORANGE, hatch="", label=f"English ({langs.count('en')} texts)")],
                  loc="upper left", bbox_to_anchor=(-0.33, 1.0), fontsize=6.8, title="language (row bar)",
                  title_fontsize=6.8)
    paths = F.save(fig, out, "G6_text_component_clustermap", stamp)
    caption("G6_text_component_clustermap", "Texts by semantic components",
            f"Rows: the {len(rids)} confirmatory texts ({langs.count('hi')} Hindi, {langs.count('en')} English); "
            f"columns: the K = {len(comps)} components. Cells: component hits per 100 finite clauses (a clause counts "
            "once per component; predictions.p2_text_counts), each component standardised across the "
            f"{len(rids)} texts (column z-score; "
            + (f"{SUMMARY['G6']['zero_variance_columns']} columns with no variation set to 0" if
               SUMMARY['G6']['zero_variance_columns'] else "every column varies") + "); the colour scale runs from the lowest "
            "z-score to 3 (higher values clipped for display). "
            "Ward clustering (Euclidean) of rows and of columns, with dendrograms; the bar left of the map gives each "
            "text's language. The top-level row split (two clusters) against language: cluster 1 = "
            f"{tab[(1, 'hi')]} Hindi / {tab[(1, 'en')]} English, cluster 2 = {tab[(2, 'hi')]} Hindi / "
            f"{tab[(2, 'en')]} English; adjusted Rand index {ari:.3f} (0 = chance agreement, 1 = the split is "
            "language). Descriptive; not a test.",
            ["data/processed/clause_features.csv (comp_* columns, finite clauses)", "lexicon/entry_vectors.csv"])
    return paths


def g7(out, stamp):
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import pdist
    C.register_fonts()
    comps = components_list(LEX)
    vec = {r["entry_id"]: np.array([int(r[c]) for c in comps], bool) for r in read(LEX / "entry_vectors.csv")}
    lex = read(LEX / "lexicon.csv")
    native = native_only_entries(read(LEX / "molecules.csv"), lex)
    head = {e["entry_id"]: (e["headword_deva"] if e["lang"] == "hi" else e["headword_en"]).split(" / ")[0].strip()
            for e in lex}
    hi = [e["entry_id"] for e in lex if e["lang"] == "hi"]
    en = [e["entry_id"] for e in lex if e["lang"] == "en"]
    A, Bv = np.array([vec[i] for i in hi]), np.array([vec[i] for i in en])
    inter = (A[:, None, :] & Bv[None, :, :]).sum(2)
    union = (A[:, None, :] | Bv[None, :, :]).sum(2)
    J = np.where(union > 0, inter / np.where(union > 0, union, 1), np.nan)

    def order(V):
        if len(V) < 2:
            return list(range(len(V)))
        return list(leaves_list(linkage(pdist(V, "jaccard"), "average")))
    ro, co = order(A), order(Bv)
    M = J[np.ix_(ro, co)]
    best = np.nanmax(np.where(np.isnan(J), -1, J), axis=1)
    SUMMARY["G7"] = dict(n_hi=len(hi), n_en=len(en), n_components=len(comps), native_only=sorted(native),
                         zero_vector_entries=int((~A.any(1)).sum() + (~Bv.any(1)).sum()),
                         hi_entries_with_an_identical_en_vector=int((best >= 1).sum()),
                         native_only_best_jaccard={i: round(float(best[hi.index(i)]), 3) for i in sorted(native)},
                         median_best_jaccard_hi=round(float(np.median(best)), 3))
    fig = plt.figure(figsize=(9.0, 9.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[40, 1], wspace=0.03)
    ax, cax = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    cmap = matplotlib.colormaps["cividis"].copy()
    cmap.set_bad("#eeeeee")
    im = ax.imshow(np.ma.masked_invalid(M), aspect="auto", cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
    short = {k: v if len(v) <= 26 else v[:25].rstrip() + "…" for k, v in head.items()}
    ax.set_xticks(range(len(co)), [short[en[c]] for c in co], rotation=90, fontsize=4.6, color=F.INK)
    rlabels = [f"{short[hi[r]]}  {hi[r]}" + ("  ◆" if hi[r] in native else "") for r in ro]
    ax.set_yticks(range(len(ro)), rlabels, fontsize=4.6,
                  fontfamily=F.font_list())
    for t, r in zip(ax.get_yticklabels(), ro):
        if hi[r] in native:
            t.set_color(F.VERMILLION)
            t.set_fontweight("bold")
    ax.tick_params(length=0, pad=1.5)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel(f"English entries ({len(en)}), clustered", fontsize=8)
    ax.set_ylabel(f"Hindi entries ({len(hi)}), clustered", fontsize=8)
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("Jaccard overlap of component vectors", fontsize=7.5)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6.5)
    ax.set_title(f"◆ native-only Hindi entry ({len(native)}): its explication needs a molecule no English entry uses",
                 fontsize=7.5, fontweight="normal", color=F.VERMILLION, loc="left")
    paths = F.save(fig, out, "G7_lexicon_overlap_heatmap", stamp)
    caption("G7_lexicon_overlap_heatmap", "Overlap of the Hindi and English lexicon entries",
            f"Cells: Jaccard overlap |a ∩ b| / |a ∪ b| of the binary component vectors (K = {len(comps)}) of each "
            f"Hindi entry (rows, {len(hi)}) and English entry (columns, {len(en)}); grey = both vectors empty. Each "
            "language's entries are ordered by average-linkage clustering of the Jaccard distances among its own "
            f"vectors. Native-only Hindi entries (◆, vermillion; {len(native)}: the explication needs a molecule no "
            "English entry uses, strict definition, translation_bias.native_only_entries) are marked. "
            f"{SUMMARY['G7']['hi_entries_with_an_identical_en_vector']} of {len(hi)} Hindi entries have an English "
            "entry with an identical component vector; median best overlap per Hindi entry "
            f"{SUMMARY['G7']['median_best_jaccard_hi']:.2f}. Headwords are the lexicon's own (the first variant), "
            "not corpus text.", ["lexicon/entry_vectors.csv", "lexicon/lexicon.csv", "lexicon/molecules.csv"],
            status="frozen lexicon v0.2 (lexicon/FREEZE.md); every entry has status proposed")
    return paths


def cooccurrence():
    comps = components_list(LEX)
    out = {lg: dict(N=0, n=np.zeros(len(comps)), pair=np.zeros((len(comps), len(comps)))) for lg in ("hi", "en")}
    for r in clause_features():
        if not P.flag(r["is_finite"]) or not P.in_split(r["record_id"], "confirmatory"):
            continue
        v = np.array([P.flag(r["comp_" + c]) for c in comps], float)
        o = out[r["lang"]]
        o["N"] += 1
        o["n"] += v
        if v.sum() > 1:
            o["pair"] += np.outer(v, v)
    return comps, out


def pmi_matrix(o):
    N, n, pair = o["N"], o["n"], o["pair"]
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log2(pair * N / np.outer(n, n))
    keep = (pair >= MIN_PAIR) & np.isfinite(pmi) & (pmi >= PMI_MIN)
    np.fill_diagonal(keep, False)
    return pmi, keep


def g8(out, stamp):
    from scipy.cluster.hierarchy import leaves_list, linkage
    comps, co = cooccurrence()
    K = len(comps)
    pm = {lg: pmi_matrix(co[lg]) for lg in co}
    feats = np.hstack([np.nan_to_num(np.where(np.isfinite(pm[lg][0]), pm[lg][0], 0), nan=0) for lg in ("hi", "en")])
    order = list(leaves_list(linkage(feats, "average")))
    ang = {c: np.pi / 2 - 2 * np.pi * i / K for i, c in enumerate(order)}
    pos = {c: (math.cos(ang[c]), math.sin(ang[c])) for c in order}
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 4.0))
    rate_max = max((100 * co[lg]["n"] / co[lg]["N"]).max() for lg in co)
    pmi_max = max(pm[lg][0][pm[lg][1]].max() for lg in co if pm[lg][1].any())
    SUMMARY["G8"] = dict(threshold=dict(pmi_min=PMI_MIN, min_pair_clauses=MIN_PAIR), components=K,
                         node_order=[comps[i] for i in order])
    for ax, lg in zip(axes, ("hi", "en")):
        meta = F.LANG[lg]
        pmi, keep = pm[lg]
        rate = 100 * co[lg]["n"] / co[lg]["N"]
        edges = [(i, j) for i in range(K) for j in range(i + 1, K) if keep[i, j]]
        for i, j in sorted(edges, key=lambda e: pmi[e]):
            w = pmi[i, j] / pmi_max
            ax.plot(*zip(pos[i], pos[j]), color=meta["colour"], lw=0.4 + 2.6 * w, alpha=0.25 + 0.55 * w,
                    solid_capstyle="round", zorder=1)
        for i in range(K):
            x, y = pos[i]
            if rate[i] > 0:
                ax.scatter(x, y, s=8 + 300 * math.sqrt(rate[i] / rate_max), color=meta["colour"], marker=meta["marker"],
                           edgecolor="white", lw=0.6, zorder=3)
            else:
                ax.scatter(x, y, s=12, facecolor="white", edgecolor=F.GREY, lw=0.6, marker=meta["marker"], zorder=3)
            a = ang[i]
            ax.text(1.17 * math.cos(a), 1.17 * math.sin(a), comps[i], fontsize=5.4, color=F.INK,
                    ha="left" if math.cos(a) > 0.15 else "right" if math.cos(a) < -0.15 else "center",
                    va="center", rotation=0)
        ax.set_xlim(-1.75, 1.75)
        ax.set_ylim(-1.35, 1.35)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"({'a' if lg == 'hi' else 'b'}) {meta['name']}: {len(edges)} edges, "
                     f"{co[lg]['N']:,} finite clauses", loc="left", fontsize=8.5)
        SUMMARY["G8"][lg] = dict(finite_clauses=int(co[lg]["N"]), edges=len(edges),
                                 components_absent=[comps[i] for i in range(K) if rate[i] == 0],
                                 top_edges=[dict(a=comps[i], b=comps[j], pmi=round(float(pmi[i, j]), 3),
                                                 clauses=int(co[lg]["pair"][i, j]))
                                            for i, j in sorted(edges, key=lambda e: -pmi[e])[:5]])
    fig.tight_layout()
    paths = F.save(fig, out, "G8_component_networks", stamp)
    caption("G8_component_networks", "Component co-occurrence networks",
            f"Nodes: the K = {K} semantic components, at the same position in both panels (circle ordered by "
            "average-linkage clustering of the two languages' PMI profiles side by side); marker area grows with "
            "the square root of the share of finite clauses carrying the component (open grey = absent in that "
            "language). Edges: pairs of components in the same clause with PMI = log2(n_ab N / (n_a n_b)) ≥ "
            f"{PMI_MIN:g} and at least {MIN_PAIR} clauses together; width and opacity grow with PMI (same scale "
            "in both panels). Confirmatory set, finite clauses: (a) Hindi "
            f"{co['hi']['N']:,} clauses, {SUMMARY['G8']['hi']['edges']} edges; (b) English {co['en']['N']:,} "
            f"clauses, {SUMMARY['G8']['en']['edges']} edges. Descriptive; not a test.",
            ["data/processed/clause_features.csv (comp_* columns)", "data/processed/split.csv"])
    return paths


def run_r(only, out):
    fonts = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    cmd = ["Rscript", str(ROOT / "R" / "figures_v2.R"), "--font-dir", str(fonts), "--out", str(out), "--only",
           ",".join(only), "--root", str(ROOT)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode:
        raise SystemExit(f"R/figures_v2.R failed:\n{res.stderr[-3000:]}")
    return [Path(out) / f"{s}.{e}" for s in (["G2_sankey"] if "G2" in only else []) +
            (["G9_audit_slopes"] if "G9" in only else []) for e in ("pdf", "png")]


def g2_caption():
    j = json.loads((RES / "decompose_relational_confirmatory.json").read_text())
    tot = {lg: j[f"forced_{lg}"] + j[f"chosen_{lg}"] + j[f"nominative_alt_{lg}"] for lg in ("hi", "en")}
    caption("G2_sankey", "Relational sites and what happened at them",
            "Alluvial diagram per language: every relational site in the confirmatory texts (eligibility.csv, "
            f"marker relational; Hindi {tot['hi']:,}, English {tot['en']:,}) flows into forced (honorific plural "
            "for an elder, REL-HON-F: no alternative; Hindi "
            f"{j['forced_hi']:,}, English {j['forced_en']:,}), chosen (the relational option taken where an "
            f"individual one exists; {j['chosen_hi']:,} / {j['chosen_en']:,}) or alternative available, not chosen "
            f"(I / a pronoun / singular reference; {j['nominative_alt_hi']:,} / {j['nominative_alt_en']:,}). Widths "
            "are site counts on one scale for both languages; the gaps between outcome boxes are spacing only. "
            "English has no forced relational sites under the rule table. "
            f"Sites left for review ({j['review_hi']} Hindi, {j['review_en']} English) "
            "are not drawn. The counts are checked against the decomposition's own counts. Values after the "
            "deceased-detection fix (2bd38d6).",
            ["data/processed/eligibility.csv", "data/processed/split.csv",
             "results/decompose_relational_confirmatory.json"])


def g9_caption():
    pairs = read(PROC / "audit_pairs.csv")
    ids = {r["passage_id_hi"] for r in pairs} | {r["passage_id_en"] for r in pairs}
    sc = read(PROC / "audit" / "passage_scores.csv")
    n_cls = {m: len({r["passage_id"] for r in sc if r["model"] == m} & ids) for m in ("xlm_emo", "muril_sent")}
    chat = [r for r in read(RES / "audit_chat_scores.csv") if "llama" in r["system"] and r["cue"] == "none"
            and r["rating"] not in ("", "NA")]
    n_llama = len({r["passage_id"] for r in chat} & ids)
    samples = Counter(r["passage_id"] for r in chat)
    lm = [r for r in read(RES / "audit_lmer.csv") if r["term"] == "hindi" and r["pairs"] == "all"
          and (r["system"] in ("xlm_emo", "muril_sent") or "llama" in r["system"])]
    coef = {("Llama" if "llama" in r["system"] else {"xlm_emo": "XLM-EMO", "muril_sent": "MuRIL"}[r["system"]]):
            (float(r["estimate"]), float(r["ci_lo"]), float(r["ci_hi"])) for r in lm}
    reg = "; ".join(f"{k} {fmt(v[0], 3, True)} [{fmt(v[1], 3)}, {fmt(v[2], 3)}]" for k, v in coef.items())
    caption("G9_audit_slopes", "Machine scores against human-rated intensity",
            f"One panel per system, on the {len(pairs)} matched Hindi–English passage pairs ({len(ids)} passages; "
            "development texts): x = the passage's mean rating by two raters (1–7; reviewed machine-prefilled "
            "ratings), y = the system's score standardised over all its rows as in R/audit.R (XLM-EMO: p(sadness); "
            "MuRIL sentiment: p(negative); Llama 3.1 8B: the 1–7 rating, "
            + ("one sample per passage" if max(samples.values()) == 1 else
               f"mean over {min(samples.values())}–{max(samples.values())} samples")
            + ", both cue conditions in the standardisation, "
            "no-cue condition shown). Points (jittered horizontally by ±0.06) and a least-squares line per language "
            "with its 95% confidence band; Hindi blue circles, English orange squares. Passages per panel: XLM-EMO "
            f"{n_cls['xlm_emo']}, MuRIL {n_cls['muril_sent']}, Llama {n_llama}. The lines are a display aid; the "
            "registered estimate is the hindi coefficient of the mixed model (score_z ~ intensity × hindi + (1 | "
            f"pair); results/audit_lmer.csv): {reg} (negative = under-reading of Hindi).",
            ["data/processed/audit_pairs.csv", "data/processed/audit_ratings.csv",
             "data/processed/audit/passage_scores.csv", "results/audit_chat_scores.csv", "results/audit_lmer.csv"])


EXAMPLES = [
    ("a", "dative (the form used)", "hi", ["मुझे", "दुख", "हुआ"], ["mujhe", "dukh", "hua"],
     ["I.DAT", "grief", "happen.PFV.M.SG"], "‘to me grief happened’ = I felt grief", 0),
    ("a", "nominative alternative", "hi", ["मैं", "दुखी", "हूँ"], ["main", "dukhi", "hoon"],
     ["I.NOM", "sad", "be.PRS.1SG"], "‘I am sad’", None),
    ("a", "English", "en", ["I", "am", "sad"], None, ["I.NOM", "be.PRS.1SG", "sad"], "‘I am sad’", None),
    ("b", "dative (the only frame)", "hi", ["मुझे", "उसकी", "याद", "आती", "है"],
     ["mujhe", "uski", "yaad", "aati", "hai"], ["I.DAT", "3SG.GEN.F", "memory(F)", "come.IPFV.F", "be.PRS.3SG"],
     "‘to me (the) memory of him/her comes’ = I miss him/her", 0),
    ("b", "English", "en", ["I", "miss", "him/her"], None, ["I.NOM", "miss", "3SG.ACC"], "‘I miss him/her’", None),
]


def inventory():
    return {(r["predicate"], r["lang"]): r for r in read(PROC / "predicate_inventory.csv")}


def g10(out, stamp):
    C.register_fonts()
    inv = inventory()
    rules = {"a_hi": inv[("दुख+हो", "hi")], "a_en": inv[("sad", "en")], "b_hi": inv[("याद+आ", "hi")],
             "b_en": inv[("miss", "en")]}
    assert rules["a_hi"]["decision"] == "chosen_dative" and rules["b_hi"]["decision"] == "forced_dative"
    deva = F.font_list()
    fig = plt.figure(figsize=(7.2, 4.75))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 7.2)
    ax.set_ylim(0.65, 5.4)
    ax.axis("off")
    r = fig.canvas.get_renderer()
    inch = fig.dpi

    def width(s, **kw):
        t = ax.text(0, 0, s, **kw)
        w = t.get_window_extent(r).width / inch
        t.remove()
        return w

    def interlinear(x0, y, ex):
        _, label, lg, words, translit, gloss, trans, dat = ex
        colour = F.LANG[lg]["colour"]
        wkw = dict(fontsize=11 if lg == "hi" else 10, fontfamily=deva if lg == "hi" else None)
        tkw, gkw = dict(fontsize=7.5, style="italic"), dict(fontsize=6.8)
        ax.text(x0, y + 0.02, label, fontsize=6.8, color=F.MUTED, va="bottom")
        x = x0
        tiers = [(words, wkw, y - 0.22, colour)] + ([(translit, tkw, y - 0.47, F.INK)] if translit else []) + \
            [(gloss, gkw, y - (0.69 if translit else 0.47), F.INK)]
        for k in range(len(words)):
            w = max(width(t[0][k], **t[1]) for t in tiers) + 0.16
            for items, kw, ty, c in tiers:
                ax.text(x, ty, items[k], va="center", color=c, **kw)
            if dat == k:
                ax.add_patch(FancyBboxPatch((x - 0.05, tiers[-1][2] - 0.13), w - 0.08, y - tiers[-1][2] - 0.02,
                                            boxstyle="round,pad=0.02,rounding_size=0.05", fc="none",
                                            ec=NEUTRAL, lw=0.9))
            x += w
        ax.text(x0, tiers[-1][2] - 0.24, trans, fontsize=7.2, color=F.INK, va="center")
        return x

    def badge(x, y, text, colour):
        ax.text(x, y, text, fontsize=8.5, fontweight="bold", color="white", va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc=colour, ec="none"))

    def rule_note(x, y, lines):
        ax.text(x, y, "\n".join(lines), fontsize=6.6, color=F.INK, va="top", linespacing=1.45,
                fontfamily=deva)

    ax.text(0.15, 5.2, "(a) मुझे दुख हुआ: the dative is chosen; a nominative alternative exists", fontsize=9,
            fontweight="bold", va="center", fontfamily=deva)
    badge(6.15, 5.2, "CHOSEN", NEUTRAL)
    xs = [0.25, 2.55, 4.85]
    for x, ex in zip(xs, EXAMPLES[:3]):
        interlinear(x, 4.8, ex)
    a_hi, a_en = rules["a_hi"], rules["a_en"]
    rule_note(0.25, 3.68, [f"rule {a_hi['rule_id']} ({a_hi['predicate']}): {a_hi['decision']}",
                           f"alternative: {a_hi['alternative']}"])
    rule_note(4.85, 3.68, [f"rule {a_en['rule_id']}, twin {a_en['twin']} ({a_en['predicate']}):",
                           "person subject → nominative"])
    ax.plot([0.15, 7.05], [3.2, 3.2], color=F.RULE, lw=0.8)
    ax.text(0.15, 2.95, "(b) याद आना: the dative is forced; there is no nominative alternative", fontsize=9,
            fontweight="bold", va="center", fontfamily=deva)
    badge(6.2, 2.95, "FORCED", F.INK)
    interlinear(0.25, 2.55, EXAMPLES[3])
    interlinear(4.85, 2.55, EXAMPLES[4])
    b_hi, b_en = rules["b_hi"], rules["b_en"]
    assert b_hi["alternative"].startswith("none") and ("याद+कर", "hi") in inv
    rule_note(0.25, 1.43, [f"rule {b_hi['rule_id']} ({b_hi['predicate']}): {b_hi['decision']}",
                           "alternative: none under the rule table (याद करना is coded as a separate predicate, "
                           "active remembering)"])
    rule_note(4.85, 1.43, [f"rule {b_en['rule_id']} ({b_en['predicate']}):", b_en["decision"]])
    ax.text(7.05, 0.78, "dative experiencer boxed · Hindi blue, English orange · constructed examples, not corpus text",
            fontsize=6.3, color=F.MUTED, ha="right")
    paths = F.save(fig, out, "G10_worked_example", stamp)
    caption("G10_worked_example", "Chosen and forced dative experiencers",
            "Constructed examples (not corpus text) with interlinear glosses (Leipzig conventions: DAT dative, NOM "
            "nominative, GEN genitive, PFV perfective, IPFV imperfective, PRS present, M/F masculine/feminine, SG "
            "singular). (a) मुझे दुख हुआ (mujhe dukh hua, ‘to me grief happened’) frames the experiencer in the "
            "dative (boxed) although the nominative मैं दुखी हूँ (main dukhi hoon, ‘I am sad’) exists, so the "
            f"eligibility rules count it as a chosen site (rule {a_hi['rule_id']}, {a_hi['decision']}); English "
            f"‘I am sad’ is the nominative member of a same-root twin pair (rule {a_en['rule_id']}, twin "
            f"{a_en['twin']}). (b) याद आना (yaad aana, ‘memory comes to me’) has only the dative frame (no alternative under the rule table; "
            f"याद करना is coded as a separate predicate, active remembering), so the site is forced (rule {b_hi['rule_id']}, {b_hi['decision']}); "
            f"English ‘miss’ has only the nominative frame (rule {b_en['rule_id']}). Rule ids and alternatives are "
            "read from the predicate inventory.", ["data/processed/predicate_inventory.csv"],
            status="constructed example; rule table machine-built (eligibility.py), checked against the gold set")
    return paths


DRAW = {"G1": g1, "G3": g3, "G4": g4, "G5": g5, "G6": g6, "G7": g7, "G8": g8, "G10": g10}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", default=",".join(f.split("_")[0] for f in FIGURES))
    ap.add_argument("--out", default=str(ROOT / "figures" / "final"))
    ap.add_argument("--summary", default=str(RES / "figures_v2_summary.json"))
    args = ap.parse_args(argv)
    only = [s.strip() for s in args.only.split(",") if s.strip()]
    F.setup_style()
    stamp = F.stamp_for(RES)
    out = Path(args.out)
    written = []
    for key in [f.split("_")[0] for f in FIGURES if f.split("_")[0] in only]:
        if key in DRAW:
            written += DRAW[key](out, stamp)
        else:
            written += run_r([key], out)
            (g2_caption if key == "G2" else g9_caption)()
        print(f"{key}: done", flush=True)
    if SUMMARY:
        path = Path(args.summary)
        old = json.loads(path.read_text()) if path.exists() else {}
        old.update(SUMMARY)
        path.write_text(json.dumps(old, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in written:
        print(p)


if __name__ == "__main__":
    main()
