# Headline inference and charts for the top 100 tracks in each cohort.
# Run from the repository root, or run this file directly. Rscript sets the
# working directory to the repository root below.

args_all <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_all, value = TRUE)
if (length(file_arg)) {
  script_path <- normalizePath(sub("^--file=", "", file_arg[[1]]))
  setwd(normalizePath(file.path(dirname(script_path), "..")))
}

source("R/tempo_stats.R")
source("R/theme_bpm.R")

tracks <- utils::read.csv("data/processed/analysis_tracks.csv", stringsAsFactors = FALSE)
audit <- utils::read.csv("outputs/sql/06_afrobeat_label_audit.csv", stringsAsFactors = FALSE)
countries <- utils::read.csv("outputs/sql/05_country_tempo.csv", stringsAsFactors = FALSE)
lookup <- utils::read.csv("data/reference/african_primary_artists.csv", stringsAsFactors = FALSE)

folded <- fold_tempo(tracks$tempo_raw)
if (any(abs(folded - tracks$tempo_corrected) > 1e-4, na.rm = TRUE)) {
  stop("R fold_tempo does not match tempo_corrected on the analysis table")
}
folded_alt <- fold_tempo(tracks$tempo_raw, low = 80, high = 160)
if (any(abs(folded_alt - tracks$tempo_corrected_alt) > 1e-4, na.rm = TRUE)) {
  stop("R alternate fold does not match tempo_corrected_alt")
}

top <- tracks[tracks$is_top100 == 1, ]
africa <- top[top$cohort_id == "africa_popular", ]
hiphop <- top[top$cohort_id == "us_hiphop_genre", ]
if (nrow(africa) < 2 || nrow(hiphop) < 2) {
  stop("Each headline cohort needs at least two tracks")
}

cohort_block <- function(frame, eligible_n) {
  list(
    n_top = nrow(frame),
    n_eligible = eligible_n,
    popularity_min = min(frame$popularity),
    popularity_max = max(frame$popularity),
    tempo_raw_mean = mean(frame$tempo_raw),
    tempo_raw_median = stats::median(frame$tempo_raw),
    tempo_raw_sd = stats::sd(frame$tempo_raw),
    tempo_raw_iqr = unname(stats::quantile(frame$tempo_raw, 0.75) - stats::quantile(frame$tempo_raw, 0.25)),
    tempo_corrected_mean = mean(frame$tempo_corrected),
    tempo_corrected_median = stats::median(frame$tempo_corrected),
    tempo_corrected_sd = stats::sd(frame$tempo_corrected),
    share_octave_shifted = mean(frame$octave_shifted == 1),
    share_raw_ge_140 = mean(frame$tempo_raw >= 140)
  )
}

africa_eligible_n <- sum(tracks$cohort_id == "africa_popular")
hiphop_eligible_n <- sum(tracks$cohort_id == "us_hiphop_genre")

raw_tests <- two_sample_tests(africa$tempo_raw, hiphop$tempo_raw)
corrected_tests <- two_sample_tests(africa$tempo_corrected, hiphop$tempo_corrected)
alt_tests <- two_sample_tests(africa$tempo_corrected_alt, hiphop$tempo_corrected_alt)
eligible_africa <- tracks$tempo_raw[tracks$cohort_id == "africa_popular"]
eligible_hiphop <- tracks$tempo_raw[tracks$cohort_id == "us_hiphop_genre"]
eligible_tests <- two_sample_tests(eligible_africa, eligible_hiphop)

fmt1 <- function(x) sprintf("%.1f", x)
fmt2 <- function(x) sprintf("%.2f", x)
fmt_p <- function(p) if (p < 0.001) "< 0.001" else sprintf("%.3f", p)
fmt_pct <- function(x) sprintf("%.1f%%", 100 * x)

top_country <- countries[which.max(countries$n_tracks), ]

display <- list(
  africa_n_eligible = sprintf("Africa eligible tracks: %d", africa_eligible_n),
  hiphop_n_eligible = sprintf("Hip-hop eligible tracks: %d", hiphop_eligible_n),
  africa_n_top = sprintf("Africa top tracks: %d", nrow(africa)),
  hiphop_n_top = sprintf("Hip-hop top tracks: %d", nrow(hiphop)),
  africa_popularity = sprintf(
    "Africa top-100 popularity runs from %d to %d",
    min(africa$popularity),
    max(africa$popularity)
  ),
  hiphop_popularity = sprintf(
    "Hip-hop top-100 popularity runs from %d to %d",
    min(hiphop$popularity),
    max(hiphop$popularity)
  ),
  africa_raw = sprintf(
    "Africa mean raw tempo: %s BPM (sd %s)",
    fmt1(mean(africa$tempo_raw)),
    fmt1(stats::sd(africa$tempo_raw))
  ),
  hiphop_raw = sprintf(
    "Hip-hop mean raw tempo: %s BPM (sd %s)",
    fmt1(mean(hiphop$tempo_raw)),
    fmt1(stats::sd(hiphop$tempo_raw))
  ),
  africa_median_raw = sprintf("Africa median raw tempo: %s BPM", fmt1(stats::median(africa$tempo_raw))),
  hiphop_median_raw = sprintf("Hip-hop median raw tempo: %s BPM", fmt1(stats::median(hiphop$tempo_raw))),
  africa_iqr_raw = sprintf("Africa raw IQR: %s BPM", fmt1(stats::IQR(africa$tempo_raw))),
  hiphop_iqr_raw = sprintf("Hip-hop raw IQR: %s BPM", fmt1(stats::IQR(hiphop$tempo_raw))),
  median_gap_raw = sprintf(
    "Median raw gap (Africa minus hip-hop): %s BPM",
    fmt1(stats::median(africa$tempo_raw) - stats::median(hiphop$tempo_raw))
  ),
  mean_gap_raw = sprintf(
    "Mean raw gap (Africa minus hip-hop): %s BPM",
    fmt1(mean(africa$tempo_raw) - mean(hiphop$tempo_raw))
  ),
  welch_raw = sprintf(
    "Welch t (raw) = %s on %s df, p = %s",
    fmt2(raw_tests$welch_stat),
    fmt1(raw_tests$welch_df),
    fmt_p(raw_tests$welch_p)
  ),
  cohens_raw = sprintf("Cohen's d (raw) = %s", fmt2(raw_tests$cohens_d)),
  cliffs_raw = sprintf("Cliff's delta (raw) = %s", fmt2(raw_tests$cliffs_delta)),
  mann_raw = sprintf("Mann-Whitney p (raw) = %s", fmt_p(raw_tests$mannwhitney_p)),
  africa_median_corrected = sprintf(
    "Africa median corrected tempo: %s BPM",
    fmt1(stats::median(africa$tempo_corrected))
  ),
  hiphop_median_corrected = sprintf(
    "Hip-hop median corrected tempo: %s BPM",
    fmt1(stats::median(hiphop$tempo_corrected))
  ),
  africa_mean_corrected = sprintf(
    "Africa mean corrected tempo: %s BPM",
    fmt1(mean(africa$tempo_corrected))
  ),
  hiphop_mean_corrected = sprintf(
    "Hip-hop mean corrected tempo: %s BPM",
    fmt1(mean(hiphop$tempo_corrected))
  ),
  median_gap_corrected = sprintf(
    "Median corrected gap (Africa minus hip-hop): %s BPM",
    fmt1(stats::median(africa$tempo_corrected) - stats::median(hiphop$tempo_corrected))
  ),
  mean_gap_corrected = sprintf(
    "Mean corrected gap (Africa minus hip-hop): %s BPM",
    fmt1(mean(africa$tempo_corrected) - mean(hiphop$tempo_corrected))
  ),
  welch_corrected = sprintf(
    "Welch t (corrected) = %s on %s df, p = %s",
    fmt2(corrected_tests$welch_stat),
    fmt1(corrected_tests$welch_df),
    fmt_p(corrected_tests$welch_p)
  ),
  cohens_corrected = sprintf("Cohen's d (corrected) = %s", fmt2(corrected_tests$cohens_d)),
  cliffs_corrected = sprintf("Cliff's delta (corrected) = %s", fmt2(corrected_tests$cliffs_delta)),
  mann_corrected = sprintf("Mann-Whitney p (corrected) = %s", fmt_p(corrected_tests$mannwhitney_p)),
  africa_shift = sprintf(
    "Africa tracks with an octave shift: %s",
    fmt_pct(mean(africa$octave_shifted == 1))
  ),
  hiphop_shift = sprintf(
    "Hip-hop tracks with an octave shift: %s",
    fmt_pct(mean(hiphop$octave_shifted == 1))
  ),
  africa_ge_140 = sprintf(
    "Africa tracks at or above 140 BPM raw: %s",
    fmt_pct(mean(africa$tempo_raw >= 140))
  ),
  hiphop_ge_140 = sprintf(
    "Hip-hop tracks at or above 140 BPM raw: %s",
    fmt_pct(mean(hiphop$tempo_raw >= 140))
  ),
  alt_mann = sprintf(
    "Alternate window [80, 160) Mann-Whitney p = %s",
    fmt_p(alt_tests$mannwhitney_p)
  ),
  alt_cliffs = sprintf(
    "Alternate window Cliff's delta = %s",
    fmt2(alt_tests$cliffs_delta)
  ),
  eligible_mann = sprintf(
    "Eligible-set Mann-Whitney p (raw) = %s",
    fmt_p(eligible_tests$mannwhitney_p)
  ),
  eligible_cliffs = sprintf(
    "Eligible-set Cliff's delta (raw) = %s",
    fmt2(eligible_tests$cliffs_delta)
  ),
  audit = sprintf(
    "Afrobeat-label top 25 on the lookup: %d of %d",
    sum(audit$on_african_lookup == 1),
    nrow(audit)
  ),
  largest_country = sprintf(
    "%s accounts for %d of the African top 100",
    top_country$country,
    top_country$n_tracks
  ),
  lookup_size = sprintf("Artist lookup size: %d names", nrow(lookup))
)

results <- list(
  cohorts = list(
    africa_popular = cohort_block(africa, africa_eligible_n),
    us_hiphop_genre = cohort_block(hiphop, hiphop_eligible_n)
  ),
  tests = list(
    top100_raw = raw_tests,
    top100_corrected = corrected_tests,
    top100_corrected_alt = alt_tests,
    eligible_raw = eligible_tests
  ),
  audit = list(
    afrobeat_top25_n = nrow(audit),
    afrobeat_top25_on_lookup = sum(audit$on_african_lookup == 1)
  ),
  display = display
)

dir.create("outputs", showWarnings = FALSE)
jsonlite::write_json(
  results,
  "outputs/results.json",
  auto_unbox = TRUE,
  pretty = TRUE,
  digits = 8,
  null = "null"
)
writeLines(unlist(display, use.names = FALSE), "outputs/display_lines.txt")

top$cohort_name <- factor(top$cohort_name, levels = names(cohort_colours))
caption <- "Top 100 by Spotify popularity in each cohort. Source: maharshipandya/spotify-tracks-dataset, revision 635b034f."

medians_raw <- aggregate(tempo_raw ~ cohort_name, top, stats::median)
density_raw <- ggplot2::ggplot(top, ggplot2::aes(tempo_raw, fill = cohort_name, colour = cohort_name)) +
  ggplot2::geom_density(alpha = 0.42, linewidth = 1.05, adjust = 0.9) +
  ggplot2::geom_vline(
    data = medians_raw,
    ggplot2::aes(xintercept = tempo_raw, colour = cohort_name),
    linewidth = 0.7,
    linetype = "dashed",
    show.legend = FALSE
  ) +
  ggplot2::scale_fill_manual(values = cohort_colours) +
  ggplot2::scale_colour_manual(values = cohort_colours) +
  ggplot2::coord_cartesian(xlim = c(55, 210)) +
  ggplot2::labs(
    title = "Raw tempo sits in the same broad range",
    subtitle = "Dashed lines are medians. The axis is clipped for display; the statistics use every track.",
    x = "Spotify tempo (BPM)",
    y = "Density",
    caption = caption
  ) +
  theme_bpm()

medians_corrected <- aggregate(tempo_corrected ~ cohort_name, top, stats::median)
density_corrected <- ggplot2::ggplot(
  top,
  ggplot2::aes(tempo_corrected, fill = cohort_name, colour = cohort_name)
) +
  ggplot2::geom_density(alpha = 0.42, linewidth = 1.05, adjust = 0.9) +
  ggplot2::geom_vline(
    data = medians_corrected,
    ggplot2::aes(xintercept = tempo_corrected, colour = cohort_name),
    linewidth = 0.7,
    linetype = "dashed",
    show.legend = FALSE
  ) +
  ggplot2::scale_fill_manual(values = cohort_colours) +
  ggplot2::scale_colour_manual(values = cohort_colours) +
  ggplot2::coord_cartesian(xlim = c(65, 145)) +
  ggplot2::labs(
    title = "After the half-time fold, hip-hop's upper hump comes down",
    subtitle = "Tempos outside 70 to 140 BPM are halved or doubled until they fall inside that window.",
    x = "Corrected tempo (BPM)",
    y = "Density",
    caption = caption
  ) +
  theme_bpm()

band_levels <- c("Under 80", "80-99", "100-119", "120-139", "140-159", "160 and above")
band_frame <- expand.grid(
  cohort_name = levels(top$cohort_name),
  raw_band = band_levels,
  stringsAsFactors = FALSE
)
counted <- aggregate(track_id ~ cohort_name + raw_band, top, length)
names(counted)[3] <- "n_tracks"
band_frame <- merge(band_frame, counted, by = c("cohort_name", "raw_band"), all.x = TRUE)
band_frame$n_tracks[is.na(band_frame$n_tracks)] <- 0
band_frame$cohort_n <- ave(band_frame$n_tracks, band_frame$cohort_name, FUN = sum)
band_frame$share <- band_frame$n_tracks / band_frame$cohort_n
band_frame$raw_band <- factor(band_frame$raw_band, levels = band_levels)
band_frame$cohort_name <- factor(band_frame$cohort_name, levels = names(cohort_colours))

band_plot <- ggplot2::ggplot(
  band_frame,
  ggplot2::aes(raw_band, share, fill = cohort_name)
) +
  ggplot2::geom_col(position = ggplot2::position_dodge(width = 0.8), width = 0.72) +
  ggplot2::scale_y_continuous(labels = function(x) sprintf("%d%%", round(100 * x))) +
  ggplot2::scale_fill_manual(values = cohort_colours) +
  ggplot2::labs(
    title = "Hip-hop has a thicker fast tail before any correction",
    subtitle = "Share of the top 100 tracks in each raw tempo band.",
    x = "Raw tempo band (BPM)",
    y = "Share of cohort",
    caption = caption
  ) +
  theme_bpm()

pop_counted <- aggregate(popularity ~ cohort_name + raw_band, top, mean)
names(pop_counted)[3] <- "mean_popularity"
pop_frame <- merge(
  band_frame[band_frame$n_tracks > 0, c("cohort_name", "raw_band", "n_tracks")],
  pop_counted,
  by = c("cohort_name", "raw_band")
)
pop_frame$raw_band <- factor(pop_frame$raw_band, levels = band_levels)
pop_frame$cohort_name <- factor(pop_frame$cohort_name, levels = names(cohort_colours))

pop_plot <- ggplot2::ggplot(
  pop_frame,
  ggplot2::aes(raw_band, mean_popularity, fill = cohort_name)
) +
  ggplot2::geom_col(position = ggplot2::position_dodge(width = 0.8), width = 0.72) +
  ggplot2::scale_fill_manual(values = cohort_colours) +
  ggplot2::labs(
    title = "Popularity does not climb with tempo inside the top 100",
    subtitle = "Mean Spotify popularity by raw tempo band. Empty bands are omitted. The index is not a stream count.",
    x = "Raw tempo band (BPM)",
    y = "Mean popularity (0-100)",
    caption = caption
  ) +
  theme_bpm()

dir.create("outputs/figures", showWarnings = FALSE, recursive = TRUE)
save_bpm(density_raw, "outputs/figures/01_tempo_density_raw.png")
save_bpm(density_corrected, "outputs/figures/02_tempo_density_corrected.png")
save_bpm(band_plot, "outputs/figures/03_tempo_band_share.png")
save_bpm(pop_plot, "outputs/figures/04_popularity_by_band.png")

message("Wrote outputs/results.json and four figures")
