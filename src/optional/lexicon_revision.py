"""Write the lexicon v0.3 revision list for the lexicon editor (lexicon/ is read only here)."""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from gold import split_of
from lexmatch import NUKTA, SURFACE_ONLY, headword_variants, load_lexicon, load_tokens, match_clause, norm_word

ROOT = Path(__file__).resolve().parents[2]
ZERO = {"hi": ["P-HI-09", "P-HI-19", "P-HI-20", "P-HI-40", "P-HI-46", "P-HI-50", "P-HI-51", "P-HI-55"],
        "en": ["L-EN-29", "P-EN-20", "P-EN-23", "P-EN-30", "P-EN-46", "P-EN-65", "P-EN-66", "P-EN-68"]}
INFLATED = ["P-HI-32", "P-HI-33", "L-EN-16"]
FIX = {
    "P-HI-32": "Lemma channel: drop the bare variant घर (house/home, mostly literal: घर गया, घर पर). Keep परिवार and "
               "घर वाले; the pattern already covers परिवार / घर वाले / कुटुंब / ख़ानदान. Edit `headword_deva` to "
               "`परिवार / घर वाले`, or mark the entry pattern-only. If 'home' as a family place is wanted, make a "
               "separate entry whose pattern needs a possessive or kin context (हमारा घर, मायका).",
    "P-HI-33": "Lemma channel: bare बड़े is the adjective 'big/elder' (बड़े भाई, बड़े अस्पताल). Drop it from the "
               "headword (`बुज़ुर्ग / बड़े-बुज़ुर्ग / बड़ों`) and keep the pattern, which already requires बड़ों or "
               "बड़े-बुज़ुर्ग. Note that बड़े भाई (elder brother) is kin, not 'elders'.",
    "L-EN-16": "Lemma channel: the variant `death (of)` loses its parenthesis and matches bare death/deaths, which "
               "belongs to P-EN-60 (died / death, direct). Make the headword `passing / demise`, and leave "
               "possessive 'X's death' to the pattern (which already lists his/her/the/my/dad's … death). Bare 'passing' (no possessor) is also a lemma-only "
               "trigger and is often not about death; keep 'passing' only through the pattern.",
}


def denukta(s):
    return s.replace(NUKTA, "")


def key_words(e):
    hw = e["headword_deva"] if e["lang"] == "hi" else e["headword_en"]
    hw = re.sub(r"\([^)]*\)", " ", hw)
    stop = {"hi": {"में", "से", "का", "की", "के", "ने", "को", "है", "हैं", "नहीं", "सब", "देता", "कर", "गया", "गए",
                   "वाले", "लिया", "उनका", "हमारे", "बीच", "रहे"},
            "en": {"the", "a", "of", "to", "on", "it", "me", "my", "he", "she", "him", "her", "what", "used", "do",
                   "did", "way", "with", "went", "through", "be", "yourself", "myself", "take", "if", "only"}}
    words = {norm_word(w, e["lang"]) for v in hw.split("/") for w in re.split(r"[\s,~…]+", v)}
    return sorted(w for w in words if len(w) > 2 and w not in stop[e["lang"]] and w != "x")


def clause_words(toks):
    return {w for form, lemma in toks for w in (form, lemma)}


def lemma_triggers(e, toks, lang):
    keys = [{norm_word(f, lang), norm_word(l, lang)} for f, l in toks]
    out = []
    for variant in e["variants"]:
        n = len(variant)
        for i in range(len(toks) - n + 1):
            if all(variant[k] in keys[i + k] for k in range(n)):
                out.append(" ".join(toks[i + k][0] for k in range(n)))
    return out


def stage5_counts(path):
    counts = defaultdict(Counter)
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = [c for c in reader.fieldnames if c[:2] in ("L-", "P-")]
        for r in reader:
            for c in cols:
                if r[c] == "1":
                    counts[c][r["lang"]] += 1
    return counts


def cell(s, n=None):
    s = str(s).replace("|", "\\|").replace("\n", " ")
    return s if n is None or len(s) <= n else s[: n - 1] + "…"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.csv"))
    ap.add_argument("--out", default=str(ROOT / "docs/lexicon_v03_revision_list.md"))
    ap.add_argument("--examples-out", default=str(ROOT / "data/processed/lexicon_v03_examples.md"))
    args = ap.parse_args(argv)
    proc = Path(args.inp).parent

    lex = load_lexicon(args.lexicon)
    for e in lex["entries"]:
        if e["entry_id"] in SURFACE_ONLY:
            e["variants"] = headword_variants(e, include_surface_only=True)
    entry = {e["entry_id"]: e for e in lex["entries"]}
    clauses = [json.loads(line) for line in open(args.inp, encoding="utf-8")]
    dev = [c for c in clauses if split_of(c["record_id"]) == "dev"]
    devtext = {c["clause_id"]: c for c in dev}
    toks_all = load_tokens(proc / "tokens.csv")
    toks = {cid: [(norm_word(f, devtext[cid]["lang"]), norm_word(l, devtext[cid]["lang"])) for f, l in t]
            for cid, t in toks_all.items() if cid in devtext}
    raw_toks = {cid: t for cid, t in toks_all.items() if cid in devtext}
    full = stage5_counts(proc / "clause_features.csv")

    surface, lemma = defaultdict(set), defaultdict(set)
    for c in dev:
        t = toks.get(c["clause_id"], [])
        tsets = [{f, l} for f, l in t]
        for eid, how in match_clause(c, tsets, lex).items():
            if how in ("surface", "both"):
                surface[eid].add(c["clause_id"])
            if how in ("lemma", "both"):
                lemma[eid].add(c["clause_id"])
    dev_n = {lang: sum(c["lang"] == lang for c in dev) for lang in ("hi", "en")}
    dev_texts = {lang: len({c["record_id"] for c in dev if c["lang"] == lang}) for lang in ("hi", "en")}
    examples = {}
    md = []
    w = md.append

    w("# Lexicon v0.3 revision list\n")
    w("_Generated by `src/analysis/lexicon_revision.py`. Proposals for the lexicon editor; nothing in `lexicon/` was "
      "changed. All matches are unreviewed (machine-provisional)._\n")
    w(f"- Evidence comes from the **dev split only** (hi {dev_texts['hi']} texts / {dev_n['hi']:,} clause units, en "
      f"{dev_texts['en']} / {dev_n['en']:,}), so the confirmatory 70% does not shape v0.3. Whole-corpus counts appear "
      "only in (e), as Stage 5 already logged them.")
    w("- Example clauses are cited by `clause_id`. The texts are in `data/processed/lexicon_v03_examples.md` "
      "(git-ignored; third-party text stays out of git). clause_ids are positional and change if Stage 3 is re-run.\n")

    w("## (a) Zero-match entries (16): reword or remove\n")
    w("Near-miss search on dev clauses, per '/'-separated headword variant: (1) the variant phrase verbatim in "
      "clause_text (case- and nukta-insensitive), where the pattern did not fire (either the pattern is narrower than the headword by design, or it is broken); (2) clauses that "
      "contain two or more different content words of the same variant (form or lemma), e.g. भगवान + बुला. A single "
      "common word (करना, will, life) is not evidence and is only listed. Near misses → reword (check the examples); "
      "none → no corpus evidence: hold as `proposed` for the expanded corpus, or remove.\n")
    w("| entry | headword | verbatim | ≥ 2 variant words in one clause | single-word counts | suggested action | examples |")
    w("|---|---|---|---|---|---|---|")
    for lang in ("hi", "en"):
        for eid in ZERO[lang]:
            e = entry[eid]
            hw = e["headword_deva"] if lang == "hi" else e["headword_en"]
            variants = [re.sub(r"\([^)]*\)", " ", v).strip() for v in hw.split("/")]
            verbatim, co, single = [], [], {}
            for v in variants:
                phrase = denukta(norm_word(v, lang)).lower()
                if len(phrase) > 3:
                    verbatim += [cid for cid, c in devtext.items() if c["lang"] == lang
                                 and phrase in denukta(c["clause_text"]).lower() and cid not in verbatim]
                kws = [denukta(k) for k in key_words(dict(e, headword_deva=v, headword_en=v))]
                for cid, t in toks.items():
                    if devtext[cid]["lang"] != lang:
                        continue
                    ws = {denukta(x) for x in clause_words(t)}
                    present = [k for k in kws if k in ws]
                    for k in present:
                        single[k] = single.get(k, 0) + 1
                    if len(set(present)) >= 2 and cid not in co:
                        co.append(cid)
            hits = verbatim + [c for c in co if c not in verbatim]
            for cid in hits[:3]:
                examples[cid] = devtext[cid]["clause_text"]
            action = ("headword phrase present but pattern silent: check the examples (sense may differ)" if verbatim else
                      "reword: near misses, check examples" if co else
                      "no dev evidence: hold as proposed or remove")
            w(f"| {eid} | {cell(hw, 60)} | {len(verbatim)} | {len(co)} | "
              f"{'; '.join(f'{k} {v}' for k, v in sorted(single.items(), key=lambda kv: -kv[1])) or '—'} | "
              f"{action} | {', '.join('`' + c + '`' for c in hits[:3]) or '—'} |")
    w("\nP-HI-46 note: both verbatim dev hits are the deceased's own routine (चाय बनाना as a request, उनका काम करना on "
      "the farm), not a survivor taking it over; the pattern's जैसे/जो X करते/बनाते थे frame is what carries "
      "'takeover', so the zero is real in dev. The 30 two-word hits are almost all काम + करना (generic).")
    w("")

    w("## (b) Lemma-channel inflation (3 entries)\n")
    w("Stage 5 ORs the regex pattern with a headword-lemma channel. For these three entries the lemma channel adds "
      "far more clauses than the pattern finds (whole corpus: P-HI-32 +404, P-HI-33 +143, L-EN-16 +114).\n")
    w("Interim status (decision 2026-10-10, code review): **L-EN-16 is matched by its pattern only** "
      "(`lexmatch.SURFACE_ONLY`) until v0.3 rewords the headword; the counts below still show what the lemma channel "
      "would add. P-HI-32 and P-HI-33 still use both channels.\n")
    w("| entry | headword | dev: pattern | dev: lemma only | top lemma-only triggers (dev) | examples (lemma only) |")
    w("|---|---|---|---|---|---|")
    for eid in INFLATED:
        e = entry[eid]
        only = sorted(lemma[eid] - surface[eid])
        trig = Counter(t for cid in only for t in lemma_triggers(e, raw_toks.get(cid, []), e["lang"]))
        for cid in only[:3]:
            examples[cid] = devtext[cid]["clause_text"]
        hw = e["headword_deva"] if e["lang"] == "hi" else e["headword_en"]
        w(f"| {eid} | {cell(hw)} | {len(surface[eid])} | {len(only)} | "
          f"{', '.join(f'{k} ({v})' for k, v in trig.most_common(5)) or '—'} | "
          f"{', '.join('`' + c + '`' for c in only[:3]) or '—'} |")
    w("")
    for eid in INFLATED:
        w(f"- **{eid}**: {FIX[eid]}")
    w("- General option: run lexmatch with `--channels surface` for every entry whose pattern was written to carry "
      "context, and keep the lemma channel only where the headword is a single unambiguous lemma.\n")

    w("## (c) Collocation candidates (from `docs/collocation_candidates.csv`)\n")
    w("PMI = log2(c(e,w)·N / (c(e)·c(w)·2·5)), window ±5 words within a sentence, dev split, c(e,w) ≥ 3, "
      "PMI ≥ 3 and ≥ 2 texts for the candidate list. Counts are small (3–7): treat these as leads.\n")
    pmi = list(csv.DictReader(open(ROOT / "results/collocation_pmi.csv", encoding="utf-8")))
    by_entry = defaultdict(list)
    for r in pmi:
        by_entry[(r["lang"], r["entry_id"])].append(r)
    cands = list(csv.DictReader(open(ROOT / "docs/collocation_candidates.csv", encoding="utf-8")))
    for c in cands:
        lang, cand = c["lang"], c["candidate"]
        anchors = [r for r in pmi if r["lang"] == lang and r["collocate"] == cand]
        best = c["best_anchor"]
        neigh = sorted((r for r in by_entry[(lang, best)] if r["collocate"] != cand),
                       key=lambda r: -float(r["pmi"]))[:5]
        ex = [cid for cid in sorted(surface[best] | lemma[best])
              if denukta(cand) in {denukta(x) for x in clause_words(toks.get(cid, []))}]
        if len(ex) < 3:
            sent_ids = {(devtext[cid]["record_id"], devtext[cid]["sent_index"]) for cid in surface[best] | lemma[best]}
            ex += [cid for cid, t in toks.items() if cid not in ex
                   and (devtext[cid]["record_id"], devtext[cid]["sent_index"]) in sent_ids
                   and denukta(cand) in {denukta(x) for x in clause_words(t)}]
        for cid in ex[:3]:
            examples[cid] = devtext[cid]["clause_text"]
        w(f"### {lang} · {cand}\n")
        w(f"- Anchors: " + "; ".join(f"{r['entry_id']} {r['headword']} (PMI {float(r['pmi']):.2f}, "
                                     f"co-occ {r['cooc']}, {r['n_texts']} texts)" for r in anchors))
        w(f"- Candidate frequency in dev: {c['candidate_freq']}")
        w(f"- Other collocates of {best} ({c['best_anchor_headword']}): "
          + (", ".join(f"{r['collocate']} {float(r['pmi']):.2f}" for r in neigh) or "—"))
        w(f"- Examples: {', '.join('`' + x + '`' for x in ex[:3]) or '—'}\n")

    w("## (d) L-HI-C2 (honorific plural for the deceased) and the referent-stage honorific flag\n")
    c2_full = full["L-HI-C2"]["hi"]
    n_hi_full = sum(c["lang"] == "hi" for c in clauses)
    refs = {r["clause_id"]: r for r in csv.DictReader(open(proc / "referents.csv", encoding="utf-8"))}
    c2_dev = surface["L-HI-C2"] | lemma["L-HI-C2"]
    fin = [cid for cid in c2_dev if cid in refs]
    hon = [cid for cid in fin if refs[cid]["honorific"] == "True"]
    dec = [cid for cid in hon if refs[cid]["referent_class"] == "deceased"]
    cls = Counter(refs[cid]["referent_class"] for cid in fin)
    hon_dev = [cid for cid, r in refs.items() if cid in devtext and devtext[cid]["lang"] == "hi"
               and r["honorific"] == "True"]
    hon_dec_dev = [cid for cid in hon_dev if refs[cid]["referent_class"] == "deceased"]
    for cid in sorted(set(c2_dev) - set(dec))[:3]:
        examples[cid] = devtext[cid]["clause_text"]
    w(f"- Whole corpus (Stage 5): {c2_full:,} of {n_hi_full:,} Hindi clause units = "
      f"{100 * c2_full / n_hi_full:.1f}%. Dev: {len(c2_dev):,} of {dev_n['hi']:,} = "
      f"{100 * len(c2_dev) / dev_n['hi']:.1f}%.")
    w(f"- Dev overlap with `referents.csv` (finite clauses): {len(fin):,} C2 clauses; honorific = True in "
      f"{len(hon):,}; of those, referent_class = deceased in {len(dec):,}. Referent classes of C2 clauses: "
      + ", ".join(f"{k} {v}" for k, v in cls.most_common()) + ".")
    w(f"- The referent stage flags {len(hon_dev):,} dev Hindi finite clauses as honorific, {len(hon_dec_dev):,} of "
      "them with a deceased referent.")
    w("- Why it is broad: the pattern is a 3rd-person/आप pronoun form followed within 80 characters by any plural-"
      "looking verb ending. It has no referent, so every polite or plural वे/उनका about anyone (doctors, relatives, "
      "groups) matches; the lexicon's own note says singular reference needs the parse or a human. Examples of C2 "
      "hits without a deceased honorific referent: "
      + ", ".join("`" + x + "`" for x in sorted(set(c2_dev) - set(dec))[:3]) + ".")
    w("- **Proposal.** Keep one definition of 'honorific plural for the deceased', and let the referent stage own it:")
    w("  1. L-HI-C2 stops being a regex dictionary match. In v0.3 it becomes a *derived* entry: a clause carries "
      "L-HI-C2 when referents.csv has honorific = True **and** referent_class = deceased (agreement-based, the Stage 5b "
      "decision recorded in PROGRESS.md). The regex can stay in `constructions.yaml` as a candidate generator for "
      "review, not as a count.")
    w("  2. Its grammar_forced value is resolved per clause from the deceased's relation (parent / elder → Y; "
      "younger or same-generation → context, i.e. a choice), instead of the entry-level 'context'.")
    w("  3. Counts of C2 are reported apart from chosen relational language (matcher rule R2), as the entry note "
      "already requires; orientation F should not be credited from a grammar-forced honorific.")
    w("  4. Before either version is used, validate the referent-stage honorific flag on the gold set (it agrees "
      "with Stanza's Polite=Form on only 805 of 2,857 clauses flagged by either; see RESULTS_LOG).\n")

    w("## (e) Match counts for every entry\n")
    w("Clauses with ≥ 1 match (surface OR lemma channel). `whole` = Stage 5 run over the whole corpus "
      "(already logged); `dev` = this script on the dev split; `lemma only` = dev clauses found only by the lemma "
      "channel.\n")
    w("| entry | lang | headword | pos | whole | dev | dev lemma only |")
    w("|---|---|---|---|---|---|---|")
    for e in lex["entries"]:
        eid, lang = e["entry_id"], e["lang"]
        hw = e["headword_deva"] if lang == "hi" else e["headword_en"]
        both = surface[eid] | lemma[eid]
        w(f"| {eid} | {lang} | {cell(hw, 50)} | {cell(e['pos'], 30)} | {full[eid][lang]} | {len(both)} | "
          f"{len(lemma[eid] - surface[eid])} |")
    Path(args.out).write_text("\n".join(md) + "\n", encoding="utf-8")

    ex = ["# Lexicon v0.3 revision list: example clauses (LOCAL ONLY, third-party text, do not commit)\n",
          "| clause_id | clause_text |", "|---|---|"]
    ex += [f"| `{cid}` | {cell(examples[cid])} |" for cid in sorted(examples)]
    Path(args.examples_out).write_text("\n".join(ex) + "\n", encoding="utf-8")
    print(f"{args.out}; {len(examples)} example clauses -> {args.examples_out}")
    print(json.dumps(dict(c2_dev=len(c2_dev), c2_fin=len(fin), c2_hon=len(hon), c2_hon_dec=len(dec),
                          hon_dev=len(hon_dev), hon_dec_dev=len(hon_dec_dev),
                          inflated={i: [len(surface[i]), len(lemma[i] - surface[i])] for i in INFLATED})))


if __name__ == "__main__":
    main()
