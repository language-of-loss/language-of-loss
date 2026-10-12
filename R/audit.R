source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))),
                 "common.R"))
CLASSIFIERS <- list(xlm_emo = "p_sadness", muril_sent = "p_negative")
STAB_B <- 100
STAB_PI <- 0.6
SEED <- 20261010

opt <- parse_args()
guard(opt)
pp <- function(...) path(opt, ...)
need <- c(pairs = pp("data", "processed", "audit_pairs.csv"), ratings = pp("data", "processed", "audit_ratings.csv"),
          scores = pp("data", "processed", "audit", "passage_scores.csv"),
          comps = pp("data", "processed", "audit_passage_components.csv"))
missing <- need[!file.exists(need)]
if (length(missing)) stop("missing input(s): ", paste(missing, collapse = ", "),
                          " (audit_match.py needs the two filled rating sheets; audit_models.py --passages; ",
                          "audit_passages.py)")
pairs <- fread(need[["pairs"]], encoding = "UTF-8")
ratings <- fread(need[["ratings"]], encoding = "UTF-8")[, .(passage_id, mean_rating)]
long <- rbind(pairs[, .(pair_id, passage_id = passage_id_hi, hindi = 1L, agreed)],
              pairs[, .(pair_id, passage_id = passage_id_en, hindi = 0L, agreed)])
long <- merge(long, ratings, by = "passage_id")
long[, intensity_c := mean_rating - mean(mean_rating)]

sc <- fread(need[["scores"]], encoding = "UTF-8")
sys_rows <- rbindlist(lapply(names(CLASSIFIERS), function(m) {
  col <- CLASSIFIERS[[m]]
  if (!col %in% names(sc)) return(NULL)
  sc[model == m, .(passage_id, system = m, cue = 0L, score = get(col))]
}))
chat_file <- pp("results", "audit_chat_scores.csv")
if (file.exists(chat_file)) {
  ch <- fread(chat_file, encoding = "UTF-8")[!is.na(rating)]
  sys_rows <- rbind(sys_rows, ch[, .(score = mean(as.numeric(rating))), by = .(passage_id, system,
                                                                          cue = as.integer(cue == "india"))])
}
frame <- merge(long, sys_rows, by = "passage_id", allow.cartesian = TRUE)

if (opt$mode == "dry-run") {
  lines <- c("# Audit model frame (dry run: counts only, no score or rating)", "",
             sprintf("pairs: %d (agreed %d)", nrow(pairs), sum(pairs$agreed)),
             sprintf("passages in pairs: %d", nrow(long)),
             paste0("rows per system x cue: ", paste(frame[, .N, by = .(system, cue)][, sprintf("%s/cue%d=%d", system, cue, N)],
                                                     collapse = ", ")))
  dir.create(pp("results"), showWarnings = FALSE)
  writeLines(lines, pp("results", "audit_frame.md"))
  cat(lines, sep = "\n")
  quit(save = "no")
}

suppressPackageStartupMessages({
  library(lme4)
  library(lmerTest)
  library(glmnet)
})
set.seed(SEED)
frame[, score_z := (score - mean(score)) / sd(score), by = system]

fit_one <- function(d, sys, set) {
  has_cue <- uniqueN(d$cue) > 1
  form <- if (has_cue) score_z ~ intensity_c * hindi * cue + (1 | pair_id) else score_z ~ intensity_c * hindi + (1 | pair_id)
  m <- lmerTest::lmer(form, data = d)
  s <- summary(m)$coefficients
  ci <- suppressMessages(confint(m, method = "Wald", parm = "beta_"))
  data.table(system = sys, pairs = set, term = rownames(s), estimate = s[, "Estimate"], se = s[, "Std. Error"],
             df = s[, "df"], t = s[, "t value"], p = s[, "Pr(>|t|)"], ci_lo = ci[rownames(s), 1],
             ci_hi = ci[rownames(s), 2], n_pairs = uniqueN(d$pair_id), n_rows = nrow(d), cue_terms = has_cue,
             singular = isSingular(m), status = STATUS)
}
lm_out <- rbindlist(lapply(unique(frame$system), function(sys) {
  d <- frame[system == sys]
  rbind(fit_one(d, sys, "all"), if (nrow(d[agreed == 1]) && uniqueN(d[agreed == 1]$pair_id) > 2)
    fit_one(d[agreed == 1], sys, "agreed"))
}))
fwrite(lm_out, pp("results", "audit_lmer.csv"))
print(lm_out[term %in% c("hindi", "hindi:cue"), .(system, pairs, term, estimate, ci_lo, ci_hi, p)])

comps <- fread(need[["comps"]], encoding = "UTF-8")
comp_cols <- grep("^comp_", names(comps), value = TRUE)
stab <- rbindlist(lapply(unique(frame$system), function(sys) {
  d <- merge(frame[system == sys & cue == 0 & hindi == 1], comps[, c("passage_id", comp_cols), with = FALSE],
             by = "passage_id")
  d <- d[complete.cases(d[, ..comp_cols])]
  zi <- (frame[system == sys & cue == 0]$mean_rating)
  d[, error := score_z - (mean_rating - mean(zi)) / sd(zi)]
  X <- as.matrix(d[, ..comp_cols])
  keep <- apply(X, 2, function(v) sd(v) > 0)
  X <- X[, keep, drop = FALSE]
  if (nrow(X) < 10 || ncol(X) < 2) return(NULL)
  cv <- cv.glmnet(X, d$error, alpha = 1, standardize = TRUE, nfolds = min(10, nrow(X)))
  lam <- cv$lambda.1se
  sel <- matrix(0L, STAB_B, ncol(X), dimnames = list(NULL, colnames(X)))
  for (b in seq_len(STAB_B)) {
    i <- sample(nrow(X), floor(nrow(X) / 2))
    f <- glmnet(X[i, , drop = FALSE], d$error[i], alpha = 1, standardize = TRUE, lambda = lam)
    sel[b, ] <- as.integer(as.vector(coef(f))[-1] != 0)
  }
  freq <- colMeans(sel)
  q <- mean(rowSums(sel))
  full <- as.vector(coef(cv, s = "lambda.1se"))[-1]
  data.table(system = sys, component = sub("^comp_", "", colnames(X)), selection_freq = freq, full_data_coef = full,
             stable = freq >= STAB_PI & full < 0, lambda = lam, B = STAB_B, threshold = STAB_PI, mean_selected = q,
             pfer_bound = q^2 / ((2 * STAB_PI - 1) * ncol(X)), n_passages = nrow(X), status = STATUS)
}))
if (nrow(stab)) stab <- stab[order(system, -selection_freq)]
fwrite(stab, pp("results", "audit_stability.csv"))
print(stab[stable == TRUE])
write_session(opt, "audit")
