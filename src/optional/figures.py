"""Draft figures from the dev smoke outputs; every figure is stamped \"DEV SMOKE — NOT A RESULT\"."""
import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from gold import split_of
from predictions import boot_ratio

ROOT = Path(__file__).resolve().parents[2]
STAMP = "DEV SMOKE — NOT A RESULT"
LANG_COLOUR = {"hi": "#0072B2", "en": "#E69F00"}
LANG_NAME = {"hi": "Hindi (हिंदी)", "en": "English"}
INK, MUTED, GRID = "#222222", "#666666", "#e6e6e6"
COMPONENT_STYLE = {"forced_share": ("forced", "#4d4d4d", ""), "opportunity_share": ("opportunity", "#9a9a9a", "//"),
                   "choice_share": ("choice", "#d9d9d9", "..")}
CLASSES = ["self", "kin", "community", "deceased", "God", "impersonal", "other"]


def setup_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from collocation import font_family
    plt.rcParams.update({"font.family": font_family() + ["DejaVu Sans"], "font.size": 9, "axes.edgecolor": MUTED,
                         "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
                         "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                         "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
                         "savefig.dpi": 200, "savefig.bbox": "tight"})
    return plt


def stamp(fig):
    fig.text(0.995, 0.995, STAMP, ha="right", va="top", fontsize=8, fontweight="bold", color="#8b0000",
             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#8b0000", lw=0.8))


def save(fig, path):
    stamp(fig)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def flag(v):
    return str(v).strip() in ("1", "True", "true", "1.0")


def wilson(k, n, z=1.96):
    if n == 0:
        return math.nan, math.nan
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def in_split(rid, split):
    return split == "all" or split_of(rid) == split


def fmt(est, lo, hi, d=2):
    return f"{est:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]"


def quantities(path):
    return {r["quantity"]: (float(r["estimate"]), float(r["lo"]), float(r["hi"])) for r in read_csv(path)}


def relational_counts(referent_rows, eligibility_rows, split):
    forced = {r["clause_id"] for r in eligibility_rows if r.get("marker_type") == "relational"
              and r["decision"] == "forced_relational"}
    lang = {r["clause_id"]: r["lang"] for r in eligibility_rows}
    out = {"hi": defaultdict(Counter), "en": defaultdict(Counter)}
    for r in referent_rows:
        cid = r["clause_id"]
        rid = cid.split("#")[0]
        lg = lang.get(cid)
        if lg not in out or not in_split(rid, split):
            continue
        c = out[lg][rid]
        rel = flag(r["relational"])
        c["n"] += 1
        c["rel"] += rel
        if cid not in forced:
            c["n_s"] += 1
            c["rel_s"] += rel
    return out


def referent_counts(referent_rows, eligibility_rows, split):
    lang = {r["clause_id"]: r["lang"] for r in eligibility_rows}
    out = {"hi": defaultdict(Counter), "en": defaultdict(Counter)}
    for r in referent_rows:
        rid = r["clause_id"].split("#")[0]
        lg = lang.get(r["clause_id"])
        if lg in out and in_split(rid, split):
            out[lg][rid]["n"] += 1
            out[lg][rid][r["referent_class"]] += 1
    return out


def fig1(plt, counts, out, B):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    cap = {}
    for ax, (key_n, key_k, title) in zip(axes, (("n", "rel", "Full: all finite clauses"),
                                                ("n_s", "rel_s", "Stripped: no forced_relational clauses"))):
        x0 = 0
        for lg in ("hi", "en"):
            texts = sorted(counts[lg], key=lambda t: counts[lg][t][key_k] / max(counts[lg][t][key_n], 1))
            xs = np.arange(x0, x0 + len(texts))
            for x, t in zip(xs, texts):
                n, k = counts[lg][t][key_n], counts[lg][t][key_k]
                if n:
                    lo, hi = wilson(k, n)
                    ax.plot([x, x], [lo, hi], color=LANG_COLOUR[lg], lw=1, alpha=0.6)
                    ax.plot(x, k / n, "o", ms=4, color=LANG_COLOUR[lg], mec="white", mew=0.6)
            est, lo, hi = boot_ratio([counts[lg][t][key_k] for t in texts], [counts[lg][t][key_n] for t in texts], B)
            if len(xs):
                ax.fill_between([xs[0] - 0.4, xs[-1] + 0.4], lo, hi, color=LANG_COLOUR[lg], alpha=0.15, lw=0)
                ax.plot([xs[0] - 0.4, xs[-1] + 0.4], [est, est], color=LANG_COLOUR[lg], lw=2,
                        label=f"{LANG_NAME[lg]}: pooled {est:.2f} [{lo:.2f}, {hi:.2f}]")
            cap[(title.split(":")[0], lg)] = (est, lo, hi, len(texts))
            x0 += len(texts) + 2
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.set_xticks([])
        ax.set_xlabel("texts (sorted within language)")
        ax.set_ylim(0, 1)
        ax.legend(loc="upper left", fontsize=8)
    axes[0].set_ylabel("relational share of finite clauses")
    fig.suptitle("Relational share per text (dots: Wilson 95% CI; band: text-bootstrap 95% CI)", x=0.01, ha="left",
                 fontsize=11, color=INK)
    return save(fig, out), cap


def fig1b(plt, counts, out, B):
    fig, ax = plt.subplots(figsize=(8, 4))
    width, cap = 0.38, {}
    y = np.arange(len(CLASSES))
    for j, lg in enumerate(("hi", "en")):
        texts = sorted(counts[lg])
        den = [counts[lg][t]["n"] for t in texts]
        vals = [boot_ratio([counts[lg][t][c] for t in texts], den, B) for c in CLASSES]
        est = np.array([100 * v[0] for v in vals])
        err = np.array([[100 * (v[0] - v[1]) for v in vals], [100 * (v[2] - v[0]) for v in vals]])
        pos = y + (j - 0.5) * width
        ax.barh(pos, est, height=width - 0.04, color=LANG_COLOUR[lg], label=LANG_NAME[lg])
        ax.errorbar(est, pos, xerr=err, fmt="none", ecolor=INK, elinewidth=0.9, capsize=2)
        for c, v in zip(CLASSES, vals):
            cap[(c, lg)] = tuple(100 * x for x in v)
    ax.set_yticks(y, CLASSES)
    ax.invert_yaxis()
    ax.set_xlabel("clauses per 100 finite clauses (referent class of the subject/experiencer)")
    ax.legend(loc="lower right")
    ax.set_title("Referent density by class and language (text-bootstrap 95% CI)", loc="left", fontsize=11, color=INK)
    return save(fig, out), cap


def fig2(plt, panels, out):
    fig, axes = plt.subplots(1, len(panels), figsize=(5.2 * len(panels), 4.2), squeeze=False)
    cap = {}
    for ax, (name, q) in zip(axes[0], panels):
        pos_base = neg_base = 0.0
        for key, (label, colour, hatch) in COMPONENT_STYLE.items():
            v = q[key][0]
            base = pos_base if v >= 0 else neg_base
            ax.bar(0, v, bottom=base, width=0.6, color=colour, hatch=hatch, edgecolor="white", lw=1.2, label=label)
            if v >= 0:
                pos_base += v
            else:
                neg_base += v
        xs = [1.2, 2.0, 2.8, 3.8]
        keys = list(COMPONENT_STYLE) + ["delta"]
        for x, key in zip(xs, keys):
            est, lo, hi = q[key]
            colour = COMPONENT_STYLE[key][1] if key in COMPONENT_STYLE else INK
            ax.errorbar(x, est, yerr=[[est - lo], [hi - est]], fmt="o", color=colour, mec=INK, mew=0.6, ms=7,
                        ecolor=INK, elinewidth=1, capsize=3)
            cap[(name, key)] = (est, lo, hi)
        ax.plot(0, q["delta"][0], marker="_", ms=26, mew=2.5, color=INK)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xticks([0] + xs, ["stacked\n(point)", "forced", "opportunity", "choice", "D = hi − en"])
        ax.set_ylabel("per 100 finite clauses")
        ax.set_title(f"{name} marking: D = {fmt(*q['delta'])}", loc="left", fontsize=10, color=INK)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=8)
    fig.suptitle("Decomposition of the Hindi − English gap (markers: text-bootstrap 95% CI)", x=0.01, ha="left",
                 fontsize=11, color=INK)
    return save(fig, out), cap


def fig3(plt, choice, logodds, out):
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw=dict(width_ratios=[1, 1.3]))
    rows = [("dative_choice_rate", "chosen dative among\neligible sites (choice)"),
            ("forced_baseline_dative_share", "dative share where the\ngrammar decides (forced baseline)")]
    cap = {}
    for i, (key, label) in enumerate(rows):
        r = choice[key]
        est, lo, hi = float(r["estimate"]), float(r["lo"]), float(r["hi"])
        a.barh(i, est, height=0.55, color=LANG_COLOUR["hi"] if i == 0 else "#9ecae1")
        a.errorbar(est, i, xerr=[[est - lo], [hi - est]], fmt="none", ecolor=INK, capsize=3)
        a.text(min(hi + 0.02, 0.98), i, f"{r['k']}/{r['n']}", va="center", fontsize=8, color=MUTED)
        cap[key] = (est, lo, hi, r["k"], r["n"])
    a.set_yticks(range(len(rows)), [r[1] for r in rows])
    a.invert_yaxis()
    a.set_xlim(0, 1)
    a.set_xlabel("share (Hindi, text-bootstrap 95% CI)")
    a.set_title("Hindi dative choice vs forced baseline", loc="left", fontsize=10, color=INK)
    order = sorted(logodds, key=lambda r: (r["delta"] == "", float(r["delta"] or 0)))
    for i, r in enumerate(order):
        if r["delta"] == "":
            b.text(0.5, i, f"n/a — {r.get('note', '').removeprefix('n/a: ')}", ha="center", va="center", fontsize=8,
                   color=MUTED, transform=b.get_yaxis_transform())
            cap[r["category"]] = "n/a"
            continue
        d, sd = float(r["delta"]), float(r["sd"])
        colour = LANG_COLOUR["hi"] if d > 0 else LANG_COLOUR["en"]
        b.errorbar(d, i, xerr=1.96 * sd, fmt="o", color=colour, ecolor=colour, ms=6, capsize=3)
        b.text(d, i - 0.22, f"z {float(r['z']):.1f}", ha="center", va="bottom", fontsize=7, color=MUTED)
        cap[r["category"]] = (d, d - 1.96 * sd, d + 1.96 * sd, float(r["z"]))
    b.axvline(0, color=MUTED, lw=0.8)
    b.set_ylim(-0.6, len(order) - 0.4)
    b.invert_yaxis()
    b.set_yticks(range(len(order)), [r["category"].replace("_", " ") for r in order])
    b.set_xlabel("weighted log-odds, Hindi vs English (± 1.96 sd)\n← more English        more Hindi →")
    b.set_title("POS profile of emotional predication", loc="left", fontsize=10, color=INK)
    return save(fig, out), cap


def fig4(plt, profile, logodds, residue, jsd_row, out):
    lo_by = {r["component"]: r for r in logodds}
    comps = sorted(lo_by, key=lambda c: float(lo_by[c]["delta"]))
    share = {(r["lang"], r["component"]): float(r["profile_share"]) for r in profile}
    totals = {lg: sum(int(r["clauses"]) for r in profile if r["lang"] == lg) for lg in ("hi", "en")}
    res = {(r["lang"], r["residue"]): r for r in residue}
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 7.5), sharey=True, gridspec_kw=dict(width_ratios=[1.2, 1]))
    y = np.arange(len(comps))
    for j, lg in enumerate(("hi", "en")):
        pos = y + (j - 0.5) * 0.4
        a.barh(pos, [share.get((lg, c), 0) for c in comps], height=0.36, color=LANG_COLOUR[lg], label=LANG_NAME[lg])
    gf = res.get(("hi", "grammar_forced_component_clauses"))
    cap = {}
    if gf and int(gf["count"]) and "HAPPEN_TO" in comps and totals["hi"]:
        i = comps.index("HAPPEN_TO")
        base = share.get(("hi", "HAPPEN_TO"), 0)
        extra = int(gf["count"]) / totals["hi"]
        a.barh(i - 0.2, extra, left=base, height=0.36, color="white", edgecolor=LANG_COLOUR["hi"], hatch="////",
               lw=0.8, label="residue: grammar-forced HAPPEN_TO (gf_, not in profile)")
        cap["gf_residue_hi"] = (int(gf["count"]), extra)
    a.set_yticks(y, [c.replace("_", " ") for c in comps])
    a.set_xlabel("share of component hits (profile)")
    a.legend(loc="lower right", fontsize=8)
    a.set_title("Component profiles", loc="left", fontsize=10, color=INK)
    for i, c in enumerate(comps):
        d, sd = float(lo_by[c]["delta"]), float(lo_by[c]["sd"])
        colour = LANG_COLOUR["hi"] if d > 0 else LANG_COLOUR["en"]
        b.errorbar(d, i, xerr=1.96 * sd, fmt="o", color=colour, ecolor=colour, ms=4, capsize=2, elinewidth=0.9)
        cap[c] = (d, d - 1.96 * sd, d + 1.96 * sd, float(lo_by[c]["z"]))
    b.axvline(0, color=MUTED, lw=0.8)
    b.set_xlabel("weighted log-odds, Hindi vs English (± 1.96 sd)\n← more English        more Hindi →")
    b.set_title("Per-component log-odds", loc="left", fontsize=10, color=INK)
    lines = ["Residue (not in the profile)"]
    for lg in ("hi", "en"):
        for key, label in (("emotion_sites_in_unmatched_clauses", "emotion sites, no lexicon match"),
                           ("matched_clauses_without_component", "matched, no component"),
                           ("grammar_forced_component_clauses", "grammar-forced component clauses")):
            r = res.get((lg, key))
            if r:
                lines.append(f"{lg}: {label} {r['count']}/{r['denominator']}")
                cap[(lg, key)] = (int(r["count"]), int(r["denominator"]))
    fig.text(0.01, -0.01, lines[0] + ": " + "; ".join(lines[1:4]) + "\n" + " " * 28 + "; ".join(lines[4:]),
             fontsize=8, color=INK, va="top")
    j = (float(jsd_row["estimate"]), float(jsd_row["lo"]), float(jsd_row["hi"]))
    cap["jsd"] = j
    fig.suptitle(f"Component profiles by language; JSD (base 2) = {fmt(*j, d=3)}, text-bootstrap 95% CI",
                 x=0.01, ha="left", fontsize=11, color=INK)
    return save(fig, out), cap


def found(res, name):
    p = Path(res) / name
    return p if p.exists() or not (Path(res) / "optional" / name).exists() else Path(res) / "optional" / name


def captions(caps, sources):
    c1, c1b, c2, c3, c4 = (caps.get(k, {}) for k in ("fig1", "fig1b", "fig2", "fig3", "fig4"))
    L = ["# Figure captions (draft)", "",
         f"All figures are stamped **{STAMP}**: dev split only, machine-provisional unreviewed labels. No figure carries a "
         "p value: the binomial test and the beta regression are refused until "
         "`results/agreement/agreement_summary.csv` exists (study protocol; same guard as R/common.R). The interval each "
         "caption must carry is given with it; copy numbers only via RESULTS_LOG.md.", "",
         "Sources: " + "; ".join(f"`{k}` {v}" for k, v in sources.items()), ""]
    if c1:
        L += ["## fig1_relational_share.png", "",
              "Relational share of finite clauses per text (dots, Wilson 95% intervals) and pooled per language "
              "(line and band, text-bootstrap 95% interval). Left: all finite clauses; right: stripped of clauses "
              "with a grammar-forced relational site. Must carry: " + "; ".join(
                  f"{part} {LANG_NAME[lg]} {fmt(*c1[(part, lg)][:3])} ({c1[(part, lg)][3]} texts)"
                  for part in ("Full", "Stripped") for lg in ("hi", "en") if (part, lg) in c1) + ".", ""]
    if c1b:
        L += ["## fig1b_referent_density.png", "",
              "Clauses per 100 finite clauses by referent class of the subject/experiencer, per language, with "
              "text-bootstrap 95% intervals. Must carry: " + "; ".join(
                  f"{c} hi {fmt(*c1b[(c, 'hi')], d=1)} / en {fmt(*c1b[(c, 'en')], d=1)}" for c in CLASSES
                  if (c, "hi") in c1b) + ".", ""]
    if c2:
        names = sorted({k[0] for k in c2})
        L += ["## fig2_decomposition.png", "",
              "Decomposition of the Hindi − English gap D (per 100 finite clauses) into forced, opportunity "
              "(eligibility) and choice shares; stacked bar = point estimates, markers = text-bootstrap 95% "
              "intervals. Panels: " + ", ".join(names) + ". Must carry: " + "; ".join(
                  f"{n}: D {fmt(*c2[(n, 'delta')])}, forced {fmt(*c2[(n, 'forced_share')])}, opportunity "
                  f"{fmt(*c2[(n, 'opportunity_share')])}, choice {fmt(*c2[(n, 'choice_share')])}" for n in names)
              + ".", ""]
    if c3:
        d = c3.get("dative_choice_rate")
        f = c3.get("forced_baseline_dative_share")
        L += ["## fig3_dative_choice.png", "",
              "Left: Hindi dative-choice rate among eligible experiencer sites against the forced baseline (dative "
              "share where the grammar decides), text-bootstrap 95% intervals. Right: weighted log-odds (informative "
              "Dirichlet prior, Monroe et al. 2008) of emotional-predication categories per token, Hindi vs English, "
              "± 1.96 sd. English emotion nouns are 0 by construction (no noun predicates in the English rules). "
              "Must carry: " + (f"choice {fmt(*d[:3])} ({d[3]}/{d[4]}), baseline {fmt(*f[:3])} ({f[3]}/{f[4]}); "
                                if d and f else "") + "; ".join(
                  f"{k.replace('_', ' ')} delta {v[0]:.2f} [{v[1]:.2f}, {v[2]:.2f}] (z {v[3]:.1f})"
                  for k, v in c3.items() if k not in ("dative_choice_rate", "forced_baseline_dative_share")
                  and v != "n/a")
              + "".join(f"; {k.replace('_', ' ')}: n/a (0 by construction in one language)" for k, v in c3.items()
                        if v == "n/a")
              + ". No binomial p (refused).", ""]
    if c4:
        j = c4.get("jsd")
        tops = sorted(((k, v) for k, v in c4.items() if isinstance(k, str) and k.isupper()),
                      key=lambda kv: -abs(kv[1][3]))[:5]
        L += ["## fig4_components.png", "",
              "Component profiles (share of component hits) per language and per-component weighted log-odds "
              "(± 1.96 sd). Hatched: grammar-forced HAPPEN_TO hits kept apart by matcher rule R2 (residue, not in "
              "the profile); footnote: the other residue counts. Must carry: JSD " + (fmt(*j, d=3) if j else "n/a")
              + " (text-bootstrap 95% CI); largest |z|: " + "; ".join(
                  f"{k} {v[0]:.2f} [{v[1]:.2f}, {v[2]:.2f}]" for k, v in tops) + "; residue " + "; ".join(
                  f"{k[0]} {k[1].replace('_', ' ')} {v[0]}/{v[1]}" for k, v in c4.items() if isinstance(k, tuple))
              + ".", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--processed", default=str(ROOT / "data" / "processed"))
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out-dir", default=str(ROOT / "figures" / "optional"))
    ap.add_argument("--split", default="dev", choices=["dev", "confirmatory", "all"])
    ap.add_argument("--B", type=int, default=2000)
    args = ap.parse_args(argv)
    plt = setup_style()
    proc, res, out = Path(args.processed), Path(args.results), Path(args.out_dir)
    refs, elig = read_csv(proc / "referents.csv"), read_csv(proc / "eligibility.csv")
    caps, written, sources = {}, [], {}

    p, caps["fig1"] = fig1(plt, relational_counts(refs, elig, args.split), out / "fig1_relational_share.png", args.B)
    written.append(p)
    p, caps["fig1b"] = fig1b(plt, referent_counts(refs, elig, args.split), out / "fig1b_referent_density.png", args.B)
    written.append(p)
    sources["fig1/1b"] = "data/processed/referents.csv + eligibility.csv"

    dat = found(res, f"decompose_{args.split}.csv")
    rel = [res / f"decompose_relational_{args.split}.csv"]
    rel = [r for r in rel if r.exists()]
    panels = [("dative", quantities(dat))] + [("relational", quantities(r)) for r in rel]
    p, caps["fig2"] = fig2(plt, panels, out / "fig2_decomposition.png")
    written.append(p)
    sources["fig2"] = ", ".join([f"results/{dat.name}"] + [f"results/{r.name}" for r in rel])
    for name in ("p1_choice.csv", "p1_pos_logodds.csv", "p2_component_profile.csv", "p2_component_logodds.csv",
                 "p2_residue.csv", "p2_jsd.csv"):
        splits = {r.get("split", args.split) for r in read_csv(found(res, name))}
        if splits != {args.split}:
            raise SystemExit(f"{name} is for split {sorted(splits)}, not {args.split}: rerun predictions.py")

    choice = {r["quantity"]: r for r in read_csv(res / "p1_choice.csv")}
    p, caps["fig3"] = fig3(plt, choice, read_csv(found(res, "p1_pos_logodds.csv")), out / "fig3_dative_choice.png")
    written.append(p)
    sources["fig3"] = "results/p1_choice.csv, p1_pos_logodds.csv"

    p, caps["fig4"] = fig4(plt, read_csv(found(res, "p2_component_profile.csv")), read_csv(found(res, "p2_component_logodds.csv")),
                           read_csv(found(res, "p2_residue.csv")), read_csv(res / "p2_jsd.csv")[0],
                           out / "fig4_components.png")
    written.append(p)
    sources["fig4"] = "results/p2_component_profile.csv, p2_component_logodds.csv, p2_residue.csv, p2_jsd.csv"
    elig_hash = next((r.get("eligibility_sha256", "") for r in read_csv(res / "p1_choice.csv")), "")
    if elig_hash:
        sources["P1/P2 eligibility.csv sha256"] = elig_hash[:16] + "…"
    (out / "captions.md").write_text(captions(caps, sources) + "\n", encoding="utf-8")
    written.append(out / "captions.md")
    for p in written:
        print(p)
    return written


if __name__ == "__main__":
    main()
