"""Final figures for outputs 1-9, drawn only from the result CSVs the core steps write (nothing is re-estimated)."""
import argparse
import csv
import logging
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.transforms import offset_copy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from predictions import tests_allowed
from synthetic_results import is_synthetic, refuse_synthetic_in_real

ROOT = Path(__file__).resolve().parents[2]
AGREEMENT = Path("agreement") / "agreement_summary_gold_sheet_v1.csv"
SERIF = ["TeX Gyre Termes", "Nimbus Roman", "Nimbus Roman No9 L", "STIXGeneral", "STIX Two Text", "Times New Roman",
         "Times"]
DEVANAGARI_SERIF = ["Tiro Devanagari Hindi", "Noto Serif Devanagari", "Kohinoor Devanagari", "Devanagari Sangam MN"]
DPI = 300
BLUE, ORANGE, VERMILLION, GREEN, SKY, PURPLE, GREY = ("#0072B2", "#E69F00", "#D55E00", "#009E73", "#56B4E9",
                                                       "#CC79A7", "#999999")
INK, MUTED, RULE = "#1a1a1a", "#5f5f5f", "#d9d9d9"
CHOICE = "#1b7837"
LANG = {"hi": dict(name="Hindi", colour=BLUE, marker="o"), "en": dict(name="English", colour=ORANGE, marker="s")}
TERMS = [("delta", "Δ (gap)", INK, ""), ("forced_share", "forced", GREY, "///"),
         ("opportunity_share", "opportunity", SKY, ".."), ("choice_share", "choice", CHOICE, "")]
RUNS = [("run1", "Run 1\nall finite clauses"), ("run2", "Run 2\nforced relational out"),
        ("run2b", "Run 2b\nhonorific elders out too"), ("rF6", "R-F6 (robustness)\nRun 2, closing formulae out")]
ESTIMATORS = [("glmer", "GLMM (conditional)", INK, "o", True), ("CR2", "GLM + CR2 (marginal)", VERMILLION, "s", False)]
OR_PANELS = [("", ""), ("_rival", "Output 4: rival check (+ diaspora, platform)")]
OR_TICKS = [0.25, 0.33, 0.5, 0.67, 0.8, 1, 1.25, 1.5, 2, 3, 4]
STAMP_SYNTHETIC = "SYNTHETIC PLACEHOLDER — NOT DATA"
STAMP_SMOKE = "DEV SMOKE — NOT A RESULT"


class Missing(Exception):
    pass


def font_list():
    names = {f.name for f in font_manager.fontManager.ttflist}
    latin = [f for f in SERIF if f in names] or ["DejaVu Serif"]
    return latin + [f for f in DEVANAGARI_SERIF if f in names] + ["DejaVu Serif"]


def setup_style():
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    plt.rcParams.update({
        "font.family": font_list(), "mathtext.fontset": "stix", "font.size": 8.5, "axes.titlesize": 9.5,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.labelsize": 8.5, "axes.labelcolor": INK,
        "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": RULE, "grid.linewidth": 0.4, "axes.axisbelow": True,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK, "ytick.labelcolor": INK,
        "xtick.major.width": 0.5, "ytick.major.width": 0.5, "legend.frameon": False, "legend.fontsize": 7.5,
        "savefig.dpi": DPI, "savefig.bbox": "tight", "savefig.pad_inches": 0.04, "pdf.fonttype": 42,
        "ps.fonttype": 42, "figure.dpi": 100})


def read(results, name, optional_dir=False):
    for d in ([Path(results), Path(results) / "optional"] if optional_dir else [Path(results)]):
        p = d / name
        if p.exists():
            with open(p, encoding="utf-8", newline="") as fh:
                return list(csv.DictReader(fh))
    raise Missing(name)


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def statuses(rows):
    return sorted({r.get("status", "") for r in rows if r.get("status")})


def save(fig, out, stem, stamp):
    if stamp:
        top = max(ax.get_position().y1 for ax in fig.axes)
        fig.text(0.995, top, stamp, ha="right", va="bottom", fontsize=8, fontweight="bold", color=VERMILLION,
                 transform=offset_copy(fig.transFigure, fig=fig, y=20, units="points"))
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext, meta in (("pdf", {"CreationDate": None, "Producer": None}), ("png", {"Software": None})):
        p = out / f"{stem}.{ext}"
        fig.savefig(p, format=ext, metadata=meta)
        paths.append(p)
    plt.close(fig)
    return paths


def wilson(k, n, z=1.959964):
    if not n:
        return None, None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def zero_line(ax, x=0, vertical=True):
    (ax.axvline if vertical else ax.axhline)(x, color=MUTED, lw=0.7, zorder=1)


def fig_decomposition(results):
    stem = ("decompose_relational_confirmatory" if (Path(results) / "decompose_relational_confirmatory.csv").exists()
            else "decompose_relational_dev")
    rows = {r["quantity"]: r for r in read(results, f"{stem}.csv")}
    try:
        sens = [r for r in read(results, f"{stem}_drop_largest.csv") if r["variant"] != "all"]
    except Missing:
        sens = []
    panels = [("Relational marking, Hindi − English", rows, sens)]
    fig, axes = plt.subplots(1, len(panels), figsize=(4.2, 2.9), sharey=True, squeeze=False)
    for ax, (title, rows, sens) in zip(axes[0], panels):
        x = np.arange(len(TERMS))
        for i, (q, label, colour, hatch) in enumerate(TERMS):
            r = rows.get(q)
            e, lo, hi = (num(r["estimate"]), num(r["lo"]), num(r["hi"])) if r else (None, None, None)
            if e is None:
                continue
            ax.bar(i, e, width=0.62, color=colour if q != "delta" else "white", edgecolor=colour if q != "delta"
                   else INK, hatch=hatch, lw=0.8, zorder=2)
            if lo is not None and hi is not None:
                ax.errorbar(i, e, yerr=[[e - lo], [hi - e]], fmt="none", ecolor=INK, elinewidth=0.9, capsize=3,
                            zorder=3)
            ax.annotate(f"{e:+.1f}".replace("-", "−"), (i, hi if (hi is not None and e >= 0) else (lo or e)),
                        xytext=(0, 3 if e >= 0 else -4), textcoords="offset points", ha="center",
                        va="bottom" if e >= 0 else "top", fontsize=7, color=INK)
            for j, s in enumerate(r2 for r2 in sens if r2["quantity"] == q):
                v = num(s["estimate"])
                if v is not None:
                    ax.plot(i + 0.2 + 0.07 * j, v, marker="D", ms=3.2, mfc="white", mec=INK, mew=0.6, ls="none",
                            zorder=4)
        zero_line(ax, vertical=False)
        ax.margins(y=0.14)
        ax.set_xticks(x, [t[1] for t in TERMS])
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    axes[0][0].set_ylabel("Hindi − English, per 100 finite clauses")
    handles = [Line2D([], [], color=INK, marker="|", ls="none", ms=8, label="95% bootstrap interval (texts)"),
               Line2D([], [], marker="D", ms=3.5, mfc="white", mec=INK, ls="none",
                      label="largest text dropped (hi, en, both)")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2)
    srcs = [r for _, rows, _ in panels for r in rows.values()]
    return fig, ("Decomposition of the Hindi − English gap in relational marking, Δ = forced + opportunity + choice "
                 "(per 100 finite clauses; choice = headline statistic), with 95% intervals from 2,000 bootstrap "
                 "resamples of texts; open diamonds re-estimate each term without the largest Hindi text, the "
                 "largest English text, and both.", [f"{stem}*.csv"], statuses(srcs))


def fig_odds_ratios(results):
    panels = []
    for suffix, title in OR_PANELS:
        rows = []
        for run, _ in RUNS:
            try:
                rows += [dict(r, run=run) for r in read(results, f"h1_glmm_{run}{suffix}.csv") if r["term"] == "hindi"]
            except Missing:
                pass
        if rows:
            panels.append((title, rows))
        elif not suffix:
            raise Missing("h1_glmm_run1.csv")
    fig, axes = plt.subplots(1, len(panels), figsize=(3.6 * len(panels), 3.0), sharex=True, sharey=True,
                             squeeze=False)
    for ax, (title, rows) in zip(axes[0], panels):
        for k, (key, label, colour, marker, filled) in enumerate(ESTIMATORS):
            for i, (run, _) in enumerate(RUNS):
                r = next((r for r in rows if r["run"] == run and key in r["estimator"]), None)
                if not r or num(r["estimate"]) is None:
                    continue
                y = len(RUNS) - 1 - i + (0.14 if k == 0 else -0.14)
                e, lo, hi = math.exp(num(r["estimate"])), num(r["ci_lo"]), num(r["ci_hi"])
                if lo is not None and hi is not None:
                    ax.plot([math.exp(lo), math.exp(hi)], [y, y], color=colour, lw=1.1, zorder=2)
                ax.plot(e, y, marker=marker, ms=4.5, color=colour, mfc=colour if filled else "white", mew=1,
                        ls="none", zorder=3)
        zero_line(ax, 1)
        ax.set_xscale("log")
        ax.set_yticks(range(len(RUNS)), [lab for _, lab in reversed(RUNS)])
        ax.set_ylim(-0.6, len(RUNS) - 0.4)
        ax.set_title(title)
        ax.set_xlabel("odds ratio, Hindi vs English (log scale)")
        ax.grid(axis="y", visible=False)
        ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator(OR_TICKS))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    handles = [Line2D([], [], color=c, marker=m, mfc=c if f else "white", lw=1.1, label=lab)
               for _, lab, c, m, f in ESTIMATORS]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2)
    return fig, ("Odds ratio for Hindi (relational ~ hindi + log clauses + loss type + (1 | text)) in Run 1, Run 2 "
                 "(clauses with a forced relational site removed), Run 2b (honorific reference to elders removed as "
                 "well) and the R-F6 robustness check (Run 2 without closing formulae); right panel, when present: "
                 "the output-4 rival check with diaspora and platform added. GLMM conditional effect with Wald 95% CI "
                 "and population-averaged GLM with CR2 cluster-robust 95% CI (Satterthwaite df).",
                 ["h1_glmm_*.csv"], statuses([r for _, rs in panels for r in rs]))


def fig_components(results):
    prof = read(results, "p2_component_profile.csv", optional_dir=True)
    lo = {r["component"]: r for r in read(results, "p2_component_logodds.csv", optional_dir=True)}
    try:
        jsd = read(results, "p2_jsd.csv")[0]
    except (Missing, IndexError):
        jsd = None
    share = {(r["lang"], r["component"]): num(r["profile_share"]) for r in prof}
    comps = sorted(lo, key=lambda c: num(lo[c]["delta"]) or 0)
    y = np.arange(len(comps))
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.0, 0.19 * len(comps) + 1.3), sharey=True,
                               gridspec_kw=dict(width_ratios=[1, 1.15], wspace=0.08))
    for c_i, c in enumerate(comps):
        vals = [share.get((lang, c)) for lang in ("hi", "en")]
        if None not in vals:
            a.plot(vals, [c_i, c_i], color=RULE, lw=1.2, zorder=1)
    for lang, st in LANG.items():
        a.plot([share.get((lang, c), np.nan) for c in comps], y, marker=st["marker"], ms=4, ls="none",
               color=st["colour"], label=st["name"], zorder=2)
    a.set_yticks(y, [c.replace("_", " ").lower() for c in comps])
    a.set_xlabel("share of the language's component hits")
    a.set_title("Profile")
    a.legend(loc="lower right")
    a.set_xlim(left=0)
    for i, c in enumerate(comps):
        d, sd = num(lo[c]["delta"]), num(lo[c]["sd"])
        if d is None:
            continue
        colour = BLUE if d > 0 else ORANGE
        strong = sd is not None and abs(d) > 1.959964 * sd
        if sd is not None:
            b.plot([d - 1.959964 * sd, d + 1.959964 * sd], [i, i], color=colour, lw=1.0, alpha=1 if strong else 0.5)
        b.plot(d, i, marker="o" if d > 0 else "s", ms=4, color=colour, mfc=colour if strong else "white", mew=1,
               ls="none")
    zero_line(b)
    b.set_xlabel("log-odds δ, Hindi vs English (± 1.96 sd)")
    b.set_title("Log-odds")
    lim = max(abs(v) for v in b.get_xlim())
    b.set_xlim(-lim, lim)
    b.text(0.98, 0.01, "more Hindi →", transform=b.transAxes, ha="right", va="bottom", fontsize=7, color=BLUE)
    b.text(0.02, 0.01, "← more English", transform=b.transAxes, ha="left", va="bottom", fontsize=7, color=ORANGE)
    for ax in (a, b):
        ax.grid(axis="y", visible=False)
    if jsd and num(jsd["estimate"]) is not None:
        a.annotate(f"Jensen–Shannon divergence {num(jsd['estimate']):.3f} [{num(jsd['lo']):.3f}, "
                   f"{num(jsd['hi']):.3f}] (base 2, text bootstrap)", xy=(0, 1), xycoords="axes fraction",
                   xytext=(0, 16), textcoords="offset points", fontsize=8.5, color=MUTED, va="bottom")
    return fig, (f"Component profiles of the {len(comps)} semantic components by language (left) and the log-odds "
                 "with an informative Dirichlet prior (right; δ ± 1.96 sd, filled where the interval excludes 0, "
                 "positive = more frequent in Hindi); components ordered by δ. The title gives the JSD between the "
                 "two profiles with its text-bootstrap 95% interval.",
                 ["p2_component_profile.csv", "p2_component_logodds.csv", "p2_jsd.csv"],
                 statuses(prof + list(lo.values())))


def fig_audit_underreading(results):
    lm = read(results, "audit_lmer.csv")
    systems = list(dict.fromkeys(r["system"] for r in lm))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 0.42 * len(systems) + 1.2), sharey=True)
    for ax, term, title in ((axes[0], "hindi", "Under-reading (hindi, no cue)"),
                            (axes[1], "hindi:cue", "Cue effect (hindi × cue)")):
        for i, s in enumerate(systems):
            y0 = len(systems) - 1 - i
            rows = [r for r in lm if r["system"] == s and r["term"] == term]
            if not rows:
                ax.text(0, y0, "no cue condition", ha="center", va="center", fontsize=7, color=MUTED,
                        style="italic")
                continue
            for r in rows:
                agreed = r["pairs"] == "agreed"
                y = y0 + (-0.14 if agreed else 0.14)
                e, lo, hi = num(r["estimate"]), num(r["ci_lo"]), num(r["ci_hi"])
                if lo is not None and hi is not None:
                    ax.plot([lo, hi], [y, y], color=INK, lw=1.0)
                ax.plot(e, y, "o", ms=4.5, color=INK, mfc="white" if agreed else INK, mew=1)
        zero_line(ax)
        ax.set_title(title)
        ax.set_xlabel("difference in standardised score (SD)")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(systems)), list(reversed(systems)))
    axes[0].set_ylim(-0.6, len(systems) - 0.4)
    handles = [Line2D([], [], color=INK, marker="o", lw=1, label="all pairs"),
               Line2D([], [], color=INK, marker="o", mfc="white", lw=1, label="agreed pairs (raters within 1 point)")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2)
    return fig, ("Audit, per system: the Hindi − English difference in standardised score at mean human-rated "
                 "intensity without the culture cue (left; negative = Hindi under-read) and its change when the cue "
                 "'the writer is in India' is given (right), from score_z ~ intensity × hindi × cue + (1 | pair); "
                 "Wald 95% intervals. Off-the-shelf classifiers have no cue condition.", ["audit_lmer.csv"],
            statuses(lm))


def fig_audit_components(results):
    st = read(results, "audit_stability.csv")
    systems = list(dict.fromkeys(r["system"] for r in st))
    try:
        sys.path.insert(0, str(ROOT / "lexicon" / "src"))
        from components import K_IDS
        order = [c for c in K_IDS if any(r["component"] == c for r in st)]
    except ImportError:
        order = []
    order += [c for c in dict.fromkeys(r["component"] for r in st) if c not in order]
    m = np.full((len(order), len(systems)), np.nan)
    stable = np.zeros_like(m, dtype=bool)
    for r in st:
        i, j = order.index(r["component"]), systems.index(r["system"])
        m[i, j] = num(r["selection_freq"])
        stable[i, j] = str(r["stable"]).strip().lower() in ("true", "1")
    thr = num(st[0].get("threshold")) if st else None
    fig, ax = plt.subplots(figsize=(1.0 * len(systems) + 2.6, 0.2 * len(order) + 1.2))
    im = ax.imshow(m, cmap="cividis", vmin=0, vmax=1, aspect="auto")
    for i, j in zip(*np.nonzero(stable)):
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=VERMILLION, lw=1.6))
        ax.text(j, i, "●", ha="center", va="center", fontsize=6, color="white")
    ax.set_xticks(range(len(systems)), systems, rotation=25, ha="right")
    ax.set_yticks(range(len(order)), [c.replace("_", " ").lower() for c in order])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03)
    cb.set_label("selection frequency")
    cb.outline.set_visible(False)
    if thr is not None:
        cb.ax.axhline(thr, color=VERMILLION, lw=1.2)
    ax.set_title("Stable under-read components (Hindi passages)")
    return fig, ("Stability selection of the machine error (standardised score − standardised human intensity) on "
                 "the passage component profile, per system (Hindi passages of the matched pairs, no cue): selection "
                 f"frequency over subsamples; outlined cells are stable under-read components (frequency ≥ "
                 f"{thr if thr is not None else 'threshold'} and negative full-data coefficient; line on the colour "
                 "bar = threshold).", ["audit_stability.csv"], statuses(st))


def fig_validation(results):
    vt = [r for r in read(results, "validation_table.csv") if r["channel"] == "dict" and r["lang"] in LANG]
    if not vt:
        raise Missing("validation_table.csv (no dict rows)")
    try:
        from gold import CODEBOOK
        fields = [f for f in CODEBOOK if any(r["field"] == f for r in vt)]
    except ImportError:
        fields = []
    fields += [f for f in dict.fromkeys(r["field"] for r in vt) if f not in fields]
    ncol = min(4, len(fields))
    nrow = math.ceil(len(fields) / ncol)
    heights = [max(len({r["value"] for r in vt if r["field"] == f}) for f in fields[k * ncol:(k + 1) * ncol])
               for k in range(nrow)]
    fig, axes = plt.subplots(nrow, ncol, figsize=(7.2, 0.3 * sum(heights) + 0.9 * nrow), squeeze=False,
                             gridspec_kw=dict(height_ratios=heights, hspace=0.5, wspace=0.95))
    for k, f in enumerate(fields):
        ax = axes[k // ncol][k % ncol]
        rows = [r for r in vt if r["field"] == f]
        values = list(dict.fromkeys(r["value"] for r in rows))
        for vi, v in enumerate(values):
            y0 = len(values) - 1 - vi
            for lang, off in (("hi", 0.18), ("en", -0.18)):
                r = next((r for r in rows if r["value"] == v and r["lang"] == lang), None)
                if not r:
                    continue
                tp, fp, fn = (int(float(r[c] or 0)) for c in ("tp", "fp", "fn"))
                for (k_, n_), marker, filled in (((tp, tp + fp), LANG[lang]["marker"], True),
                                                 ((tp, tp + fn), "^", False)):
                    p, lo, hi = wilson(k_, n_)
                    if p is None:
                        continue
                    dy = 0.07 if filled else -0.07
                    ax.plot([lo, hi], [y0 + off + dy] * 2, color=LANG[lang]["colour"], lw=0.8,
                            alpha=0.9 if filled else 0.6)
                    ax.plot(p, y0 + off + dy, marker=marker, ms=3.6, ls="none", color=LANG[lang]["colour"],
                            mfc=LANG[lang]["colour"] if filled else "white", mew=0.9)
        ax.set_yticks(range(len(values)), [v.replace("_", " ") for v in reversed(values)], fontsize=7.5)
        ax.set_ylim(-0.6, len(values) - 0.4)
        ax.set_xlim(-0.03, 1.03)
        ax.set_xticks([0, 0.5, 1], ["0", ".5", "1"])
        ax.set_title(f.replace("_", " "), fontsize=8.5)
        ax.grid(axis="y", visible=False)
    for k in range(len(fields), nrow * ncol):
        axes[k // ncol][k % ncol].set_visible(False)
    handles = [Line2D([], [], color=BLUE, marker="o", lw=0.8, label="Hindi precision"),
               Line2D([], [], color=BLUE, marker="^", mfc="white", lw=0.8, label="Hindi recall"),
               Line2D([], [], color=ORANGE, marker="s", lw=0.8, label="English precision"),
               Line2D([], [], color=ORANGE, marker="^", mfc="white", lw=0.8, label="English recall")]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.06), ncol=4)
    return fig, ("Dictionary channel against the adjudicated gold set: precision (filled) and recall (open "
                 "triangles) per codebook category and language, with Wilson 95% intervals computed from the tp, "
                 "fp and fn counts of validation_table.csv (one-vs-rest per category).", ["validation_table.csv"],
            statuses(vt))


def fig_collocation(results, lang, top=8):
    import collocation as C
    rows = [dict(r, pmi=float(r["pmi"])) for r in read(results, "collocation_pmi.csv") if r["lang"] == lang]
    if not rows:
        raise Missing(f"collocation_pmi.csv (no {lang} rows)")
    g = C.build_graph(rows, lang, top)
    pos = C.mds_layout(g)
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    pmis = [d["pmi"] for _, _, d in g.edges(data=True)]
    pmax = max(pmis) if pmis else 1
    for a_, b_, d in g.edges(data=True):
        (x0, y0), (x1, y1) = pos[a_], pos[b_]
        ax.plot([x0, x1], [y0, y1], color=GREY, lw=0.3 + 1.4 * d["pmi"] / pmax, alpha=0.55, zorder=1)
    for n, d in g.nodes(data=True):
        x, y = pos[n]
        if d["kind"] == "entry":
            ax.plot(x, y, "o", ms=6.5, color=VERMILLION, mec="white", mew=0.6, zorder=3)
            ax.annotate(d["label"], (x, y), xytext=(4, 3), textcoords="offset points", fontsize=9, fontweight="bold",
                        color=INK, zorder=4)
        else:
            ax.plot(x, y, "s", ms=3.2, color=BLUE, zorder=2)
            ax.annotate(d["label"], (x, y), xytext=(3, -2), textcoords="offset points", fontsize=7, color=MUTED,
                        zorder=4)
    ax.set_xticks([]), ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    n_entries = sum(1 for _, d in g.nodes(data=True) if d["kind"] == "entry")
    name = LANG[lang]["name"]
    ax.set_title(f"{name}: {n_entries} lexicon entries, {g.number_of_nodes() - n_entries} collocates")
    handles = [Line2D([], [], marker="o", color=VERMILLION, ls="none", ms=6, label="lexicon entry"),
               Line2D([], [], marker="s", color=BLUE, ls="none", ms=3.5, label="collocate (lemma)"),
               Line2D([], [], color=GREY, lw=1.4, label="edge width ∝ PMI")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3)
    return fig, (f"{name} collocation network (appendix exhibit): lexicon entries and their top {top} collocates by "
                 "PMI in a ±5-word window; positions from metric MDS of shortest-path distances with edge length "
                 "1/PMI. Exploratory instrument description, not a test.", ["collocation_pmi.csv"], [])


FIGURES = [
    ("F3a_decomposition", 3, "a", fig_decomposition),
    ("F3b_odds_ratios", 3, "b", fig_odds_ratios),
    ("F7_component_profile", 7, "c", fig_components),
    ("F5a_audit_underreading", 5, "d", fig_audit_underreading),
    ("F5b_audit_components", 5, "e", fig_audit_components),
    ("F2_validation", 2, "f", fig_validation),
    ("F9a_collocation_hi", 9, "g", lambda res: fig_collocation(res, "hi")),
    ("F9b_collocation_en", 9, "g", lambda res: fig_collocation(res, "en")),
]


def stamp_for(results):
    if is_synthetic(results):
        return STAMP_SYNTHETIC
    return "" if tests_allowed(Path(results) / AGREEMENT) else STAMP_SMOKE


def build(results, out):
    refuse_synthetic_in_real(results)
    setup_style()
    stamp = stamp_for(results)
    written, pending, captions = {}, {}, []
    for stem, output, _, builder in FIGURES:
        try:
            fig, (caption, sources, status) = builder(results)
        except Missing as e:
            pending[stem] = str(e)
            captions.append(f"## {stem} (output {output})\n\n*Pending: `{e}` does not exist.*\n")
            continue
        written[stem] = save(fig, Path(out), stem, stamp)
        label = f" **{stamp}.**" if stamp else ""
        captions.append(f"## {stem} (output {output})\n\n{caption}{label}\n\nSource: "
                        + ", ".join(f"`{s}`" for s in sources)
                        + (f" (status: {'; '.join(status)})" if status else "") + ".\n")
    (Path(out) / "captions.md").write_text(
        f"# Figure captions, outputs 1-9\n\nGenerated by `src/analysis/figures.py` from `{rel(results)}`. "
        "Regenerate; do not edit by hand.\n\n" + "\n".join(captions), encoding="utf-8")
    return written, pending, stamp


def rel(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=None, help="default: figures/final, or figures/synthetic for synthetic results")
    args = ap.parse_args(argv)
    out = args.out or str(ROOT / "figures" / ("synthetic" if is_synthetic(args.results) else "final"))
    Path(out).mkdir(parents=True, exist_ok=True)
    written, pending, stamp = build(args.results, out)
    print(f"{len(written)} figures (pdf + png, {DPI} dpi) -> {rel(out)}; stamp: {stamp or 'none'}")
    for stem, missing in pending.items():
        print(f"  pending {stem}: {missing} missing")


if __name__ == "__main__":
    main()
