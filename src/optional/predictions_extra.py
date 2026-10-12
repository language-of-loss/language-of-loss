"""Optional (not on the core path): the P1 / P2 descriptives that are not outputs 1-9 of `make core`."""
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from predictions import (EMOTION_RULES, LANGS, MIN_MATCHES, POS_CATS, REFUSED, STRUCTURAL_ZERO,
                         boot_ratio, experiencer_sites, in_split, load_p2_texts, parser, provenance, read_csv,
                         record_of, tests_allowed, write_csv)
from predictions import ROOT, jsd

OUT = ROOT / "results" / "optional"


def monroe_log_odds(counts_a, counts_b, total_a, total_b, alpha0=500.0):
    out = {}
    n = total_a + total_b
    for w in sorted(set(counts_a) | set(counts_b)):
        ya, yb = counts_a.get(w, 0), counts_b.get(w, 0)
        aw = alpha0 * (ya + yb) / n if n else 0.0
        if aw <= 0:
            out[w] = dict(delta=math.nan, sd=math.nan, z=math.nan)
            continue
        la = math.log((ya + aw) / (total_a + alpha0 - ya - aw))
        lb = math.log((yb + aw) / (total_b + alpha0 - yb - aw))
        var = 1.0 / (ya + aw) + 1.0 / (yb + aw)
        out[w] = dict(delta=la - lb, sd=math.sqrt(var), z=(la - lb) / math.sqrt(var))
    return out


def norm_hi(s):
    return (s or "").replace("़", "").strip("।.,!?\"'“”‘’()")


def predicate_category(site, clause_tokens):
    pred = site["predicate"]
    if site["lang"] == "hi":
        if "+" not in pred:
            for t in clause_tokens:
                if t["upos"] in ("VERB", "AUX") and (norm_hi(t["lemma"]).startswith(pred)
                                                    or norm_hi(t["token"]).startswith(pred)):
                    return "emotion_verb"
            return None
        x = pred.split("+")[0]
        for t in clause_tokens:
            if x in (norm_hi(t["lemma"]), norm_hi(t["token"])):
                return {"ADJ": "emotion_adjective", "VERB": "emotion_verb"}.get(t["upos"], "emotion_noun")
        return None
    for t in clause_tokens:
        if pred in (t["lemma"].lower(), t["token"].lower()):
            return {"ADJ": "emotion_adjective", "NOUN": "emotion_noun"}.get(t["upos"], "emotion_verb")
    return None


def p1_pos(sites, tokens_by_clause, n_tokens_by_text, referent_class, alpha0=500.0, B=2000, seed=20261010):
    counts = {lg: defaultdict(Counter) for lg in LANGS}
    for s in sites:
        if not EMOTION_RULES.match(s["rule_id"]):
            continue
        rid = record_of(s["clause_id"])
        cat = predicate_category(s, tokens_by_clause.get(s["clause_id"], []))
        counts[s["lang"]][rid][cat or "unclassified"] += 1
        if s.get("construction") == "nominative" and referent_class.get(s["clause_id"]) == "self":
            counts[s["lang"]][rid]["agentive_self"] += 1
    profile, totals, tot_tokens = [], {}, {}
    for lg in LANGS:
        texts = sorted(t for t, l in n_tokens_by_text.items() if l[0] == lg)
        den = [n_tokens_by_text[t][1] for t in texts]
        tot_tokens[lg] = int(sum(den))
        totals[lg] = Counter()
        for c in POS_CATS:
            num = [counts[lg][t][c] for t in texts]
            totals[lg][c] = int(sum(num))
            est, lo, hi = boot_ratio(num, den, B, seed)
            profile.append(dict(lang=lg, category=c, count=int(sum(num)), n_tokens=int(sum(den)), n_texts=len(texts),
                                per_1000=1000 * est, lo=1000 * lo, hi=1000 * hi))
    for lg in LANGS:
        profile.append(dict(lang=lg, category="unclassified", count=sum(counts[lg][t]["unclassified"]
                                                                         for t in counts[lg]),
                            n_tokens=tot_tokens[lg], n_texts="", per_1000="", lo="", hi=""))
    lo_rows = []
    for c, v in monroe_log_odds(totals["hi"], totals["en"], tot_tokens["hi"], tot_tokens["en"], alpha0).items():
        row = dict(category=c, count_hi=totals["hi"][c], count_en=totals["en"][c], tokens_hi=tot_tokens["hi"],
                   tokens_en=tot_tokens["en"], alpha0=alpha0, **v, note="")
        zero = [lg for lg in LANGS if (lg, c) in STRUCTURAL_ZERO]
        if zero:
            row.update(delta="", sd="", z="", note=f"n/a: {'/'.join(zero)} = 0 by construction")
        lo_rows.append(row)
    return profile, lo_rows


def p1_we_i(sites, pronouns, B=2000, seed=20261010):
    clauses = {(s["lang"], s["clause_id"]) for s in sites if s["decision"].startswith("chosen_")}
    per = {lg: defaultdict(Counter) for lg in LANGS}
    for lg, cid in clauses:
        person, number = pronouns.get(cid, ("", ""))
        c = per[lg][record_of(cid)]
        c["sites"] += 1
        if person == "1":
            c["we" if number == "pl" else "I" if number == "sg" else "other1"] += 1
    rows = []
    for lg in LANGS:
        texts = sorted(per[lg])
        we, i = [per[lg][t]["we"] for t in texts], [per[lg][t]["I"] for t in texts]
        est, lo, hi = boot_ratio(we, i, B, seed)
        rows.append(dict(lang=lg, eligible_clauses=sum(per[lg][t]["sites"] for t in texts), we=int(sum(we)),
                         I=int(sum(i)), we_per_I=est, lo=lo, hi=hi, n_texts=len(texts)))
    return rows


def p2_naming(texts, B=2000, seed=20261010):
    per_text, dropped = [], Counter()
    for rid, t in sorted(texts.items()):
        n = sum(t["cls"].values())
        if n < MIN_MATCHES:
            dropped[t["lang"]] += 1
            continue
        n2 = sum(t["cls_ngf"].values())
        per_text.append(dict(record_id=rid, lang=t["lang"], matches=n, naming=t["cls"]["naming"],
                             absence_memory_duty=t["cls"]["absence_memory_duty"], other=t["cls"]["other"],
                             naming_share=t["cls"]["naming"] / n, matches_excl_gf=n2,
                             naming_excl_gf=t["cls_ngf"]["naming"],
                             naming_share_excl_gf=t["cls_ngf"]["naming"] / n2 if n2 else math.nan))
    summary = []
    for lg in LANGS:
        rows = [r for r in per_text if r["lang"] == lg]
        shares = np.array([r["naming_share"] for r in rows])
        pooled = boot_ratio([r["naming"] for r in rows], [r["matches"] for r in rows], B, seed)
        mean = boot_ratio(shares, np.ones(len(shares)), B, seed)
        amd = boot_ratio([r["absence_memory_duty"] for r in rows], [r["matches"] for r in rows], B, seed)
        summary += [dict(lang=lg, quantity="mean_text_naming_share", estimate=mean[0], lo=mean[1], hi=mean[2],
                         n_texts=len(rows), dropped_texts=dropped[lg]),
                    dict(lang=lg, quantity="pooled_naming_share", estimate=pooled[0], lo=pooled[1], hi=pooled[2],
                         n_texts=len(rows), dropped_texts=dropped[lg]),
                    dict(lang=lg, quantity="pooled_absence_memory_duty_share", estimate=amd[0], lo=amd[1],
                         hi=amd[2], n_texts=len(rows), dropped_texts=dropped[lg])]
        ngf = boot_ratio([r["naming_excl_gf"] for r in rows], [r["matches_excl_gf"] for r in rows], B, seed)
        summary.append(dict(lang=lg, quantity="pooled_naming_share_excl_gf", estimate=ngf[0], lo=ngf[1], hi=ngf[2],
                            n_texts=len(rows), dropped_texts=dropped[lg]))
    return per_text, summary


def p2_beta(per_text, allow_tests=False):
    if not allow_tests:
        return [dict(term="hindi", method="", estimate="", se="", z="", p="", n_texts=len(per_text), note=REFUSED)]
    import statsmodels.api as sm
    y = np.array([r["naming_share"] for r in per_text])
    n = len(y)
    ys = (y * (n - 1) + 0.5) / n
    X = sm.add_constant(np.array([1.0 if r["lang"] == "hi" else 0.0 for r in per_text]))
    try:
        from statsmodels.othermod.betareg import BetaModel
        res = BetaModel(ys, X).fit(disp=0)
        if not np.all(np.isfinite(res.bse[:2])):
            raise RuntimeError("non-finite SEs")
        method, names = "statsmodels BetaModel (ML, logit link, constant precision)", ["const", "hindi", "precision"]
    except Exception as e:
        res = sm.OLS(np.log(ys / (1 - ys)), X).fit(cov_type="HC1")
        method, names = f"OLS on logit(share), HC1 SEs (BetaModel failed: {e})", ["const", "hindi"]
    return [dict(term=nm, method=method, estimate=float(res.params[i]), se=float(res.bse[i]),
                 z=float(res.tvalues[i]), p=float(res.pvalues[i]), n_texts=n,
                 note="squeezed (y(n-1)+0.5)/n; split-level fit, text = unit")
            for i, nm in enumerate(names)]


def p2_components(texts, emotion_unmatched, alpha0=500.0, B=2000, seed=20261010):
    comps = sorted({c for t in texts.values() for c in t["comp"]})
    by_lang = {lg: sorted(r for r, t in texts.items() if t["lang"] == lg) for lg in LANGS}
    mat = {lg: np.array([[texts[r]["comp"][c] for c in comps] for r in by_lang[lg]], float).reshape(-1, len(comps))
           for lg in LANGS}
    tot = {lg: mat[lg].sum(0) for lg in LANGS}
    profile = []
    for lg in LANGS:
        s = tot[lg].sum()
        n_cl = sum(texts[r]["n_clauses"] for r in by_lang[lg])
        for j, c in enumerate(comps):
            profile.append(dict(lang=lg, component=c, clauses=int(tot[lg][j]), profile_share=tot[lg][j] / s if s else
                                math.nan, per_100_clauses=100 * tot[lg][j] / n_cl if n_cl else math.nan))
    ca = {c: int(tot["hi"][j]) for j, c in enumerate(comps)}
    cb = {c: int(tot["en"][j]) for j, c in enumerate(comps)}
    lo_rows = [dict(component=c, count_hi=ca[c], count_en=cb[c], alpha0=alpha0, **v)
               for c, v in monroe_log_odds(ca, cb, sum(ca.values()), sum(cb.values()), alpha0).items()]
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
    jsd_rows = [dict(quantity="jsd_component_profiles_base2", estimate=est,
                     lo=float(np.percentile(reps, 2.5)) if reps else math.nan,
                     hi=float(np.percentile(reps, 97.5)) if reps else math.nan, B=B, n_components=len(comps),
                     n_texts_hi=len(by_lang["hi"]), n_texts_en=len(by_lang["en"]),
                     note="plug-in JSD, biased upward in small samples; CI = text bootstrap of the plug-in value")]
    residue = []
    for lg in LANGS:
        ts = [texts[r] for r in by_lang[lg]]
        n_cl, matched = sum(t["n_clauses"] for t in ts), sum(t["matched"] for t in ts)
        hits = sum(t["comp"][c] for t in ts for c in comps)
        rows = [("grammar_forced_component_clauses", sum(t["gf"] for t in ts), n_cl, "finite clauses",
                 "gf_* hits kept apart from comp_* by matcher rule R2 (not in the profile)"),
                ("matched_clauses_without_component", sum(t["matched_no_comp"] for t in ts), matched,
                 "lexicon-matched clauses", "entry matched but contributes no component"),
                ("emotion_sites_in_unmatched_clauses", emotion_unmatched.get(lg, (0, 0))[0],
                 emotion_unmatched.get(lg, (0, 0))[1], "emotion experiencer sites (P1 rules)",
                 "emotional predication the lexicon does not match"),
                ("component_hits_in_profile", hits, n_cl, "finite clauses", "for scale")]
        residue += [dict(lang=lg, residue=k, count=int(c), denominator=int(d), denominator_unit=u,
                         share=c / d if d else math.nan, note=nt) for k, c, d, u, nt in rows]
    return profile, lo_rows, jsd_rows, residue


def load_tokens(path, clause_ids, split):
    by_clause, n_tok = defaultdict(list), Counter()
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            cid = r["clause_id"]
            rid = record_of(cid)
            if not in_split(rid, split):
                continue
            if r["upos"] != "PUNCT":
                n_tok[rid] += 1
            if cid in clause_ids:
                by_clause[cid].append(r)
    return by_clause, n_tok


def run(args):
    out = Path(args.out_dir)
    allow = tests_allowed(args.agreement)
    meta = provenance(args)
    sites = experiencer_sites(read_csv(args.eligibility), args.split)
    refs = read_csv(args.referents)
    ref_class = {r["clause_id"]: r["referent_class"] for r in refs}
    pronouns = {r["clause_id"]: (r["pronoun_person"], r["pronoun_number"]) for r in refs}
    cf, texts = load_p2_texts(args)
    lang_of = {r["record_id"]: r["lang"] for r in cf}
    tokens_by_clause, n_tok = load_tokens(args.tokens, {s["clause_id"] for s in sites}, args.split)
    n_tokens_by_text = {rid: (lang_of.get(rid, ""), n) for rid, n in n_tok.items() if rid in lang_of}

    written = {}
    prof, lo = p1_pos(sites, tokens_by_clause, n_tokens_by_text, ref_class, args.alpha0, args.B, args.seed)
    written["p1_pos_profile"] = write_csv(out / "p1_pos_profile.csv", prof, meta)
    written["p1_pos_logodds"] = write_csv(out / "p1_pos_logodds.csv", lo, meta)
    written["p1_we_i"] = write_csv(out / "p1_we_i.csv", p1_we_i(sites, pronouns, args.B, args.seed), meta)
    per_text, summary = p2_naming(texts, args.B, args.seed)
    written["p2_naming_texts"] = write_csv(out / "p2_naming_texts.csv", per_text, meta)
    written["p2_naming_share"] = write_csv(out / "p2_naming_share.csv", summary, meta)
    written["p2_beta"] = write_csv(out / "p2_beta.csv", p2_beta(per_text, allow), meta)
    unmatched = Counter()
    for s in sites:
        if EMOTION_RULES.match(s["rule_id"]):
            t = texts.get(record_of(s["clause_id"]))
            unmatched[(s["lang"], "all")] += 1
            if t is not None and s["clause_id"] in t["unmatched_clauses"]:
                unmatched[(s["lang"], "unmatched")] += 1
    emo_un = {lg: (unmatched[(lg, "unmatched")], unmatched[(lg, "all")]) for lg in LANGS}
    prof, lo, _, residue = p2_components(texts, emo_un, args.alpha0, args.B, args.seed)
    written["p2_component_profile"] = write_csv(out / "p2_component_profile.csv", prof, meta)
    written["p2_component_logodds"] = write_csv(out / "p2_component_logodds.csv", lo, meta)
    written["p2_residue"] = write_csv(out / "p2_residue.csv", residue, meta)
    return written, allow


def main(argv=None):
    ap = parser(__doc__)
    ap.set_defaults(out_dir=str(OUT))
    args = ap.parse_args(argv)
    written, allow = run(args)
    print(f"split {args.split}; tests {'RUN (agreement statistics found)' if allow else 'REFUSED (no agreement statistics)'}")
    for name, p in written.items():
        print(f"  {p}")


if __name__ == "__main__":
    main()
