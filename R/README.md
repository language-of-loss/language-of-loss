# R/: modelling scripts

These scripts were written on 2026-10-10 before R was installed. On 2026-10-10 R 4.6.1 was installed and every
script passed `--dry-run` on the real inputs. The `--run` branches have been exercised only on **synthetic random
inputs** in a throwaway `--root` with a dummy agreement file, as a code check. That run caught one bug: in
`h1_glmm.R` the data variable `df` was masked by the `df` column inside `out[, ...]`. Nothing has been fitted on
corpus data.

| script | model | reads | writes (results/) |
|---|---|---|---|
| `h1_glmm.R` (core, outputs 3 and 4) | H1: `glmer(relational ~ hindi + log_clauses + loss_type + (1 \| record_id), binomial)`; Run 1 = all finite clauses, Run 2 = without the clauses the relational rules mark forced (`forced_relational` in eligibility.csv), Run 2b = Run 2 without closing-formula clauses (construction F6); CR2 cluster-robust SEs (clubSandwich) from the companion GLM. `--subset english_home` (output 4): English side = writers stating English as home language (human-confirmed only for `--run`) | clause_features, text_features, text_meta, split, eligibility, referents | `h1_glmm_run{1,2,2b}[_english_home].csv` |
| `audit.R` (core, output 5) | per system: `lmer(score_z ~ intensity_c * hindi * cue + (1 \| pair))` (classifiers without the cue terms), on all pairs and on the agreed pairs; lasso + stability selection of the error `z(score) − z(intensity)` on the Hindi passages' component profiles (stable under-read = selected ≥ 0.6 of 100 half-samples with a negative coefficient) | data/processed/{audit_pairs, audit_ratings, audit_passage_scores, audit_passage_components}.csv, results/audit_chat_scores.csv | `audit_lmer.csv`, `audit_stability.csv` |
| `optional/p2_beta.R` (off the core path) | P2: `betareg(naming_share ~ hindi)` (+ `log_clauses` sensitivity), sandwich SEs | clause_features, text_features, text_meta, split | `p2_beta.csv`, `p2_beta_predicted.csv` |
| `optional/audit_mediation.R` (retired from the core path 2026-10-10: no cue term) | `lmer(score ~ intensity * hindi + (1 \| pair))`; `mediation::mediate`; glmnet lasso with stability selection | audit_scores, text_features, clause_features, text_meta, split (+ data/annotation/human_text_scores.csv) | `audit_lmer.csv`, `audit_mediation.csv`, `audit_stability.csv` |
| `common.R` | argument parsing, input loading, the guard, the `--subset` rule | | |

Scripts in `R/optional/` source `../common.R`; the repo root is the nearest ancestor holding `R/common.R`.

Each script header defines its variables (relational, naming share, intensity, pair, error) and the reason for
each choice. Each script also writes `<name>_sessioninfo.txt` with the package versions it actually used.

## Guard: no fitting before human agreement

As the study protocol requires, `--run` stops unless `results/agreement/agreement_summary_gold_sheet_v1.csv` holds real
agreement statistics (>= 1 field coded by both coders with a finite alpha; the same check as `predictions.py`), written by
`src/analysis/agreement.py` from two independent coders. It fits on the **confirmatory** split by default.
`--dry-run` is always allowed, but **on the dev split only**: `--split confirmatory` or `--split all` is refused, so
the held-out split is reachable only through `--run`, behind the guard. It builds the model frame and fits nothing.
It writes `results/<name>_frame.md` with row counts and predictor summaries only, and never any outcome statistic
(no relational shares, naming shares, audit scores or audit intensity, overall or by language). `results/*_frame.md` is git-ignored.

```bash
Rscript R/h1_glmm.R --dry-run            # check the frame now (dev split, predictors only)
Rscript R/h1_glmm.R --run                # after agreement statistics exist; confirmatory split
Rscript R/h1_glmm.R --run --split dev    # exploratory only; prints a warning
```

Inputs come from `make all` (data/processed/*). `split.csv` comes from `make gold`, and `audit_scores.csv` from
`src/analysis/audit_models.py`.

## Install (macOS, exact lines)

```bash
brew install r                       # or the CRAN installer: https://cloud.r-project.org/bin/macosx/
Rscript -e 'install.packages(c("data.table", "lme4", "lmerTest", "clubSandwich", "betareg", "sandwich", "lmtest", "mediation", "glmnet"), repos = "https://cloud.r-project.org")'
Rscript -e 'for (p in c("data.table", "lme4", "lmerTest", "clubSandwich", "betareg", "sandwich", "lmtest", "mediation", "glmnet")) cat(p, as.character(packageVersion(p)), "\n")'
```

The third line prints the installed versions. Versions installed:

| package | version |
|---|---|
| R | 4.6.1 (2026-06-24), CRAN arm64 build (`R-4.6.1-arm64.pkg`, macOS) |
| data.table | 1.18.6.1 |
| lme4 | 2.0.6 |
| lmerTest | 3.2.1 |
| clubSandwich | 0.7.0 |
| betareg | 3.2.6 |
| sandwich | 3.1.3 |
| lmtest | 0.9.40 |
| mediation | 4.5.1 |
| glmnet | 5.1 |

Recorded 2026-10-10 from the third install line above. Binaries came from cloud.r-project.org (sonoma-arm64).

For a fully frozen environment, use `renv` instead (`Rscript -e 'install.packages("renv"); renv::init()'`) and
commit `renv.lock`.

## Known choices to review

- **H1 cluster-robust SEs.** clubSandwich has no method for `glmerMod`. CR2 SEs therefore come from the
  population-averaged logistic GLM, clustered by text, and are reported next to the GLMM. They estimate different
  things: the marginal effect versus the conditional (within-text) effect.
- **relational** follows the paper's definition: the union of subject/experiencer referent in {kin, community,
  deceased}, target referent in those classes, or a matched lexicon entry with orientation F or C. It is computed
  once, per finite clause, in `src/analysis/referents.py` (`referents.csv`: `relational` and the three channels
  `rel_subject`, `rel_target`, `rel_entry`; text-level rates in `text_features.csv` as `rel_any` and so on). The
  referent channels are heuristic and the entry channel is matcher-recall-limited, so each channel needs
  validation against the gold codes.
- **loss_type** comes from the machine-written `deceased_relation_as_stated` (`src/analysis/text_meta.py`). The
  category set is fixed once on the **full corpus** (all of `text_meta.csv`) by `loss_type_kept()` in `common.R`:
  candidates parent, grandparent, sibling, spouse, child, friend, other; a candidate needs at least
  `LOSS_MIN_PER_LANG` = 5 texts in each language, otherwise it (and any value outside the set, such as `unstated`)
  merges into `other`. The same mapping applies to every split; nothing is re-pooled per split.
- **intensity** for the audit is a lexicon proxy (the comp_FEEL_BAD rate) until a human intensity rating exists.
  The **pair** variable is a matching convention: hi/en texts matched within split × loss_type on length.
- **naming_share** uses emotional clauses as the denominator (names_emotion or FEEL_BAD). Texts with fewer than
  5 emotional clauses are dropped.
