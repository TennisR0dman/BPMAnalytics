candidates <- c(
  "R/tempo_stats.R",
  "../R/tempo_stats.R",
  "../../R/tempo_stats.R"
)
present <- candidates[file.exists(candidates)]
if (!length(present)) {
  stop("Could not find R/tempo_stats.R from the working directory")
}
source(present[[1]])

testthat::test_that("fold_tempo uses the primary half-time window", {
  testthat::expect_equal(fold_tempo(140), 70)
  testthat::expect_equal(fold_tempo(70), 70)
  testthat::expect_equal(fold_tempo(100), 100)
  testthat::expect_equal(fold_tempo(160), 80)
  testthat::expect_equal(fold_tempo(50), 100)
  testthat::expect_equal(fold_tempo(280), 70)
  testthat::expect_equal(fold_tempo(0), NA_real_)
  testthat::expect_equal(fold_tempo(NA_real_), NA_real_)
})

testthat::test_that("Cohen's d is signed from the first sample and is zero when means match", {
  testthat::expect_equal(cohens_d(c(1, 2, 3), c(2, 3, 4)), -1)
  testthat::expect_equal(cohens_d(c(10, 12, 14), c(10, 12, 14)), 0)
})

testthat::test_that("Cliff's delta reaches the extremes and treats ties as neither win", {
  testthat::expect_equal(cliffs_delta(c(3, 4), c(1, 2)), 1)
  testthat::expect_equal(cliffs_delta(c(1, 2), c(3, 4)), -1)
  testthat::expect_equal(cliffs_delta(c(1, 2), c(1, 2)), 0)
})
