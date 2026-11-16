# Summary statistics and effect sizes for the tempo comparison.
# Mann-Whitney is the primary test because raw tempo is often skewed and
# can be two-humped when the estimator locks onto double-time.
# Welch's t-test is the parametric companion. It does not assume equal variance.

fold_tempo <- function(bpm, low = 70, high = 140) {
  sapply(bpm, function(tempo) {
    if (is.na(tempo) || !is.finite(tempo) || tempo <= 0) {
      return(NA_real_)
    }
    for (step in seq_len(6)) {
      if (tempo >= high) {
        tempo <- tempo / 2
      } else if (tempo < low) {
        tempo <- tempo * 2
      } else {
        break
      }
    }
    tempo
  })
}

cohens_d <- function(x, y) {
  x <- x[is.finite(x)]
  y <- y[is.finite(y)]
  nx <- length(x)
  ny <- length(y)
  pooled <- sqrt(((nx - 1) * stats::var(x) + (ny - 1) * stats::var(y)) / (nx + ny - 2))
  (mean(x) - mean(y)) / pooled
}

# Positive Cliff's delta: a random value from x tends to land above a random value from y.
cliffs_delta <- function(x, y) {
  x <- x[is.finite(x)]
  y <- y[is.finite(y)]
  comparison <- outer(x, y, `-`)
  (sum(comparison > 0) - sum(comparison < 0)) / (length(x) * length(y))
}

two_sample_tests <- function(x, y) {
  welch <- stats::t.test(x, y, var.equal = FALSE, alternative = "two.sided")
  mann <- stats::wilcox.test(
    x,
    y,
    exact = FALSE,
    correct = TRUE,
    alternative = "two.sided"
  )
  list(
    n_x = length(x),
    n_y = length(y),
    mean_x = mean(x),
    mean_y = mean(y),
    mean_diff = mean(x) - mean(y),
    median_x = stats::median(x),
    median_y = stats::median(y),
    median_diff = stats::median(x) - stats::median(y),
    welch_stat = unname(welch$statistic),
    welch_df = unname(welch$parameter),
    welch_p = unname(welch$p.value),
    cohens_d = cohens_d(x, y),
    mannwhitney_p = unname(mann$p.value),
    mannwhitney_u = unname(mann$statistic),
    cliffs_delta = cliffs_delta(x, y)
  )
}
