# Tempo comparison for the current-chart snapshot, set next to the
# Spotify-dataset results already written to outputs/results.json.

args_all <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_all, value = TRUE)
if (length(file_arg)) {
  script_path <- normalizePath(sub("^--file=", "", file_arg[[1]]))
  setwd(normalizePath(file.path(dirname(script_path), "..")))
}

source("R/tempo_stats.R")
source("R/theme_bpm.R")

charts <- utils::read.csv("data/current/chart_analysis.csv", stringsAsFactors = FALSE)
original <- jsonlite::fromJSON("outputs/results.json", simplifyVector = FALSE)
coverage <- jsonlite::fromJSON("data/current/coverage.json", simplifyVector = FALSE)

folded <- fold_tempo(charts$tempo_raw)
if (any(abs(folded - charts$tempo_corrected) > 1e-4, na.rm = TRUE)) {
  stop("R fold does not match tempo_corrected on the current-chart table")
}

africa <- charts[charts$cohort_id == "africa_charts", ]
hiphop <- charts[charts$cohort_id == "us_rb_hiphop_chart", ]
if (nrow(africa) < 2 || nrow(hiphop) < 2) {
  stop("Each current-chart cohort needs at least two measured tempos")
}

raw_tests <- two_sample_tests(africa$tempo_raw, hiphop$tempo_raw)
corrected_tests <- two_sample_tests(africa$tempo_corrected, hiphop$tempo_corrected)
alt_tests <- two_sample_tests(africa$tempo_corrected_alt, hiphop$tempo_corrected_alt)

both <- charts[!is.na(charts$deezer_bpm) & charts$deezer_bpm > 0, ]
agreement <- list(n_both = nrow(both))
if (nrow(both) >= 3) {
  deezer_folded <- fold_tempo(both$deezer_bpm)
  librosa_folded <- fold_tempo(both$librosa_bpm)
  ratio <- both$librosa_bpm / both$deezer_bpm
  octave <- abs(log(ratio) / log(2))
  octave <- pmin(octave %% 1, 1 - (octave %% 1))
  agreement <- list(
    n_both = nrow(both),
    median_abs_diff_raw = stats::median(abs(both$librosa_bpm - both$deezer_bpm)),
    median_abs_diff_folded = stats::median(abs(librosa_folded - deezer_folded)),
    pearson_folded = unname(stats::cor(librosa_folded, deezer_folded)),
    share_within_5_bpm_folded = mean(abs(librosa_folded - deezer_folded) <= 5),
    share_within_octave_tenth = mean(octave <= 0.1)
  )
}

fmt1 <- function(x) sprintf("%.1f", x)
fmt2 <- function(x) sprintf("%.2f", x)
fmt_p <- function(p) if (p < 0.001) "< 0.001" else sprintf("%.3f", p)
fmt_pct <- function(x) sprintf("%.1f%%", 100 * x)

block <- function(frame) {
  list(
    n = nrow(frame),
    tempo_raw_median = stats::median(frame$tempo_raw),
    tempo_raw_mean = mean(frame$tempo_raw),
    tempo_raw_sd = stats::sd(frame$tempo_raw),
    tempo_corrected_median = stats::median(frame$tempo_corrected),
    tempo_corrected_mean = mean(frame$tempo_corrected),
    share_octave_shifted = mean(frame$octave_shifted == 1),
    share_raw_ge_140 = mean(frame$tempo_raw >= 140)
  )
}

africa_cov <- coverage$cohorts$africa_charts
hiphop_cov <- coverage$cohorts$us_rb_hiphop_chart

display <- list(
  africa_chart_n = sprintf("Current Africa charts measured: %d of %d", africa_cov$librosa_measured, africa_cov$chart_rows),
  hiphop_chart_n = sprintf("Current US chart measured: %d of %d", hiphop_cov$librosa_measured, hiphop_cov$chart_rows),
  africa_chart_coverage = sprintf("Current Africa chart coverage: %s", fmt_pct(africa_cov$coverage_rate)),
  hiphop_chart_coverage = sprintf("Current US chart coverage: %s", fmt_pct(hiphop_cov$coverage_rate)),
  africa_chart_median_raw = sprintf("Current Africa median librosa tempo: %s BPM", fmt1(stats::median(africa$tempo_raw))),
  hiphop_chart_median_raw = sprintf("Current US chart median librosa tempo: %s BPM", fmt1(stats::median(hiphop$tempo_raw))),
  africa_chart_mean_raw = sprintf(
    "Current Africa mean librosa tempo: %s BPM (sd %s)",
    fmt1(mean(africa$tempo_raw)),
    fmt1(stats::sd(africa$tempo_raw))
  ),
  hiphop_chart_mean_raw = sprintf(
    "Current US chart mean librosa tempo: %s BPM (sd %s)",
    fmt1(mean(hiphop$tempo_raw)),
    fmt1(stats::sd(hiphop$tempo_raw))
  ),
  chart_median_gap_raw = sprintf(
    "Current median raw gap (Africa charts minus US chart): %s BPM",
    fmt1(stats::median(africa$tempo_raw) - stats::median(hiphop$tempo_raw))
  ),
  chart_welch_raw = sprintf(
    "Current Welch t (raw) = %s on %s df, p = %s",
    fmt2(raw_tests$welch_stat),
    fmt1(raw_tests$welch_df),
    fmt_p(raw_tests$welch_p)
  ),
  chart_cohens_raw = sprintf("Current Cohen's d (raw) = %s", fmt2(raw_tests$cohens_d)),
  chart_cliffs_raw = sprintf("Current Cliff's delta (raw) = %s", fmt2(raw_tests$cliffs_delta)),
  chart_mann_raw = sprintf("Current Mann-Whitney p (raw) = %s", fmt_p(raw_tests$mannwhitney_p)),
  africa_chart_median_corrected = sprintf(
    "Current Africa median corrected tempo: %s BPM",
    fmt1(stats::median(africa$tempo_corrected))
  ),
  hiphop_chart_median_corrected = sprintf(
    "Current US chart median corrected tempo: %s BPM",
    fmt1(stats::median(hiphop$tempo_corrected))
  ),
  chart_median_gap_corrected = sprintf(
    "Current median corrected gap (Africa charts minus US chart): %s BPM",
    fmt1(stats::median(africa$tempo_corrected) - stats::median(hiphop$tempo_corrected))
  ),
  chart_welch_corrected = sprintf(
    "Current Welch t (corrected) = %s on %s df, p = %s",
    fmt2(corrected_tests$welch_stat),
    fmt1(corrected_tests$welch_df),
    fmt_p(corrected_tests$welch_p)
  ),
  chart_cohens_corrected = sprintf("Current Cohen's d (corrected) = %s", fmt2(corrected_tests$cohens_d)),
  chart_cliffs_corrected = sprintf("Current Cliff's delta (corrected) = %s", fmt2(corrected_tests$cliffs_delta)),
  chart_mann_corrected = sprintf("Current Mann-Whitney p (corrected) = %s", fmt_p(corrected_tests$mannwhitney_p)),
  chart_alt_mann = sprintf(
    "Current alternate window [80, 160) Mann-Whitney p = %s",
    fmt_p(alt_tests$mannwhitney_p)
  ),
  chart_alt_cliffs = sprintf("Current alternate window Cliff's delta = %s", fmt2(alt_tests$cliffs_delta))
)

display$deezer_nonzero <- sprintf(
  "Deezer BPM was nonzero on %d of %d measured tracks",
  agreement$n_both,
  nrow(charts)
)

if (!is.null(agreement$median_abs_diff_folded)) {
  display$deezer_n <- sprintf("Deezer BPM was set on %d measured tracks", agreement$n_both)
  display$deezer_median_gap <- sprintf(
    "Median absolute gap, librosa vs Deezer, after the 70-140 fold: %s BPM",
    fmt1(agreement$median_abs_diff_folded)
  )
  display$deezer_within_5 <- sprintf(
    "Share within 5 BPM after the fold: %s",
    fmt_pct(agreement$share_within_5_bpm_folded)
  )
  display$deezer_pearson <- sprintf(
    "Pearson correlation after the fold: %s",
    fmt2(agreement$pearson_folded)
  )
}

dataset_africa <- original$cohorts$africa_popular
dataset_hiphop <- original$cohorts$us_hiphop_genre
chart_africa <- block(africa)
chart_hiphop <- block(hiphop)

results <- list(
  coverage = coverage,
  cohorts = list(
    africa_charts = chart_africa,
    us_rb_hiphop_chart = chart_hiphop
  ),
  tests = list(
    raw = raw_tests,
    corrected = corrected_tests,
    corrected_alt = alt_tests
  ),
  agreement = agreement,
  side_by_side = list(
    dataset_africa_median_raw = dataset_africa$tempo_raw_median,
    dataset_hiphop_median_raw = dataset_hiphop$tempo_raw_median,
    charts_africa_median_raw = chart_africa$tempo_raw_median,
    charts_hiphop_median_raw = chart_hiphop$tempo_raw_median,
    dataset_africa_median_corrected = dataset_africa$tempo_corrected_median,
    dataset_hiphop_median_corrected = dataset_hiphop$tempo_corrected_median,
    charts_africa_median_corrected = chart_africa$tempo_corrected_median,
    charts_hiphop_median_corrected = chart_hiphop$tempo_corrected_median
  ),
  display = display
)

jsonlite::write_json(
  results,
  "outputs/current_results.json",
  auto_unbox = TRUE,
  pretty = TRUE,
  digits = 8,
  null = "null"
)
writeLines(unlist(display, use.names = FALSE), "outputs/current_display_lines.txt")

compare <- data.frame(
  group = c(
    "Dataset, African popular music",
    "Dataset, US hip-hop genre proxy",
    "Charts, Nigeria and South Africa",
    "Charts, Billboard Hot R&B/Hip-Hop"
  ),
  median_raw = c(
    dataset_africa$tempo_raw_median,
    dataset_hiphop$tempo_raw_median,
    chart_africa$tempo_raw_median,
    chart_hiphop$tempo_raw_median
  ),
  median_corrected = c(
    dataset_africa$tempo_corrected_median,
    dataset_hiphop$tempo_corrected_median,
    chart_africa$tempo_corrected_median,
    chart_hiphop$tempo_corrected_median
  ),
  stringsAsFactors = FALSE
)
long <- rbind(
  data.frame(group = compare$group, bpm = compare$median_raw, measure = "Median raw", stringsAsFactors = FALSE),
  data.frame(group = compare$group, bpm = compare$median_corrected, measure = "Median folded to 70-140", stringsAsFactors = FALSE)
)
long$group <- factor(long$group, levels = unique(compare$group))
long$measure <- factor(long$measure, levels = c("Median raw", "Median folded to 70-140"))

plot <- ggplot2::ggplot(long, ggplot2::aes(group, bpm, fill = measure)) +
  ggplot2::geom_col(position = ggplot2::position_dodge(width = 0.72), width = 0.66) +
  ggplot2::scale_fill_manual(values = c("Median raw" = "#FF4D8D", "Median folded to 70-140" = "#3DDCFF")) +
  ggplot2::coord_flip() +
  ggplot2::labs(
    title = "Dataset medians and current-chart medians",
    subtitle = "Chart tempos are librosa estimates on 30-second previews. The fold uses the 70 to 140 BPM window.",
    x = NULL,
    y = "BPM",
    caption = "Fetched 2026-11-16. Kworb NG 2026-11-14, ZA 2026-11-13. Billboard week of November 14, 2026."
  ) +
  theme_bpm()

dir.create("outputs/figures", showWarnings = FALSE, recursive = TRUE)
save_bpm(plot, "outputs/figures/05_dataset_vs_current_charts.png")
message("Wrote outputs/current_results.json")
