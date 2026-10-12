"""Appendix E: power simulation for Run 2 and for the choice-share interval. A DESIGN COMPUTATION, NOT A RESULT."""
import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decompose as D
from gold import split_of

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
STATUS = "design computation (power simulation), not a result"
ODDS_RATIOS = (1.0, 1.1, 1.25, 1.5, 1.75, 2.0)
DIFFS = (0.0, 0.025, 0.05, 0.10, 0.15, 0.20)
B_BOOT = 400
SEED = 20261011


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def anova_icc(groups):
    groups = [(k, m) for k, m in groups if m > 0]
    g, N = len(groups), sum(m for _, m in groups)
    if g < 2 or N <= g:
        return float("nan")
    p = sum(k for k, _ in groups) / N
    ssb = sum(m * (k / m - p) ** 2 for k, m in groups)
    ssw = sum(k - k * k / m for k, m in groups)
    msb, msw = ssb / (g - 1), ssw / (N - g)
    n0 = (N - sum(m * m for _, m in groups) / N) / (g - 1)
    den = msb + (n0 - 1) * msw
    return float((msb - msw) / den) if den > 0 else float("nan")


def dev_inputs(proc=PROC):
    forced_clause = set()
    with open(proc / "eligibility.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        if r.get("marker_type") == "relational" and r["decision"] == "forced_relational":
            forced_clause.add(r["clause_id"])
    flags = D.clause_flags(rows, "relational", "site")
    lang_of, run2 = {}, defaultdict(lambda: [0, 0])
    with open(proc / "referents.csv", encoding="utf-8", newline="") as fh:
        refs = list(csv.DictReader(fh))
    for r in refs:
        rid = r["clause_id"].split("#")[0]
        if split_of(rid) != "dev" or r["clause_id"] in forced_clause:
            continue
        run2[rid][0] += r["relational"] == "True"
        run2[rid][1] += 1
    for r in rows:
        lang_of[r["clause_id"].split("#")[0]] = r["lang"]
    texts = D.text_counts(refs, flags, split="dev")
    out = {}
    for lang in ("hi", "en"):
        km = [tuple(v) for rid, v in sorted(run2.items()) if lang_of.get(rid) == lang]
        prof = [(t["n"], t["forced"], t["chosen"], t["nominative_alt"]) for _, t in sorted(texts[lang].items())]
        out[lang] = dict(km=km, profiles=prof)
    return out


def sigma_u(icc):
    icc = min(max(icc, 1e-4), 0.95)
    return math.sqrt(icc * (math.pi ** 2 / 3) / (1 - icc))


def sim_run2(inputs, n_texts, odds_ratio, sims, icc, p_en, rng):
    import statsmodels.api as sm
    s = sigma_u(icc)
    m_hi = np.array([m for _, m in inputs["hi"]["km"]])
    m_en = np.array([m for _, m in inputs["en"]["km"]])
    base = math.log(p_en / (1 - p_en))
    hits = 0
    for _ in range(sims):
        mh, me = rng.choice(m_hi, n_texts["hi"]), rng.choice(m_en, n_texts["en"])
        uh, ue = rng.normal(0, s, len(mh)), rng.normal(0, s, len(me))
        kh = rng.binomial(mh, 1 / (1 + np.exp(-(base + math.log(odds_ratio) + uh))))
        ke = rng.binomial(me, 1 / (1 + np.exp(-(base + ue))))
        k, m = np.concatenate([kh, ke]), np.concatenate([mh, me])
        x = sm.add_constant(np.concatenate([np.ones(len(mh)), np.zeros(len(me))]))
        try:
            fit = sm.GLM(np.column_stack([k, m - k]), x, family=sm.families.Binomial()).fit(cov_type="HC0")
            sig = fit.pvalues[1] < 0.05
            ok = sig if odds_ratio == 1.0 else sig and (fit.params[1] > 0) == (odds_ratio > 1)
        except Exception:
            ok = False
        hits += bool(ok)
    return hits / sims


def rho_sites(profiles):
    return anova_icc([(c, c + a) for _, _, c, a in profiles if c + a > 0])


def sim_choice(inputs, n_texts, diff, sims, p_en, rho, rng, boot=B_BOOT):
    prof = {lg: np.array(inputs[lg]["profiles"], float) for lg in ("hi", "en")}
    hits = 0
    for _ in range(sims):
        draws = {}
        for lg, p in (("hi", min(p_en + diff, 0.99)), ("en", p_en)):
            pr = prof[lg][rng.integers(0, len(prof[lg]), n_texts[lg])]
            sites = (pr[:, 2] + pr[:, 3]).astype(int)
            r = min(max(rho[lg], 0.01), 0.9)
            conc = (1 - r) / r
            pt = rng.beta(p * conc, (1 - p) * conc, len(pr))
            taken = rng.binomial(sites, pt)
            draws[lg] = np.column_stack([pr[:, 0], pr[:, 1], taken, sites - taken])
        reps = []
        for lg in ("hi", "en"):
            d = draws[lg]
            idx = rng.integers(0, len(d), (boot, len(d)))
            reps.append(d[idx].sum(1))
        hi, en = (D.rates(r[:, 0], r[:, 1], r[:, 2], r[:, 3]) for r in reps)
        cs = D.decompose(hi, en)["choice_share"]
        cs = cs[np.isfinite(cs)]
        hits += bool(len(cs) and np.percentile(cs, 2.5) > 0)
    return hits / sims


def figure(run2_rows, choice_rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, rows, xkey, xlabel, title in (
            (axes[0], run2_rows, "odds_ratio", "odds ratio (hindi)", "Run 2: P(p < .05, correct sign)"),
            (axes[1], choice_rows, "diff_p", "p_hi − p_en (share of choice sites taken)", "Choice share: P(95% CI > 0)")):
        for label in dict.fromkeys(r["n_label"] for r in rows):
            rr = [r for r in rows if r["n_label"] == label]
            ax.plot([r[xkey] for r in rr], [r["power"] for r in rr], marker="o", label=label)
        ax.axhline(0.8, color="grey", lw=0.8, ls="--")
        ax.axhline(0.05, color="grey", lw=0.6, ls=":")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("power")
        ax.set_ylim(0, 1)
        ax.set_title(title, fontsize=11)
        ax.legend(title="texts per language", fontsize=8)
    fig.suptitle("Appendix E power simulation: design computation from development-split inputs, not a result",
                 fontsize=10)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    return path


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--processed", default=str(PROC))
    ap.add_argument("--sims", type=int, default=1000)
    ap.add_argument("--sims-choice", type=int, default=300)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=str(ROOT / "results" / "power"))
    ap.add_argument("--figure", default=str(ROOT / "figures" / "power.pdf"))
    args = ap.parse_args(argv)
    proc, out = Path(args.processed), Path(args.out)
    inputs = dev_inputs(proc)
    icc = {lg: anova_icc(inputs[lg]["km"]) for lg in ("hi", "en")}
    icc["pooled"] = anova_icc(inputs["hi"]["km"] + inputs["en"]["km"])
    p_en = sum(k for k, _ in inputs["en"]["km"]) / sum(m for _, m in inputs["en"]["km"])
    taken_en = sum(c for _, _, c, _ in inputs["en"]["profiles"]) / sum(c + a for _, _, c, a in inputs["en"]["profiles"])
    rho = {lg: rho_sites(inputs[lg]["profiles"]) for lg in ("hi", "en")}
    meta = {}
    with open(proc / "text_meta.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            meta.setdefault((r["lang"], r["split"]), 0)
            meta[(r["lang"], r["split"])] += 1
    conf = {lg: meta.get((lg, "confirmatory"), 0) for lg in ("hi", "en")}
    designs = [(f"current confirmatory (hi {conf['hi']}, en {conf['en']})", conf), ("70", dict(hi=70, en=70)),
               ("100", dict(hi=100, en=100))]
    rng = np.random.default_rng(args.seed)
    run2_rows, choice_rows = [], []
    for label, n in designs:
        for orr in ODDS_RATIOS:
            run2_rows.append(dict(n_label=label, n_hi=n["hi"], n_en=n["en"], odds_ratio=orr, icc=round(icc["pooled"], 4),
                                  p_en=round(p_en, 4), sims=args.sims,
                                  power=sim_run2(inputs, n, orr, args.sims, icc["pooled"], p_en, rng), status=STATUS))
        for d in DIFFS:
            choice_rows.append(dict(n_label=label, n_hi=n["hi"], n_en=n["en"], diff_p=d, p_en=round(taken_en, 4),
                                    rho_hi=round(rho["hi"], 4), rho_en=round(rho["en"], 4), boot=B_BOOT,
                                    sims=args.sims_choice,
                                    power=sim_choice(inputs, n, d, args.sims_choice, taken_en, rho, rng), status=STATUS))
        print(f"{label}: done", flush=True)
    write(out / "run2_power.csv", run2_rows)
    write(out / "choice_share_power.csv", choice_rows)
    design = dict(status=STATUS, seed=args.seed, split_read="dev only",
                  dev_texts={lg: len(inputs[lg]["km"]) for lg in ("hi", "en")},
                  run2_clauses_per_text={lg: dict(mean=float(np.mean([m for _, m in inputs[lg]["km"]])),
                                                  median=float(np.median([m for _, m in inputs[lg]["km"]])))
                                         for lg in ("hi", "en")},
                  icc_run2=icc, p_en_run2=p_en, choice_share_taken_en=taken_en, rho_sites=rho,
                  confirmatory_texts=conf, odds_ratios=ODDS_RATIOS, diffs=DIFFS, boot=B_BOOT,
                  inputs={f: sha(proc / f) for f in ("referents.csv", "eligibility.csv", "text_meta.csv")})
    (out / "design_inputs.json").write_text(json.dumps(design, indent=1) + "\n", encoding="utf-8")
    figure(run2_rows, choice_rows, args.figure)
    print(json.dumps({k: design[k] for k in ("dev_texts", "icc_run2", "p_en_run2", "choice_share_taken_en", "rho_sites")},
                     indent=1))


if __name__ == "__main__":
    main()
