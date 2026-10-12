source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))),
                 "common.R"))
opt <- parse_args()
guard(opt)
d <- read_inputs(opt)

elig <- fread(path(opt, "data", "processed", "eligibility.csv"), encoding = "UTF-8")
forced_rel <- unique(elig[marker_type == "relational" & decision == "forced_relational", .(clause_id, rel_forced = 1L)])
refs <- fread(path(opt, "data", "processed", "referents.csv"), encoding = "UTF-8")[
  , .(clause_id, relational, rel_subject, rel_target, rel_entry, honorific_elder)]
cl <- merge(d$cf[as_flag(is_finite) == 1, .(clause_id, record_id, lang, formulaic = as_flag(flag_F6))], forced_rel,
            by = "clause_id", all.x = TRUE)
cl <- merge(cl, refs, by = "clause_id")
cl <- merge(cl, d$tf[, .(record_id, n_clauses)], by = "record_id")
cl <- merge(cl, d$meta[, intersect(c("record_id", "loss_type", "diaspora", "platform", "source_domain"), names(d$meta)),
                       with = FALSE],
            by = "record_id")
if (opt$covariates == "rival") {
  for (v in c("diaspora", "platform")) if (!v %in% names(cl)) stop("--covariates rival: text_meta.csv has no ", v)
  cl[, `:=`(diaspora = factor(diaspora), platform = factor(platform))]
}
loss_kept <- loss_type_kept(opt)
cl[, `:=`(relational = as_flag(relational), rel_subject = as_flag(rel_subject), rel_target = as_flag(rel_target),
          rel_entry = as_flag(rel_entry),
          hindi = as.integer(lang == "hi"),
          log_clauses = log(n_clauses),
          gf = as.integer(!is.na(rel_forced)), elder = as_flag(honorific_elder),
          loss_type = pool_loss_type(loss_type, loss_kept))]
cl[, loss_type := droplevels(loss_type)]

runs <- list(run1 = cl, run2 = cl[gf == 0], run2b = cl[gf == 0 & elder == 0], rF6 = cl[gf == 0 & formulaic == 0])
suffix <- paste0(if (opt$subset == "all") "" else paste0("_", opt$subset),
                 if (opt$covariates == "none") "" else paste0("_", opt$covariates))

if (opt$mode == "dry-run") {
  describe_frame(cl, path(opt, "results", "h1_glmm_frame.md"),
                 sprintf(paste("H1 model frame (dry run, split = %s, subset = %s, covariates = %s; run 2 drops %d",
                               "clauses with a forced_relational site; run 2b also drops %d honorific-elder clauses;",
                               "R-F6 drops %d closing-formula clauses from run 2; loss_type kept on the full corpus at",
                               ">= %d texts per language: %s, rest -> other)"),
                         opt$split, opt$subset, opt$covariates, sum(cl$gf), sum(cl$gf == 0 & cl$elder == 1),
                         sum(cl$gf == 0 & cl$formulaic == 1), LOSS_MIN_PER_LANG, paste(loss_kept, collapse = ", ")),
                 c("hindi", "log_clauses", "loss_type", "lang"))
  quit(save = "no")
}

suppressPackageStartupMessages({
  library(lme4)
  library(clubSandwich)
})
form <- relational ~ hindi + log_clauses + loss_type
if (opt$covariates == "rival") form <- update(form, . ~ . + diaspora + platform)

for (nm in names(runs)) {
  dat <- runs[[nm]]
  g <- glmer(update(form, . ~ . + (1 | record_id)), data = dat, family = binomial,
             control = glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 2e5)))
  s <- summary(g)$coefficients
  glmm <- data.table(term = rownames(s), estimate = s[, 1], se = s[, 2], stat = s[, 3], df = NA_real_,
                     p = s[, 4], estimator = "glmer (conditional, model-based SE)")
  ci <- suppressMessages(confint(g, method = "Wald", parm = "beta_"))
  glmm[, `:=`(ci_lo = ci[term, 1], ci_hi = ci[term, 2])]

  m <- glm(form, data = dat, family = binomial)
  ct <- coef_test(m, vcov = "CR2", cluster = dat$record_id, test = "Satterthwaite")
  ct <- as.data.frame(ct)
  cr2 <- data.table(term = ct$Coef, estimate = ct$beta, se = ct$SE, stat = ct$tstat, df = ct$df_Satt,
                    p = ct$p_Satt, estimator = "glm + CR2 cluster-robust (marginal)")
  cr2[, `:=`(ci_lo = estimate - qt(0.975, df) * se, ci_hi = estimate + qt(0.975, df) * se)]

  dom <- NULL
  if ("source_domain" %in% names(dat) && uniqueN(dat$source_domain) > 1) {
    gd <- glmer(update(form, . ~ . + (1 | record_id) + (1 | source_domain)), data = dat, family = binomial,
                control = glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 2e5)))
    sd <- summary(gd)$coefficients
    dom <- data.table(term = rownames(sd), estimate = sd[, 1], se = sd[, 2], stat = sd[, 3], df = NA_real_,
                      p = sd[, 4], estimator = "glmer + domain random intercept (conditional, model-based SE)")
    dom[, `:=`(ci_lo = estimate - qnorm(0.975) * se, ci_hi = estimate + qnorm(0.975) * se)]
  }

  perm_b <- as.integer(Sys.getenv("H1_PERM_B", "999"))
  b_obs <- coef(m)[["hindi"]]
  texts <- unique(dat[, .(record_id, hindi)])
  set.seed(20261009)
  b_perm <- vapply(seq_len(perm_b), function(i) {
    lab <- setNames(sample(texts$hindi), texts$record_id)
    pd <- copy(dat)[, hindi := lab[record_id]]
    coef(glm(form, data = pd, family = binomial))[["hindi"]]
  }, numeric(1))
  perm <- data.table(term = "hindi", estimate = b_obs, se = NA_real_, stat = NA_real_, df = NA_real_,
                     p = (1 + sum(abs(b_perm) >= abs(b_obs))) / (perm_b + 1), ci_lo = NA_real_, ci_hi = NA_real_,
                     estimator = sprintf("permutation over texts (glm coefficient, B = %d)", perm_b))

  out <- rbind(glmm, cr2, dom, perm)
  out[, `:=`(run = nm, split = opt$split, subset = opt$subset, n_clauses = nrow(dat), n_texts = uniqueN(dat$record_id),
             singular = isSingular(g), converged = is.null(g@optinfo$conv$lme4$messages),
             odds_ratio = exp(estimate), status = STATUS)]
  fwrite(out, path(opt, "results", paste0("h1_glmm_", nm, suffix, ".csv")))
  cat("\n==", nm, "(", nrow(dat), "clauses,", uniqueN(dat$record_id), "texts )\n")
  print(out[term == "hindi", .(estimator, estimate, se, p, odds_ratio)])
}
write_session(opt, "h1_glmm")
