"""Generate docs/preregistration.md from the quantities the code actually uses, so the registration text and the code"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assemble
import audit_match
import audit_passages
import core
import freeze
import gold
import meta_prefill
import rae
import referents
import text_meta

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "preregistration.md"
DRAFT = ("generated 2026-10-11 from the code; registered by the annotated git tag named in docs/registration.txt "
         "(`make register`); OSF filing (DOI) pending")
DEVIATIONS = [
    "Gold set (decisions 2026-10-10: 100 clauses per language, component subset 100, pilot 20 per language; the "
    "per-text cap raised from 5% to 7% because 15 Hindi development texts cannot supply 100 clauses at 5%, decided "
    "before any coding began): Hindi 100 (all 15 dev texts, 7 per text at most), English 100. The Hindi pilot repeats "
    "texts (20 clauses from 15 dev texts). The draw was locked before the corpus review "
    "(docs/review_master_2026-10.csv) was finished: texts the review adds do not enter it.",
    "Output 4 (second-language rival) is not estimable from text-internal evidence: no text states the writer's home "
    "language (rule pre-fill 0 of 123), so English-dominant writers cannot be identified. Registered instead: the rival "
    "check, Runs 1 / 2 / 2b / R-F6 with diaspora and platform covariates. Limitation: the second-language detachment "
    "account is not tested directly; diaspora is 'unknown' unless a text states residence (2 of 123 by rule).",
    "Output 5: romanised short-form passages may come from confirmatory short-form posts (decision 2026-10-10): 58 of "
    "100 (every romanised / code-mixed post: 18 dev, 40 confirmatory); the long-form hypothesis passages stay dev only "
    "(150 + 150).",
    "Output 8: the MuRIL classifier pair (GoEmotions-MT vs BRIGHTER-Hindi + native gold) has not been run on gold "
    "labels; only the McNemar step is part of this registration's code.",
    "Lexicon v0.2 re-frozen 2026-10-10 after the investigators' decisions (DUTY_UNDONE dropped from P-HI-44 / P-EN-44; the four "
    "DUTY counterpart links two-way); 21 other one-way counterpart links remain and do not enter any estimate.",
    "Referent coder v2 + the decisions of 2026-10-10 (address to the dead = REL-VOC chosen_relational; a second-person "
    "subject addressing the deceased = deceased) moved the dev relational choice share 5.56 -> 4.68 -> 6.93 "
    "(RESULTS_LOG 2026-10-10). Run 2b now treats honorific reference to elders as forced; the former Run 2b (minus "
    "closing formulae) is robustness check R-F6.",
    "2026-10-11, annotation provenance (investigators' decision): every gold label, audit rating, calibration rating, metadata "
    "confirmation and corpus include/exclude decision was machine pre-filled in a two machine runs (two machine runs "
    "of one brief) and reviewed and accepted by the investigators; logged corrections: 0. Inter-coder alpha is "
    "agreement between the two machine runs, not independent human reliability. Adjudicated gold = the fields on which "
    "both reviewed sheets agree (codebook 115 of 200 clauses on all fields, 166-197 per field); disagreements listed "
    "in docs/adjudication_needed.md and skipped.",
    "2026-10-11, corpus: the review added 161 texts (over-cap texts included: Hindi 69, English 48). Texts: Hindi 146 "
    "(36 dev, 110 confirmatory), English 137 (47 dev, 90 confirmatory); 53,847 clause units. The locked gold set and "
    "the audit passages (drawn from the earlier dev texts) are unchanged; all 200 gold clauses verified present.",
    "2026-10-11, relation of the 161 added texts is a category word from the review (parent, grandparent, ...): "
    "father and mother cannot be told apart there, so the Run 2b honorific-elder rule cannot fire for a deceased "
    "father in those texts (Run 2b under-removes).",
    "2026-10-11, eligibility rule accuracy against the adjudicated labels: Hindi grammar_forced .739 (Wilson 95% "
    ".641-.818, n = 92) is below the 0.80 bar; the decomposition is reported as provisional.",
    "2026-10-11, added before registration: H1 domain random intercept (1 | source_domain) and a permutation test of "
    "the language label over texts (B = 999) in every run; output-7 JSD permutation test; Holm over outputs 6 and 7. "
    "The decomposition stays on the observed site rates as registered (Rogan-Gladen corrected rates are reported for "
    "the codebook categories separately; the eligibility sites have no per-site validation to correct with).",
    "2026-10-11, output 4: diaspora is human-confirmed (reviewed pre-fill) for 118 of 283 texts; the 161 added texts "
    "have no metadata review rows. The rival check runs only when every text in the split is confirmed "
    "(R/common.R guard); otherwise it is reported as not run.",
    "2026-10-11, output 8: a1_gold.csv is derived, not coded: Hindi gold clause emotional = 1 when the adjudicated "
    "process is L or Rs, 0 when NA, left out when not agreed (91 clauses: 48 / 43; scripts/derive_a1_gold.py).",
]


def r_const(path, name):
    m = re.search(rf"^{name} <- (.+)$", (ROOT / path).read_text(encoding="utf-8"), flags=re.M)
    return m.group(1).strip() if m else "?"


def argparse_default(path, flag):
    m = re.search(rf'"--{flag}"[^)]*default=([^,)]+)', (ROOT / path).read_text(encoding="utf-8"))
    return m.group(1).strip() if m else "?"


def r_header(path, start, stop):
    lines, on = [], False
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        if line.startswith(start):
            on = True
        if on and line.startswith(stop):
            break
        if on:
            lines.append(line.lstrip("# ").rstrip())
    return [x for x in lines if x]


def build():
    rec = freeze.recorded()
    lex_hash = rec.get("lexicon/lexicon.csv", ("?", 0))[0]
    version = re.search(r"^# Lexicon freeze: (.+)$", freeze.FREEZE.read_text(encoding="utf-8"), flags=re.M)
    comps = gold.components_list(ROOT / "lexicon")
    L = ["# Pre-registration (core outputs 1–9)", "",
         f"Status: {DRAFT}. Generated by `src/analysis/preregistration.py`; do not edit by hand (the test "
         "`tests/test_preregistration.py` fails when this file and the code disagree).", "",
         "## 1. Data and split", "",
         "- Long-form corpus: provisionally eligible Devanagari-Hindi and English texts (`data/clean/blogs_merged.jsonl`); "
         "the unit of inference is the text.",
         f"- Split: a record is development when sha256(`{gold.SPLIT_NS}` + record_id), read as a fraction, is "
         f"< {gold.DEV_SHARE}; otherwise confirmatory. The rule depends on the record_id only.",
         "- Every instrument is built and tuned on the development split. The confirmatory split is opened only by the "
         "fitting runs (`--run`), behind the agreement guard (section 3), after this registration is filed.", "",
         "## 2. Instrument", "",
         f"- Lexicon {version.group(1) if version else '?'}: `lexicon/lexicon.csv` sha256 `{lex_hash}` "
         f"(all frozen files in `lexicon/FREEZE.md`); K = {len(comps)} components: {', '.join(comps)}.",
         "- Gold codebook (fields and values): " + "; ".join(f"{k} = {'/'.join(v)}" for k, v in gold.CODEBOOK.items())
         + ".",
         f"- Gold set: {argparse_default('src/analysis/gold.py', 'n-per-lang')} finite clauses per language, development "
         f"split only, at most {argparse_default('src/analysis/gold.py', 'max-text-share')} of them from one text, seed "
         f"{gold.SEED}; component subset {argparse_default('src/analysis/gold.py', 'n-components')} (half per language, "
         f"half lexicon-matched); calibration pilot {argparse_default('src/analysis/gold.py', 'pilot-n')} clauses per language "
         "(one per text before a text repeats). Labels: machine pre-filled by two independent machine runs of one brief "
         "(two machine runs, 2026-10-11), each reviewed and accepted by one investigator (investigators' decision 2026-10-11; "
         "every sheet carries a `provenance` column and a `corrections` count). This is machine-assisted annotation "
         "with investigator verification, not independent human coding; every output is labelled \"reviewed "
         "machine-prefilled labels\".",
         f"- Referent coder: rules {', '.join(referents.RULES_V2)} (v2); the output before v2 is kept in *_v1 columns.",
         "- Text metadata: " + "; ".join(f"{k} = {'/'.join(v)}" for k, v in meta_prefill.FIELDS.items())
         + "; rule pre-fill, used for estimation only after human confirmation.", "",
         "## 3. Guards", "",
         f"- No hypothesis test, model fit or corrected rate before `{core.AGREEMENT}` holds real agreement statistics "
         "(at least one field coded in both sheets with a finite Krippendorff's alpha; "
         "`predictions.tests_allowed`, `R/common.R agreement_ok`).",
         "- The confirmatory split is fitted only after this document is filed: `make core` waits for "
         "`docs/registration.txt` (the `make register` git tag, or an OSF DOI) before the R fits that open it "
         "(`core.registered`).",
         "- Agreement threshold: alpha >= 0.70 per field (paper §3.4); fields below it are revised and re-coded.",
         f"- Rogan–Gladen correction only when the per-language recall gap is <= {rae.RECALL_GAP_MAX} "
         "(`rae.RECALL_GAP_MAX`); a sign change under correction is not reported as a finding.",
         "- Corpus text leaves the machine only through `src/analysis/llm_coder.py` and `src/analysis/audit_chat.py` "
         "(in `make core` only with `LLM=1`), and the reader-study forms (study protocol, 2026-10-11).", "",
         "## 4. Outputs, estimands and models", ""]
    spec = {
        1: ["Krippendorff's alpha (nominal) per codebook field and per component between the two reviewed "
            "machine-prefilled sheets (`agreement.py`; agreement between two machine runs, each reviewed by one "
            "investigator)."],
        2: ["Per category (codebook value) and language: precision, recall (sensitivity), F1 and false-positive rate "
            "of the dictionary channel against the adjudicated gold set (`validate.py`; adjudicated = the fields on "
            "which both reviewed sheets agree, the rest listed in docs/adjudication_needed.md and skipped).",
            "Corrected rate pi = (o − phi)/(s − phi), o = mean of per-text rates over finite clauses; interval by double "
            f"bootstrap (texts and validation items), B = {argparse_default('src/analysis/corrected_rates.py', 'B')} "
            f"(`corrected_rates.py` → `rae.py`)."],
        3: r_header("R/h1_glmm.R", "# H1:", "# In :")
           + ["Runs: " + "; ".join(f"{k} = {v}" for k, v in assemble.RUN_LABEL.items()) + ".",
              "Decomposition (marker relational, unit site): r_L = f_L + q_L·p_L; Δ = (f_hi − f_en) + (q_hi − q_en)·p̄ "
              "+ q̄·(p_hi − p_en) = forced + opportunity + choice; percentile intervals from "
              f"B = {argparse_default('src/analysis/decompose.py', 'B')} bootstrap resamples of texts within language, "
              f"seed {argparse_default('src/analysis/decompose.py', 'seed')}. The choice share is the headline statistic."],
        4: [assemble.NOT_ESTIMABLE_4,
            "Model: the output-3 GLMM and CR2 GLM with `diaspora` (yes / no / unknown, human-confirmed) and `platform` "
            "(type of publishing site from the source domain: " + ", ".join(sorted(["self_published", "personal_site"]
            + list(text_meta.PLATFORM_TYPES))) + ") added (`R/h1_glmm.R --covariates rival`)."],
        5: r_header("R/audit.R", "# 1. Recognition model", "# In :")
           + [f"Passages: {audit_passages.LO}–{audit_passages.HI} words, density without "
              f"{', '.join(audit_passages.EXCLUDE_ENTRIES + audit_passages.EXCLUDE_FLAGS)}, "
              f"{argparse_default('src/analysis/audit_passages.py', 'n-long')} per language from the development split; "
              f"{argparse_default('src/analysis/audit_passages.py', 'n-short')} romanised short-form posts; "
              f"{argparse_default('src/analysis/audit_passages.py', 'n-calibration')} BRIGHTER-Hindi calibration items.",
              f"Matching: Hindi–English pairs within the same relationship, |mean rating difference| <= "
              f"{audit_match.TOLERANCE}; agreed = both raters within {audit_match.AGREE_WITHIN} point.",
              f"Stability selection: B = {r_const('R/audit.R', 'STAB_B')}, threshold {r_const('R/audit.R', 'STAB_PI')}, "
              f"seed {r_const('R/audit.R', 'SEED')}."],
        6: ["Hindi chosen-dative rate = chosen_dative / (chosen_dative + chosen_nominative) against the forced baseline "
            "forced_dative / (forced_dative + forced_nominative); exact binomial test, two-sided, H0: p = forced "
            f"baseline; text-bootstrap intervals B = {argparse_default('src/analysis/predictions.py', 'B')} "
            "(`predictions.py`). Holm-corrected together with the output-7 permutation p."],
        7: ["Jensen–Shannon divergence (base 2) between the two languages' component-hit profiles; text-bootstrap "
            "interval of the plug-in value; permutation test (language labels shuffled across texts, same B), "
            "Holm-corrected together with the output-6 binomial p (`predictions.py`)."],
        8: ["Recall of NRC-Hindi and of the native lexicon on native-only versus translatable Hindi gold items (strict "
            "native-only definition; tolerated-molecule definition as sensitivity), paired item bootstrap "
            "(`translation_bias.py`).",
            "One MuRIL pair (translated vs native training data, same configuration) on held-out native Hindi gold "
            "clauses: accuracy, F1, exact McNemar (`mcnemar.py`)."],
        9: [f"PMI collocation networks per language, development split: window ±{argparse_default('src/analysis/collocation.py', 'window')}, "
            f"entries with >= {argparse_default('src/analysis/collocation.py', 'min-matches')} matched clauses, "
            f"c(e,w) >= {argparse_default('src/analysis/collocation.py', 'min-count')}; an appendix exhibit of lexicon "
            "candidate generation, not a test (`collocation.py`)."],
    }
    for k, what in core.OUTPUTS.items():
        L += [f"### Output {k}: {what}", ""] + [f"- {x}" for x in spec[k]] + [""]
    L += ["## 5. Pre-registered directions", "",
          "Expected sign: + = Hindi higher (or the quantity > 0), − = Hindi lower. Source: draft v4 §1.5 / §3.6, as "
          "restated in `assemble.expectations`.", "",
          "| ID | Output | Expectation | Sign |", "|---|---|---|---|"]
    L += [f"| {eid} | {k} | {stmt} | {sign} |" for eid, k, stmt, sign, _, _ in assemble.expectations(ROOT / "nonexistent")]
    L += ["", "## 6. Multiple comparisons", "",
          "- Draft v4 §3.6: the hypothesis is tested once (Run 2 plus the choice share) and is uncorrected; P1–P3 are "
          "Holm-corrected as a family; A1 and A2 are applications reported descriptively with intervals. On the core "
          "path the family is output 6 (binomial) and output 7 (JSD permutation), Holm-corrected together "
          "(`predictions.holm`); P3 is off the main path (src/optional/). The H1 runs additionally report a "
          "permutation p over texts (R/h1_glmm.R), not multiplicity-corrected (one hypothesis).", "",
          "## 7. Deviations and open items (dated 2026-10-10 and 2026-10-11)", ""]
    L += [f"- {d}" for d in DEVIATIONS]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    text = build()
    if args.check:
        same = Path(args.out).exists() and Path(args.out).read_text(encoding="utf-8") == text
        print("preregistration.md is current" if same else "preregistration.md is STALE: regenerate it")
        sys.exit(0 if same else 1)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
