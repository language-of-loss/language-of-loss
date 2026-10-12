source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))),
                 "..", "common.R"))
SCORE_MODEL <- "xlm_emo"
SCORE_COL <- "p_sadness"
INTENSITY_SOURCE <- "auto"
SIMS <- 1000
STAB_B <- 100
STAB_PI <- 0.6
SEED <- 20261009

opt <- parse_args()
guard(opt)
d <- read_inputs(opt)
pp <- function(...) path(opt, ...)

sc_file <- pp("data", "processed", "audit_scores.csv")
if (!file.exists(sc_file)) stop("missing ", sc_file, " (run src/analysis/audit_models.py)")
sc <- fread(sc_file, encoding = "UTF-8")[model == SCORE_MODEL, .(record_id, score = get(SCORE_COL))]
human_file <- pp("data", "annotation", "human_text_scores.csv")
human <- if (file.exists(human_file)) fread(human_file, encoding = "UTF-8") else NULL

comp_cols <- grep("^comp_", names(d$tf), value = TRUE)
tx <- merge(d$tf[, c("record_id", "lang", "n_clauses", comp_cols), with = FALSE], sc, by = "record_id")
tx <- merge(tx, d$meta[, .(record_id, pair_id)], by = "record_id")
use_human_int <- !is.null(human) && "intensity" %in% names(human) && INTENSITY_SOURCE != "lexicon"
if (INTENSITY_SOURCE == "human" && !use_human_int) stop("INTENSITY_SOURCE = human but no intensity column in ", human_file)
if (use_human_int) {
  tx <- merge(tx, human[, .(record_id, intensity)], by = "record_id")
} else {
  tx[, intensity := comp_FEEL_BAD]
}
n_unpaired <- tx[is.na(pair_id) | pair_id == "", .N]
tx <- tx[!is.na(pair_id) & pair_id != ""]
tx[, `:=`(hindi = as.integer(lang == "hi"), pair = factor(pair_id))]

if (opt$mode == "dry-run") {
  describe_frame(tx, pp("results", "audit_frame.md"),
                 sprintf("Audit model frame (dry run, split = %s; score = %s %s; intensity = %s; %d unpaired dropped; human file %s)",
                         opt$split, SCORE_MODEL, SCORE_COL, if (use_human_int) "human" else "lexicon comp_FEEL_BAD",
                         n_unpaired, if (is.null(human)) "absent" else "present"),
                 c("hindi", "lang", "n_clauses"))
  quit(save = "no")
}

suppressPackageStartupMessages({
  library(lme4)
  library(lmerTest)
  library(mediation)
  library(glmnet)
})
set.seed(SEED)
meta_cols <- list(split = opt$split, n_texts = nrow(tx), n_pairs = uniqueN(tx$pair), n_unpaired_dropped = n_unpaired,
                  score = paste(SCORE_MODEL, SCORE_COL), intensity = if (use_human_int) "human" else "lexicon",
                  status = STATUS)

m1 <- lmerTest::lmer(score ~ intensity * hindi + (1 | pair), data = tx)
s1 <- summary(m1)$coefficients
lm_out <- data.table(term = rownames(s1), estimate = s1[, "Estimate"], se = s1[, "Std. Error"], df = s1[, "df"],
                     t = s1[, "t value"], p = s1[, "Pr(>|t|)"], singular = isSingular(m1))
fwrite(cbind(lm_out, as.data.table(meta_cols)), pp("results", "audit_lmer.csv"))
print(lm_out)

med.fit <- lme4::lmer(intensity ~ hindi + (1 | pair), data = tx)
out.fit <- lme4::lmer(score ~ intensity * hindi + (1 | pair), data = tx)
med <- mediate(med.fit, out.fit, treat = "hindi", mediator = "intensity", sims = SIMS)
ms <- summary(med)
med_out <- data.table(
  quantity = c("ACME (en)", "ACME (hi)", "ADE (en)", "ADE (hi)", "total effect", "prop. mediated (avg)"),
  estimate = c(ms$d0, ms$d1, ms$z0, ms$z1, ms$tau.coef, ms$n.avg),
  ci_lo = c(ms$d0.ci[1], ms$d1.ci[1], ms$z0.ci[1], ms$z1.ci[1], ms$tau.ci[1], ms$n.avg.ci[1]),
  ci_hi = c(ms$d0.ci[2], ms$d1.ci[2], ms$z0.ci[2], ms$z1.ci[2], ms$tau.ci[2], ms$n.avg.ci[2]),
  p = c(ms$d0.p, ms$d1.p, ms$z0.p, ms$z1.p, ms$tau.p, ms$n.avg.p))
fwrite(cbind(med_out, as.data.table(meta_cols), sims = SIMS), pp("results", "audit_mediation.csv"))
print(med_out)

if (is.null(human)) {
  message("step 3 skipped: ", human_file, " not found (needs human text scores on the model's 0-1 scale)")
} else {
  ex <- merge(tx, human[, .(record_id, human_score)], by = "record_id")
  ex[, error := score - human_score]
  X <- as.matrix(ex[, ..comp_cols])
  keep <- apply(X, 2, function(v) sd(v) > 0)
  X <- X[, keep, drop = FALSE]
  y <- ex$error
  cv <- cv.glmnet(X, y, alpha = 1, standardize = TRUE, nfolds = min(10, nrow(X)))
  lam <- cv$lambda.1se
  sel <- matrix(0L, STAB_B, ncol(X), dimnames = list(NULL, colnames(X)))
  for (b in seq_len(STAB_B)) {
    i <- sample(nrow(X), floor(nrow(X) / 2))
    f <- glmnet(X[i, , drop = FALSE], y[i], alpha = 1, standardize = TRUE, lambda = lam)
    sel[b, ] <- as.integer(as.vector(coef(f))[-1] != 0)
  }
  freq <- colMeans(sel)
  q <- mean(rowSums(sel))
  full <- as.vector(coef(cv, s = "lambda.1se"))[-1]
  stab <- data.table(component = colnames(X), selection_freq = freq, stable = freq >= STAB_PI,
                     full_data_coef = full)[order(-selection_freq)]
  stab[, `:=`(lambda = lam, B = STAB_B, threshold = STAB_PI, mean_selected = q,
              pfer_bound = q^2 / ((2 * STAB_PI - 1) * ncol(X)), n_texts_error = nrow(ex),
              components_constant_dropped = sum(!keep))]
  fwrite(cbind(stab, as.data.table(meta_cols[c("split", "score", "status")])), pp("results", "audit_stability.csv"))
  print(stab[1:min(10, .N)])
}
write_session(opt, "audit_mediation")
