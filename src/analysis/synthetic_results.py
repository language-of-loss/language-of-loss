"""Synthetic placeholder result CSVs for outputs 1-9, so the figure and table layer renders before any real result."""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corrected_rates
import validate
from gold import CODEBOOK

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lexicon" / "src"))
from components import K_IDS

STATUS = "SYNTHETIC placeholder, not data"
MARKER = "SYNTHETIC.md"
AGREEMENT_COLUMNS = ["field", "n_units", "n_both_coded", "n_agree", "pct_agree", "alpha_nominal", "n_out_of_codebook",
                     "status"]
H1_COLUMNS = ["term", "estimate", "se", "stat", "df", "p", "estimator", "ci_lo", "ci_hi", "run", "split", "subset",
              "n_clauses", "n_texts", "singular", "converged", "odds_ratio", "status"]
AUDIT_LMER_COLUMNS = ["system", "pairs", "term", "estimate", "se", "df", "t", "p", "ci_lo", "ci_hi", "n_pairs",
                      "n_rows", "cue_terms", "singular", "status"]
AUDIT_STAB_COLUMNS = ["system", "component", "selection_freq", "full_data_coef", "stable", "lambda", "B", "threshold",
                      "mean_selected", "pfer_bound", "n_passages", "status"]
PMI_COLUMNS = ["lang", "entry_id", "headword", "entry_clauses", "entry_occurrences", "collocate", "cooc",
               "collocate_freq", "pmi", "n_texts"]
RUNS = (("run1", 0.55), ("run2", 0.42), ("run2b", 0.33), ("rF6", 0.40))
SYSTEMS = {"xlm_emo": False, "muril_sent": False, "commercial_llm_A": True}
COLLOCATES = {"hi": "याद घर माँ आँसू दिन रात रोना दिल बचपन सपना हाथ आवाज़ चेहरा कमरा फ़ोन तस्वीर खाना सुबह शाम "
                    "बारिश दवा अस्पताल रास्ता खिड़की".split(),
              "en": "memory home mother tears day night cry heart childhood dream hand voice face room phone photo "
                    "food morning evening rain medicine hospital road window".split()}
STAT_Z = 1.959964


def r6(v):
    return round(float(v), 6) if isinstance(v, (float, np.floating)) and math.isfinite(v) else v


def write(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({k: r6(r.get(k, "")) for k in columns})
    return path


def interval(rng, est, width):
    return est, est - width * rng.uniform(0.7, 1.3), est + width * rng.uniform(0.7, 1.3)


def agreement(rng):
    code = [dict(field=f, n_units=600, n_both_coded=600, n_agree=(a := int(rng.integers(420, 570))),
                 pct_agree=round(100 * a / 600, 1), alpha_nominal=round(rng.uniform(0.55, 0.9), 3),
                 n_out_of_codebook=int(rng.integers(0, 4)), status=STATUS) for f in CODEBOOK]
    comp = [dict(field=k, n_units=200, n_both_coded=200, n_agree=(a := int(rng.integers(150, 196))),
                 pct_agree=round(100 * a / 200, 1), alpha_nominal=round(rng.uniform(0.5, 0.92), 3),
                 n_out_of_codebook=0, status=STATUS) for k in K_IDS]
    return code, comp


def validation(rng):
    rows = []
    for field, values in CODEBOOK.items():
        for value in values:
            for lang in ("hi", "en"):
                n_pos = int(rng.integers(8, 120))
                n_neg = 300 - n_pos
                tp = int(rng.binomial(n_pos, rng.uniform(0.35, 0.95)))
                fp = int(rng.binomial(n_neg, rng.uniform(0.01, 0.12)))
                fn, tn = n_pos - tp, n_neg - fp
                prec = tp / (tp + fp) if tp + fp else ""
                rec = tp / n_pos
                f1 = 2 * tp / (2 * tp + fp + fn)
                rows.append(dict(channel="dict", field=field, value=value, lang=lang, n_items=300, tp=tp, fp=fp,
                                 fn=fn, tn=tn, precision=prec, recall=rec, f1=f1, measure=f"dict:{field}={value}",
                                 sensitivity=rec, fpr=fp / n_neg, n_pos=n_pos, n_neg=n_neg, status=STATUS))
    return rows


def corrected(rng, vt):
    rows, diffs = [], []
    for field in ("orientation", "experiencer"):
        for value in CODEBOOK[field][:4]:
            measure = f"dict:{field}={value}"
            est = {}
            for lang in ("hi", "en"):
                v = next(r for r in vt if r["measure"] == measure and r["lang"] == lang)
                o, olo, ohi = interval(rng, rng.uniform(0.03, 0.3), 0.03)
                s, phi = v["sensitivity"], v["fpr"]
                pi = (o - phi) / (s - phi) if s != phi else float("nan")
                pi, lo, hi = interval(rng, pi, 0.08)
                est[lang] = (o, pi, s)
                rows.append(dict(measure=measure, lang=lang, n_texts=int(rng.integers(60, 100)), observed=o,
                                 observed_lo=olo, observed_hi=ohi, corrected=pi, lo=lo, hi=hi, sensitivity=s, fpr=phi,
                                 n_pos=v["n_pos"], n_neg=v["n_neg"],
                                 flags="out_of_range" if not 0 <= pi <= 1 else "", status=STATUS, split="dev"))
            d, lo, hi = interval(rng, est["hi"][1] - est["en"][1], 0.1)
            gap = abs(est["hi"][2] - est["en"][2])
            diffs.append(dict(measure=measure, lang="hi-en", diff_observed=est["hi"][0] - est["en"][0],
                              diff_corrected=d, lo=lo, hi=hi,
                              sign_flip=(d > 0) != (est["hi"][0] > est["en"][0]), p_flip=rng.uniform(0, 0.4),
                              recall_gap=gap, gap_ok=gap <= 0.10, status=STATUS, split="dev"))
    return rows, diffs


def h1(rng, run, rival, base):
    terms = [("(Intercept)", -1.6), ("hindi", base), ("log_clauses", 0.05), ("loss_typesibling", 0.1),
             ("loss_typespouse", -0.15), ("loss_typeother", 0.02)]
    if rival:
        terms += [("diasporayes", 0.08), ("platformreddit", -0.1), ("platformyoutube", 0.05)]
    n_cl = {"run1": 6400, "run2": 6150, "run2b": 5900, "rF6": 6020}[run]
    n_tx = 190
    out = []
    for estimator, df in (("glmer (conditional, model-based SE)", ""), ("glm + CR2 cluster-robust (marginal)", None)):
        for term, b in terms:
            est = b + rng.normal(0, 0.05)
            se = rng.uniform(0.08, 0.2) * (1.3 if rival else 1)
            d = rng.uniform(40, 150) if df is None else ""
            crit = STAT_Z if df == "" else 2.0
            out.append(dict(term=term, estimate=est, se=se, stat=est / se, df=d,
                            p=math.erfc(abs(est / se) / math.sqrt(2)), estimator=estimator, ci_lo=est - crit * se,
                            ci_hi=est + crit * se, run=run, split="confirmatory", subset="all", n_clauses=n_cl,
                            n_texts=n_tx, singular=False, converged=True, odds_ratio=math.exp(est), status=STATUS))
    return out


def decomposition(rng):
    q = {}
    scale = 1.0
    for lang, (r, f, qq, p) in {"hi": (20, 7.5, 27, 0.46), "en": (12.5, 0.4, 40, 0.30)}.items():
        q[f"r_{lang}"], q[f"f_{lang}"] = interval(rng, r, 4 * scale), interval(rng, f, 2.5 * scale)
        q[f"q_{lang}"], q[f"p_{lang}"] = interval(rng, qq, 6 * scale), interval(rng, p, 0.06 * scale)
    pbar = (q["p_hi"][0] + q["p_en"][0]) / 2
    qbar = (q["q_hi"][0] + q["q_en"][0]) / 2
    forced = q["f_hi"][0] - q["f_en"][0]
    opp = (q["q_hi"][0] - q["q_en"][0]) * pbar
    choice = qbar * (q["p_hi"][0] - q["p_en"][0])
    q["delta"] = interval(rng, forced + opp + choice, 5.5 * scale)
    q["forced_share"] = interval(rng, forced, 3.0 * scale)
    q["opportunity_share"] = interval(rng, opp, 3.5 * scale)
    q["choice_share"] = interval(rng, choice, 3.4 * scale)
    order = [f"{k}_{lang}" for lang in ("hi", "en") for k in "rfqp"] + ["delta", "forced_share", "opportunity_share",
                                                                        "choice_share"]
    rows = [dict(quantity=k, estimate=q[k][0], lo=q[k][1], hi=q[k][2]) for k in order]
    sens = []
    for variant, dropped in (("all", ""), ("drop_largest_hi", "hi:synthetic_text_hi"),
                             ("drop_largest_en", "en:synthetic_text_en"),
                             ("drop_largest_both", "hi:synthetic_text_hi; en:synthetic_text_en")):
        jitter = 0 if variant == "all" else 1
        for k in order:
            e = q[k][0] + jitter * rng.normal(0, 0.06 * (abs(q[k][0]) + 0.5))
            sens.append(dict(variant=variant, dropped=dropped, quantity=k, estimate=e, lo=e - (q[k][0] - q[k][1]),
                             hi=e + (q[k][2] - q[k][0])))
    meta = dict(B=2000, replicates_dropped=0, seed=20261009, n_texts_hi=15, n_texts_en=23, n_hi=3100, n_en=3300,
                split="dev", subset="all",
                experiencer="all", marker="relational", unit="site", status=STATUS)
    return rows, sens, meta


def audit(rng):
    lmer, stab = [], []
    for system, cue in SYSTEMS.items():
        terms = ["(Intercept)", "intensity_c", "hindi", "intensity_c:hindi"]
        if cue:
            terms = ["(Intercept)", "intensity_c", "hindi", "cue", "intensity_c:hindi", "intensity_c:cue", "hindi:cue",
                     "intensity_c:hindi:cue"]
        for pairs, n_pairs in (("all", 150), ("agreed", 104)):
            for term in terms:
                base = {"hindi": rng.uniform(-0.6, -0.1), "hindi:cue": rng.uniform(-0.1, 0.35),
                        "intensity_c": 0.5}.get(term, rng.normal(0, 0.1))
                se = rng.uniform(0.06, 0.15) * (1.2 if pairs == "agreed" else 1)
                df = rng.uniform(100, 300)
                lmer.append(dict(system=system, pairs=pairs, term=term, estimate=base, se=se, df=df, t=base / se,
                                 p=math.erfc(abs(base / se) / math.sqrt(2)), ci_lo=base - STAT_Z * se,
                                 ci_hi=base + STAT_Z * se, n_pairs=n_pairs, n_rows=n_pairs * 2 * (2 if cue else 1),
                                 cue_terms=cue, singular=False, status=STATUS))
        freqs = rng.beta(0.7, 2.2, len(K_IDS))
        coefs = rng.normal(0, 0.15, len(K_IDS)) * (freqs > 0.2) + 0.0
        q = float(freqs.sum())
        for comp, fr, cf in zip(K_IDS, freqs, coefs):
            stab.append(dict(system=system, component=comp, selection_freq=fr, full_data_coef=cf,
                             stable=bool(fr >= 0.6 and cf < 0), lambda_=0.04, B=100, threshold=0.6, mean_selected=q,
                             pfer_bound=q * q / ((2 * 0.6 - 1) * len(K_IDS)), n_passages=150, status=STATUS))
    for r in stab:
        r["lambda"] = r.pop("lambda_")
    return lmer, stab


def p1(rng):
    meta = dict(status=STATUS, split="dev", eligibility_sha256="synthetic")
    return [dict(quantity="dative_choice_rate", lang="hi", estimate=0.21, lo=0.15, hi=0.28, k=63, n=300, n_texts=80,
                 test="", p="", **meta),
            dict(quantity="forced_baseline_dative_share", lang="hi", estimate=0.12, lo=0.08, hi=0.17, k=24, n=200,
                 n_texts=60, test="", p="", **meta),
            dict(quantity="binomial_test_vs_forced_baseline", lang="hi", estimate=0.21, lo="", hi="", k=63, n=300,
                 n_texts=80, test="exact binomial, one-sided, H0 rate = forced baseline", p=0.0001, **meta)]


def p2(rng):
    meta = dict(status=STATUS, split="dev", eligibility_sha256="synthetic")
    counts = {lang: rng.multinomial(2400 if lang == "hi" else 2700, rng.dirichlet(np.full(len(K_IDS), 1.4)))
              for lang in ("hi", "en")}
    n_cl = {"hi": 3100, "en": 3300}
    prof, lo = [], []
    for lang in ("hi", "en"):
        tot = counts[lang].sum()
        for k, c in zip(K_IDS, counts[lang]):
            prof.append(dict(lang=lang, component=k, clauses=int(c), profile_share=c / tot,
                             per_100_clauses=100 * c / n_cl[lang], **meta))
    a0 = 500.0
    nh, ne = counts["hi"].sum(), counts["en"].sum()
    for i, k in enumerate(K_IDS):
        ah = ae = a0 / len(K_IDS)
        yh, ye = counts["hi"][i], counts["en"][i]
        d = math.log((yh + ah) / (nh + a0 - yh - ah)) - math.log((ye + ae) / (ne + a0 - ye - ae))
        sd = math.sqrt(1 / (yh + ah) + 1 / (ye + ae))
        lo.append(dict(component=k, count_hi=int(yh), count_en=int(ye), alpha0=a0, delta=d, sd=sd, z=d / sd, **meta))
    jsd = [dict(quantity="jsd_component_profiles_base2", estimate=0.09, lo=0.06, hi=0.13, B=2000,
                n_components=len(K_IDS), n_texts_hi=80, n_texts_en=90, note="plug-in JSD (synthetic)", **meta)]
    return prof, lo, jsd


def a1(rng):
    rows = []
    for definition in ("strict", "tolerated"):
        point = {"lexicon": (0.78, 0.81), "nrc_hi": (0.31, 0.62)}
        for res, (nat, tr) in point.items():
            for name, e in (("recall_native_only", nat), ("recall_translatable", tr)):
                e, lo, hi = interval(rng, e + rng.normal(0, 0.02), 0.07)
                rows.append(dict(definition=definition, resource=res, quantity=name, estimate=e, lo=lo, hi=hi,
                                 n_items=120 if "native" in name else 260, status=STATUS))
            e, lo, hi = interval(rng, tr - nat, 0.09)
            rows.append(dict(definition=definition, resource=res, quantity="gap_translatable_minus_native",
                             estimate=e, lo=lo, hi=hi, n_items=380, status=STATUS))
    mc = [("n_clauses", 400), ("gold_positive", 170), ("accuracy_translated", 0.71), ("f1_translated", 0.62),
          ("accuracy_native", 0.79), ("f1_native", 0.73), ("discordant_translated_right_native_wrong", 21),
          ("discordant_native_right_translated_wrong", 53), ("mcnemar_exact_p_two_sided", 0.0003)]
    return rows, [dict(quantity=q, value=v, status=STATUS) for q, v in mc]


def collocation(rng):
    lex = list(csv.DictReader(open(ROOT / "lexicon" / "lexicon.csv", encoding="utf-8")))
    from collocation import headword
    rows = []
    for lang in ("hi", "en"):
        entries = [e for e in lex if e["lang"] == lang][:9]
        for e in entries:
            n_cl = int(rng.integers(10, 60))
            n_occ = n_cl + int(rng.integers(0, 6))
            for w in rng.choice(COLLOCATES[lang], size=7, replace=False):
                c = int(rng.integers(3, 12))
                rows.append(dict(lang=lang, entry_id=e["entry_id"], headword=headword(e), entry_clauses=n_cl,
                                 entry_occurrences=n_occ, collocate=str(w), cooc=c,
                                 collocate_freq=int(rng.integers(c, 200)), pmi=round(float(rng.uniform(0.3, 5.5)), 3),
                                 n_texts=int(rng.integers(2, 8))))
    return rows


def build(out, seed=20261010):
    rng = np.random.default_rng(seed)
    out = Path(out)
    files = []
    code, comp = agreement(rng)
    files.append(write(out / "agreement" / "agreement_summary_gold_sheet_v1.csv", code, AGREEMENT_COLUMNS))
    files.append(write(out / "agreement" / "agreement_summary_gold_components_v1.csv", comp, AGREEMENT_COLUMNS))
    vt = validation(rng)
    files.append(write(out / "validation_table.csv", vt, validate.COLUMNS))
    cr, crd = corrected(rng, vt)
    files.append(write(out / "corrected_rates.csv", cr, corrected_rates.COLUMNS))
    files.append(write(out / "corrected_rates_hi_minus_en.csv", crd, corrected_rates.DIFF_COLUMNS))
    for suffix in ("", "_rival"):
        for run, base in RUNS:
            files.append(write(out / f"h1_glmm_{run}{suffix}.csv",
                               h1(rng, run, bool(suffix), base * (0.8 if suffix else 1)), H1_COLUMNS))
    rows, sens, meta = decomposition(rng)
    stem = "decompose_relational_dev"
    meta["drop_largest_file"] = f"{stem}_drop_largest.csv"
    files.append(write(out / f"{stem}.csv", rows, ["quantity", "estimate", "lo", "hi"]))
    files.append(write(out / f"{stem}_drop_largest.csv", sens, ["variant", "dropped", "quantity", "estimate", "lo", "hi"]))
    (out / f"{stem}.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    files.append(out / f"{stem}.json")
    lm, st = audit(rng)
    files.append(write(out / "audit_lmer.csv", lm, AUDIT_LMER_COLUMNS))
    files.append(write(out / "audit_stability.csv", st, AUDIT_STAB_COLUMNS))
    p1_rows = p1(rng)
    files.append(write(out / "p1_choice.csv", p1_rows, list(p1_rows[0])))
    prof, lo, jsd = p2(rng)
    files.append(write(out / "p2_component_profile.csv", prof, list(prof[0])))
    files.append(write(out / "p2_component_logodds.csv", lo, list(lo[0])))
    files.append(write(out / "p2_jsd.csv", jsd, list(jsd[0])))
    rr, mc = a1(rng)
    files.append(write(out / "a1_resource_recall.csv", rr, list(rr[0])))
    files.append(write(out / "mcnemar_muril.csv", mc, ["quantity", "value", "status"]))
    files.append(write(out / "collocation_pmi.csv", collocation(rng), PMI_COLUMNS))
    (out / MARKER).write_text(
        "# SYNTHETIC placeholder results\n\nEvery CSV in this directory was written by "
        "`src/analysis/synthetic_results.py` from a seeded random generator, with the same file names and columns "
        "as the real core outputs, so that `src/analysis/figures.py` and `src/analysis/assemble_tables.py` render "
        "today. None of these numbers comes from data. Never copy one anywhere; RESULTS_LOG.md does not list them.\n",
        encoding="utf-8")
    return files


def is_synthetic(results):
    results = Path(results)
    if (results / MARKER).exists():
        return True
    for p in list(results.glob("*.csv")) + list(results.glob("agreement/*.csv")):
        with open(p, encoding="utf-8", newline="") as fh:
            rd = csv.DictReader(fh)
            if "status" in (rd.fieldnames or []) and any("synthetic" in (r.get("status") or "").lower() for r in rd):
                return True
    return False


def refuse_synthetic_in_real(results):
    if Path(results).resolve() == (ROOT / "results").resolve() and is_synthetic(results):
        raise SystemExit("refusing: results/ holds synthetic placeholder CSVs (status or SYNTHETIC.md); synthetic "
                         "files belong in results/synthetic/ only")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(ROOT / "results" / "synthetic"))
    ap.add_argument("--seed", type=int, default=20261010)
    args = ap.parse_args(argv)
    if Path(args.out).resolve() == (ROOT / "results").resolve():
        raise SystemExit("refusing: synthetic CSVs must not be written into results/ itself")
    files = build(args.out, args.seed)
    print(f"{len(files)} synthetic files -> {args.out} (status '{STATUS}')")


if __name__ == "__main__":
    main()
