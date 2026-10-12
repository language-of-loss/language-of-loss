"""Outputs 6 and 7 of the core pipeline: the Hindi chosen-dative rate against the forced baseline (P1) and the"""
import argparse
import csv
import hashlib
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gold import split_of

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
SMOKE = "dev smoke, not a result"
LANGS = ("hi", "en")
MIN_MATCHES = 5
POS_CATS = ("emotion_verb", "emotion_adjective", "emotion_noun", "agentive_self")
STRUCTURAL_ZERO = {("en", "emotion_noun")}
AMD_COMPONENTS = {"NOT_HERE", "THINK_OF", "SPEAK_TO_DEAD", "LONG_TIME", "DUTY_DONE", "DUTY_UNDONE"}
EMOTION_RULES = re.compile(r"^(HI-C\d+|HI-N\d+|HI-NK-.*|HI-F01|HI-F07|HI-R0[1-5]|HI-R0[78]|HI-R12|"
                           r"EN-(?!R0[12]$).*)$")
REFUSED = "refused: no codebook agreement statistics (results/agreement/agreement_summary_gold_sheet_v1.csv " \
          "with >= 1 field coded by both coders and a finite alpha; study protocol: no hypothesis test before human " \
          "annotation and agreement statistics)"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tests_allowed(agreement_path):
    path = Path(agreement_path)
    if not path.exists():
        return False
    for r in read_csv(path):
        if "synthetic" in (r.get("status") or "").lower():
            return False
        try:
            if int(r.get("n_both_coded") or 0) > 0 and math.isfinite(float(r.get("alpha_nominal") or "nan")):
                return True
        except ValueError:
            continue
    return False


def flag(v):
    return str(v).strip() in ("1", "True", "true", "1.0")


def record_of(clause_id):
    return clause_id.split("#")[0]


def in_split(record_id, split):
    return split == "all" or split_of(record_id) == split


def boot_ratio(num, den, B=2000, seed=20261010):
    num, den = np.asarray(num, float), np.asarray(den, float)
    if len(num) == 0 or den.sum() == 0:
        return math.nan, math.nan, math.nan
    est = num.sum() / den.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num), size=(B, len(num)))
    n, d = num[idx].sum(1), den[idx].sum(1)
    r = n[d > 0] / d[d > 0]
    return float(est), float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def jsd(p, q):
    p, q = np.asarray(p, float), np.asarray(q, float)
    if p.sum() == 0 or q.sum() == 0:
        return math.nan
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2

    def kl(a, b):
        k = a > 0
        return float((a[k] * np.log2(a[k] / b[k])).sum())
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, meta):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [dict(r, **meta) for r in rows]
    fields = list(dict.fromkeys(k for r in rows for k in r)) if rows else list(meta)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (float(f"{v:.6g}") if isinstance(v, float) and math.isfinite(v) else v) for k, v in r.items()})
    return path


def experiencer_sites(elig_rows, split):
    return [r for r in elig_rows if r.get("marker_type", "dative") == "dative" and r["decision"] != "NA"
            and in_split(record_of(r["clause_id"]), split)]


def p1_choice(sites, B=2000, seed=20261010, allow_tests=False):
    per = defaultdict(Counter)
    for r in sites:
        if r["lang"] == "hi":
            per[record_of(r["clause_id"])][r["decision"]] += 1
    texts = sorted(per)
    cd = [per[t]["chosen_dative"] for t in texts]
    cn = [per[t]["chosen_nominative"] for t in texts]
    fd = [per[t]["forced_dative"] for t in texts]
    fn = [per[t]["forced_nominative"] for t in texts]
    elig = [a + b for a, b in zip(cd, cn)]
    forced = [a + b for a, b in zip(fd, fn)]
    rate = boot_ratio(cd, elig, B, seed)
    base = boot_ratio(fd, forced, B, seed + 1)
    k, n = int(sum(cd)), int(sum(elig))
    rows = [dict(quantity="dative_choice_rate", lang="hi", estimate=rate[0], lo=rate[1], hi=rate[2], k=k, n=n,
                 n_texts=sum(1 for e in elig if e), test="", p=""),
            dict(quantity="forced_baseline_dative_share", lang="hi", estimate=base[0], lo=base[1], hi=base[2],
                 k=int(sum(fd)), n=int(sum(forced)), n_texts=sum(1 for f in forced if f), test="", p="")]
    test = dict(quantity="binomial_test_vs_forced_baseline", lang="hi", estimate=rate[0], lo="", hi="", k=k, n=n,
                n_texts=rows[0]["n_texts"], test="exact binomial, two-sided, H0: p = forced baseline", p="")
    if not allow_tests:
        test["test"] = REFUSED
    elif n and math.isfinite(base[0]):
        from scipy.stats import binomtest
        test["p"] = float(binomtest(k, n, base[0], alternative="two-sided").pvalue)
        test["test"] += f" (p0 = {base[0]:.4f}, text clustering ignored by the binomial model)"
    rows.append(test)
    return rows


def entry_classes(entry_vector_rows):
    out = {}
    for r in entry_vector_rows:
        if flag(r.get("names_emotion")):
            out[r["entry_id"]] = "naming"
        elif any(flag(r.get(c)) for c in AMD_COMPONENTS):
            out[r["entry_id"]] = "absence_memory_duty"
        else:
            out[r["entry_id"]] = "other"
    return out


def grammar_forced_entries(lexicon_rows):
    return {r["entry_id"] for r in lexicon_rows if r.get("grammar_forced", "N") != "N"}


def p2_text_counts(cf_rows, classes, split, gf_entries=frozenset()):
    entry_cols = [c for c in (cf_rows[0] if cf_rows else {}) if c in classes]
    comp_cols = [c for c in (cf_rows[0] if cf_rows else {}) if c.startswith("comp_")]
    gf_cols = [c for c in (cf_rows[0] if cf_rows else {}) if c.startswith("gf_")]
    texts = {}
    for r in cf_rows:
        if not flag(r["is_finite"]) or not in_split(r["record_id"], split):
            continue
        t = texts.setdefault(r["record_id"], dict(lang=r["lang"], n_clauses=0, cls=Counter(), cls_ngf=Counter(),
                                                  comp=Counter(),
                                                  gf=0, matched=0, matched_no_comp=0, unmatched_clauses=set()))
        t["n_clauses"] += 1
        hits = [c for c in entry_cols if flag(r[c])]
        for c in hits:
            t["cls"][classes[c]] += 1
            if c not in gf_entries:
                t["cls_ngf"][classes[c]] += 1
        comps = [c for c in comp_cols if flag(r[c])]
        for c in comps:
            t["comp"][c[5:]] += 1
        gf = any(flag(r[c]) for c in gf_cols)
        t["gf"] += int(gf)
        if hits:
            t["matched"] += 1
            t["matched_no_comp"] += int(not comps and not gf)
        else:
            t["unmatched_clauses"].add(r["clause_id"])
    return texts


def holm(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def jsd_permutation_p(mat, est, B=2000, seed=20261011):
    allm = np.vstack([mat["hi"], mat["en"]])
    n_hi = len(mat["hi"])
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(B):
        idx = rng.permutation(len(allm))
        v = jsd(allm[idx[:n_hi]].sum(0), allm[idx[n_hi:]].sum(0))
        hits += v >= est - 1e-12
    return (1 + hits) / (B + 1)


def p2_jsd(texts, B=2000, seed=20261010, allow_tests=False):
    comps = sorted({c for t in texts.values() for c in t["comp"]})
    by_lang = {lg: sorted(r for r, t in texts.items() if t["lang"] == lg) for lg in LANGS}
    mat = {lg: np.array([[texts[r]["comp"][c] for c in comps] for r in by_lang[lg]], float).reshape(-1, len(comps))
           for lg in LANGS}
    tot = {lg: mat[lg].sum(0) for lg in LANGS}
    est = jsd(tot["hi"], tot["en"])
    rng = np.random.default_rng(seed)
    reps = []
    if all(len(mat[lg]) for lg in LANGS):
        for _ in range(B):
            a = mat["hi"][rng.integers(0, len(mat["hi"]), len(mat["hi"]))].sum(0)
            b = mat["en"][rng.integers(0, len(mat["en"]), len(mat["en"]))].sum(0)
            v = jsd(a, b)
            if math.isfinite(v):
                reps.append(v)
    return [dict(quantity="jsd_component_profiles_base2", estimate=est,
                 lo=float(np.percentile(reps, 2.5)) if reps else math.nan,
                 hi=float(np.percentile(reps, 97.5)) if reps else math.nan, B=B, n_components=len(comps),
                 n_texts_hi=len(by_lang["hi"]), n_texts_en=len(by_lang["en"]),
                 note="plug-in JSD, biased upward in small samples; CI = text bootstrap of the plug-in value",
                 test=("permutation of language labels across texts" if allow_tests and reps else
                       REFUSED if not allow_tests else ""),
                 p=jsd_permutation_p(mat, est, B, seed + 1) if allow_tests and reps else "")]


def provenance(args):
    return dict(status=getattr(args, "status", "") or (SMOKE if args.split == "dev" else "exploratory, unreviewed labels"),
                split=args.split,
                eligibility_sha256=sha256(Path(args.eligibility)))


def load_p2_texts(args):
    cf = read_csv(args.clause_features)
    classes = entry_classes(read_csv(args.entry_vectors))
    lex = Path(args.lexicon)
    return cf, p2_text_counts(cf, classes, args.split, grammar_forced_entries(read_csv(lex)) if lex.exists() else set())


def run(args):
    out = Path(args.out_dir)
    allow = tests_allowed(args.agreement)
    meta = provenance(args)
    sites = experiencer_sites(read_csv(args.eligibility), args.split)
    _, texts = load_p2_texts(args)
    p1 = p1_choice(sites, args.B, args.seed, allow)
    p2 = p2_jsd(texts, args.B, args.seed, allow)
    tests = [r for r in p1 + p2 if isinstance(r.get("p"), float) and math.isfinite(r["p"])]
    if allow and tests:
        for r, a in zip(tests, holm([r["p"] for r in tests])):
            r["p_holm"] = a
            r["family"] = "Holm over outputs 6 (binomial) and 7 (JSD permutation)"
    written = {"p1_choice": write_csv(out / "p1_choice.csv", p1, meta),
               "p2_jsd": write_csv(out / "p2_jsd.csv", p2, meta)}
    return written, allow


def parser(doc=None):
    ap = argparse.ArgumentParser(description=(doc or __doc__).split("\n")[0])
    ap.add_argument("--eligibility", default=str(PROC / "eligibility.csv"))
    ap.add_argument("--referents", default=str(PROC / "referents.csv"))
    ap.add_argument("--tokens", default=str(PROC / "tokens.csv"))
    ap.add_argument("--clause-features", default=str(PROC / "clause_features.csv"))
    ap.add_argument("--entry-vectors", default=str(ROOT / "lexicon" / "entry_vectors.csv"))
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon" / "lexicon.csv"), help="grammar_forced tags")
    ap.add_argument("--agreement", default=str(ROOT / "results" / "agreement" / "agreement_summary_gold_sheet_v1.csv"))
    ap.add_argument("--split", default="dev", choices=["dev", "confirmatory", "all"])
    ap.add_argument("--alpha0", type=float, default=500.0, help="Dirichlet prior size (Monroe et al. alpha_0)")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--out-dir", default=str(ROOT / "results"))
    ap.add_argument("--status", default="", help="status label for every row (default: by split)")
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    written, allow = run(args)
    print(f"split {args.split}; tests {'RUN (agreement statistics found)' if allow else 'REFUSED (no agreement statistics)'}")
    for name, p in written.items():
        print(f"  {p}")


if __name__ == "__main__":
    main()
