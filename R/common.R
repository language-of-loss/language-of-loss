suppressPackageStartupMessages({
  library(data.table)
})

parse_args <- function(args = commandArgs(trailingOnly = TRUE)) {
  opt <- list(mode = NA_character_, split = NA_character_, root = NA_character_, subset = "all", covariates = "none")
  i <- 1
  while (i <= length(args)) {
    a <- args[[i]]
    if (a %in% c("--dry-run", "--run")) {
      opt$mode <- sub("^--", "", a)
    } else if (a %in% c("--split", "--root", "--subset", "--covariates") && i < length(args)) {
      opt[[sub("^--", "", a)]] <- args[[i + 1]]
      i <- i + 1
    } else {
      stop("unknown argument: ", a,
           "  (use --dry-run or --run [--split dev|confirmatory|all] [--subset all|english_home] [--root DIR])")
    }
    i <- i + 1
  }
  if (is.na(opt$mode)) stop("say --dry-run (describe the frame) or --run (fit; needs agreement statistics)")
  if (is.na(opt$split)) opt$split <- if (opt$mode == "dry-run") "dev" else "confirmatory"
  if (!opt$split %in% c("dev", "confirmatory", "all")) stop("--split must be dev, confirmatory or all")
  if (!opt$subset %in% c("all", "english_home")) stop("--subset must be all or english_home")
  if (!opt$covariates %in% c("none", "rival")) stop("--covariates must be none or rival")
  if (opt$mode == "dry-run" && opt$split != "dev") {
    stop("--dry-run describes the dev split only; the confirmatory split is reachable only through --run, ",
         "behind the agreement guard")
  }
  if (is.na(opt$root)) {
    file_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
    here <- if (length(file_arg)) dirname(normalizePath(sub("^--file=", "", file_arg[1]))) else getwd()
    root <- here
    while (!file.exists(file.path(root, "R", "common.R")) && dirname(root) != root) root <- dirname(root)
    opt$root <- normalizePath(root)
  }
  opt
}

path <- function(opt, ...) file.path(opt$root, ...)

agreement_ok <- function(file) {
  if (!file.exists(file)) return(FALSE)
  a <- tryCatch(utils::read.csv(file, stringsAsFactors = FALSE), error = function(e) NULL)
  if (is.null(a) || !all(c("n_both_coded", "alpha_nominal") %in% names(a))) return(FALSE)
  if ("status" %in% names(a) && any(grepl("synthetic", a$status, ignore.case = TRUE))) return(FALSE)
  n <- suppressWarnings(as.numeric(a$n_both_coded))
  alpha <- suppressWarnings(as.numeric(a$alpha_nominal))
  any(!is.na(n) & n > 0 & is.finite(alpha))
}

guard <- function(opt) {
  if (opt$mode != "run") return(invisible(TRUE))
  agr <- path(opt, "results", "agreement", "agreement_summary_gold_sheet_v1.csv")
  if (!agreement_ok(agr)) {
    stop("refusing to fit: ", agr, " is missing or holds no agreement statistics (needs >= 1 field with ",
         "n_both_coded > 0 and a finite alpha_nominal). study protocol: no hypothesis-testing model before independent ",
         "human annotation and agreement statistics. Use --dry-run to check the model frame.")
  }
  if (opt$split == "dev") message("NOTE: fitting on the dev split: exploratory only, do not report as confirmatory")
  invisible(TRUE)
}

read_inputs <- function(opt) {
  pp <- function(f) path(opt, "data", "processed", f)
  for (f in c("text_features.csv", "clause_features.csv", "text_meta.csv", "split.csv")) {
    if (!file.exists(pp(f))) stop("missing input ", pp(f), " (run `make all`; split.csv comes from `make gold`)")
  }
  tf <- fread(pp("text_features.csv"), encoding = "UTF-8")
  cf <- fread(pp("clause_features.csv"), encoding = "UTF-8")
  meta <- fread(pp("text_meta.csv"), encoding = "UTF-8")
  split <- fread(pp("split.csv"), encoding = "UTF-8")[, .(record_id, split)]
  meta[, split := NULL]
  meta <- merge(meta, split, by = "record_id", all.x = TRUE)
  keep <- if (opt$split == "all") unique(meta$record_id) else meta[split == opt$split, record_id]
  keep <- intersect(keep, subset_records(opt, meta))
  if (opt$covariates == "rival" && opt$mode == "run") {
    if (!"diaspora_conf" %in% names(meta)) stop("--covariates rival: text_meta.csv has no diaspora_conf (run text_meta.py)")
    pre <- meta[record_id %in% keep & diaspora_conf != "human", .N]
    if (pre) stop("refusing --covariates rival --run: ", pre, " text(s) with a pre-filled, unconfirmed diaspora value ",
                  "(data/annotation/meta_review.csv)")
  }
  list(tf = tf[record_id %in% keep], cf = cf[record_id %in% keep], meta = meta[record_id %in% keep])
}

subset_records <- function(opt, meta) {
  if (opt$subset == "all") return(unique(meta$record_id))
  for (col in c("home_language_statement", "meta_review_status")) {
    if (!col %in% names(meta)) stop("--subset english_home: text_meta.csv has no ", col, " column (run text_meta.py)")
  }
  en <- meta[lang == "en" & home_language_statement == "en"]
  if (!nrow(en)) stop("--subset english_home: no English text has home_language_statement = en in text_meta.csv; ",
                      "output 4 cannot be estimated on this corpus as specified")
  if (opt$mode == "run" && nrow(en[meta_review_status != "human_confirmed"])) {
    stop("refusing --subset english_home --run: ", nrow(en[meta_review_status != "human_confirmed"]),
         " English text(s) have a pre-filled, unconfirmed home_language_statement (data/annotation/meta_review.csv)")
  }
  c(meta[lang == "hi", record_id], en$record_id)
}

LOSS_TYPES <- c("parent", "grandparent", "sibling", "spouse", "child", "friend", "other")
LOSS_MIN_PER_LANG <- 5

loss_type_kept <- function(opt) {
  m <- fread(path(opt, "data", "processed", "text_meta.csv"), encoding = "UTF-8")[lang %in% c("hi", "en")]
  n <- dcast(m[, .N, by = .(loss_type, lang)], loss_type ~ lang, value.var = "N", fill = 0L)
  for (l in c("hi", "en")) if (!l %in% names(n)) n[, (l) := 0L]
  kept <- n[loss_type %in% setdiff(LOSS_TYPES, "other") & hi >= LOSS_MIN_PER_LANG & en >= LOSS_MIN_PER_LANG,
            loss_type]
  kept <- intersect(LOSS_TYPES, kept)
  if (!"parent" %in% kept) stop("loss_type rule: 'parent' (reference level) has < ", LOSS_MIN_PER_LANG,
                                " texts in a language on the full corpus")
  kept
}

pool_loss_type <- function(x, kept) {
  factor(ifelse(x %in% kept, x, "other"), levels = c(kept, "other"))
}

as_flag <- function(x) {
  if (is.logical(x)) return(as.integer(!is.na(x) & x))
  if (is.numeric(x)) return(as.integer(!is.na(x) & x > 0))
  as.integer(tolower(as.character(x)) %in% c("true", "1", "yes", "y"))
}

describe_frame <- function(df, outfile, title, vars) {
  lines <- c(paste0("# ", title), "", paste("rows:", nrow(df)), "")
  for (v in vars) {
    x <- df[[v]]
    if (is.numeric(x)) {
      lines <- c(lines, sprintf("%s: mean %.4f, sd %.4f, min %.4f, max %.4f, NA %d", v, mean(x, na.rm = TRUE),
                                sd(x, na.rm = TRUE), min(x, na.rm = TRUE), max(x, na.rm = TRUE), sum(is.na(x))))
    } else {
      tab <- table(x, useNA = "ifany")
      lines <- c(lines, paste0(v, ": ", paste(names(tab), tab, sep = "=", collapse = ", ")))
    }
  }
  dir.create(dirname(outfile), showWarnings = FALSE, recursive = TRUE)
  writeLines(lines, outfile)
  cat(lines, sep = "\n")
}

write_session <- function(opt, name) {
  f <- path(opt, "results", paste0(name, "_sessioninfo.txt"))
  writeLines(capture.output(sessionInfo()), f)
}

STATUS <- "machine-provisional features (lexicon matcher / rule-based eligibility); no human-validated labels"
