source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))),
                 "..", "common.R"))
MIN_EMO <- 5
opt <- parse_args()
guard(opt)
d <- read_inputs(opt)

cl <- d$cf[as_flag(is_finite) == 1, .(record_id, lang, name = as_flag(names_emotion), bad = as_flag(comp_FEEL_BAD))]
tx <- cl[, .(lang = lang[1], n_emo = sum(name | bad), n_named = sum(name)), by = record_id]
tx <- merge(tx, d$tf[, .(record_id, n_clauses)], by = "record_id")
n_dropped <- tx[n_emo < MIN_EMO, .N]
tx <- tx[n_emo >= MIN_EMO]
n <- nrow(tx)
tx[, `:=`(hindi = as.integer(lang == "hi"), log_clauses = log(n_clauses), share_raw = n_named / n_emo)]
tx[, naming_share := (share_raw * (n - 1) + 0.5) / n]

if (opt$mode == "dry-run") {
  describe_frame(tx, path(opt, "results", "p2_beta_frame.md"),
                 sprintf("P2 model frame (dry run, split = %s; %d texts dropped with < %d emotional clauses)",
                         opt$split, n_dropped, MIN_EMO),
                 c("hindi", "log_clauses", "lang"))
  quit(save = "no")
}

suppressPackageStartupMessages({
  library(betareg)
  library(sandwich)
  library(lmtest)
})
fits <- list(main = betareg(naming_share ~ hindi, data = tx, link = "logit"),
             sensitivity = betareg(naming_share ~ hindi + log_clauses, data = tx, link = "logit"))
out <- rbindlist(lapply(names(fits), function(nm) {
  f <- fits[[nm]]
  s <- summary(f)$coefficients$mean
  rob <- coeftest(f, vcov = sandwich(f))
  rob <- rob[rownames(rob) %in% rownames(s), , drop = FALSE]
  data.table(model = nm, term = rownames(s), estimate = s[, 1], se = s[, 2], z = s[, 3], p = s[, 4],
             se_robust = rob[rownames(s), 2], p_robust = rob[rownames(s), 4],
             phi = coef(f)[["(phi)"]], pseudo_r2 = f$pseudo.r.squared)
}))
out[, `:=`(split = opt$split, n_texts = n, n_dropped = n_dropped, min_emotional_clauses = MIN_EMO, status = STATUS)]
nd <- data.table(hindi = c(0, 1))
pred <- data.table(lang = c("en", "hi"), predicted_share = predict(fits$main, newdata = nd, type = "response"))
fwrite(out, path(opt, "results", "p2_beta.csv"))
fwrite(pred, path(opt, "results", "p2_beta_predicted.csv"))
print(out[term == "hindi"])
print(pred)
write_session(opt, "p2_beta")
