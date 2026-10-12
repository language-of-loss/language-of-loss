"""Tables for outputs 1-9, one Markdown file per output, from the result CSVs (real or synthetic); computes nothing new."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble as A
from synthetic_results import is_synthetic, refuse_synthetic_in_real

ROOT = Path(__file__).resolve().parents[2]
SYNTH = "synthetic"
OUT_DIR = "tables_full"
FIGURE_OF = {1: None, 2: ["F2_validation"], 3: ["F3a_decomposition", "F3b_odds_ratios"], 4: ["F3b_odds_ratios"],
             5: ["F5a_audit_underreading", "F5b_audit_components"], 6: None, 7: ["F7_component_profile"], 8: None,
             9: ["F9a_collocation_hi", "F9b_collocation_en"]}
TOP_COLLOCATES = 8


class SyntheticLabeller(A.Labeller):

    def __init__(self):
        self.smoke = True

    def __call__(self, *a, **k):
        return super().__call__(*a, **k).replace(f"({A.SMOKE})", f"({SYNTH})")

    def banner(self):
        return ("> **SYNTHETIC PLACEHOLDER, NOT DATA.** Every number below was drawn by "
                "`src/analysis/synthetic_results.py` from a seeded random generator so that the table layout can be "
                "checked before any result exists. None of it may be quoted anywhere.")


def figure_line(k, figures_dir):
    stems = FIGURE_OF.get(k)
    if not stems:
        return ""
    rel = figures_dir.relative_to(ROOT) if figures_dir.is_relative_to(ROOT) else figures_dir
    return "Figure: " + ", ".join(f"`{rel}/{s}.pdf`" for s in stems) + " (figures.py).\n"


def section(title, header, rows, missing, what):
    out = ["", f"## {title}", ""]
    out.append(A.md_table(header, rows) if rows else A.pending(missing, what))
    return "\n".join(out) + "\n"


def extra2(res, lab):
    d = A.read(res, "corrected_rates_hi_minus_en.csv")
    rows = [[r["measure"], lab(r["diff_observed"], digits=3), lab(r["diff_corrected"], r["lo"], r["hi"], 3),
             r["sign_flip"], lab(r["p_flip"], digits=3), lab(r["recall_gap"], digits=3), r["gap_ok"]]
            for r in d or []]
    return section("2c. Hindi − English, observed and corrected", ["Measure", "Observed difference",
                   "Corrected difference [95% CI]", "Sign flip", "p(flip)", "Recall gap", "Gap ≤ 0.10"], rows,
                   "corrected_rates_hi_minus_en.csv", "corrected_rates.py")


def extra3(res, lab):
    sens = A.read(res, "decompose_relational_dev_drop_largest.csv")
    keep = ("delta", "forced_share", "opportunity_share", "choice_share")
    rows = [[r["variant"], r["quantity"], lab(r["estimate"], r["lo"], r["hi"], signed=True)]
            for r in sens or [] if r["quantity"] in keep and r["variant"] != "all"]
    return section("Decomposition without the largest text (sensitivity)", ["Variant", "Term", "Estimate [95% CI]"],
                   rows, "decompose_relational_dev_drop_largest.csv", "decompose.py")


def _read_opt(res, name):
    return A.read(res, name) or A.read(Path(res) / "optional", name)


def extra7(res, lab):
    prof = _read_opt(res, "p2_component_profile.csv") or []
    lo = _read_opt(res, "p2_component_logodds.csv") or []
    share = {(r["lang"], r["component"]): r for r in prof}
    rows = []
    for r in sorted(lo, key=lambda r: -(A.num(r["delta"]) or 0)):
        h, e = share.get(("hi", r["component"]), {}), share.get(("en", r["component"]), {})
        d, sd = A.num(r["delta"]), A.num(r["sd"])
        ci = (d - 1.959964 * sd, d + 1.959964 * sd) if d is not None and sd is not None else (None, None)
        rows.append([r["component"], lab(h.get("profile_share"), digits=3), lab(e.get("profile_share"), digits=3),
                     f"{r['count_hi']} / {r['count_en']}", lab(d, *ci, digits=2, signed=True), lab(r["z"], digits=2)])
    return section("Component profile and log-odds (positive δ = more Hindi; interval δ ± 1.96 sd)",
                   ["Component", "Share hi", "Share en", "Clauses hi / en", "δ [95%]", "z"], rows,
                   "p2_component_logodds.csv", "predictions_extra.py (component profile)")


def output9(res, lab, figures_dir):
    out = A.head(9, "Collocation networks (appendix exhibit of the lexicon candidate-generation step)", lab, [
        "collocation.py, dev split: PMI in a ±5-word window around every lexicon entry with ≥ 10 matched clauses. "
        "Exploratory: an instrument description, not a test.", "", figure_line(9, figures_dir)])
    pmi = A.read(res, "collocation_pmi.csv")
    if not pmi:
        return "\n".join(out) + "\n" + A.pending("collocation_pmi.csv", "collocation.py") + "\n"
    for lang in ("hi", "en"):
        by = {}
        for r in pmi:
            if r["lang"] == lang and (A.num(r["pmi"]) or 0) > 0:
                by.setdefault((r["entry_id"], r["headword"], r["entry_clauses"]), []).append(r)
        rows = [[eid, hw, n, ", ".join(f"{c['collocate']} ({float(c['pmi']):.2f})" for c in
                                      sorted(rs, key=lambda c: -float(c["pmi"]))[:TOP_COLLOCATES])]
                for (eid, hw, n), rs in sorted(by.items())]
        out += ["", f"## {A.LANG[lang]}: top {TOP_COLLOCATES} collocates per entry (PMI, log2)", "",
                A.md_table(["Entry", "Headword", "Matched clauses", "Collocates (PMI)"], rows) if rows else
                f"*No {A.LANG[lang]} pairs with PMI > 0.*"]
    return "\n".join(out) + "\n"


def tables(res, lab, figures_dir):
    def fig(k, text):
        line = figure_line(k, figures_dir)
        if not line:
            return text
        head, sep, rest = text.partition("\n\n")
        banner, sep2, rest2 = rest.partition("\n\n")
        return f"{head}{sep}{banner}{sep2}{line}\n{rest2}"

    return {
        "Output1_agreement.md": A.output1(res, lab),
        "Output2_validation.md": fig(2, A.output2(res, lab)) + extra2(res, lab),
        "Output3_hypothesis.md": fig(3, A.hypothesis_table(3, res, lab, "", "Hypothesis: Run 1 / Run 2 / Run 2b "
                                                           "odds ratios and the decomposition",
                                                           "decompose_relational_dev.csv")) + extra3(res, lab),
        "Output4_rival_check.md": fig(4, A.output4(res, lab)),
        "Output5_audit.md": fig(5, A.output5(res, lab)),
        "Output6_dative_choice.md": A.output6(res, lab),
        "Output7_jsd.md": fig(7, A.output7(res, lab)) + extra7(res, lab),
        "Output8_translation.md": A.output8(res, lab),
        "Output9_collocation.md": output9(res, lab, figures_dir),
    }


def build(results, out=None, figures_dir=None):
    refuse_synthetic_in_real(results)
    synthetic = is_synthetic(results)
    lab = SyntheticLabeller() if synthetic else A.Labeller(results)
    figures_dir = Path(figures_dir or ROOT / "figures" / ("synthetic" if synthetic else "final"))
    out = Path(out or Path(results) / OUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    docs = tables(str(results), lab, figures_dir)
    for name, text in docs.items():
        (out / name).write_text(text, encoding="utf-8")
    return out, docs, synthetic


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=None, help=f"default: <results>/{OUT_DIR}")
    ap.add_argument("--figures", default=None, help="where figures.py wrote (for the Figure: lines)")
    args = ap.parse_args(argv)
    out, docs, synthetic = build(args.results, args.out, args.figures)
    print(f"{len(docs)} tables -> {out}; label: {SYNTH if synthetic else 'assemble.Labeller'}")


if __name__ == "__main__":
    main()
