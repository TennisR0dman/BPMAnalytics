# Dark theme for the tempo charts. Pink is the African cohort, cyan is hip-hop.

cohort_colours <- c(
  "African popular music" = "#FF4D8D",
  "US hip-hop (genre proxy)" = "#3DDCFF"
)

theme_bpm <- function() {
  ggplot2::theme_minimal(base_size = 13, base_family = "sans") +
    ggplot2::theme(
      plot.background = ggplot2::element_rect(fill = "#0B0F14", colour = NA),
      panel.background = ggplot2::element_rect(fill = "#0B0F14", colour = NA),
      panel.grid.major = ggplot2::element_line(colour = "#243140", linewidth = 0.35),
      panel.grid.minor = ggplot2::element_blank(),
      axis.text = ggplot2::element_text(colour = "#D7DEE7"),
      axis.title = ggplot2::element_text(colour = "#F4F7FB"),
      plot.title = ggplot2::element_text(colour = "#FFFFFF", face = "bold", size = 16),
      plot.subtitle = ggplot2::element_text(colour = "#9FB0C3", size = 11),
      plot.caption = ggplot2::element_text(colour = "#7D8B9A", size = 9, hjust = 0),
      legend.background = ggplot2::element_rect(fill = "#0B0F14", colour = NA),
      legend.key = ggplot2::element_rect(fill = "#0B0F14", colour = NA),
      legend.text = ggplot2::element_text(colour = "#D7DEE7"),
      legend.title = ggplot2::element_blank(),
      legend.position = "bottom"
    )
}

save_bpm <- function(plot, path) {
  ggplot2::ggsave(
    filename = path,
    plot = plot,
    width = 10,
    height = 6.2,
    dpi = 150,
    bg = "#0B0F14"
  )
}
