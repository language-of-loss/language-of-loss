suppressPackageStartupMessages({
  library(data.table)
  library(ggplot2)
  library(ggalluvial)
  library(showtext)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
arg <- function(name, default = NULL) {
  i <- match(name, args)
  if (is.na(i)) default else args[[i + 1]]
}
root <- arg("--root", normalizePath(file.path(dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE),
                                                                             value = TRUE)[1])), "..")))
out <- arg("--out", file.path(root, "figures", "final"))
only <- strsplit(arg("--only", "G2,G9"), ",")[[1]]
font_dir <- arg("--font-dir")
if (is.null(font_dir)) stop("--font-dir (matplotlib's fonts/ttf directory, for STIXGeneral) is required")
font_add("STIXGeneral", regular = file.path(font_dir, "STIXGeneral.ttf"), bold = file.path(font_dir, "STIXGeneralBol.ttf"),
         italic = file.path(font_dir, "STIXGeneralItalic.ttf"))
showtext_auto()
FAMILY <- "STIXGeneral"
BLUE <- "#0072B2"; ORANGE <- "#E69F00"; VERMILLION <- "#D55E00"; GREY <- "#999999"
INK <- "#1a1a1a"; MUTED <- "#5f5f5f"; RULE <- "#d9d9d9"
LANG_COL <- c(Hindi = BLUE, English = ORANGE)
LANG_SHAPE <- c(Hindi = 16, English = 15)
p <- function(...) file.path(root, ...)

theme_v2 <- function() {
  theme_minimal(base_family = FAMILY, base_size = 8.5) +
    theme(text = element_text(colour = INK), axis.text = element_text(colour = INK, size = 7.5),
          axis.line = element_line(colour = MUTED, linewidth = 0.3), axis.ticks = element_line(colour = MUTED,
                                                                                               linewidth = 0.25),
          panel.grid.major = element_line(colour = RULE, linewidth = 0.2), panel.grid.minor = element_blank(),
          strip.text = element_text(face = "bold", size = 9, hjust = 0), legend.position = "bottom",
          legend.title = element_blank(), plot.title = element_text(face = "bold", size = 9.5),
          plot.background = element_rect(fill = "white", colour = NA))
}

save_both <- function(plot, stem, width, height) {
  dir.create(out, showWarnings = FALSE, recursive = TRUE)
  showtext_opts(dpi = 72)
  pdf(file.path(out, paste0(stem, ".pdf")), width = width, height = height, useDingbats = FALSE)
  print(plot)
  invisible(dev.off())
  showtext_opts(dpi = 300)
  png(file.path(out, paste0(stem, ".png")), width = width, height = height, units = "in", res = 300, type = "quartz",
      bg = "white")
  print(plot)
  invisible(dev.off())
  cat("wrote", file.path(out, paste0(stem, ".{pdf,png}")), "\n")
}

g2 <- function() {
  split <- fread(p("data", "processed", "split.csv"))
  el <- fread(p("data", "processed", "eligibility.csv"), encoding = "UTF-8",
              select = c("clause_id", "lang", "marker_type", "decision"))[marker_type == "relational"]
  el[, record_id := sub("#.*$", "", clause_id)]
  el <- merge(el, split, by = "record_id")[split == "confirmatory"]
  outcome <- c(forced_relational = "forced", chosen_relational = "chosen",
               chosen_individual = "alternative\navailable,\nnot chosen")
  n <- el[decision %in% names(outcome), .N, by = .(lang, decision)]
  js <- fromJSON(p("results", "decompose_relational_confirmatory.json"))
  for (lg in c("hi", "en")) {
    want <- c(forced_relational = js[[paste0("forced_", lg)]], chosen_relational = js[[paste0("chosen_", lg)]],
              chosen_individual = js[[paste0("nominative_alt_", lg)]])
    got <- setNames(sapply(names(want), function(d) n[lang == lg & decision == d, sum(N)]), names(want))
    if (!identical(as.numeric(got), as.numeric(want))) stop("G2: eligibility counts differ from the decomposition (",
                                                             lg, "): ", paste(got, collapse = "/"), " vs ",
                                                             paste(want, collapse = "/"))
  }
  full <- CJ(lang = c("hi", "en"), decision = names(outcome))
  n <- merge(full, n, all.x = TRUE)[is.na(N), N := 0L]
  n[, language := factor(ifelse(lang == "hi", "Hindi", "English"), levels = c("Hindi", "English"))]
  outcome_levels <- unname(outcome)
  n[, outcome := factor(outcome[decision], levels = outcome_levels)]
  n <- n[N > 0]
  tot <- n[, .(total = sum(N)), by = language]
  n <- merge(n, tot, by = "language")
  gap <- 0.06 * max(tot$total)
  rows <- list()
  for (lg in levels(n$language)) {
    d <- n[language == lg][order(outcome)]
    src <- sprintf("relational\nsites\n%s", format(d$total[1], big.mark = ","))
    k <- nrow(d)
    real <- data.table(language = lg, alluvium = paste(lg, d$outcome), outcome = as.character(d$outcome), N = d$N,
                       src = src, dst = sprintf("%s\n%s", d$outcome, format(d$N, big.mark = ",")), real = TRUE)
    pads <- data.table(language = lg, alluvium = paste(lg, "pad", seq_len(k - 1)), outcome = NA_character_,
                       N = gap, src = ifelse(seq_len(k - 1) <= (k - 1) / 2, strrep(" ", 1), strrep(" ", 2)),
                       dst = strrep(" ", 2 + 5 * match(lg, levels(n$language)) + seq_len(k - 1)),
                       real = FALSE)
    order_dst <- c(rbind(real$dst, c(pads$dst[seq_len(k - 1)], NA)))
    order_dst <- order_dst[!is.na(order_dst)]
    rows[[lg]] <- list(dt = rbind(real, pads), dst = order_dst)
  }
  dt <- rbindlist(lapply(rows, `[[`, "dt"))
  srcs <- unique(dt$src[dt$real])
  lv <- unique(c(" ", srcs, "  ", unlist(lapply(rows, `[[`, "dst"))))
  long <- rbind(dt[, .(language, alluvium, outcome, N, real, axis = "sites", stratum = src)],
                dt[, .(language, alluvium, outcome, N, real, axis = "outcome", stratum = dst)])
  long[, axis := factor(axis, levels = c("sites", "outcome"))]
  long[, stratum := factor(stratum, levels = lv)]
  long[, language := factor(language, levels = c("Hindi", "English"))]
  long[, outcome := factor(outcome, levels = outcome_levels)]
  long[, flow_fill := ifelse(real, as.character(language), "pad")]
  long[, box := ifelse(real, "box", "pad")]
  plt <- ggplot(long, aes(x = axis, stratum = stratum, alluvium = alluvium, y = N)) +
    geom_flow(aes(fill = flow_fill, alpha = outcome), width = 0.3, colour = "transparent", linewidth = 0, knot.pos = 0.35) +
    geom_stratum(aes(fill = box, colour = box), width = 0.3, linewidth = 0.3) +
    geom_text(stat = "stratum", aes(label = after_stat(stratum)), family = FAMILY, size = 2.7, lineheight = 0.9,
              colour = INK) +
    facet_wrap(~language, nrow = 1) +
    scale_fill_manual(values = c(LANG_COL, pad = "transparent", box = "white"), guide = "none") +
    scale_colour_manual(values = c(pad = "transparent", box = INK), guide = "none") +
    scale_alpha_manual(values = c(0.95, 0.6, 0.25), drop = FALSE, na.value = 0, na.translate = FALSE,
                       guide = "none") +
    scale_x_discrete(labels = c("all relational sites", "outcome at the site"), expand = c(0.14, 0.14)) +
    scale_y_continuous(breaks = NULL, expand = c(0.01, 0)) +
    labs(x = NULL, y = NULL) +
    theme_v2() + theme(panel.grid.major = element_blank(), axis.line.y = element_blank(),
                       legend.position = "none")
  save_both(plt, "G2_sankey", 7.0, 4.2)
}

g9 <- function() {
  pairs <- fread(p("data", "processed", "audit_pairs.csv"), encoding = "UTF-8")
  ratings <- fread(p("data", "processed", "audit_ratings.csv"), encoding = "UTF-8")[, .(passage_id, mean_rating)]
  long <- rbind(pairs[, .(pair_id, passage_id = passage_id_hi, hindi = 1L)],
                pairs[, .(pair_id, passage_id = passage_id_en, hindi = 0L)])
  long <- merge(long, ratings, by = "passage_id")
  sc <- fread(p("data", "processed", "audit", "passage_scores.csv"), encoding = "UTF-8")
  cls <- rbind(sc[model == "xlm_emo", .(passage_id, system = "xlm_emo", cue = 0L, score = p_sadness)],
               sc[model == "muril_sent", .(passage_id, system = "muril_sent", cue = 0L, score = p_negative)])
  ch <- fread(p("results", "audit_chat_scores.csv"), encoding = "UTF-8")[!is.na(rating) & grepl("llama", system)]
  ch <- ch[, .(score = mean(as.numeric(rating))), by = .(passage_id, system, cue = as.integer(cue == "india"))]
  frame <- merge(long, rbind(cls, ch), by = "passage_id", allow.cartesian = TRUE)
  frame[, score_z := (score - mean(score)) / sd(score), by = system]
  frame <- frame[cue == 0L]
  label <- c(xlm_emo = "XLM-EMO (p sadness)", muril_sent = "MuRIL sentiment (p negative)")
  frame[, panel := ifelse(system %in% names(label), label[system],
                          "Llama 3.1 8B (rating 1-7)")]
  frame[, panel := factor(panel, levels = c(label, "Llama 3.1 8B (rating 1-7)"))]
  frame[, language := factor(ifelse(hindi == 1L, "Hindi", "English"), levels = c("Hindi", "English"))]
  plt <- ggplot(frame, aes(mean_rating, score_z, colour = language, fill = language, shape = language)) +
    geom_hline(yintercept = 0, colour = MUTED, linewidth = 0.3) +
    geom_point(position = position_jitter(width = 0.06, height = 0, seed = 1), size = 1.1, alpha = 0.7, stroke = 0) +
    geom_smooth(method = "lm", formula = y ~ x, se = TRUE, level = 0.95, linewidth = 0.7, alpha = 0.18) +
    facet_wrap(~panel, nrow = 1) +
    scale_colour_manual(values = LANG_COL) + scale_fill_manual(values = LANG_COL) +
    scale_shape_manual(values = LANG_SHAPE) +
    scale_x_continuous(breaks = 1:7, limits = c(0.8, 7.2)) +
    labs(x = "human-rated intensity (mean of two ratings, 1-7)", y = "system score (standardised)") +
    theme_v2()
  save_both(plt, "G9_audit_slopes", 7.2, 3.0)
}

if ("G2" %in% only) g2()
if ("G9" %in% only) g9()
