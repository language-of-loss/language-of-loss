"""Assemble outputs 1-9 of the core pipeline: one table per output, the collocation figures, and the headline."""
import argparse
import csv
import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SMOKE = "dev smoke"
AGREEMENT_FILE = "agreement_summary_gold_sheet_v1.csv"
COMPONENTS_FILE = "agreement_summary_gold_components_v1.csv"
PAPER = "docs/paper/Paper_Draft_v4_Full.md"
FIGURES = {"colloc_hi.png": "FigureB1a_collocation_hi.png", "colloc_en.png": "FigureB1b_collocation_en.png"}
RUNS = ("run1", "run2", "run2b", "rF6")
RUN_LABEL = {"run1": "Run 1 (all finite clauses)", "run2": "Run 2 (forced relational clauses removed)",
             "run2b": "Run 2b (Run 2 with honorific reference to elders also treated as forced)",
             "rF6": "R-F6 robustness (Run 2 and closing-formula clauses removed)"}
NOT_ESTIMABLE_4 = ("Registered as not estimable from text-internal evidence (decision 2026-10-10): no text states the "
                   "writer's home language, so English-dominant writers cannot be identified from the texts. Rival "
                   "check instead: Runs 1, 2, 2b and R-F6 with diaspora and platform added as covariates. Limitation: "
                   "the second-language detachment account is not tested directly.")
DECOMP_TERMS = [("r", "r_L", "markers per 100 finite clauses"), ("f", "f_L", "forced markers per 100 clauses"),
                ("q", "q_L", "choice sites per 100 clauses"), ("p", "p_L", "share of choice sites taken relationally")]
DECOMP_SHARES = [("delta", "Δ", "gap r_hi − r_en"), ("forced_share", "forced", "(f_hi − f_en)"),
                 ("opportunity_share", "opportunity", "(q_hi − q_en)·p̄"), ("choice_share", "choice", "q̄·(p_hi − p_en)")]
LANG = {"hi": "Hindi", "en": "English"}


def read(results, name):
    path = Path(results) / name
    if not path.exists():
        return None
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def decomp_file(results):
    return ("decompose_relational_confirmatory.csv" if (Path(results) / "decompose_relational_confirmatory.csv").exists()
            else "decompose_relational_dev.csv")


def corrected_file(results):
    return ("corrected_rates_confirmatory.csv" if (Path(results) / "corrected_rates_confirmatory.csv").exists()
            else "corrected_rates.csv")


class Labeller:

    def __init__(self, results):
        from predictions import tests_allowed
        self.smoke = not tests_allowed(Path(results) / "agreement" / AGREEMENT_FILE)
        self.provenance = ""
        agr = Path(results) / "agreement" / AGREEMENT_FILE
        if not self.smoke and agr.exists():
            rows = list(csv.DictReader(open(agr, encoding="utf-8")))
            self.provenance = rows[0].get("provenance", "") if rows else ""

    def __call__(self, est, lo=None, hi=None, digits=2, pct=False, signed=False):
        e = num(est)
        if e is None:
            return "—"
        if signed:
            f = lambda v: (f"{v:+.{digits}f}" if v else f"{0:.{digits}f}").replace("-", "−")
        else:
            f = (lambda v: f"{100 * v:.{digits}f}%") if pct else (lambda v: f"{v:.{digits}f}")
        s = f(e)
        if num(lo) is not None and num(hi) is not None:
            g = (lambda v: f"{v:.{digits}f}".replace("-", "−")) if signed else f
            s += f" [{g(num(lo))}, {g(num(hi))}]"
        return s + (f" ({SMOKE})" if self.smoke else "")

    def p(self, value):
        v = num(value)
        if v is None:
            return "—"
        s = "p < 0.0001" if v < 1e-4 else f"p = {v:.4f}"
        return s + (f" ({SMOKE})" if self.smoke else "")

    def banner(self):
        if self.smoke:
            return (f"> **{SMOKE.upper()}: not results.** `results/agreement/{AGREEMENT_FILE}` holds no agreement "
                    "statistics, so every number below is a development-split smoke value from machine-provisional, "
                    "unreviewed labels (study protocol). Do not copy into the paper except through RESULTS_LOG.md.")
        if self.provenance:
            return ("> **Reviewed machine-prefilled labels.** Agreement summary present; provenance of every gold "
                    f"label and rating: {self.provenance}. Agreement is between two machine runs, not independent human "
                    "coding (study protocol, 2026-10-11). Numbers carry the status of their source CSV.")
        return "> Agreement summary present: numbers carry the status of their source CSV."


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pending(name, what):
    return f"*Pending: `results/{name}` does not exist ({what}).*"


def by_quantity(rows):
    return {r["quantity"]: r for r in rows} if rows else {}


def head(k, title, lab, extra=()):
    return [f"# Output {k}. {title}", "", lab.banner(), ""] + list(extra)


def output1(results, lab):
    out = head(1, "Gold-set inter-coder agreement (Krippendorff's α, nominal, per field)", lab,
               ["Source: `results/agreement/agreement_summary_*.csv` (agreement.py on the two investigators' blind "
                "sheets). Threshold 0.70 per variable (draft v4 §3.4).", ""])
    for name, title in ((AGREEMENT_FILE, "Codebook fields (600-clause gold set)"),
                        (COMPONENTS_FILE, "Semantic components (200-clause subset)")):
        rows = read(Path(results) / "agreement", name)
        out += [f"## {title}", ""]
        if not rows:
            out += [pending(f"agreement/{name}", "the two coded sheets do not exist yet"), ""]
            continue
        out += [md_table(["Field", "Units", "Coded by both", "Raw agreement %", "α (nominal)", "α ≥ 0.70",
                          "Out of codebook"],
                         [[r["field"], r["n_units"], r["n_both_coded"], r["pct_agree"] or "—",
                           lab(r["alpha_nominal"], digits=3),
                           "—" if num(r["alpha_nominal"]) is None else ("yes" if num(r["alpha_nominal"]) >= 0.70 else "no"),
                           r["n_out_of_codebook"]] for r in rows]), ""]
    return "\n".join(out) + "\n"


def output2(results, lab):
    out = head(2, "Dictionary channel: precision and recall per category per language; Rogan–Gladen corrected rates",
               lab, ["Sources: `results/validation_table.csv` (validate.py, channel = dict, against the adjudicated "
                     "gold set), `results/corrected_rates.csv` (corrected_rates.py → rae.py: π = (o − φ)/(s − φ), "
                     "double bootstrap).", ""])
    vt = read(results, "validation_table.csv")
    out += ["## 2a. Precision, recall (sensitivity), false-positive rate", ""]
    if vt:
        rows = [r for r in vt if r["channel"] == "dict" and r["lang"] in ("hi", "en")]
        out += ["Source status: " + "; ".join(sorted({r["status"] for r in rows})) + ".", "",
                md_table(["Variable", "Category", "Language", "Gold n", "Precision", "Recall", "F1",
                          "False-positive rate"],
                         [[r["field"], r["value"], LANG[r["lang"]], r["n_pos"], lab(r["precision"]), lab(r["recall"]),
                           lab(r["f1"]), lab(r["fpr"])] for r in rows])]
    else:
        out.append(pending("validation_table.csv", "needs the adjudicated gold sheet"))
    cr = read(results, corrected_file(results))
    out += ["", "## 2b. Corrected rates (Rogan–Gladen)", ""]
    if cr:
        out += [md_table(["Measure", "Language", "Observed o", "Corrected π [95% CI]", "s", "φ", "Flags", "Status"],
                         [[r["measure"], r["lang"], lab(r["observed"], digits=3),
                           lab(r["corrected"], r["lo"], r["hi"], 3), lab(r["sensitivity"], digits=3),
                           lab(r["fpr"], digits=3), r.get("flags", ""), r["status"]] for r in cr])]
    else:
        out.append(pending("corrected_rates.csv", "needs validated sensitivity and FPR from the gold set"))
    return "\n".join(out) + "\n"


def decomposition_rows(results, name, lab):
    rows = read(results, name)
    if rows is None:
        return None, None
    q = by_quantity(rows)
    meta_path = Path(results) / name.replace(".csv", ".json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    out = []
    for key, sym, desc in DECOMP_TERMS:
        for lang in ("hi", "en"):
            r = q.get(f"{key}_{lang}")
            if r:
                out.append([sym, desc, LANG[lang], lab(r["estimate"], r["lo"], r["hi"]), meta.get(f"n_{lang}", ""),
                            meta.get(f"n_texts_{lang}", "")])
    for key, sym, desc in DECOMP_SHARES:
        r = q.get(key)
        if r:
            out.append([sym, desc, "Hindi − English", lab(r["estimate"], r["lo"], r["hi"]),
                        f"{meta.get('n_hi', '')} / {meta.get('n_en', '')}",
                        f"{meta.get('n_texts_hi', '')} / {meta.get('n_texts_en', '')}"])
    return out, meta


def odds_ratio_rows(results, suffix, lab):
    rows = []
    for run in RUNS:
        for r in read(results, f"h1_glmm_{run}{suffix}.csv") or []:
            if r["term"] != "hindi":
                continue
            lo, hi = num(r.get("ci_lo")), num(r.get("ci_hi"))
            rows.append([RUN_LABEL[run], r["estimator"],
                         lab(math.exp(num(r["estimate"])), math.exp(lo) if lo is not None else None,
                             math.exp(hi) if hi is not None else None),
                         lab(r["p"], digits=4), r["n_clauses"], r["n_texts"], r["split"]])
    return rows


def hypothesis_table(k, results, lab, suffix, title, decomp_name):
    out = head(k, title, lab, [
        "Draft v4 §3.6: relational ~ hindi + log(clauses) + loss_type + (1 | text) (R/h1_glmm.R; odds ratio for "
        "hindi, GLMM and CR2 cluster-robust GLM); decomposition r_L = f_L + q_L·p_L, Δ = forced + opportunity + "
        "choice, 95% intervals by bootstrap over texts (2,000). The choice share is the headline statistic.", ""])
    out += ["## Odds ratios (hindi)", ""]
    ors = odds_ratio_rows(results, suffix, lab)
    out += [md_table(["Run", "Estimator", "Odds ratio [95% CI]", "p", "Clauses", "Texts", "Split"], ors) if ors else
            pending(f"h1_glmm_run1{suffix}.csv", "R/h1_glmm.R --run is refused until the agreement summary exists"
                    + ("; the English-home subset also needs human-confirmed home-language metadata" if suffix else "")),
            ""]
    rows, meta = decomposition_rows(results, decomp_name, lab)
    out += ["## Decomposition (relational marker)", ""]
    if rows is None:
        out += [pending(decomp_name, "decompose.py --marker relational")]
    else:
        out += [f"Source: `results/{decomp_name}`; split {meta.get('split', '?')}, unit {meta.get('unit', '?')}, "
                f"status {meta.get('status', '?')}.", "",
                md_table(["Symbol", "Quantity", "Language", "Estimate [95% CI]", "Finite clauses (denominator)",
                          "Texts"], rows)]
    return "\n".join(out) + "\n"


def output4(results, lab):
    out = head(4, "Second-language rival: not estimable from text-internal evidence; rival check", lab,
               [NOT_ESTIMABLE_4, ""])
    rows = odds_ratio_rows(results, "_rival", lab)
    out += ["## Odds ratios (hindi), with diaspora + platform covariates", "",
            md_table(["Run", "Estimator", "Odds ratio [95% CI]", "p", "Clauses", "Texts", "Split"], rows) if rows else
            pending("h1_glmm_run1_rival.csv", "R/h1_glmm.R --run --covariates rival: needs the agreement summary, the "
                    "registration and human-confirmed diaspora values")]
    return "\n".join(out) + "\n"


def output5(results, lab):
    out = head(5, "Audit: under-reading per system, cue interaction, stable under-read components", lab, [
        "R/audit.R: score_z ~ intensity_c × hindi × cue + (1 | pair) per system (intensity = mean human rating, "
        "centred; cue 0 = none, 1 = 'the writer is in India'); the hindi coefficient is the under-reading at mean "
        "intensity without the cue, hindi:cue the cue interaction. Re-run on the agreed pairs (both raters within 1 "
        "point). Stable under-read components: lasso + stability selection of the error on the component profile.",
        ""])
    lm = read(results, "audit_lmer.csv")
    out += ["## Under-reading and cue interaction", ""]
    if lm:
        out += [md_table(["System", "Pairs", "Term", "Estimate [95% CI]", "p", "Pairs (n)", "Status"],
                         [[r["system"], r["pairs"], r["term"], lab(r["estimate"], r["ci_lo"], r["ci_hi"], 3),
                           lab(r["p"], digits=4), r["n_pairs"], r["status"]]
                          for r in lm if r["term"] in ("hindi", "hindi:cue")])]
    else:
        out.append(pending("audit_lmer.csv", "needs the two filled rating sheets, audit_match.py and R/audit.R --run"))
    st = read(results, "audit_stability.csv")
    out += ["", "## Stable under-read components (Hindi)", ""]
    if st:
        out += [md_table(["System", "Component", "Selection frequency", "Coefficient (full data)", "Stable"],
                         [[r["system"], r["component"], lab(r["selection_freq"], digits=2),
                           lab(r["full_data_coef"], digits=3), r["stable"]] for r in st])]
    else:
        out.append(pending("audit_stability.csv", "R/audit.R --run"))
    return "\n".join(out) + "\n"


def output6(results, lab):
    out = head(6, "Chosen-dative rate against the forced baseline (P1)", lab, [
        "predictions.py: chosen_dative / (chosen_dative + chosen_nominative) over Hindi experiencer sites, against "
        "forced_dative / (forced_dative + forced_nominative); exact binomial test only behind the agreement guard.",
        ""])
    p1 = read(results, "p1_choice.csv")
    out += [md_table(["Quantity", "Language", "Estimate [95% CI]", "k / n", "Texts", "Test", "p", "Status"],
                     [[r["quantity"], r["lang"], lab(r["estimate"], r["lo"], r["hi"], 3), f"{r['k']} / {r['n']}",
                       r["n_texts"], r["test"] or "—", lab(r["p"], digits=4) if r["p"] else "—", r["status"]]
                      for r in p1]) if p1 else pending("p1_choice.csv", "predictions.py")]
    return "\n".join(out) + "\n"


def output7(results, lab):
    out = head(7, "Component-profile divergence (Jensen–Shannon, base 2)", lab)
    j = read(results, "p2_jsd.csv")
    out += [md_table(["Quantity", "Estimate [95% CI]", "Components", "Texts hi / en", "Note", "Status"],
                     [[r["quantity"], lab(r["estimate"], r["lo"], r["hi"], 3), r["n_components"],
                       f"{r['n_texts_hi']} / {r['n_texts_en']}", r["note"], r["status"]] for r in j])
            if j else pending("p2_jsd.csv", "predictions.py")]
    return "\n".join(out) + "\n"


def output8(results, lab):
    out = head(8, "NRC-Hindi against the native lexicon; the MuRIL classifier pair", lab)
    rr = read(results, "a1_resource_recall.csv")
    out += ["## 8a. Recall on native-only versus translatable items", ""]
    out += [md_table(["Native-only definition", "Resource", "Quantity", "Estimate [95% CI]", "Items", "Status"],
                     [[r.get("definition") or "—", r["resource"], r["quantity"],
                       lab(r["estimate"], r["lo"], r["hi"], 3), r["n_items"], r["status"]]
                      for r in sorted(rr, key=lambda r: r.get("definition") == "tolerated")])
            if rr else pending("a1_resource_recall.csv", "translation_bias.py")]
    mc = read(results, "mcnemar_muril.csv")
    out += ["", "## 8b. MuRIL trained on translated data versus on native data (McNemar)", ""]
    out += [md_table(["Quantity", "Value", "Status"], [[r["quantity"], r["value"], r["status"]] for r in mc])
            if mc else pending("mcnemar_muril.csv", "needs both models' predictions on held-out native Hindi gold "
                                                    "clauses (src/analysis/train_muril_pair.py) and mcnemar.py")]
    return "\n".join(out) + "\n"


def output9(results, figures, lab):
    out = head(9, "Collocation networks (appendix exhibit of the lexicon candidate-generation step)", lab, [
        "collocation.py, dev split: PMI in a ±5-word window around every lexicon entry with ≥ 10 matched clauses. "
        "Exploratory: an instrument description, not a test.", ""])
    out += [md_table(["Figure", "Source", "Present"],
                     [[dst, f"figures/{src}", "yes" if (Path(figures) / src).exists() else "no"]
                      for src, dst in FIGURES.items()])]
    pmi = read(results, "collocation_pmi.csv")
    if pmi:
        out += ["", f"Pairs behind the figures: {sum(1 for r in pmi if r.get('lang') == 'hi')} Hindi, "
                    f"{sum(1 for r in pmi if r.get('lang') == 'en')} English (`results/collocation_pmi.csv`)."]
    return "\n".join(out) + "\n"


SHARE_MEANING = {
    "forced": ("forced_share", "Hindi has more grammatically forced relational markers per 100 clauses than English",
               "Hindi has fewer grammatically forced relational markers per 100 clauses than English"),
    "opportunity": ("opportunity_share",
                    "Hindi offers more unforced relational choice sites per 100 clauses once its forced sites are "
                    "removed",
                    "Hindi offers fewer unforced relational choice sites per 100 clauses once its forced sites are "
                    "removed"),
    "choice": ("choice_share", "Hindi writers take the relational option at a larger share of the choice sites "
                               "available to them",
               "Hindi writers take the relational option at a smaller share of the choice sites available to them"),
}


def describe(row, positive, negative, lab):
    e, lo, hi = num(row["estimate"]), num(row["lo"]), num(row["hi"])
    text = lab(e, lo, hi, digits=1, signed=True)
    if e == 0:
        return text + ", meaning no difference"
    meaning = positive if e > 0 else negative
    if lo is not None and hi is not None and lo <= 0 <= hi:
        return text + f", a point estimate meaning {meaning}; the interval includes zero, so the sign is not established"
    return text + f", meaning {meaning}"


def gap_sentence(rel, lab):
    parts = [f"Relational marking was {lab(rel['r_hi']['estimate'], digits=1)} per 100 clauses in Hindi and "
             f"{lab(rel['r_en']['estimate'], digits=1)} in English; the gap Δ was "
             + describe(rel["delta"], "relational marking is more frequent in Hindi",
                        "relational marking is less frequent in Hindi", lab) + "."]
    for term, (key, pos, neg) in SHARE_MEANING.items():
        parts.append(f"The {term} share was " + describe(rel[key], pos, neg, lab) + ".")
    return " ".join(parts)


def _q(results, name, quantity, lang=None):
    for r in read(results, name) or []:
        if r.get("quantity") == quantity and (lang is None or r.get("lang") == lang):
            return r
    return None


def _diff(a, b):
    if not a or not b or num(a["estimate"]) is None or num(b["estimate"]) is None:
        return None
    return dict(estimate=num(a["estimate"]) - num(b["estimate"]), lo=None, hi=None)


def _a1(results, resource):
    return next((r for r in read(results, "a1_resource_recall.csv") or []
                 if r["resource"] == resource and r["quantity"] == "recall_native_only"
                 and r.get("definition", "strict") in ("strict", "")), None)


def _dry(results):
    return any("dry run" in r.get("status", "") for r in read(results, "a1_resource_recall.csv") or [])


def expectations(results):
    rel = decomp_file(results)
    return [
        ("H-1", 3, "relational marking higher in Hindi: Δ = r_hi − r_en", "+", _q(results, rel, "delta"), ""),
        ("H-2", 3, "relational choice share > 0 (falsified if its CI includes 0)", "+",
         _q(results, rel, "choice_share"), "headline statistic"),
        ("P1", 6, "dative chosen more often than grammar requires: choice rate − forced baseline", "+",
         _diff(_q(results, "p1_choice.csv", "dative_choice_rate"),
               _q(results, "p1_choice.csv", "forced_baseline_dative_share")), "difference of point estimates"),
        ("A1", 8, "native lexicon recall above NRC-Hindi on native-only items (lexicon − nrc_hi)", "+",
         None if _dry(results) else _diff(_a1(results, "lexicon"), _a1(results, "nrc_hi")),
         "dry run: the reference is our lexicon's own matches" if _dry(results) else "difference of point estimates"),
        ("A2", 5, "systems under-read Hindi at equal human intensity (hindi coefficient)", "−",
         next((dict(estimate=r["estimate"], lo=r["ci_lo"], hi=r["ci_hi"]) for r in read(results, "audit_lmer.csv")
               or [] if r["term"] == "hindi" and r["pairs"] == "all"), None), "first system listed"),
    ]


def verdict(sign, obs):
    if obs is None:
        return "not assessable"
    e, lo, hi = num(obs.get("estimate")), num(obs.get("lo")), num(obs.get("hi"))
    if e is None:
        return "not assessable"
    if e == 0:
        return "zero"
    if (e > 0) != (sign == "+"):
        return "DIFFERS"
    if lo is not None and hi is not None and lo <= 0 <= hi:
        return "as expected, CI includes 0"
    return "as expected" if lo is not None else "as expected (no CI)"


def output_lines(results, figures, lab):
    rel = by_quantity(read(results, decomp_file(results)) or [])
    agr = read(Path(results) / "agreement", AGREEMENT_FILE)
    vt = read(results, "validation_table.csv")
    p1 = by_quantity(read(results, "p1_choice.csv") or [])
    j = read(results, "p2_jsd.csv")
    rival = odds_ratio_rows(results, "_rival", lab)
    L = {
        1: (f"α computed for {sum(1 for r in agr if num(r['alpha_nominal']) is not None)} fields (Output1_agreement.md)"
            if agr else "pending: the two investigators' coded gold sheets"),
        2: ("see Output2_validation.md" if vt else "pending: the adjudicated gold sheet (validate.py, corrected_rates.py)"),
        3: (f"choice share {lab(rel['choice_share']['estimate'], rel['choice_share']['lo'], rel['choice_share']['hi'], 1, signed=True)}"
            f"; odds ratios {'see Output3_hypothesis.md' if odds_ratio_rows(results, '', lab) else 'pending (R --run refused by the agreement guard)'}"
            if rel else "pending: decompose.py --marker relational"),
        4: ("not estimable from text-internal evidence (registered); rival check with diaspora + platform: "
            + ("see Output4_rival_check.md" if rival else "pending (R --run refused by the guard)")),
        5: ("see Output5_audit.md" if read(results, "audit_lmer.csv") else
            "pending: the two filled audit rating sheets, then audit_match.py and R/audit.R"),
        6: (f"chosen-dative rate {lab(p1['dative_choice_rate']['estimate'], p1['dative_choice_rate']['lo'], p1['dative_choice_rate']['hi'], 3)}"
            f" vs forced baseline {lab(p1['forced_baseline_dative_share']['estimate'], p1['forced_baseline_dative_share']['lo'], p1['forced_baseline_dative_share']['hi'], 3)}"
            f"; binomial test {lab.p(p1['binomial_test_vs_forced_baseline']['p']) if p1['binomial_test_vs_forced_baseline']['p'] else 'refused (no agreement statistics)'}"
            if p1 else "pending: predictions.py"),
        7: (f"JSD {lab(j[0]['estimate'], j[0]['lo'], j[0]['hi'], 3)}" if j else "pending: predictions.py"),
        8: (("resource recall: " + ("dry run (reference = our lexicon's matches), not a result"
                                    if any("dry run" in r["status"] for r in read(results, "a1_resource_recall.csv"))
                                    else "see Output8_translation.md") if read(results, "a1_resource_recall.csv")
             else "pending: translation_bias.py")
            + ("; McNemar: see Output8_translation.md" if read(results, "mcnemar_muril.csv")
               else "; McNemar pending: the two MuRIL models' predictions")),
        9: ("both figures present" if all((Path(figures) / s).exists() for s in FIGURES) else
            "pending: collocation.py"),
    }
    return L


def headline(results, figures, lab):
    rel = by_quantity(read(results, decomp_file(results)) or [])
    out = ["# Results headline: core outputs 1–9", "", lab.banner(), "",
           f"Template: `{PAPER}`. One line per output of the core pipeline (`make core`); nothing else is reported "
           "here. Tables: `results/tables/Output<k>_*.md`.", "", "## Outputs", ""]
    lines = output_lines(results, figures, lab)
    out += [f"{k}. **{t}**: {lines[k]}" for k, t in OUTPUT_TITLES.items()]
    out += ["", "## Section 4.2, filled (sign-neutral; output 3)", ""]
    if rel:
        out += ["Each term is stated with its sign and 95% interval and described by what that sign means; no "
                "direction is presupposed.", "", gap_sentence(rel, lab), ""]
    else:
        out += [pending(decomp_file(results), "decompose.py --marker relational"), ""]
    rows, differs = [], []
    for eid, k, stmt, sign, obs, note in expectations(results):
        v = verdict(sign, obs)
        shown = lab(obs["estimate"], obs.get("lo"), obs.get("hi")) if obs else "—"
        rows.append([eid, k, stmt, sign, shown, v, note])
        if v in ("DIFFERS", "zero"):
            differs.append(f"- **{eid}** (output {k}): {stmt}; expected {sign}, observed {shown}.")
    out += ["## Pre-registered directions that the current numbers contradict", ""] + (differs or ["None."])
    out += ["", "## All pre-registered directions within outputs 1–9", "",
            "Expected sign: + = Hindi higher (or the quantity > 0), − = Hindi lower.", "",
            md_table(["ID", "Output", "Expectation", "Sign", "Observed [95% CI]", "Verdict", "Note"], rows)]
    return "\n".join(out) + "\n", differs


OUTPUT_TITLES = {1: "Gold-set α per field", 2: "Dictionary precision / recall; corrected rates",
                 3: "Run 1 / 2 / 2b odds ratios; decomposition", 4: "Second-language rival (rival check)",
                 5: "Audit", 6: "Chosen-dative rate vs forced baseline", 7: "Component-profile JSD",
                 8: "NRC-Hindi vs native lexicon; MuRIL pair", 9: "Collocation network figures"}


def copy_figures(figures, final):
    final = Path(final)
    final.mkdir(parents=True, exist_ok=True)
    copied, missing = [], []
    for src, dst in FIGURES.items():
        p = Path(figures) / src
        if p.exists():
            shutil.copy2(p, final / dst)
            copied.append(dst)
        else:
            missing.append(src)
    return copied, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--figures", default=str(ROOT / "figures"))
    ap.add_argument("--tables-out", default=None, help="default: <results>/tables")
    ap.add_argument("--figures-out", default=None, help="default: <figures>/final")
    args = ap.parse_args(argv)

    lab = Labeller(args.results)
    res = args.results
    tables = Path(args.tables_out or Path(res) / "tables")
    tables.mkdir(parents=True, exist_ok=True)
    docs = {"Output1_agreement.md": output1(res, lab), "Output2_validation.md": output2(res, lab),
            "Output3_hypothesis.md": hypothesis_table(3, res, lab, "", "Hypothesis: Run 1 / Run 2 / Run 2b odds "
                                                      "ratios and the decomposition", decomp_file(res)),
            "Output4_rival_check.md": output4(res, lab),
            "Output5_audit.md": output5(res, lab), "Output6_dative_choice.md": output6(res, lab),
            "Output7_jsd.md": output7(res, lab), "Output8_translation.md": output8(res, lab),
            "Output9_collocation.md": output9(res, args.figures, lab)}
    for name, text in docs.items():
        (tables / name).write_text(text, encoding="utf-8")
    text, differs = headline(res, args.figures, lab)
    (Path(res) / "HEADLINE.md").write_text(text, encoding="utf-8")
    copied, missing = copy_figures(args.figures, args.figures_out or Path(args.figures) / "final")
    print(f"tables: {', '.join(docs)} -> {tables}")
    print(f"figures copied: {len(copied)}; missing sources: {missing or 'none'}")
    print(f"HEADLINE.md: {len(differs)} pre-registered direction(s) contradicted; label: "
          f"{SMOKE if lab.smoke else 'source status'}")


if __name__ == "__main__":
    main()
